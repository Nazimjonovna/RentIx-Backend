from rest_framework import serializers
from django.utils.dateparse import parse_datetime
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
from django.conf import settings
from googletrans import Translator
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from .exceptions import IncorrectAmount, PerformTransactionDoesNotExist
from django.contrib.auth import get_user_model
from .translation_helper import AutoTranslateMixin
from .models import (
    Filial, User, Company, CompanyWorkDay, Manager, CarImage, UserImage, Car, Order, ValidatedCode, Verification, Discount, 
    Rate, Chat, ChatMessage, Notification, CarRate, Payment, CompanySubscription, Plan, PLAN_PRICES, BotNotification, CashbackTransaction,
    ImagesCheckOut, ImagesCheckIn, ChekInOut, Viloyatlar,
)

User = get_user_model()
translator = Translator()

class PhoneSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=255)

    def validate_phone(self, value):
        if not value.startswith('+998'):
            raise serializers.ValidationError("Phone number must start with +998")
        return value


class SMSCodeSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=255)
    code = serializers.CharField(max_length=255)

    def validate_phone(self, value):
        if not value.startswith('+998'):
            raise serializers.ValidationError("Phone number must start with +998")
        return value


class ValidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidatedCode
        fields = (
            "phone",
            "code",
        )


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "phone",
            "code",
            "full_name",
            "tg_nick",
            "telegram_id",
            "role",
        )


class CompanyWorkDaySerializer(serializers.ModelSerializer):
    filial_name = serializers.CharField(source="filial.name", read_only=True)  # filial nomini chiqarish

    class Meta:
        model = CompanyWorkDay
        fields = (
            "id",
            "day",
            "start_time",
            "end_time",
            "is_working",
            "is_24_7",
            "filial",
            "filial_name",
        )


# Filial serializeri
class FilialSerializer(AutoTranslateMixin, serializers.ModelSerializer):
    """
    Filial serializer with translations for name and address
    """
    class Meta:
        model = Filial
        fields = (
            "id",
            "name",           # uz
            "name_ru",        # ru
            "name_en",        # en
            "address",        # uz
            "address_ru",     # ru
            "address_en",     # en
            "company",
            "phone",
        )
        read_only_fields = ['id', 'name_ru', 'name_en', 'address_ru', 'address_en']
        translatable_fields = ['name', 'address']


# Kompaniya serializeri
class CompanySerializer(AutoTranslateMixin, serializers.ModelSerializer):
    work_days = CompanyWorkDaySerializer(many=True, read_only=True)
    filials = FilialSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "name_ru",
            "name_en",
            "owner",
            "login",
            "password",
            "created_at",
            "INN",
            "click_id",
            "payme_id",
            "payme_callback_url",
            "payme_key",
            "uzum_id",
            "diedline_zalog",
            "work_days",
            "filials",
            "phone1",
            "phone2",
        )
        read_only_fields = ['id', 'created_at', 'name_ru', 'name_en']
        translatable_fields = ['name']

    def create(self, validated_data):
        instance = super().create(validated_data)
        # Mixin methodini chaqirish
        self.TRANSLATE_FIELDS = getattr(self.Meta, 'translatable_fields', [])
        self.auto_translate(instance)
        instance.save(update_fields=[f"{f}_ru" for f in self.TRANSLATE_FIELDS] +
                      [f"{f}_en" for f in self.TRANSLATE_FIELDS])
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self.TRANSLATE_FIELDS = getattr(self.Meta, 'translatable_fields', [])
        self.auto_translate(instance)
        instance.save(update_fields=[f"{f}_ru" for f in self.TRANSLATE_FIELDS] +
                      [f"{f}_en" for f in self.TRANSLATE_FIELDS])
        return instance



class OrderPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            "location_from",
            "location_to",
            "start_time",
            "end_time",
        )


class OrderSerializer(serializers.ModelSerializer):
    cost = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ("user", "cost")

    def get_cost(self, obj):
        return obj.calculate_cost()

    def validate(self, attrs):
        """
        Company ishlash vaqtini tekshiradi
        Model clean() ni ishlatamiz
        """
        request = self.context.get("request")
        user = request.user if request else None
        order = Order(user=user, **attrs)
        try:
            order.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(
                e.message_dict if hasattr(e, "message_dict") else e.messages
            )
        return attrs

    def create(self, validated_data):
        """
        User ni requestdan olamiz
        """
        user = self.context["request"].user
        order = Order(user=user, **validated_data)
        order.save()  # save() ichida full_clean + cost calculation ishlaydi
        return order

    def update(self, instance, validated_data):
        """
        Update paytida ham workday validation ishlaydi
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()  # save() ichida clean + calculate_cost ishlaydi
        return instance



class CarSerializer(serializers.ModelSerializer):
    # Fayllar uchun URL'lar
    car_image_logo_url = serializers.SerializerMethodField()
    car_image_portfolio_url = serializers.SerializerMethodField()
    tex_pasport_url = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = "__all__"
        read_only_fields = ['id', 'created', 'updated', 'car_name_ru', 'car_name_en', 'commit_ru', 'commit_en']

    # car_image_logo URL'sini olish uchun metod
    def get_car_image_logo_url(self, obj):
        if obj.car_image_logo:
            return obj.car_image_logo  # URL'ni to'g'ridan-to'g'ri qaytaramiz
        return None

    # car_image_portfolio URL'sini olish uchun metod
    def get_car_image_portfolio_url(self, obj):
        if obj.car_image_portfolio:
            return obj.car_image_portfolio  # URL'ni to'g'ridan-to'g'ri qaytaramiz
        return None

    # tex_pasport URL'sini olish uchun metod
    def get_tex_pasport_url(self, obj):
        if obj.tex_pasport:
            return obj.tex_pasport  # URL'ni to'g'ridan-to'g'ri qaytaramiz
        return None


class AvailableCarTimeFilterSerializer(serializers.Serializer):
         """
    Foydalanuvchidan mashinalarni qidirish oralig‘ini so‘raydigan serializer.
    start_time va end_time datetime formatida bo‘lishi kerak.
    Masalan: 2026-10-10T12:00 yoki 2026-10-10 12:00
    """
         start_time = serializers.CharField(required=True)
         end_time = serializers.CharField(required=False, allow_null=True, allow_blank=True)
         hours = serializers.IntegerField(required=False, min_value=1)

         def validate(self, attrs):
            start_time = parse_datetime(attrs.get("start_time"))
            if not start_time:
                raise serializers.ValidationError(
                    {"start_time": "Datetime noto‘g‘ri formatda"}
                )
            end_str = attrs.get("end_time")
            hours = attrs.get("hours")
            if end_str:
                end_time = parse_datetime(end_str)
                if not end_time:
                    raise serializers.ValidationError(
                        {"end_time": "Datetime noto‘g‘ri formatda"}
                    )
            elif hours:
                end_time = start_time + timedelta(hours=hours)
            else:
                end_time = start_time + timedelta(hours=24)
            if end_time <= start_time:
                raise serializers.ValidationError(
                    {"end_time": "End time start_time dan katta bo‘lishi kerak"}
                )
            attrs["start_time"] = start_time
            attrs["end_time"] = end_time
            return attrs


class AvailableCarModelFilterSerializer(serializers.Serializer):
    car_model = serializers.CharField(required=True)


class AvailableCarCostFilterSerializer(serializers.Serializer):
    min_price = serializers.FloatField(required=False)
    max_price = serializers.FloatField(required=False)

    def validate(self, attrs):
        min_price = attrs.get("min_price")
        max_price = attrs.get("max_price")

        if min_price is not None and max_price is not None:
            if min_price > max_price:
                raise serializers.ValidationError(
                    "min_price max_price dan katta bo‘lishi mumkin emas"
                )
        return attrs


class CashbackTransactionSerializer(serializers.ModelSerializer):
    total_earned = serializers.FloatField()
    total_spent = serializers.FloatField()
    available = serializers.FloatField()


class CreateAdminSerializer(AutoTranslateMixin, serializers.ModelSerializer):
    """
    Simplified company serializer for admin creation
    """
    class Meta:
        model = Company
        fields = (
            "id",
            "name",           # uz
            "name_ru",        # ru
            "name_en",        # en
            "owner",
            "phone1",
            "phone2",
        )
        read_only_fields = ['id', 'name_ru', 'name_en']
        translatable_fields = ['name']


class ManagerSerializer(serializers.ModelSerializer):
    """
    Manager serializer - tarjima yo'q, faqat relations
    """
    # Inputda ID bilan ishlaydi
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all())

    class Meta:
        model = Manager
        fields = [
            "id",
            "user",
            "company",
            "filial",
            "role",
            "work_time",
            "status",
            "approwed_by",
            "login",
            "password",
        ]
        read_only_fields = ["approwed_by"]

    def validate(self, attrs):
        user = attrs.get("user")
        company = attrs.get("company")
        # User roli manager bo'lishi kerak
        if user.role != "manager":
            raise serializers.ValidationError({"user": "User roli manager bo'lishi kerak"})
        # Bir kompaniyada duplicate manager bo'lishi mumkin emas
        if Manager.objects.filter(user=user, company=company).exists():
            raise serializers.ValidationError(
                "Bu user ushbu kompaniyada allaqachon manager sifatida mavjud"
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        # Superadmin yaratgan bo'lsa approwed_by avtomatik to'ldiriladi
        if request and request.user.role.lower() == "superadmin":
            validated_data["approwed_by"] = request.user
        return super().create(validated_data)

    def to_representation(self, instance):
        """
        Response uchun user va company batafsil ko'rsatish
        """
        data = super().to_representation(instance)
        
        # User ma'lumotlari
        data["user"] = {
            "id": instance.user.id,
            "full_name": instance.user.full_name,
            "email": getattr(instance.user, "email", None)
        }
        
        # Company ma'lumotlari (tarjima bilan)
        request = self.context.get('request')
        if request:
            lang = request.headers.get('Accept-Language', 'uz')[:2]
            if lang == 'ru' and hasattr(instance.company, 'name_ru'):
                company_name = instance.company.name_ru or instance.company.name
            elif lang == 'en' and hasattr(instance.company, 'name_en'):
                company_name = instance.company.name_en or instance.company.name
            else:
                company_name = instance.company.name
        else:
            company_name = instance.company.name
            
        data["company"] = {
            "id": instance.company.id,
            "name": company_name
        }
        
        return data

    

class ManagerCRUDSerializer(serializers.ModelSerializer):
    """
    Manager CRUD operations
    """
    class Meta:
        model = Manager
        fields = [
            "id",
            "user",
            "company",
            "filial",
            "role",
            "work_time",
            "status",
            "approwed_by",
            "login",
            "password",
        ]
        read_only_fields = ["approwed_by", "user", "company", "role"]
    

class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)
    

class RateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rate
        fields = (
           "id",
            "user",
            "company",
            "manager",
            "rate_manager",
            "rate_company",
            "comment",
            "created_at",
        )


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)

    class Meta:
        model = ChatMessage
        fields = (
            "id",
            "sender",
            "sender_name",
            "message",
            "created_at",
            'file',
        )
        read_only_fields = (
            "id",
            "created_at",
            "sender_name",
        )
        
        def get_file_url(self, obj):
            if obj.file:
                request = self.context.get("request")
                return request.build_absolute_uri(obj.file.url) if request else obj.file.url
            return None


class ChatSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    manager_name = serializers.CharField(source="manager.user.full_name", read_only=True)

    class Meta:
        model = Chat
        fields = (
            "id",
            "user",
            "user_name",
            "manager",
            "manager_name",
            "messages",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "messages",
        )


class NotificationSerializer(AutoTranslateMixin, serializers.ModelSerializer):
    """
    Notification serializer with translations
    """
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    manager_name = serializers.CharField(source="manager.user.full_name", read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "user",
            "user_name",
            "manager",
            "manager_name",
            "title",          # uz
            "title_ru",       # ru
            "title_en",       # en
            "message",        # uz
            "message_ru",     # ru
            "message_en",     # en
            "is_read",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "user_name",
            "manager_name",
            "title_ru",
            "title_en",
            "message_ru",
            "message_en",
        )
        translatable_fields = ['title', 'message']


class UserTokenRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15, required=True)
    telegram_id = serializers.IntegerField(required=True)

    def validate_phone(self, value):
        phone = value.strip().replace(" ", "").replace("+", "")
        if not phone.isdigit():
            raise serializers.ValidationError(
                _("Telefon raqami faqat raqamlardan iborat bo'lishi kerak.")
            )
        if len(phone) < 9:
            raise serializers.ValidationError(_("Telefon raqami juda qisqa."))
        return phone

    def validate_telegram_id(self, value):
        if value <= 0:
            raise serializers.ValidationError(_("Telegram ID musbat raqam bo'lishi kerak."))
        return value


class CarRateSerializer(AutoTranslateMixin, serializers.ModelSerializer):
    """
    Car rate serializer with translations for comments
    """
    class Meta:
        model = CarRate
        fields = (
            "id",
            "car",
            "user",
            "rate",
            "comment",           # uz
            "comment_ru",        # ru
            "comment_en",        # en
            "company_reply",     # uz
            "company_reply_ru",  # ru
            "company_reply_en",  # en
            "company_user",
            "reply_created_at",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "comment_ru",
            "comment_en",
            "company_reply_ru",
            "company_reply_en",
        )
        translatable_fields = ['comment', 'company_reply']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "order",
            "amount",
            "status",
            "transaction_id",
            "created_at",
        )

    def validate(self, data):
        order = data.get("order")
        amount = data.get("amount")
        if order and amount and float(order.amount) != float(amount):
            raise IncorrectAmount()
        return data

    def validate_amount(self, amount):
        if amount is not None and float(amount) <= float(settings.PAYME.get("PAYME_MIN_AMOUNT")):
            raise IncorrectAmount()
        return amount

    def validate_order(self, order):
        if not Order.objects.filter(id=order.id).exists():
            raise PerformTransactionDoesNotExist()
        return order


class CompanySubscriptionSerializer(serializers.ModelSerializer):
    # Narxni read_only qilamiz, chunki save() metodi avtomatik belgilaydi
    price = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CompanySubscription
        fields = (
            "id",
            "company",
            "plan",
            "price",
            "start_date",
            "end_date",
            "is_active",
            "auto_renew",
        )
    
    def validate_plan(self, value):
        if value not in dict(Plan):
            raise serializers.ValidationError("Noto‘g‘ri plan tanlandi.")
        return value

    def create(self, validated_data):
        """
        Create metodi narx va end_date ni avtomatik to‘ldiradi
        (model save() ichida ham mavjud, lekin serializerdan qo‘llash xavfsiz).
        """
        plan = validated_data.get('plan')
        if 'price' not in validated_data:
            validated_data['price'] = PLAN_PRICES.get(plan, 0)
        if 'end_date' not in validated_data:
            validated_data['end_date'] = validated_data.get('start_date') + timedelta(days=30)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Update qilganda plan o'zgarganda narx ham yangilanadi.
        """
        plan = validated_data.get('plan', instance.plan)
        if plan != instance.plan:
            instance.price = PLAN_PRICES.get(plan, instance.price)
        return super().update(instance, validated_data)


class CompanySubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySubscription
        fields = (
            "id",
            "company",
            "plan",
            "price",
            "start_date",
            "end_date",
            "is_active",
            "auto_renew",
        )

    def validate(self, data):
        """
        Umumiy validatsiya:
        - Plan narxi to'g'ri bo'lishi kerak (agar price berilmagan bo'lsa avtomatik PLAN_PRICES dan olinadi)
        - End date boshlanish sanasidan keyin bo'lishi kerak
        """
        plan = data.get("plan")
        price = data.get("price")
        start_date = data.get("start_date", timezone.now().date())
        end_date = data.get("end_date")
        # Agar price berilmagan bo'lsa, avtomatik qo'yish
        if not price:
            data["price"] = PLAN_PRICES.get(plan, 0)
        # End date tekshirish
        if end_date and end_date <= start_date:
            raise serializers.ValidationError({"end_date": "End date boshlanish sanasidan keyin bo'lishi kerak."})
        return data

    def validate_price(self, price):
        """
        Narx minimal qiymatdan past bo'lmasligi kerak (agar siz xohlasangiz)
        """
        if price is not None and price <= 0:
            raise serializers.ValidationError("Price 0 dan katta bo'lishi kerak.")
        return price


class BotNotificationSerializer(AutoTranslateMixin, serializers.ModelSerializer):
    """
    Bot notification serializer with translations
    """
    class Meta:
        model = BotNotification
        fields = (
            "id",
            "user",
            "manager",
            "title",          # uz
            "title_ru",       # ru
            "title_en",       # en
            "message",        # uz
            "message_ru",     # ru
            "message_en",     # en
            "photo",
            "is_read",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "title_ru",
            "title_en",
            "message_ru",
            "message_en",
        )
        translatable_fields = ['title', 'message'] 


class ClickUzSerializer(serializers.Serializer):
    click_trans_id = serializers.CharField(allow_blank=True)
    service_id = serializers.CharField(allow_blank=True)
    merchant_trans_id = serializers.CharField(allow_blank=True)
    merchant_prepare_id = serializers.CharField(allow_blank=True, required=False, allow_null=True)
    amount = serializers.CharField(allow_blank=True)
    action = serializers.CharField(allow_blank=True)
    error = serializers.CharField(allow_blank=True)
    error_note = serializers.CharField(allow_blank=True)
    sign_time = serializers.CharField()
    sign_string = serializers.CharField(allow_blank=True)
    click_paydoc_id = serializers.CharField(allow_blank=True)


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.CharField(allow_blank=True)
    

class BlockUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    is_blocked = serializers.BooleanField()


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = (
            "id",
            "car",
            "discount",
            "new_cost",
            "created_at",
            "updated_at",
        )

    def validate(self, data):
        car = data.get("car")
        discount = data.get("discount")
        new_cost = data.get("new_cost")
        if car and discount and new_cost:
            if float(new_cost) >= float(car.cost):
                raise serializers.ValidationError("New cost must be less than car cost")
        return data


class ImagesCheckInSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ImagesCheckIn
        fields = ("id", "image", "image_url")

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None
    

class ImagesCheckOutSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ImagesCheckOut
        fields = ("id", "image", "image_url")

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None
    

class CheckInOutSerializer(serializers.ModelSerializer):
    checkin_images = ImagesCheckInSerializer(many=True, read_only=True)
    checkout_images = ImagesCheckOutSerializer(many=True, read_only=True)

    depozite_user_url = serializers.SerializerMethodField()
    depozite_company_url = serializers.SerializerMethodField()

    class Meta:
        model = ChekInOut
        fields = (
            "id",
            "user",
            "company",
            "manager",
            "car",
            "depozite_user",
            "depozite_company",
            "depozite_user_url",
            "depozite_company_url",
            "checkin_images",
            "checkout_images",
        )

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        if attrs.get("depozite_user") and user.role != "user":
            raise serializers.ValidationError(
                {"depozite_user": "Faqat USER yuklay oladi"}
            )

        if attrs.get("depozite_company") and user.role not in ["admin", "manager"]:
            raise serializers.ValidationError(
                {"depozite_company": "Faqat ADMIN yoki MANAGER yuklay oladi"}
            )

        return attrs

    def get_depozite_user_url(self, obj):
        request = self.context.get("request")
        if obj.depozite_user and request:
            return request.build_absolute_uri(obj.depozite_user.url)
        return None

    def get_depozite_company_url(self, obj):
        request = self.context.get("request")
        if obj.depozite_company and request:
            return request.build_absolute_uri(obj.depozite_company.url)
        return None


class CarImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarImage
        fields = ('id', 'image')
        read_only_fields = ('id',)


class ViloyatlarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Viloyatlar
        fields = (
            'id',
            'viloyat',
            'cost_day',
            'cost_hour',
        )
        read_only_fields = ('id',)
        
        
class CarModelPortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = [
            "car_model",
            "car_image_portfolio"
        ]