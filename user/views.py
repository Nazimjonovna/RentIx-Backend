import requests
import base64
import binascii
import boto3
from rest_framework.decorators import action
from rest_framework import generics
from django.shortcuts import redirect
from django.apps import AppConfig
from rest_framework import viewsets, permissions, parsers
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import CreateAPIView
from rest_framework.parsers import MultiPartParser, FileUploadParser, FormParser, JSONParser
from django.db.models import Sum
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from random import randint
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
import pytz
from .utils.carsutils import is_within_work_hours
from django.utils import timezone
import datetime as d
from django.conf import settings
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.authentication import JWTAuthentication
from datetime import timedelta
from django.utils.dateparse import parse_datetime
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from django.utils.translation import gettext_lazy as _
from .click_auth import click_authorization
from .status import *
from rest_framework.decorators import action

from .models import (
    ChekInOut, Filial, Filial, User, Company, Manager, CarImage, UserImage, Car, Order, ValidatedCode, Verification, Rate,
    ChatMessage, Chat, Notification, CompanyWorkDay, CarRate, CompanySubscription, Payment,
    BotNotification, CashbackTransaction, Transaction,Discount, 
    ChekInOut, ImagesCheckOut, ImagesCheckIn, Viloyatlar
)
from .serializers import (
    AvailableCarTimeFilterSerializer, CarImageSerializer, CheckInOutSerializer, FilialSerializer, FilialSerializer, PhoneSerializer, SMSCodeSerializer, 
    ValidateSerializer, RegisterSerializer, OrderPageSerializer, UserProfileSerializer,
    CarSerializer, CreateAdminSerializer, ManagerSerializer,
    RateSerializer, ChatMessageSerializer, ChatSerializer, NotificationSerializer,
    OrderSerializer, CompanyWorkDaySerializer, UserTokenRequestSerializer,
    CarRateSerializer,  PaymentSerializer,
    CompanySubscriptionSerializer, LoginSerializer, ManagerCRUDSerializer,
    BotNotificationSerializer, AvailableCarModelFilterSerializer,
    AvailableCarCostFilterSerializer, CashbackTransactionSerializer,ClickUzSerializer,
    OrderStatusSerializer,BlockUserSerializer,DiscountSerializer,
    CheckInOutSerializer, ImagesCheckOutSerializer, ImagesCheckInSerializer,
    FilialSerializer, ViloyatlarSerializer,CarModelPortfolioSerializer,
    UploadURLResponseSerializer,UploadURLRequestSerializer, 
)
from .utils.logger import logged
from drf_yasg import openapi
from user.exceptions import MethodNotFound, PermissionDenied, PerformTransactionDoesNotExist
from user.methods.check_transaction import CheckTransaction
from user.methods.cancel_transaction import CancelTransaction
from user.methods.create_transaction import CreateTransaction
from user.methods.perform_transaction import PerformTransaction
from user.methods.check_perform_transaction import CheckPerformTransaction
from .permission import HasActiveSubscription, IsCashbackOwner

# ============== SWAGGER HEADER (barcha metodlar uchun) ==============
TRANSLATION_HEADER = openapi.Parameter(
    'Accept-Language',
    openapi.IN_HEADER,
    description="Til tanlash (uz, ru, en)",
    type=openapi.TYPE_STRING,
    default='uz',
    enum=['uz', 'ru', 'en']
)


def get_bearer_token(request):
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.split(" ", 1)[1]
    return None


def get_token_payload(request):
    token = get_bearer_token(request)
    if not token:
        return {}

    try:
        access = AccessToken(token)
        return access.payload
    except Exception:
        return {}


def get_auth_role(request):
    payload = get_token_payload(request)

    role = payload.get("role")
    if role:
        return str(role).lower()

    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        role = getattr(user, "role", None)
        if role:
            return str(role).lower()

    return None


def get_auth_company(request):
    payload = get_token_payload(request)
    role = get_auth_role(request)

    if role == "admin":
        company_id = payload.get("company_id")
        if company_id:
            return Company.objects.filter(id=company_id).first()

    if role == "manager":
        manager_id = payload.get("manager_id")
        manager = Manager.objects.filter(id=manager_id).select_related("company").first()
        return manager.company if manager else None

    return None


def get_auth_manager(request):
    payload = get_token_payload(request)
    manager_id = payload.get("manager_id")
    if manager_id:
        return Manager.objects.filter(id=manager_id).select_related("company", "filial").first()
    return None


def is_superadmin_or_admin(request):
    return get_auth_role(request) in ["superadmin", "admin"]


def is_admin_or_manager(request):
    return get_auth_role(request) in ["admin", "manager"]

utc = pytz.timezone(settings.TIME_ZONE)
min = 1
def send_sms(phone_number, step_reset=None, change_phone=None):
    try:
        verify_code = randint(1111, 9999)
        try:
            obj = Verification.objects.get(phone=phone_number)
        except Verification.DoesNotExist:
            obj = Verification(phone=phone_number, verify_code=verify_code)
            obj.step_reset=step_reset 
            obj.step_change_phone=change_phone
            obj.save()
            context = {'phone_number': str(obj.phone), 'verify_code': obj.verify_code,
                       'lifetime': _(f"{min} minutes")}
            return context
        time_now = d.datetime.now(utc)
        diff = time_now - obj.created
        three_minute = d.timedelta(minutes=min)
        if diff <= three_minute:
            time_left = str(three_minute - diff)
            return {'message': _(f"Try again in {time_left[3:4]} minute {time_left[5:7]} seconds")}
        obj.delete()
        obj = Verification(phone=phone_number)
        obj.verify_code=verify_code 
        obj.step_reset=step_reset
        obj.step_change_phone=change_phone
        obj.save()
        context = {'phone_number': str(obj.phone), 'verify_code': obj.verify_code, 'lifetime': _(f"{min} minutes")}
        return context
    except Exception as e:
        print(f"\n[ERROR] error in send_sms <<<{e}>>>\n")


class PhoneView(APIView):
    queryset = User.objects.all()
    serializer_class = PhoneSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=PhoneSerializer, tags = ['Register'])
    def post(self, request, *args, **kwargs):
        phone_number = str(request.data.get("phone"))
        if phone_number.isdigit() and len(phone_number)>8:
            user = User.objects.filter(phone__iexact=phone_number)
            if user.exists():
                return Response({
                    "status": False,
                    "detail": "Bu raqam avval registerdan otgan."
                })
            else:
                code = send_sms(phone_number)
                if 'verify_code' in code:
                    code = str(code['verify_code'])
                    try:
                        validate = ValidatedCode.objects.get(phone=phone_number)
                        if validate.validated:
                            validate.code = code
                            validate.validated= False
                            validate.save()
                        
                    except ValidatedCode.DoesNotExist as e:
                        phon = ValidatedCode.objects.filter(phone__iexact=phone_number)
                        print("expect")
                        if not phon.exists():
                            ValidatedCode.objects.create(phone=phone_number, code=code, validated=False)
                        else:
                            Response({"phone": "mavjud"})

                return Response({
                    "status": True,
                    "detail": "SMS xabarnoma jo'natildi",
                    "code":code 
                })
        else:
            if len(phone_number)<8:
                return Response({"detail":"Telefon raqamingizni kod bilan kiriting!"})
            else:    
                return Response({
                    "status": False,
                    "detail": "Telefon raqamni kiriting ."
                })


    def send_code(phone, code):
        if phone:
            code = randint(999, 9999)
            print(code)
            return code
        else:
            return False


class CodeView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=SMSCodeSerializer, tags = ['Register'])
    def post(self, request):
        phone_number = request.data.get('phone', True)
        code_send = request.data.get('code', True)
        if not phone_number and code_send:
            return Response({
                    'status': False,
                    'detail': 'codeni va phone ni kiriting'
                })

        try:
            verify = ValidatedCode.objects.get(phone=phone_number, validated=False)
            if verify.code == code_send:
                    verify.count += 1
                    verify.validated = True
                    verify.save()

                    return Response({
                        'status': True,
                        'detail': "code to'g'ri"
                        })
            else:
                return Response({
                   'status': False,
                   'error': "codeni to'g'ri kiriting"})
            
        except ValidatedCode.DoesNotExist as e:
            return Response({
               'error': "code aktiv emas yoki mavjud emas, boshqa code oling"
            })

        


class ValidatedcodeView(APIView):
    @swagger_auto_schema(tags=['Register'])
    def post(self, request, *args, **kwargs):
        phone = request.data.get('phone', False)
        code_sent = request.data.get('code', False)

        if phone and code_sent:
            old = ValidatedCode.objects.filter(phone__iexact=phone)
            if old.exists():
                old = old.first()
                code = old.code
                if str(code_sent) == str(code):
                    old.validated = True
                    old.save()   
                    return Response({
                        'status': True,
                        'detail': "code to'g'ri"
                        })
                else:
                    return Response({
                        'status': False,
                        'detail': "code noto'g'ri"
                        })
            else:
                return Response({
                    'status': False,
                    'detail': "code aktiv emas yoki mavjud emas, boshqa code oling"
                    })
            

class RegisterView(APIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    parser_class = [MultiPartParser]

    @swagger_auto_schema(tags=['Register'], request_body=RegisterSerializer)
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        phone = serializer.validated_data.get('phone')
        code = serializer.validated_data.get('code')
        full_name = serializer.validated_data.get('full_name')
        tg_nick = serializer.validated_data.get('tg_nick')
        telegram_id = serializer.validated_data.get('telegram_id')
        # ✅ Telefon raqamni normalize qilamiz (bo‘shliq, + belgini olib tashlaymiz)
        phone = str(phone).strip().replace(' ', '').replace('+', '')

        # ✅ Telegram nick tekshiruvi
        if tg_nick and not tg_nick.startswith('@'):
            return Response({
                "status": False,
                "detail": _("Telegram nick '@' bilan boshlanishi kerak.")
            }, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Telefon raqami SMS orqali tasdiqlanganmi?
        verify = ValidatedCode.objects.filter(phone__iexact=phone, validated=True)
        print("✅ ValidatedCode check:", verify)
        if not verify.exists():
            return Response({
                "status": False,
                "detail": _("Telefon raqami SMS orqali tasdiqlanmagan.")
            }, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Agar foydalanuvchi allaqachon mavjud bo‘lsa
        if User.objects.filter(phone=phone).exists():
            return Response({
                "status": False,
                "detail": _("Bu telefon raqam avval ro'yhatdan o'tgan.")
            }, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Foydalanuvchini yaratamiz
        try:
            user_obj = User.objects.create_user(
                phone=phone,
                full_name=full_name,
                tg_nick=tg_nick,
                code=code,
                telegram_id = telegram_id,
                is_phone_verified=True
            )

            # ✅ JWT tokenlar yaratamiz
            access_token = AccessToken.for_user(user_obj)
            refresh_token = RefreshToken.for_user(user_obj)

            return Response({
                "status": True,
                "message": _("Muvafaqqiyatli ro'yhatdan o'tdingiz."),
                "user": {
                    "phone": user_obj.phone,
                    "full_name": user_obj.full_name,
                    "tg_nick": user_obj.tg_nick,
                },
                "access": str(access_token),
                "refresh": str(refresh_token),
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"❌ Register error: {e}")
            return Response({
                "status": False,
                "detail": _("So'rovingizni bajarishda xatolik yuz berdi."),
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfilView(APIView):
    parser_classes = [MultiPartParser, FileUploadParser]
    
    @swagger_auto_schema(tags = ["User"])
    def get(self, request, pk, *args, **kwargs):
        #user get ni qoshdim
        try:
            user = User.objects.get(id=pk)
            serializer = UserProfileSerializer(user)
            return Response({
                "user": serializer.data,
                "status": status.HTTP_200_OK
            })
        except User.DoesNotExist:
            return Response({
                "Message": "Bunday user topilmadi",
                "status": status.HTTP_404_NOT_FOUND
            })

    @swagger_auto_schema(tags = ["User"])
    def delete(self, request, pk, *args, **kwargs):
        user = User.objects.filter(id = pk)
        if user.exists():
            user.delete()
            return Response({
                "Message":"User muvafaqiyatli o'chirildi",
                "status":status.HTTP_200_OK
            })
        else:
            return Response({
                "Message":"Bunday user topilmadi",
                "status":status.HTTP_404_NOT_FOUND
            })

    @swagger_auto_schema(request_body=UserProfileSerializer, tags = ["User"])     
    def patch(self, request, pk, *args, **kwargs):
        user = User.objects.get(id = pk)
        if user:
            serializer = UserProfileSerializer(instance = user, data = request.data, partial = True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "Message":"User muvafaqiyatli o'zgartirildi",
                    "data":serializer.data,
                    "status":status.HTTP_200_OK
                })
            else:
                return Response({
                    "Message":"Bizga topshirgan ma'lumotlaringiz yetarli emas",
                    "error":serializer.errors,
                    "status":status.HTTP_408_REQUEST_TIMEOUT
                })
        else:
            return Response({
                "Message":"Bunday user topilmadi",
                "status":status.HTTP_404_NOT_FOUND
            })
        

class UsersAllGetView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(tags=["User"])
    def get(self, request, *args, **kwargs):
        if not is_superadmin_or_admin(request):
            return Response({
                "Message": "Sizga bu ma'lumotlar yetarli emas",
                "status": status.HTTP_403_FORBIDDEN
            })
        users = User.objects.all()
        serializer = RegisterSerializer(users, many=True)
        data = serializer.data
        for i, user_obj in enumerate(users):
            data[i]["id"] = user_obj.id
        return Response({
            "users": data,
            "status": status.HTTP_200_OK
        })



class OrderPageView(APIView): # user va company uchun alohida qilishim kerak
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FileUploadParser]

    @swagger_auto_schema(request_body=OrderPageSerializer, tags = ["Order"])
    def post(self, request, *args, **kwargs):
        user = request.user
        if user.is_blocked:
            return Response({
                "detail": "Siz bloklanganingiz sababli buyurtmani o'zgartira olmaysiz."
            }, status=status.HTTP_403_FORBIDDEN)
        serializer = OrderPageSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "Message":"Buyurtma muvafaqiyatli yaratildi",
                "data": serializer.data,
                "status": status.HTTP_200_OK
            })
        else:
            return Response({
                "Message":"Bizga topshirgan ma'lumotlaringiz yetarli emas",
                "error": serializer.errors,
                "status": status.HTTP_408_REQUEST_TIMEOUT
            })


class OrderCreateView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=OrderSerializer, tags=["Order"])
    def post(self, request):
        user = request.user
        if user.is_blocked:
            return Response(
                {"detail": "Siz bloklangansiz."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = OrderSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(
            {
                "message": "Buyurtma muvaffaqiyatli yaratildi",
                "data": OrderSerializer(order).data
            },
            status=status.HTTP_201_CREATED
        )


class GetOwnAllOrderView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=["Order"])
    def get(self, request, pk):
        user = get_object_or_404(User, id=pk)
        orders = Order.objects.filter(user=user)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetCompanyAllOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(tags=["Order"])
    def get(self, request, pk):
        company = get_object_or_404(Company, id=pk)
        orders = Order.objects.filter(company=company)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        

class OrderChangeView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, pk):
        return get_object_or_404(Order, id=pk)

    @swagger_auto_schema(tags=["Order"])
    def get(self, request, pk):
        order = self.get_object(pk)
        serializer = OrderSerializer(order)
        return Response(serializer.data)


    @swagger_auto_schema(request_body=OrderSerializer, tags=["Order"])
    def patch(self, request, pk):
        if request.user.is_blocked:
            return Response(
                {"detail": "Siz bloklangansiz"},
                status=status.HTTP_403_FORBIDDEN
            )
        order = self.get_object(pk)
        serializer = OrderSerializer(
            order,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "message": "Order muvaffaqiyatli o'zgartirildi",
                "data": serializer.data
            }
        )


    @swagger_auto_schema(tags=["Order"])
    def delete(self, request, pk):
        if request.user.is_blocked:
            return Response(
                {"detail": "Siz bloklangansiz"},
                status=status.HTTP_403_FORBIDDEN
            )
        order = self.get_object(pk)
        order.delete()
        return Response(
            {"message": "Buyurtma o'chirildi"},
            status=status.HTTP_204_NO_CONTENT
        )

import uuid
class GenerateUploadURL(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Rasm yuklash",
        manual_parameters=[
            openapi.Parameter(
                "file",
                openapi.IN_FORM,
                description="Upload image",
                type=openapi.TYPE_FILE,
                required=True,
            )
        ],
        tags=["Upload"]
    )
    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "File required"}, status=400)
        ext = file.name.split(".")[-1]
        unique_name = f"{uuid.uuid4()}.{ext}"
        file_key = f"car_images/{unique_name}"
        s3 = boto3.client(
            "s3",
            region_name=settings.AWS_S3_REGION_NAME,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        s3.upload_fileobj(
            file,
            settings.AWS_STORAGE_BUCKET_NAME,
            file_key,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": file.content_type
            }
        )
        file_url = f"{settings.AWS_S3_ENDPOINT_URL}/{settings.AWS_STORAGE_BUCKET_NAME}/{file_key}"
        return Response({
            "file_url": file_url
        }, status=status.HTTP_200_OK)


class CarCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        tags=["Car"],
        request_body=CarSerializer,
        manual_parameters=[TRANSLATION_HEADER]
    )
    def post(self, request, *args, **kwargs):
        """Yangi mashina qo'shish"""
        if not is_superadmin_or_admin(request):
            return Response({
                "message": "Sizda bunday ruxsat yo'q",
                'status': status.HTTP_403_FORBIDDEN
            })
        # Fayl nomlarini olish
        car_image_logo = request.FILES.get('car_image_logo')
        car_image_portfolio = request.FILES.get('car_image_portfolio')
        tex_pasport = request.FILES.get('tex_pasport')
        # Fayllar uchun URL olish
        file_urls = {}
        if car_image_logo:
            file_urls['car_image_logo'] = self.get_presigned_url(car_image_logo.name)
        if car_image_portfolio:
            file_urls['car_image_portfolio'] = self.get_presigned_url(car_image_portfolio.name)
        if tex_pasport:
            file_urls['tex_pasport'] = self.get_presigned_url(tex_pasport.name)
        # Serializerdan foydalanish
        serializer = CarSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            car = serializer.save()
            # Fayl URL'larini saqlash
            if 'car_image_logo' in file_urls:
                car.car_image_logo = file_urls['car_image_logo']['file_url']
            if 'car_image_portfolio' in file_urls:
                car.car_image_portfolio = file_urls['car_image_portfolio']['file_url']
            if 'tex_pasport' in file_urls:
                car.tex_pasport = file_urls['tex_pasport']['file_url']
            # Fayllarni saqlash
            car.save()
            return Response({
                "Message": "Mashina muvafaqiyatli ravishda qo'shildi",
                "data": serializer.data,
                "status": status.HTTP_201_CREATED
            })
        else:
            return Response({
                'error': serializer.errors,
                "message": "Bizga topshirgan ma'lumotlaringiz yetarli emas",
                'status': status.HTTP_400_BAD_REQUEST
            })

    def get_presigned_url(self, file_name):
        """Presigned URL yaratish"""
        session = boto3.session.Session()
        client = session.client(
            "s3",
            region_name=settings.AWS_S3_REGION_NAME,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        file_key = f"car_images/{file_name}"
        url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": file_key,
                "ACL": "public-read"
            },
            ExpiresIn=3600  # 1 soatlik URL
        )
        return {
            "upload_url": url,
            "file_url": f"{settings.MEDIA_URL}{file_key}"
        }


class GetAllCarView(APIView):
    permission_classes = [AllowAny, ]
    @swagger_auto_schema(
        tags=["Car"],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def get(self, request, *args, **kwargs):
        """Barcha mashinalar"""
        cars = Car.objects.all()
        # MUHIM: context qo'shish
        serializer = CarSerializer(cars, many=True, context={'request': request})
        return Response({
            "cars": serializer.data,
            "status": status.HTTP_200_OK
        })


class CarCRUDView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FileUploadParser]

    @swagger_auto_schema(
        tags=["Car"],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def get(self, request, pk, *args, **kwargs):
        """Bitta mashina"""
        if not is_superadmin_or_admin(request):
            return Response({
                "Message": "Sizda bunday ruxsat yo'q",
                "status": status.HTTP_403_FORBIDDEN
            })
        
        car = Car.objects.filter(id=pk).first()
        if not car:
            return Response({
                "Message": "Bunday mashina topilmadi",
                "status": status.HTTP_404_NOT_FOUND
            })
        
        # MUHIM: context qo'shish
        serializer = CarSerializer(car, context={'request': request})
        return Response({
            "car": serializer.data,
            "status": status.HTTP_200_OK
        })

    @swagger_auto_schema(
        request_body=CarSerializer,
        tags=["Car"],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def patch(self, request, pk, *args, **kwargs):
        """Mashinani yangilash"""
        if not is_superadmin_or_admin(request):
            return Response({
                "Message": "Sizda bunday ruxsat yo'q",
                "status": status.HTTP_403_FORBIDDEN
            })
        
        car = Car.objects.filter(id=pk).first()
        if not car:
            return Response({
                "Message": "Bunday mashina topilmadi",
                "status": status.HTTP_404_NOT_FOUND
            })
        
        # MUHIM: context qo'shish
        serializer = CarSerializer(
            car, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "Message": "Mashina muvafaqiyatli o'zgartirildi",
                "data": serializer.data,
                "status": status.HTTP_200_OK
            })
        else:
            return Response({
                "Message": "Bizga topshirgan ma'lumotlaringiz yetarli emas",
                "error": serializer.errors,
                "status": status.HTTP_400_BAD_REQUEST
            })

    @swagger_auto_schema(tags=["Car"])
    def delete(self, request, pk, *args, **kwargs):
        """Mashinani o'chirish"""
        if not is_superadmin_or_admin(request):
            return Response({
                "Message": "Sizda bunday ruxsat yo'q",
                "status": status.HTTP_403_FORBIDDEN
            })
        car = Car.objects.filter(id=pk).first()
        if not car:
            return Response({
                "Message": "Bunday mashina topilmadi",
                "status": status.HTTP_404_NOT_FOUND
            })
        car.delete()
        return Response({
            "Message": "Mashina muvafaqiyatli o'chirildi",
            "status": status.HTTP_200_OK
        })



class AvailableCarsAPIView(APIView):

    @swagger_auto_schema(request_body=AvailableCarTimeFilterSerializer, tag = ['Filtercars'])
    def post(self, request):
        serializer = AvailableCarTimeFilterSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)

        start_time = serializer.validated_data["start_time"]
        end_time = serializer.validated_data["end_time"]
        busy_car_ids = Order.objects.filter(
            start_time__lt=end_time,
            end_time__gt=start_time
        ).values_list("car_id", flat=True)
        cars = Car.objects.exclude(id__in=busy_car_ids)
        return Response({
            "count": cars.count(),
            "cars": CarSerializer(cars, many=True).data
        })


class AvailableCarModelFilterView(APIView):
    
    @swagger_auto_schema(request_body=AvailableCarModelFilterSerializer, tag = ["Filtercars"])
    def post(self, request):
        serializer = AvailableCarModelFilterSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        car_model = serializer.validated_data["car_model"]
        cars = Car.objects.filter(car_model=car_model)
        return Response({
            "count": cars.count(),
            "cars": CarSerializer(cars, many=True).data
        })


class CarCostFilterAPIView(APIView):
    """
    Mashinalarni faqat cost_day_tash bo‘yicha filter qiladi
    """
    def get(self, request):
        serializer = AvailableCarCostFilterSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        min_price = serializer.validated_data.get("min_price")
        max_price = serializer.validated_data.get("max_price")
        cars = Car.objects.all()
        if min_price is not None:
            cars = cars.filter(cost_day_tash__gte=min_price)
        if max_price is not None:
            cars = cars.filter(cost_day_tash__lte=max_price)
        return Response({
            "count": cars.count(),
            "results": CarSerializer(cars, many=True).data
        }, status=status.HTTP_200_OK)


class CashbackTransactionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated,]

    def list(self, request):
        user = request.user
        total_earned = user.CashbackTransaction.filter(type="earn").aggregate(total=Sum("amount"))['total'] or 0
        total_spent = user.CashbackTransaction.filter(type="spend").aggregate(total=Sum("amount"))['total'] or 0
        available = total_earned - total_spent
        serializer = CashbackTransactionSerializer({
            "total_earned": total_earned,
            "total_spent": total_spent,
            "available": available
        })
        return Response(serializer.data)


# ============== COMPANY ADMIN VIEWS ==============
class CreateAdminView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FileUploadParser]

    @swagger_auto_schema(
        request_body=CreateAdminSerializer,
        tags=["Company (Admin Crate)"],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def post(self, request):
        """Yangi kompaniya yaratish"""
        if not is_superadmin_or_admin(request):
            return Response({"detail": "Sizga bunday ruxsat yo'q."}, status=403)
        # MUHIM: context qo'shish
        serializer = CreateAdminSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


class AdminCRUDView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FileUploadParser]

    @swagger_auto_schema(
        tags=["Company (Admin CRUD)"],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def get(self, request, pk=None):
        """Barcha kompaniyalar yoki bitta kompaniya"""
        if not is_superadmin_or_admin(request):
            return Response({"detail": "Sizga bunday ruxsat yo'q."}, status=403)

        if pk:
            company = Company.objects.filter(id=pk).first()
            if not company:
                return Response({"detail": "Bunday kompaniya mavjud emas."}, status=404)
            # MUHIM: context qo'shish
            serializer = CreateAdminSerializer(company, context={'request': request})
        else:
            companies = Company.objects.all()
            # MUHIM: context qo'shish
            serializer = CreateAdminSerializer(companies, many=True, context={'request': request})
        
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=CreateAdminSerializer,
        tags=["Company (Admin CRUD)"],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def patch(self, request, pk):
        """Kompaniyani yangilash"""
        if not is_superadmin_or_admin(request):
            return Response({"detail": "Sizga bunday ruxsat yo'q."}, status=403)
        company = Company.objects.filter(id=pk).first()
        if not company:
            return Response({"detail": "Bunday kompaniya mavjud emas."}, status=404)
        # MUHIM: context qo'shish
        serializer = CreateAdminSerializer(
            company, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @swagger_auto_schema(tags=["Company (Admin CRUD)"])
    def delete(self, request, pk):
        """Kompaniyani o'chirish"""
        if not is_superadmin_or_admin(request):
            return Response({"detail": "Sizga bunday ruxsat yo'q."}, status=403)
        company = Company.objects.filter(id=pk).first()
        if not company:
            return Response({"detail": "Bunday kompaniya mavjud emas."}, status=404)
        company.delete()
        return Response({"detail": "Kompaniya o'chirildi."}, status=200)
    

# ============== COMPANY WORK DAY VIEWS ==============
class CompanyWorkView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=CompanyWorkDaySerializer,
        tags=["WorkDay"],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def post(self, request, company_id=None):
        role = get_auth_role(request)

        if role not in ["superadmin", "admin"]:
            return Response({"detail": "Ruxsat yo'q."}, status=403)

        if role == "superadmin":
            company = Company.objects.filter(id=company_id).first()
        else:
            company = get_auth_company(request)

        if not company:
            return Response({"detail": "Kompaniya topilmadi."}, status=404)

        serializer = CompanyWorkDaySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(company=company)
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)


class GetFilialWorkdays(APIView):
    permission_classess = [IsAuthenticated]

    @swagger_auto_schema(tags=["WorkDay"],manual_parameters=[TRANSLATION_HEADER])
    def get(self, request, pk, *args, **kwargs):
        filial = Filial.objects.filter(id = pk).first()
        if filial:
            workdays = CompanyWorkDay.objects.filter(filial = filial).all()
            serializer = CompanyWorkDaySerializer(workdays, many = True)
            return Response({
                "data":serializer.data,
                "status": status.HTTP_200_OK
            })
        else:
            return Response({
                "data":"Bunday filial yoq",
                "status":status.HTTP_404_NOT_FOUND
            })


class CompanyWorkDayCRUDView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["WorkDay"],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def get(self, request, company_id=None, pk=None):
        role = get_auth_role(request)

        if role == "superadmin":
            if pk:
                obj = CompanyWorkDay.objects.filter(id=pk).first()
                if not obj:
                    return Response({"detail": "Topilmadi"}, status=404)
                serializer = CompanyWorkDaySerializer(obj, context={'request': request})
            elif company_id:
                days = CompanyWorkDay.objects.filter(company_id=company_id)
                serializer = CompanyWorkDaySerializer(days, many=True, context={'request': request})
            else:
                days = CompanyWorkDay.objects.all()
                serializer = CompanyWorkDaySerializer(days, many=True, context={'request': request})

        elif role == "admin":
            company = get_auth_company(request)
            if not company:
                return Response({"detail": "Sizda kompaniya yo'q."}, status=403)

            if pk:
                obj = CompanyWorkDay.objects.filter(id=pk, company=company).first()
                if not obj:
                    return Response({"detail": "Topilmadi"}, status=404)
                serializer = CompanyWorkDaySerializer(obj, context={'request': request})
            else:
                days = CompanyWorkDay.objects.filter(company=company)
                serializer = CompanyWorkDaySerializer(days, many=True, context={'request': request})

        else:
            return Response({"detail": "Ruxsat yo'q."}, status=403)

        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=CompanyWorkDaySerializer,
        tags=["WorkDay"],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def patch(self, request, pk):
        role = get_auth_role(request)

        workday = CompanyWorkDay.objects.filter(id=pk).first()
        if not workday:
            return Response({"detail": "Topilmadi."}, status=404)

        if role == "admin":
            company = get_auth_company(request)
            if not company or workday.company_id != company.id:
                return Response({"detail": "Ruxsat yo'q."}, status=403)

        elif role != "superadmin":
            return Response({"detail": "Ruxsat yo'q."}, status=403)

        serializer = CompanyWorkDaySerializer(
            workday,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=400)

    @swagger_auto_schema(tags=["WorkDay"])
    def delete(self, request, pk):
        role = get_auth_role(request)

        workday = CompanyWorkDay.objects.filter(id=pk).first()
        if not workday:
            return Response({"detail": "Topilmadi."}, status=404)

        if role == "admin":
            company = get_auth_company(request)
            if not company or workday.company_id != company.id:
                return Response({"detail": "Ruxsat yo'q."}, status=403)

        elif role != "superadmin":
            return Response({"detail": "Ruxsat yo'q."}, status=403)

        workday.delete()
        return Response({"detail": "O'chirildi."}, status=200)



# manager yaratish ko'rilishi kk va rate ing sistem qo'shilishi kk sharhlar ham

# ============== MANAGER VIEWS ==============
class CreateManagerView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FileUploadParser]

    @swagger_auto_schema(
        request_body=ManagerSerializer,
        tags=["Manager"],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def post(self, request, *args, **kwargs):
        """Yangi manager yaratish"""
        if not is_superadmin_or_admin(request):
            return Response({
                "Message": "Sizga bunday ruxsat yo'q",
                "status": status.HTTP_403_FORBIDDEN
            })
        # MUHIM: context qo'shish
        serializer = ManagerSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                "Message": "Manager muvaffaqiyatli yaratildi",
                "data": serializer.data,
                "status": status.HTTP_201_CREATED
            })
        else:
            return Response({
                'error': serializer.errors,
                "message": "Bizga topshirgan ma'lumotlaringiz yetarli emas",
                'status': status.HTTP_400_BAD_REQUEST
            })


class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=LoginSerializer,
        tags=["Login"]
    )
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        login = serializer.validated_data["login"]
        password = serializer.validated_data["password"]
        manager = Manager.objects.filter(
            login=login,
            password=password
        ).select_related("company", "filial").first()
        if manager:
            refresh = RefreshToken()
            refresh["role"] = "manager"
            refresh["manager_id"] = manager.id
            refresh["company_id"] = manager.company.id
            refresh["filial_id"] = manager.filial.id
            access = refresh.access_token
            access["role"] = "manager"
            access["manager_id"] = manager.id
            access["company_id"] = manager.company.id
            access["filial_id"] = manager.filial.id
            return Response({
                "message": "Login muvaffaqiyatli (Manager)",
                "access": str(access),
                "refresh": str(refresh),
                "user": {
                    "id": manager.id,
                    "username": manager.username,
                    "role": "manager",
                    "company_id": manager.company.id,
                    "filial_id": manager.filial.id,
                }
            }, status=status.HTTP_200_OK)

        company = Company.objects.filter(
            login=login,
            password=password
        ).first()
        if company:
            refresh = RefreshToken()
            refresh["role"] = "admin"
            refresh["company_id"] = company.id
            access = refresh.access_token
            access["role"] = "admin"
            access["company_id"] = company.id
            return Response({
                "message": "Login muvaffaqiyatli (Admin)",
                "access": str(access),
                "refresh": str(refresh),
                "user": {
                    "id": company.id,
                    "name": company.name,
                    "role": "admin",
                    "company_id": company.id,
                }
            }, status=status.HTTP_200_OK)
        return Response({
            "message": "Login yoki parol noto'g'ri"
        }, status=status.HTTP_401_UNAUTHORIZED)


class ManagerCRUDView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FileUploadParser]

    @swagger_auto_schema(
        tags=["Manager"],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def get(self, request, pk, *args, **kwargs):
        """Bitta manager"""
        if not is_superadmin_or_admin(request):
            return Response({
                "Message": "Sizga bunday ruxsat yo'q",
                "status": status.HTTP_403_FORBIDDEN
            })
        
        try:
            manager = Manager.objects.get(id=pk)
        except Manager.DoesNotExist:
            return Response({
                "Message": "Bunday Manager mavjud emas",
                "status": status.HTTP_404_NOT_FOUND
            })
        # MUHIM: context qo'shish
        serializer = ManagerCRUDSerializer(manager, context={'request': request})
        return Response({
            "Manager": serializer.data,
            "status": status.HTTP_200_OK
        })

    @swagger_auto_schema(tags=["Manager"])
    def delete(self, request, pk, *args, **kwargs):
        """Manager o'chirish"""
        if not is_superadmin_or_admin(request):
            return Response({
                "Message": "Sizga bunday ruxsat yo'q",
                "status": status.HTTP_403_FORBIDDEN
            })
        
        try:
            manager = Manager.objects.get(id=pk)
            manager.delete()
            return Response({
                "Message": "Manager muvafaqiyatli o'chirildi",
                "status": status.HTTP_200_OK
            })
        except Manager.DoesNotExist:
            return Response({
                "Message": "Bunday Manager mavjud emas",
                "status": status.HTTP_404_NOT_FOUND
            })

    @swagger_auto_schema(
        request_body=ManagerCRUDSerializer,
        tags=["Manager"],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def patch(self, request, pk, *args, **kwargs):
        """Manager yangilash"""
        if not is_superadmin_or_admin(request):
            return Response({
                "Message": "Sizga bunday ruxsat yo'q",
                "status": status.HTTP_403_FORBIDDEN
            })
        
        try:
            manager = Manager.objects.get(id=pk)
        except Manager.DoesNotExist:
            return Response({
                "Message": "Bunday Manager mavjud emas",
                "status": status.HTTP_404_NOT_FOUND
            })
        
        # MUHIM: context qo'shish
        serializer = ManagerCRUDSerializer(
            manager, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "Message": "Manager muvafaqiyatli o'zgartirildi",
                "status": status.HTTP_200_OK
            })
        else:
            return Response({
                'error': serializer.errors,
                "message": "Bizga topshirgan ma'lumotlaringiz yetarli emas",
                'status': status.HTTP_400_BAD_REQUEST
            })

class GetAllManagerView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Manager"],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def get(self, request, *args, **kwargs):
        """Barcha managerlar"""
        if not is_superadmin_or_admin(request):
            return Response({
                "Message": "Sizga bunday ruxsat yo'q",
                "status": status.HTTP_403_FORBIDDEN
            })
        
        managers = Manager.objects.all()
        # MUHIM: context qo'shish
        serializer = ManagerCRUDSerializer(managers, many=True, context={'request': request})
        return Response({
            "Managers": serializer.data,
            "status": status.HTTP_200_OK
        })

#Order + Car ga get kk yana get_all kkmi?

class GoogleRegisterView(APIView):
    """
    Step 1: Google OAuth boshlash
    URL: /api/auth/google/start/
    """
    def get(self, request):
        google_auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={settings.GOOGLE_CLIENT_ID}&"
            f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
            "response_type=code&"
            "scope=email profile"
        )
        return redirect(google_auth_url)


class GoogleCallbackView(APIView):
    """
    Step 2: Google callback — foydalanuvchini ro‘yxatdan o‘tkazadi va JWT qaytaradi
    URL: /api/auth/google/callback/
    """

    def get(self, request):
        code = request.GET.get("code")
        if not code:
            return Response({"error": "Google code not provided"}, status=status.HTTP_400_BAD_REQUEST)

        # --- Access Token olish ---
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        access_token = token_json.get("access_token")

        if not access_token:
            return Response({"error": "Failed to retrieve Google access token"}, status=400)

        # --- Google user ma'lumotlarini olish ---
        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        ).json()

        email = user_info.get("email")
        full_name = user_info.get("name")
        google_id = user_info.get("id")
        picture = user_info.get("picture")

        if not email:
            return Response({"error": "Email not provided by Google"}, status=400)

        # --- Foydalanuvchini topish yoki yaratish ---
        username = f"google_{google_id}"
        dummy_phone = f"+999{google_id[-9:]}"  # Google ID asosida "fake" telefon raqam
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "full_name": full_name,
                "phone": dummy_phone,
                "is_phone_verified": True,
            }
        )

        # --- JWT token yaratish ---
        refresh = RefreshToken.for_user(user)
        tokens = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

        # --- Javob qaytarish ---
        return Response({
            "message": "User registered via Google" if created else "User logged in via Google",
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": email,
                "picture": picture,
            },
            "tokens": tokens
        }, status=status.HTTP_200_OK)
    

class CreateRateView(APIView):
    permission_class = [IsAuthenticated]

    @swagger_auto_schema(request_body=RateSerializer, tags = ['Rate'])
    def post(self, request, *args, **kwargs):
        user = request.user
        serializer = RateSerializer(data = request.data, user = user)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "Message":"Komentariyangiz uchun raxmat",
                "data":serializer.data,
                "status":status.HTTP_201_CREATED
            })
        else:
            return Response({
                "Message":"Bergan ma'lumotlaringiz yetarli emas",
                "status":status.HTTP_203_NON_AUTHORITATIVE_INFORMATION
            })
        
    @swagger_auto_schema(tags = "Rate")
    def get_all(self, request, *args, **kwargs):
        user = request.user
        comments = Rate.objects.filter(user = user)
        if comments.is_exists():
            serializer = RateSerializer(comments, many = True)
            return Response({
                "Message":"Sizning qoldizgan sharhlaring",
                "data":serializer.data,
                "status":status.HTTP_200_OK
            })
        else:
            return Response({
                "Message":"Hozircha siz sharh yaratmagansiz",
                "status":status.HTTP_200_OK
            })
        

class ChatViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user chats. 
    Admins can see all chats, regular users only see their own.
    """
    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(self, 'swagger_fake_view', False) or not user.is_authenticated:
            return Chat.objects.none()
        if user.is_staff or user.is_superuser:
            return Chat.objects.all()
        return Chat.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ChatMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for chat messages.
    Admins can see all messages, users see only their own chats.
    """
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if getattr(self, 'swagger_fake_view', False) or not user.is_authenticated:
            return ChatMessage.objects.none()

        if user.is_staff or user.is_superuser:
            return ChatMessage.objects.all()

        return ChatMessage.objects.filter(sender=user) | ChatMessage.objects.filter(chat__user=user)

    def perform_create(self, serializer):
        user = self.request.user
        chat = serializer.validated_data['chat']

        if not user.is_staff and chat.user != user:
            raise PermissionError("Siz bu chatga yozish huquqiga ega emassiz.")

        serializer.save(sender=user)


class NotificationViewSet(viewsets.ModelViewSet): 
    """
    API for listing, creating, and marking notifications as read.
    Admins see all, users see their own.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if getattr(self, 'swagger_fake_view', False) or not user.is_authenticated:
            return Notification.objects.none()

        if user.is_staff or user.is_superuser:
            return Notification.objects.all().order_by('-created_at')
        return Notification.objects.filter(user=user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def mark_as_read(self, request, pk=None):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        return Response({'status': 'notification marked as read'}, status=status.HTTP_200_OK)
    
    
class GetUserTokenView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=UserTokenRequestSerializer, tags=['Register'])
    def post(self, request, *args, **kwargs):
        phone = request.data.get("phone")
        telegram_id = request.data.get("telegram_id")

        # Ikkalasi ham bo'lmasa xatolik qaytarish
        if not phone and not telegram_id:
            return Response({
                "status": False,
                "detail": _("phone yoki telegram_id majburiy!")
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Foydalanuvchini phone yoki telegram_id bo'yicha qidirish
            # user = None
            print(telegram_id, phone)
            if telegram_id and phone:
                user = User.objects.filter(phone=phone, telegram_id=telegram_id).first()
            elif telegram_id:
                user = User.objects.filter(telegram_id=telegram_id).first()
            elif phone:
                user = User.objects.filter(phone=phone).first()

            if not user:
                return Response({
                    "status": False,
                    "detail": _("Bunday foydalanuvchi topilmadi.")
                }, status=status.HTTP_404_NOT_FOUND)

            access_token = AccessToken.for_user(user)
            refresh_token = RefreshToken.for_user(user)

            return Response({
                "status": True,
                "message": _("Foydalanuvchi topildi."),
                "user": {
                    "id": user.id,
                    "phone": user.phone,
                    "role": user.role,
                    "full_name": user.full_name,
                    "telegram_id": user.telegram_id,
                },
                "tokens": {
                    "access": str(access_token),
                    "refresh": str(refresh_token),
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"GetUserTokenView error: {e}")
            return Response({
                "status": False,
                "detail": _("So'rovni bajarishda xatolik yuz berdi."),
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CarRateListCreateView(generics.ListCreateAPIView):
    queryset = CarRate.objects.all().order_by('-created_at')
    serializer_class = CarRateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ------------------ Retrieve, Update, Delete ------------------
class CarRateDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CarRate.objects.all()
    serializer_class = CarRateSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        # Faqat kompaniya javobi update qilishi mumkin
        instance = self.get_object()
        if "company_reply" in self.request.data:
            serializer.save(
                company_user=self.request.user,
                reply_created_at=timezone.now()
            )
        else:
            # user o'z commentini update qilishi
            serializer.save()


class MerchantAPIView(APIView):
    permission_classes = ()
    authentication_classes = ()

    @swagger_auto_schema(request_body=PaymentSerializer, tags=["Payment"])
    def post(self, request, *args, **kwargs):
        # Company ID yuboriladi, shu asosida key olinadi
        company_id = request.data.get("company_id")
        if not company_id:
            raise PermissionDenied("Company ID not provided")

        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            raise PermissionDenied("Company not found")

        password = request.META.get('HTTP_AUTHORIZATION')
        if self.authorize(password, company.payme_key):  # payme_key Company modelida bo'lishi kerak
            incoming_data: dict = request.data
            incoming_method: str = incoming_data.get("method")
            logged_message: str = "Incoming {data}"

            logged(
                logged_message=logged_message.format(
                    method=incoming_method,
                    data=incoming_data
                ),
                logged_type="info"
            )
            try:
                paycom_method_class = self.get_paycom_method_by_name(
                    incoming_method=incoming_method
                )
            except PerformTransactionDoesNotExist:
                raise PerformTransactionDoesNotExist()
            except Exception:
                raise MethodNotFound()

            # Metodni chaqirish
            paycom_method = paycom_method_class(incoming_data.get("params"))

        return Response(data=paycom_method)

    @staticmethod
    def get_paycom_method_by_name(incoming_method: str) -> object:
        available_methods: dict = {
            "CheckTransaction": CheckTransaction,
            "CreateTransaction": CreateTransaction,
            "CancelTransaction": CancelTransaction,
            "PerformTransaction": PerformTransaction,
            "CheckPerformTransaction": CheckPerformTransaction
        }

        try:
            MerchantMethod = available_methods[incoming_method]
        except KeyError:
            error_message = f"Unavailable method: {incoming_method}"
            logged(logged_message=error_message, logged_type="error")
            raise MethodNotFound(error_message=error_message)

        return MerchantMethod

    @staticmethod
    def authorize(password: str, merchant_key: str) -> bool:
        """
        Authorize the Merchant using Company-specific key
        """
        if not isinstance(password, str):
            logged(logged_message="Request from an unauthorized source!", logged_type="error")
            raise PermissionDenied("Request from an unauthorized source!")

        password = password.split()[-1]

        try:
            password = base64.b64decode(password).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError):
            logged(logged_message="Error decoding authorization header!", logged_type="error")
            raise PermissionDenied("Error decoding authorization header!")

        request_key = password.split(':')[-1]
        if request_key != merchant_key:
            logged(logged_message="Invalid key in request!", logged_type="error")
            raise PermissionDenied("Unauthorized request!")

        return True


# Bir oylik subscriptioni to'lash uchun merchant view yaratish kk

class CompanySubscriptionAPIView(APIView):
    """
    Bu API kompaniya subscriptionlarini boshqaradi.
    POST: yangi subscription yaratish
    GET: kompaniya subscriptionlarini ko'rish
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = getattr(request.user, 'company', None)
        if not company:
            return Response({"detail": "Siz kompaniya egasi emassiz."}, status=403)
        # Kompaniya subscriptionlarini tekshiramiz va active holatni yangilaymiz
        subscriptions = CompanySubscription.objects.filter(company=company)
        for sub in subscriptions:
            sub.check_active()
        serializer = CompanySubscriptionSerializer(subscriptions, many=True)
        return Response({"subscriptions": serializer.data, "status": True}, status=200)

    @swagger_auto_schema(request_body=CompanySubscriptionSerializer, tags=["Company Subscription"])
    def post(self, request, *args, **kwargs):
        company = getattr(request.user, 'company', None)
        if not company:
            return Response({"detail": "Siz kompaniya egasi emassiz."}, status=403)
        serializer = CompanySubscriptionSerializer(data=request.data)
        if serializer.is_valid():
            subscription = serializer.save(company=company)
            return Response({
                "status": True,
                "message": f"{subscription.plan} subscription muvaffaqiyatli yaratildi.",
                "subscription": serializer.data
            }, status=201)
        else:
            return Response({
                "status": False,
                "errors": serializer.errors
            }, status=400)

    @swagger_auto_schema(request_body=CompanySubscriptionSerializer, tags=["Company Subscription"])
    def patch(self, request, pk, *args, **kwargs):
        company = getattr(request.user, 'company', None)
        if not company:
            return Response({"detail": "Siz kompaniya egasi emassiz."}, status=403)
        subscription = CompanySubscription.objects.filter(id=pk, company=company).first()
        if not subscription:
            return Response({"detail": "Subscription topilmadi."}, status=404)
        serializer = CompanySubscriptionSerializer(subscription, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": True,
                "message": "Subscription muvaffaqiyatli yangilandi.",
                "subscription": serializer.data
            }, status=200)
        else:
            return Response({"status": False, "errors": serializer.errors}, status=400)

    @swagger_auto_schema(request_body=CompanySubscriptionSerializer, tags=["Company Subscription"])
    def delete(self, request, pk, *args, **kwargs):
        company = getattr(request.user, 'company', None)
        if not company:
            return Response({"detail": "Siz kompaniya egasi emassiz."}, status=403)
        subscription = CompanySubscription.objects.filter(id=pk, company=company).first()
        if not subscription:
            return Response({"detail": "Subscription topilmadi."}, status=404)
        subscription.delete()
        return Response({"status": True, "message": "Subscription muvaffaqiyatli o'chirildi."}, status=200)


class BotNotificationViewSet(viewsets.ModelViewSet):
    queryset = BotNotification.objects.all()
    serializer_class = BotNotificationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user
        if not getattr(user, "role", None) in ['admin', 'manager']:
            return Response(
                {"detail": "Siz admin yoki manager emassiz."},
                status=403
            )
        return super().create(request, *args, **kwargs)


class ClickUzMerchantAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    VALIDATE_CLASS = None

    @swagger_auto_schema(request_body=ClickUzSerializer)
    def post(self, request):
        serializer = ClickUzSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        METHODS = {
            PREPARE: self.prepare,
            COMPLETE: self.complete
        }

        merchant_trans_id = serializer.validated_data['merchant_trans_id']
        amount = serializer.validated_data['amount']
        action = serializer.validated_data['action']

        if click_authorization(**serializer.validated_data) is False:
            return Response({
                "error": AUTHORIZATION_FAIL_CODE,
                "error_note": AUTHORIZATION_FAIL
            })

        assert self.VALIDATE_CLASS != None
        check_order = self.VALIDATE_CLASS().check_order(order_id=merchant_trans_id, amount=amount)
        if check_order is True:
            result = METHODS[action](**serializer.validated_data, response_data=serializer.validated_data)
            return Response(result)
        return Response({"error": check_order})

    def prepare(self, click_trans_id: str, merchant_trans_id: str, amount: str, sign_string: str, sign_time: str,
                response_data: dict,
                *args, **kwargs) -> dict:
        """

        :param click_trans_id:
        :param merchant_trans_id:
        :param amount:
        :param sign_string:
        :param response_data:
        :param args:
        :return:
        """
        transaction = Transaction.objects.create(
            click_trans_id=click_trans_id,
            merchant_trans_id=merchant_trans_id,
            amount=amount,
            action=PREPARE,
            sign_string=sign_string,
            sign_datetime=sign_time,
        )
        response_data.update(merchant_prepare_id=transaction.id)
        return response_data

    def complete(self, click_trans_id, amount, error, merchant_prepare_id,
                 response_data, action, *args, **kwargs):
        """

        :param click_trans_id:
        :param merchant_trans_id:
        :param amount:
        :param sign_string:
        :param error:
        :param merchant_prepare_id:
        :param response_data:
        :param action:
        :param args:
        :return:
        """
        try:
            transaction = Transaction.objects.get(pk=merchant_prepare_id)

            if error == A_LACK_OF_MONEY:
                response_data.update(error=A_LACK_OF_MONEY_CODE)
                transaction.action = A_LACK_OF_MONEY
                transaction.status = Transaction.CANCELED
                transaction.save()
                return response_data

            if transaction.action == A_LACK_OF_MONEY:
                response_data.update(error=A_LACK_OF_MONEY_CODE)
                return response_data

            if transaction.amount != amount:
                response_data.update(error=INVALID_AMOUNT)
                return response_data

            if transaction.action == action:
                response_data.update(error=INVALID_ACTION)
                return response_data

            transaction.action = action
            transaction.status = Transaction.FINISHED
            transaction.save()
            response_data.update(merchant_confirm_id=transaction.id)
            self.VALIDATE_CLASS().successfully_payment(transaction.merchant_trans_id, transaction)
            return response_data
        except Transaction.DoesNotExist:
            response_data.update(error=TRANSACTION_NOT_FOUND)
            return response_data


class OrderStatusView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderStatusSerializer

    @swagger_auto_schema(request_body=OrderStatusSerializer, tags=['Order'])
    def post(self, request):
        order_status = request.data.get('status')
        if not order_status:
            return Response(
                {"detail": "Status is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        orders = Order.objects.filter(status=order_status)
        if not orders.exists():
            return Response(
                {"detail": "Orders not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = OrderStatusSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BlockUserView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BlockUserSerializer

    @swagger_auto_schema(request_body=BlockUserSerializer, tags=['User'])
    def post(self, request):
        admin = request.user
        if admin.role in ['manager', 'admin']:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            user_id = serializer.validated_data.get('user_id')
            is_blocked = serializer.validated_data.get('is_blocked')
            user = User.objects.filter(id=user_id).first()
            if not user:
                return Response(
                    {"detail": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            user.is_blocked = is_blocked
            user.save()
            message = "User blocked successfully" if is_blocked else "User unblocked successfully"
            return Response(
                {"detail": message},
                status=status.HTTP_200_OK
            )
        else:
            return Response({
                "data":"Sizga ruxsat yo"
            })


class DiscountView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DiscountSerializer

    @swagger_auto_schema(tags=['Car'])
    def get(self, request):
        discounts = Discount.objects.all()
        serializer = DiscountSerializer(discounts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=DiscountSerializer, tags=['Car'])
    def post(self, request):
        serializer = DiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class CheckInOutViewSet(viewsets.ModelViewSet):
    queryset = ChekInOut.objects.all()
    serializer_class = CheckInOutSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FileUploadParser]

    def perform_create(self, serializer):
        """
        CheckInOut yaratilganda:
        - Car status UNAVAILABLE bo‘ladi
        """
        check = serializer.save()
        car = check.car
        car.status = "unavailable"
        car.save(update_fields=["status"])

    # ============================
    # CHECK-IN IMAGES UPLOAD
    # ============================
    @action(detail=True, methods=["post"], url_path="upload-checkin-images")
    def upload_checkin_images(self, request, pk=None):
        check = self.get_object()
        images = request.FILES.getlist("images")

        if not images:
            return Response(
                {"error": "Images topilmadi"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_images = []
        for img in images:
            obj = ImagesCheckIn.objects.create(
                checkin=check,
                image=img
            )
            created_images.append(obj)

        serializer = ImagesCheckInSerializer(
            created_images,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # ============================
    # CHECK-OUT IMAGES UPLOAD
    # ============================
    @action(detail=True, methods=["post"], url_path="upload-checkout-images")
    def upload_checkout_images(self, request, pk=None):
        check = self.get_object()
        images = request.FILES.getlist("images")

        if not images:
            return Response(
                {"error": "Images topilmadi"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_images = []
        for img in images:
            obj = ImagesCheckOut.objects.create(
                checkin=check,
                image=img
            )
            created_images.append(obj)

        # CHECKOUT tugadi → car AVAILABLE
        car = check.car
        car.status = "available"
        car.save(update_fields=["status"])

        serializer = ImagesCheckOutSerializer(
            created_images,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # ============================
    # DEPOZIT UPLOAD
    # ============================
    @action(detail=True, methods=["post"], url_path="upload-depozit")
    def upload_depozit(self, request, pk=None):
        check = self.get_object()
        user = request.user

        if "depozite_user" in request.FILES:
            if user.role != "user":
                return Response(
                    {"error": "Faqat USER yuklay oladi"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            check.depozite_user = request.FILES["depozite_user"]

        if "depozite_company" in request.FILES:
            if user.role not in ["admin", "manager"]:
                return Response(
                    {"error": "Faqat ADMIN yoki MANAGER yuklay oladi"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            check.depozite_company = request.FILES["depozite_company"]

        check.save()
        serializer = self.get_serializer(check)
        return Response(serializer.data)


# ============== FILIAL VIEWS ==============
class FilialView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FilialSerializer

    @swagger_auto_schema(
        tags=['Filial'],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def get(self, request):
        """Barcha filiallar"""
        filials = Filial.objects.all()
        # MUHIM: context qo'shish
        serializer = FilialSerializer(filials, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=FilialSerializer,
        tags=['Filial'],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def post(self, request):
        """Yangi filial yaratish"""
        # MUHIM: context qo'shish
        serializer = FilialSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FilialDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FilialSerializer

    @swagger_auto_schema(
        tags=['Filial'],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def get(self, request, pk):
        """Bitta filial"""
        filial = Filial.objects.filter(id=pk).first()
        if not filial:
            return Response(
                {"detail": "Filial not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        # MUHIM: context qo'shish
        serializer = FilialSerializer(filial, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=FilialSerializer,
        tags=['Filial'],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def put(self, request, pk):
        """Filialni yangilash (to'liq)"""
        filial = Filial.objects.filter(id=pk).first()
        if not filial:
            return Response(
                {"detail": "Filial not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        # MUHIM: context qo'shish
        serializer = FilialSerializer(filial, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=FilialSerializer,
        tags=['Filial'],
        manual_parameters=[TRANSLATION_HEADER]
    )
    def patch(self, request, pk):
        """Filialni yangilash (qisman)"""
        filial = Filial.objects.filter(id=pk).first()
        if not filial:
            return Response(
                {"detail": "Filial not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        # MUHIM: context qo'shish
        serializer = FilialSerializer(
            filial, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=['Filial'])
    def delete(self, request, pk):
        """Filialni o'chirish"""
        filial = Filial.objects.filter(id=pk).first()
        if not filial:
            return Response(
                {"detail": "Filial not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        filial.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class CarImageAPIView(APIView):
    parser_classes = [MultiPartParser, FileUploadParser]
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            images = CarImage.objects.all()
            serializer = CarImageSerializer(images, many=True, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"detail": "Server error while fetching images", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @swagger_auto_schema(
        operation_description="Upload car image to DigitalOcean Spaces",
        manual_parameters=[
            openapi.Parameter(
                name="image",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="Upload image file",
            ),
        ],
        consumes=["multipart/form-data"],
        responses={201: CarImageSerializer()},
    )
    def post(self, request):
        try:
            user = request.user
            if not user.is_authenticated:
                return Response(
                    {"detail": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if getattr(user, "role", None) not in ["admin", "manager"]:
                return Response(
                    {"detail": "You are not allowed to upload images"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if "image" not in request.data:
                return Response(
                    {"image": ["No file was uploaded."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = CarImageSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            print(f"Upload error: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {"detail": "Server error while uploading image", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class CarImageDetailAPIView(APIView):
    parser_classes = [MultiPartParser, FileUploadParser]
    permission_classes = [AllowAny]

    def get_object(self, pk):
        try:
            return CarImage.objects.get(pk=pk)
        except CarImage.DoesNotExist:
            return None

    def get(self, request, pk):
        image = self.get_object(pk)
        if not image:
            return Response({"detail": "Not found"}, status=404)

        serializer = CarImageSerializer(
            image, context={"request": request}
        )
        return Response(serializer.data)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        user = request.user

        if not user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=401,
            )

        if getattr(user, "role", None) not in ["admin", "manager"]:
            return Response(
                {"detail": "You are not allowed to update images"},
                status=403,
            )

        image = self.get_object(pk)
        if not image:
            return Response({"detail": "Not found"}, status=404)

        serializer = CarImageSerializer(
            image,
            data=request.data,
            partial=partial,
            context={"request": request},
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        user = request.user

        if not user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=401,
            )

        if getattr(user, "role", None) not in ["admin", "manager"]:
            return Response(
                {"detail": "You are not allowed to delete images"},
                status=403,
            )

        image = self.get_object(pk)
        if not image:
            return Response({"detail": "Not found"}, status=404)

        image.delete()
        return Response({"detail": "Deleted successfully"}, status=204)


class ViloyatlarViewSet(ModelViewSet):
    queryset = Viloyatlar.objects.all()
    serializer_class = ViloyatlarSerializer
    permission_classes = [AllowAny]

    def _check_role(self, request):
        user = request.user

        if not user.is_authenticated:
            raise PermissionDenied("Authentication required")

        if getattr(user, 'role', None) not in ['admin', 'manager']:
            raise PermissionDenied("You are not allowed to manage regions")

    def create(self, request, *args, **kwargs):
        self._check_role(request)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self._check_role(request)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._check_role(request)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._check_role(request)
        return super().destroy(request, *args, **kwargs)
    

class GetCompaniView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FileUploadParser]
    
    @swagger_auto_schema(tag = 'Company')
    def get(self, request, *args, **kwargs):
        user = request.user
        if user.role in ['admin', 'manager']:
            company = Company.objects.filter(owner = user).first()
            return Response({
                "company_id":company.id,
                "status":status.HTTP_200_OK
            })
        else:
            return Response({
                "data":"Siz admin emassiz",
                "status":status.HTTP_200_OK
            })
            
            
class GetCarModelView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FileUploadParser]
    
    @swagger_auto_schema(tag = ['Filter-car'])
    def get(self, request, *args, **kwargs):
        rdata = Car.objects.all()
        serializer = CarModelPortfolioSerializer(rdata, many = True)
        return Response({
            "data":serializer.data,
            "status":status.HTTP_200_OK
        })