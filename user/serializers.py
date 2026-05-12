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
from .services import create_default_filial_and_workdays
from .models import (
    Filial, User, Company, CompanyWorkDay, Manager, CarImage, UserImage, Car, Order, ValidatedCode, Verification, Discount, 
    Rate, Chat, ChatMessage, Notification, CarRate, Payment, CompanySubscription, Plan, PLAN_PRICES, BotNotification, CashbackTransaction,
    ImagesCheckOut, ImagesCheckIn, ChekInOut, Viloyatlar,CarBrand, CarModel,
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
        fields = "__all__"
        

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


class CompanyWorkDaySerializer(serializers.ModelSerializer):
    weekday_display = serializers.CharField(
        source="get_weekday_display",
        read_only=True
    )

    class Meta:
        model = CompanyWorkDay
        fields = [
            "id",
            "company",
            "filial",
            "weekday",
            "weekday_display",
            "start_time",
            "end_time",
            "is_working",
            "is_24_7",
        ]
        read_only_fields = ["id", "company"]


# Filial serializeri
class FilialSerializer(AutoTranslateMixin, serializers.ModelSerializer):
    workdays = serializers.SerializerMethodField()

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
            "workdays",
        )
        read_only_fields = ['id', 'name_ru', 'name_en', 'address_ru', 'address_en', "workdays",]
        translatable_fields = ['name', 'address']
        
    def get_workdays(self, obj):
        workdays = CompanyWorkDay.objects.filter(
            company=obj.company
        ).order_by("id")

        return CompanyWorkDaySerializer(
            workdays,
            many=True,
            context=self.context
        ).data


# Kompaniya serializeri
class CompanySerializer(AutoTranslateMixin, serializers.ModelSerializer):
    work_days = CompanyWorkDaySerializer(many=True, read_only=True)
    filials = FilialSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        fields = "__all__"
        read_only_fields = ['id', 'created_at', 'name_ru', 'name_en']
        translatable_fields = ['name']

    def create(self, validated_data):
        instance = super().create(validated_data)
        self.TRANSLATE_FIELDS = getattr(self.Meta, 'translatable_fields', [])
        self.auto_translate(instance)
        instance.save(
            update_fields=[f"{f}_ru" for f in self.TRANSLATE_FIELDS] +
                          [f"{f}_en" for f in self.TRANSLATE_FIELDS]
        )
        create_default_filial_and_workdays(instance)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self.TRANSLATE_FIELDS = getattr(self.Meta, 'translatable_fields', [])
        self.auto_translate(instance)
        instance.save(
            update_fields=[f"{f}_ru" for f in self.TRANSLATE_FIELDS] +
                          [f"{f}_en" for f in self.TRANSLATE_FIELDS]
        )
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


class CarBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarBrand
        fields = [
            "id",
            "name",
            "name_ru",
            "name_en",
        ]


class CarModelSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    class Meta:
        model = CarModel
        fields = [
            "id",
            "brand",
            "brand_name",
            "name",
            "name_ru",
            "name_en",
        ]

    def validate(self, attrs):
        brand = attrs.get("brand")
        name = attrs.get("name")
        qs = CarModel.objects.filter(brand=brand, name__iexact=name)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError({
                "name": "Bu brand ichida bunday model allaqachon mavjud"
            })

        return attrs


class CarSerializer(serializers.ModelSerializer):
    car_image_logo_url = serializers.SerializerMethodField()
    car_image_portfolio_url = serializers.SerializerMethodField()
    tex_pasport_url = serializers.SerializerMethodField()
    car_images = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = "__all__"
        read_only_fields = [
            "id",
            "company",
            "created",
            "updated",
            "car_name_ru",
            "car_name_en",
            "commit_ru",
            "commit_en",
            "car_image_logo_url",
            "car_image_portfolio_url",
            "tex_pasport_url",
            "car_images",
        ]

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        extra_fields = [
            "car_image_logo_url",
            "car_image_portfolio_url",
            "tex_pasport_url",
            "car_images",
        ]
        for field in extra_fields:
            if field not in fields:
                fields.append(field)
        return fields

    def build_absolute_file_url(self, file_value):
        if not file_value:
            return None
        request = self.context.get("request")
        try:
            url = file_value.url
        except Exception:
            url = str(file_value)
        if not url:
            return None
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if request:
            try:
                return request.build_absolute_uri(url)
            except Exception:
                return url
        return url

    def get_car_image_logo_url(self, obj):
        return self.build_absolute_file_url(
            getattr(obj, "car_image_logo", None)
        )

    def get_car_image_portfolio_url(self, obj):
        return self.build_absolute_file_url(
            getattr(obj, "car_image_portfolio", None)
        )

    def get_tex_pasport_url(self, obj):
        return self.build_absolute_file_url(
            getattr(obj, "tex_pasport", None)
        )

    def get_car_images(self, obj):
        images = CarImage.objects.filter(car=obj).order_by("id")
        return CarImageSerializer(
            images,
            many=True,
            context=self.context
        ).data

class AvailableCarTimeFilterSerializer(serializers.Serializer):
    company = serializers.IntegerField(required=False)
    filial = serializers.IntegerField(required=True)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()


class AvailableCarModelFilterSerializer(serializers.Serializer):
    car_model = serializers.IntegerField()
    company = serializers.IntegerField(required=False)
    filial = serializers.IntegerField(required=False)


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
        fields = "__all__"
        read_only_fields = ['id', 'name_ru', 'name_en', 'password']
        translatable_fields = ['name']


class ManagerSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all())
    filial = serializers.PrimaryKeyRelatedField(queryset=Filial.objects.all())

    class Meta:
        model = Manager
        fields = "__all__"
        read_only_fields = ["approwed_by", "role", 'password']

    def create(self, validated_data):
        request = self.context.get("request")

        validated_data["role"] = "manager"

        if request and getattr(request.user, "role", "").lower() == "superadmin":
            validated_data["approwed_by"] = request.user

        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["manager"] = {
            "id": instance.id,
            "phone": instance.phone,
            "phone1": instance.phone1,
            "login": instance.login,
            "role": instance.role,
            "status": instance.status,
            "work_time": instance.work_time,
        }

        data["company"] = {
            "id": instance.company.id,
            "name": instance.company.name,
        }

        data["filial"] = {
            "id": instance.filial.id,
            "name": instance.filial.name,
        }

        return data

    

class ManagerCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manager
        fields = "__all__"
        read_only_fields = ["approwed_by", "role", 'password']
    

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
    manager_name = serializers.CharField(source="manager.username", read_only=True)

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
        read_only_fields = ("id", "created_at", "messages")


class NotificationSerializer(AutoTranslateMixin, serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    manager_name = serializers.CharField(source="manager.username", read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "user",
            "user_name",
            "manager",
            "manager_name",
            "title",
            "title_ru",
            "title_en",
            "message",
            "message_ru",
            "message_en",
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
        translatable_fields = ["title", "message"]


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
        plan = validated_data.get('plan')
        if 'price' not in validated_data:
            validated_data['price'] = PLAN_PRICES.get(plan, 0)
        if 'end_date' not in validated_data:
            validated_data['end_date'] = validated_data.get('start_date') + timedelta(days=30)
        return super().create(validated_data)

    def update(self, instance, validated_data):
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
        if price is not None and price <= 0:
            raise serializers.ValidationError("Price 0 dan katta bo'lishi kerak.")
        return price


class BotNotificationSerializer(AutoTranslateMixin, serializers.ModelSerializer):
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
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = CarImage
        fields = [
            "id",
            "car",
            "image",
            "image_url",
        ]
        read_only_fields = ["id", "image_url"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        image = getattr(obj, "image", None)
        if not image:
            return None
        try:
            url = image.url
        except Exception:
            url = str(image)
        if not url:
            return None
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if request:
            return request.build_absolute_uri(url)
        return url


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
        

class UploadURLResponseSerializer(serializers.Serializer):
    upload_url = serializers.CharField()
    file_url = serializers.CharField()
    
class UploadURLRequestSerializer(serializers.Serializer):
    file_name = serializers.CharField()
    
    
class StaffOrderListItemSerializer(serializers.ModelSerializer):
    car = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    order_id = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_id",
            "status",
            "status_display",
            "car",
            "start_date",
            "end_date",
            "total_price",
        ]

    def get_order_id(self, obj):
        return (
            getattr(obj, "order_id", None)
            or getattr(obj, "order_number", None)
            or getattr(obj, "code", None)
            or f"#{obj.id}"
        )

    def get_status_display(self, obj):
        if hasattr(obj, "get_status_display"):
            return obj.get_status_display()
        return getattr(obj, "status", None)

    def get_start_date(self, obj):
        value = (
            getattr(obj, "start_date", None)
            or getattr(obj, "start_time", None)
            or getattr(obj, "from_date", None)
            or getattr(obj, "take_date", None)
        )
        return self.format_datetime(value)

    def get_end_date(self, obj):
        value = (
            getattr(obj, "end_date", None)
            or getattr(obj, "end_time", None)
            or getattr(obj, "to_date", None)
            or getattr(obj, "return_date", None)
        )
        return self.format_datetime(value)

    def get_total_price(self, obj):
        return (
            getattr(obj, "total_price", None)
            or getattr(obj, "total_amount", None)
            or getattr(obj, "price", None)
            or getattr(obj, "amount", None)
        )

    def get_car(self, obj):
        car = getattr(obj, "car", None)

        if not car:
            return None

        return {
            "id": car.id,
            "name": self.get_car_name(car),
            "plate_number": (
                getattr(car, "plate_number", None)
                or getattr(car, "number", None)
                or getattr(car, "car_number", None)
                or getattr(car, "state_number", None)
            ),
            "image": self.get_car_image(car),
        }

    def get_car_name(self, car):
        brand = getattr(car, "brand", None)
        model = getattr(car, "model", None)

        brand_name = getattr(brand, "name", None) if brand else None
        model_name = getattr(model, "name", None) if model else None

        if brand_name or model_name:
            return f"{brand_name or ''} {model_name or ''}".strip()

        return str(car)

    def get_car_image(self, car):
        request = self.context.get("request")

        try:
            car_image = CarImage.objects.filter(car=car).first()
            if car_image and car_image.image:
                url = car_image.image.url
                return request.build_absolute_uri(url) if request else url
        except Exception:
            pass

        return None

    def format_datetime(self, value):
        if not value:
            return None

        try:
            return value.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return str(value)


class StaffOrderDetailSerializer(serializers.ModelSerializer):
    order_id = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    customer = serializers.SerializerMethodField()
    car = serializers.SerializerMethodField()
    manager = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()

    order_details = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()
    previous_orders = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_id",
            "status",
            "status_display",
            "customer",
            "car",
            "manager",
            "company",
            "order_details",
            "payment",
            "previous_orders",
        ]

    def get_order_id(self, obj):
        return (
            getattr(obj, "order_id", None)
            or getattr(obj, "order_number", None)
            or getattr(obj, "code", None)
            or f"#{obj.id}"
        )

    def get_status_display(self, obj):
        if hasattr(obj, "get_status_display"):
            return obj.get_status_display()
        return getattr(obj, "status", None)

    def get_customer(self, obj):
        user = getattr(obj, "user", None)

        if not user:
            return None

        return {
            "id": user.id,
            "full_name": (
                getattr(user, "full_name", None)
                or getattr(user, "username", None)
                or getattr(user, "phone", None)
            ),
            "phone": getattr(user, "phone", None),
            "second_phone": (
                getattr(user, "second_phone", None)
                or getattr(user, "extra_phone", None)
                or getattr(user, "additional_phone", None)
            ),
            "passport": (
                getattr(user, "passport", None)
                or getattr(user, "passport_number", None)
            ),
            "birth_date": self.format_date(
                getattr(user, "birth_date", None)
                or getattr(user, "date_of_birth", None)
            ),
            "address": getattr(user, "address", None),
            "role": getattr(user, "role", None),
            "order_count": getattr(user, "order_count", 0),
        }

    def get_car(self, obj):
        car = getattr(obj, "car", None)

        if not car:
            return None

        brand = getattr(car, "brand", None)
        model = getattr(car, "model", None)

        brand_name = getattr(brand, "name", None) if brand else None
        model_name = getattr(model, "name", None) if model else None

        return {
            "id": car.id,
            "name": f"{brand_name or ''} {model_name or ''}".strip() or str(car),
            "brand": brand_name,
            "model": model_name,
            "plate_number": (
                getattr(car, "plate_number", None)
                or getattr(car, "number", None)
                or getattr(car, "car_number", None)
                or getattr(car, "state_number", None)
            ),
            "color": getattr(car, "color", None),
            "year": getattr(car, "year", None),
            "transmission": getattr(car, "transmission", None),
            "fuel_type": getattr(car, "fuel_type", None),
            "status": getattr(car, "status", None),
            "deposit": getattr(car, "deposit", None),
            "daily_price": (
                getattr(car, "daily_price", None)
                or getattr(car, "price_per_day", None)
            ),
            "hourly_price": (
                getattr(car, "hourly_price", None)
                or getattr(car, "price_per_hour", None)
            ),
            "image": self.get_car_image(car),
        }

    def get_manager(self, obj):
        manager = getattr(obj, "manager", None)

        if not manager:
            return None

        manager_user = getattr(manager, "user", None)

        return {
            "id": manager.id,
            "full_name": (
                getattr(manager_user, "full_name", None)
                or getattr(manager_user, "username", None)
                or str(manager)
            ) if manager_user else str(manager),
            "phone": getattr(manager_user, "phone", None) if manager_user else None,
        }

    def get_company(self, obj):
        company = self.get_order_company(obj)

        if not company:
            return None

        return {
            "id": company.id,
            "name": getattr(company, "name", None),
        }

    def get_order_details(self, obj):
        return {
            "created_at": self.format_datetime(getattr(obj, "created_at", None)),
            "start_date": self.format_datetime(
                getattr(obj, "start_date", None)
                or getattr(obj, "start_time", None)
                or getattr(obj, "from_date", None)
                or getattr(obj, "take_date", None)
            ),
            "end_date": self.format_datetime(
                getattr(obj, "end_date", None)
                or getattr(obj, "end_time", None)
                or getattr(obj, "to_date", None)
                or getattr(obj, "return_date", None)
            ),
            "pickup_filial": self.get_filial_name(
                getattr(obj, "pickup_filial", None)
                or getattr(obj, "from_filial", None)
                or getattr(obj, "filial", None)
            ),
            "return_filial": self.get_filial_name(
                getattr(obj, "return_filial", None)
                or getattr(obj, "to_filial", None)
                or getattr(obj, "filial", None)
            ),
            "pickup_address": (
                getattr(obj, "pickup_address", None)
                or getattr(obj, "from_address", None)
            ),
            "return_address": (
                getattr(obj, "return_address", None)
                or getattr(obj, "to_address", None)
            ),
            "comment": getattr(obj, "comment", None),
        }

    def get_payment(self, obj):
        return {
            "payment_type": (
                getattr(obj, "payment_type", None)
                or getattr(obj, "payment_method", None)
            ),
            "payment_status": getattr(obj, "payment_status", None),
            "daily_price": (
                getattr(obj, "daily_price", None)
                or getattr(obj, "price_per_day", None)
            ),
            "hourly_price": (
                getattr(obj, "hourly_price", None)
                or getattr(obj, "price_per_hour", None)
            ),
            "rent_price": (
                getattr(obj, "rent_price", None)
                or getattr(obj, "car_price", None)
            ),
            "insurance_price": getattr(obj, "insurance_price", None),
            "delivery_price": getattr(obj, "delivery_price", None),
            "discount_price": (
                getattr(obj, "discount_price", None)
                or getattr(obj, "discount_amount", None)
            ),
            "deposit": getattr(obj, "deposit", None),
            "total_price": (
                getattr(obj, "total_price", None)
                or getattr(obj, "total_amount", None)
                or getattr(obj, "price", None)
                or getattr(obj, "amount", None)
            ),
        }

    def get_previous_orders(self, obj):
        user = getattr(obj, "user", None)

        if not user:
            return []

        previous_orders = (
            Order.objects
            .filter(user=user)
            .exclude(id=obj.id)
            .order_by("-id")[:10]
        )

        return StaffOrderListItemSerializer(
            previous_orders,
            many=True,
            context=self.context
        ).data

    def get_order_company(self, obj):
        company = getattr(obj, "company", None)

        if company:
            return company

        car = getattr(obj, "car", None)
        if car:
            return getattr(car, "company", None)

        manager = getattr(obj, "manager", None)
        if manager:
            return getattr(manager, "company", None)

        return None

    def get_filial_name(self, filial):
        if not filial:
            return None

        return getattr(filial, "name", None) or str(filial)

    def get_car_image(self, car):
        request = self.context.get("request")

        try:
            car_image = CarImage.objects.filter(car=car).first()
            if car_image and car_image.image:
                url = car_image.image.url
                return request.build_absolute_uri(url) if request else url
        except Exception:
            pass

        return None

    def format_datetime(self, value):
        if not value:
            return None

        try:
            return value.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return str(value)

    def format_date(self, value):
        if not value:
            return None

        try:
            return value.strftime("%d.%m.%Y")
        except Exception:
            return str(value)