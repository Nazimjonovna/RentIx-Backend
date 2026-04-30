from datetime import timedelta
from django.db import models
from django.conf import settings
from django.db.models import Avg, Sum
from django.utils import timezone
from datetime import datetime
from django.templatetags.static import static
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

MODEL = [
    ("chevrolet_cobalt", "Chevrolet Cobalt"),
    ("chevrolet_damas", "Chevrolet Damas"),
    ("chevrolet_tracker", "Chevrolet Tracker"),
    ("chevrolet_onix", "Chevrolet Onix"),
    ("chevrolet_labo", "Chevrolet Labo"),
    ("chevrolet_lacetti", "Chevrolet Lacetti"),
    ("kia_sonet", "KIA Sonet"),
    ("byd_song_plus_champion", "BYD Song Plus Champion"),
    ("byd_chazor", "BYD Chazor"),
    ("chery_tiggo", "Chery Tiggo"),
]

COLOR = [
    ("white", "White"),
    ("smoky", "Smoky"),
    ("dark_gray", "Dark Gray"),
    ("silver", "Silver"),
    ("pearl_gray", "Pearl-Gray"),
    ("black", "Black"),
    ("pearl_brown", "Pearl-Brown"),
    ("burnt_coconut", "Burnt Coconut"),
    ("glossy_gray", "Glossy Gray"),
    ("dark_turquoise", "Dark Turquoise"),
]

STATUS_CAR = [
    ("budget", "Budget"),
    ("premium", "Premium"),
    ("crossovers", "Crossovers"),
    ("suvs", "SUVs"),
    ("minivans", "Minivans"),
    ("pickup_trucks", "Pickup trucks"),
]

USER_ROLES = [
    ("superadmin", "SuperAdmin"),
    ("admin", "Admin"),
    ("manager", "Manager"),
    ("cutomer", "customer"),
    ("regular customer", "regular customer"),
]

STATUS = [
    ("active", "Active"),
    ("pending", "Pending"),
    ("busy", "Busy"),
]

CarStatus = [
    ("available", "Available"),
    ("unavailable", "Unavailable"),
]

Status_User = [
    ('active', 'active'),
    ('deactive', 'deactive'),
]

VILOYATLAR = [
    ('andijan', 'Andijon'),
    ('bukhara', 'Buxoro'),
    ('fergana', 'Fargʻona'),
    ('jizzakh', 'Jizzax'),
    ('namangan', 'Namangan'),
    ('navoi', 'Navoiy'),
    ('kashkadarya', 'Qashqadaryo'),
    ('samarkand', 'Samarqand'),
    ('sirdarya', 'Sirdaryo'),
    ('surkhandarya', 'Surxondaryo'),
    ('tashkent', 'Toshkent'),
    ('khorezm', 'Xorazm'),
]

Fuel = [
    ("Benzin", "Benzin"),
    ("Gibrid", "Gibrid"),
    ("Electro", "Electro"),
    ("Gaz", "Gaz"),
]

Plan = [
    ("basic", "Basic"),
    ("standard", "Standard"),
    ("premium", "Premium"),
    ("VIP", "VIP"),
]

PLAN_PRICES = {
    "basic": 50000,
    "standard": 70000,
    "premium": 100000,
    "VIP": 200000,
}

NotificationDay = [
    ("1", "1"),
    ("12", "12"),
    ("24", "24"),
    ("78", "78"),
]

Location_ok = [
    ("company_address", "Company Address"),
    ("international_airport", "International Airport"),
    ("national_airport", "National Airport"),
    ("other", "Other"),
]

PAYMENT_SYSTEM = [
    ("click", "Click"),
    ("payme", "Payme"),
    ("uzum", "Uzum"),
    ("card", "Card"),
    ("cash", "Cash"),
]

Codes = [
    ("01", "01"),
    ("10", "10"),
    ("20", "20"),
    ("25", "25"),
    ("30", "30"),
    ("40", "40"),
    ("50", "50"),
    ("60", "60"),
    ("70", "70"),
    ("75", "75"),
    ("80", "80"),
    ("85", "85"),
    ("90", "90"),
]


WEEKDAYS = (
    (0, "Dushanba"),
    (1, "Seshanba"),
    (2, "Chorshanba"),
    (3, "Payshanba"),
    (4, "Juma"),
    (5, "Shanba"),
    (6, "Yakshanba"),
)


class UserManager(BaseUserManager):
    """
    create_user: qaysi ma'lumot berilganiga qarab user yaratadi:
    - agar phone + password bo'lsa odatiy ro'yhatdan o'tqazish
    - agar telegram_id berilsa: tg user yaratiladi parolsiz
    - kamida birini berish talab qilinadi
    """
    use_in_migrations = True

    def _create_user(self, username, phone, password, **extra_fields):
        if not phone:
            raise ValueError("Phone required")
        
        if not username:
            username = phone

        user = self.model(username = username, phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password() #Telegram id bilan auto login uchun kk
        user.save()
        return user

    def create_user(self, phone, telegram_id, password = None, username = None, **extra_fields):
        """
        Yaratadi:
        - agar phone berilgan bo'lsa: username ni phone qilib oladi(yoki berilgan username) va password bo'lishini kutadi(Mobil version uchun)
        - agar telegram_id berilgan bo'lsa: username ni 'tg_<telegram_id>' qiladi, password ni unusable qiladi(Telegram orqali authentifikatsiya uchun)
        - agar ikkala ma'lumot ham bo'lsa: phone+password prioritet
        """
        if telegram_id:
            username_final = username or f"tg_{telegram_id}"
            extra_fields.setdefault("telegram_id", telegram_id)
            return self._create_user(username_final, phone, None, **extra_fields)
        
        #Mobil versiya uchun
        if not password:
            raise ValueError("Password is required")
        
        username_final = username or phone
        return self._create_user(username_final, phone, password, **extra_fields)
    
    def create_superuser(self, phone, password=None, username=None, telegram_id=None, **extra_fields):
        """Super User yaratish"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "superadmin")

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff = True")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser = True")
        
        username_final = username or (f"tg_{telegram_id}" if telegram_id else phone)
        if telegram_id and not password:
            extra_fields.setdefault("telegram_id", telegram_id)
            return self._create_user(username_final, phone, None, **extra_fields)
        return self._create_user(username_final, phone, password, **extra_fields)
    
    def create_admin(self, phone, password=None, username=None, telegram_id=None, **extra_fields):
        """Admin(company egasi) ni yaratish funksiyasi"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")

        username_final = username or (f"tg_{telegram_id}" if telegram_id else phone)
        if telegram_id and not password:
            extra_fields.setdefault("telegram_id", telegram_id)
            return self._create_user(username_final, phone, None, **extra_fields)
        return self._create_user(username_final, phone, password, **extra_fields)
    
    def create_manager(self, phone, password=None, username=None, telegram_id=None, **extra_fields):
        """Manager(company ishchilari) ni yaratish funksiyasi"""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", "manager")

        username_final = username or (f"tg_{telegram_id}" if telegram_id else phone)
        if telegram_id and not password:
            extra_fields.setdefault("telegram_id", telegram_id)
            return self._create_user(username_final, phone, None, **extra_fields)
        return self._create_user(username_final, phone, password, **extra_fields)
    

class Company(models.Model):
    name = models.CharField(max_length=500)
    created_at = models.DateField(auto_now=True)
    password = models.TextField(null=True, blank=True)
    login = models.TextField(null=True, blank=True)
    phone_regex = RegexValidator(
        regex=r'^\+?\d{9,15}$',
        message="Telefon raqamini +9989XXXXXXXX kabi kiriting!"
    )
    phone1 = models.CharField(validators=[phone_regex],max_length=200)
    phone2 = models.CharField(validators=[phone_regex],max_length=200)
    full_name = models.TextField()
    role = models.CharField(choices = USER_ROLES, max_length=500, default="admin", editable=False)
    diedline_zalog = models.PositiveIntegerField(default=72, help_text="Kompaniya zalog muddati (soatlarda)")
    INN = models.CharField(max_length=100, null=True, blank=True)
    click_id = models.CharField(max_length=200, null=True, blank=True)
    payme_id = models.CharField(max_length=200, null=True, blank=True)
    payme_callback_url = models.CharField(max_length=500, null=True, blank=True)
    payme_key = models.CharField(max_length=200, null=True, blank=True)     
    uzum_id = models.CharField(max_length=200, null=True, blank=True)
    waiting_from_airport = models.BooleanField(default=False)
    waiting_from_air = models.BooleanField(default=False)
    driver = models.BooleanField(default=False)
    cost_driver = models.FloatField(default=0)
    airport_VIP_cost = models.FloatField(default=0)
    cost_air = models.FloatField(default=0)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        permissions = [
            ("can_view_company_data", "Can view company data"),
            ("can_manage_company", "Can manage company"),
        ]
        
    def save(self, *args, **kwargs):
        self.role = "admin"
        super().save(*args, **kwargs)
        
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False        

    def __str__(self):
        return self.name


class Filial(models.Model):
    name = models.CharField(max_length=500)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="filials")
    address = models.TextField(null=True, blank=True)
    phone_regex = RegexValidator(
        regex=r'^\+?\d{9,15}$',
        message="Telefon raqamini +9989XXXXXXXX kabi kiriting!"
    )
    phone = models.CharField(validators=[phone_regex],max_length=200)

    def __str__(self):
        return self.name
    

# Har bir kompaniya uchun haftalik ish jadvali
class CompanyWorkDay(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="work_days"
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.CASCADE,
        related_name="work_days"
    )
    weekday = models.IntegerField(choices=WEEKDAYS)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    is_working = models.BooleanField(default=True)
    is_24_7 = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Company Work Day"
        verbose_name_plural = "Company Work Days"
        unique_together = ("filial", "weekday")
        ordering = ["filial", "weekday"]

    def clean(self):
        if self.filial and self.company and self.filial.company_id != self.company_id:
            raise ValidationError("Filial ushbu companyga tegishli emas")
        if not self.is_working:
            self.is_24_7 = False
            self.start_time = None
            self.end_time = None
            return
        if self.is_24_7:
            self.start_time = None
            self.end_time = None
            return
        if not self.start_time or not self.end_time:
            raise ValidationError("Ish kuni bo‘lsa start_time va end_time majburiy")
        if self.start_time >= self.end_time:
            raise ValidationError("start_time end_time dan oldin bo‘lishi kerak")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        day_name = self.get_weekday_display()
        if not self.is_working:
            return f"{self.filial.name} — {day_name}: Dam olish"
        if self.is_24_7:
            return f"{self.filial.name} — {day_name}: 24/7"
        return f"{self.filial.name} — {day_name}: {self.start_time} - {self.end_time}"


class User(AbstractUser):
    phone_regex = RegexValidator(
        regex=r'^\+?\d{9,15}$',
        message="Telefon raqamini +9989XXXXXXXX kabi kiriting!"
    )
    phone = models.CharField(validators=[phone_regex],max_length=200, unique=True)
    phone_tg = models.CharField(validators = [ phone_regex], max_length=200, null=True, blank=True)                                      #User da tgda boshqa nomer bo'lsa startni bosganda shu yerga tushadi
    telegram_id = models.BigIntegerField(unique= True, null=True, blank=True)
    full_name = models.TextField(null = True, blank = True)
    age = models.IntegerField(null = True, blank = True)
    address = models.TextField(null = True, blank = True)
    tg_nick = models.CharField(max_length=200, null = True, blank = True)
    driver_litsence = models.FileField(null = True, blank = True)
    created_at = models.DateField(auto_now=True)
    pasport = models.TextField(null = True, blank = True)
    pasport_image = models.FileField(null = True, blank = True)
    pasport_given_date = models.DateField(null = True, blank = True)
    pasport_exp_date = models.DateField(null = True, blank = True)
    pasport_place = models.TextField(null = True, blank = True)
    lived_address = models.TextField(null = True, blank = True)
    updated_at = models.DateField(auto_now=True)
    company = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        limit_choices_to={"role":"admin"}, # bunda barcha user lardan faqat company larni filter qilib beradi
        help_text="Foydalanuvchining ishlaydigan kompaniyasi(adminga ishora qiladi)"
    )
    role = models.CharField(max_length=20, choices=USER_ROLES, default='user')
    is_blocked = models.BooleanField(default=False)
    order_count = models.IntegerField(default=0)
    code = models.CharField(max_length=10, null=True, blank=True, help_text="So‘nggi yuborilgan OTP kodi")
    is_phone_verified = models.BooleanField(default=False, help_text="Telefon raqami SMS orqali tasdiqlangan")
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )
    objects = UserManager()
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        permissions = [
            ("can_create_order", "Can create order"),
            ("can_delete_own_order", "Can delete own order"),
        ]
    
    def __str__(self):
        return self.full_name or self.username or f"tg:{self.telegram_id} - {self.tg_nick}"


class UserImage(models.Model):
    image = models.FileField(upload_to = 'images/')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="images")

    class Meta:
        verbose_name = "User Image"
        verbose_name_plural = "User Images"

    def __str__(self):
        return f"{self.user.full_name} | {self.image}"
    

class ValidatedCode(models.Model):
    """
    Ushbu model foydalanuvchiga yuborilgan SMS kodni saqlaydi.
    Kodni kiritishlar sonini va validatsiya holatini kuzatadi.
    """
    phone_regex = RegexValidator(
        regex=r'^\+?\d{9,15}$',
        message="Telefon raqamini +9989XXXXXXXX kabi kiriting!"
    )
    phone = models.CharField(validators=[phone_regex], max_length=15, unique=True)
    code = models.CharField(max_length=9, blank=True, null=True)
    count = models.IntegerField(default=0, help_text='Kodni kiritishlar soni:')
    validated = models.BooleanField(default=False, help_text="Shaxsiy kabinetingizni yaratishingiz mumkin!")

    def __str__(self):
        return f"{self.phone} - {'✅' if self.validated else '❌'}"


class Verification(models.Model):
    """
    SMS orqali yuborilgan tasdiqlash kodi.
    Foydalanuvchi ro‘yxatdan o‘tishda yoki telefon raqamini almashtirganda ishlatiladi.
    """
    STATUS = (
        ('send', 'send'),
        ('confirmed', 'confirmed'),
    )

    phone = models.CharField(max_length=15, unique=True)
    verify_code = models.SmallIntegerField()
    is_verified = models.BooleanField(default=False)
    step_reset = models.CharField(max_length=10, null=True, blank=True, choices=STATUS)
    step_change_phone = models.CharField(max_length=30, null=True, blank=True, choices=STATUS)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.phone} --- {self.verify_code}"
    
    
class Manager(models.Model):
    phone_regex = RegexValidator(regex=r'^\+?\d{9,15}$', message="Telefon raqamini +9989XXXXXXXX kabi kiriting!")
    phone = models.CharField(validators=[phone_regex],max_length=200)
    phone1 = models.CharField(validators=[phone_regex], max_length=200, null=True, blank=True)
    full_name = models.TextField()
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="managers")
    filial = models.ForeignKey(Filial, on_delete=models.CASCADE, related_name="managers")
    role = models.CharField(choices = USER_ROLES, max_length=500, default="manager", editable=False)
    work_time = models.CharField(max_length = 500)
    password = models.TextField(null=True, blank=True)
    login = models.TextField(null=True, blank=True)
    status = models.CharField(choices = Status_User, max_length=500)
    approwed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approwed_managers",
        limit_choices_to={"role":"superadmin"},
        help_text="Superadmin tomonidan tasdiqlangan"
    )
    
    class Meta:
        verbose_name = "Manager"
        verbose_name_plural = "Managers"
        permissions = [
            ("can_manage_orders", "can manage company orders"),
        ]
        
    def clean(self):
        if self.filial and self.company and self.filial.company_id != self.company_id:
            raise ValidationError("Manager filiali ushbu companyga tegishli emas")
        
    def save(self, *args, **kwargs):
        self.role = "manager"
        super().save(*args, **kwargs)
        
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __str__(self):
        return f"{self.full_name} | {self.company} | {self.filial}"
    

class CarImage(models.Model):
    image = models.FileField(upload_to='car-images/')

    class Meta:
        verbose_name = "Image"
        verbose_name_plural = "Images"
        permissions = [
            ("can_manage_images", "Can manage images"),
        ]


class Viloyatlar(models.Model):
    viloyat = models.CharField(choices = VILOYATLAR, max_length=500)
    cost_day = models.FloatField()
    cost_hour = models.FloatField()

    def __str__(self):
        return self.viloyat


class Car(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="cars")
    car_color = models.CharField(choices=COLOR, max_length=500)
    is_auto = models.BooleanField(default=True)
    fuel = models.CharField(max_length=200, choices=Fuel)
    fuel_cons = models.FloatField(default=0)
    sit_number = models.IntegerField(default=0)
    baggage = models.IntegerField(default=0)
    transmission = models.BooleanField(default=False)
    speed = models.IntegerField(default=0)
    power = models.IntegerField(default=0)
    conditioner = models.BooleanField(default=False)
    insurance = models.BooleanField(default=False)
    age_for = models.IntegerField(default=0)
    day_limit_city = models.IntegerField(default=0)
    day_limit_reg = models.IntegerField(default=0)
    cashbeck = models.FloatField(default=0)
    cost_day_tash = models.FloatField(default=0)
    cost_hour_tash = models.FloatField(default=0)
    costs = models.ForeignKey(
        Viloyatlar,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    depozit = models.FloatField(default=0)
    is_discount = models.BooleanField(default=False)
    car_model = models.CharField(choices=MODEL, max_length=500)
    car_name = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )
    car_name_ru = models.CharField(max_length=500, null=True, blank=True)
    car_name_en = models.CharField(max_length=500, null=True, blank=True)
    car_code = models.CharField(
        choices=Codes,
        max_length=500,
        null=True,
        blank=True
    )
    car_number = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )
    car_image_logo = models.URLField(null=True, blank=True)
    car_image_portfolio = models.URLField(null=True, blank=True)
    car_image = models.ForeignKey(
        CarImage,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    tex_pasport = models.URLField(null=True, blank=True)
    status = models.CharField(choices=CarStatus, max_length=500)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    commit = models.TextField(null=True, blank=True)
    commit_ru = models.TextField(null=True, blank=True)
    commit_en = models.TextField(null=True, blank=True)
    
# agar VIP emas uchun cost bo'lsa uni ham qo'shish kerak
    class Meta:
        verbose_name = "Car"
        verbose_name_plural = "Cars"
        permissions = [
            ("can_view_company_cars", "Can view company cars"),
            ("can_manage_cars", "Can manage cars"),
        ]

    def __str__(self):
        return self.car_name

    def get_logo_url(self):
        model_name = self.car_model.lower()
        return static(f'{model_name}.png')


class Discount(models.Model):
    discount = models.FloatField()
    is_active = models.BooleanField(default=False)
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='discounts')
    diedline = models.DateField()
    notification_day = models.CharField(max_length=255, choices = NotificationDay, null=True, blank=True)
    new_cost = models.FloatField()
    image =models.FileField(upload_to="discounts/")
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    class Meta:
        verbose_name = "Discount"
        verbose_name_plural = "Discounts"
        permissions = [
            ("can_view_company_discounts", "Can view company discounts"),  
            ("can_manage_discounts", "Can manage discounts"),
        ]

    def save(self, *args, **kwargs):
        # foiz 0–100 oralig‘ida bo‘lishi kerak
        if not 0 <= self.discount <= 100:
            raise ValueError("Discount percent must be between 0 and 100")
        # costdan foizni ayirish
        discount_amount = (self.car.cost * self.discount) / 100
        self.new_cost = self.car.cost - discount_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.discount}"

    
#think about order create logic 
class Order(models.Model):
    user = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        related_name="order_user"
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.CASCADE,
        related_name="orders"
    )
    manager = models.ForeignKey(
        Manager,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_manager"
    )
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location_from = models.CharField(choices=Location_ok, max_length=500)
    location_to = models.CharField(choices=Location_ok, max_length=500)
    airport_VIP = models.BooleanField(default=False)
    is_driver = models.BooleanField(default=False)
    use_cashback = models.BooleanField(default=False)
    status = models.CharField(choices=STATUS, max_length=500)
    payment_system = models.CharField(choices=PAYMENT_SYSTEM, max_length=500)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        permissions = [
            ("can_view_company_orders", "Can view company orders"),
            ("can_manage_orders", "Can manage orders")
        ]

    def __str__(self):
        return f"{self.start_time} dan {self.end_time} gacha {self.user.full_name}"

    def validate_filial_work_time(self, dt):
        weekday = dt.weekday()
        workday = CompanyWorkDay.objects.filter(
            company=self.company,
            filial=self.filial,
            weekday=weekday
        ).first()
        if not workday:
            raise ValidationError(
                f"{dt.date()} kuni uchun filial ish vaqti kiritilmagan"
            )
        if not workday.is_working:
            raise ValidationError(
                f"{dt.date()} kuni filial ishlamaydi"
            )
        if workday.is_24_7:
            return
        current_time = timezone.localtime(dt).time()
        if current_time < workday.start_time or current_time > workday.end_time:
            raise ValidationError(
                f"{dt.date()} kuni filial ish vaqti "
                f"{workday.start_time} - {workday.end_time}"
            )

    def clean(self):
        if self.filial and self.company and self.filial.company_id != self.company_id:
            raise ValidationError("Order filiali ushbu companyga tegishli emas")
        if self.manager:
            if self.manager.company_id != self.company_id:
                raise ValidationError("Manager ushbu companyga tegishli emas")
            if self.manager.filial_id != self.filial_id:
                raise ValidationError("Manager ushbu filialga tegishli emas")
        if self.start_time >= self.end_time:
            raise ValidationError("Boshlanish vaqti tugash vaqtidan oldin bo‘lishi kerak")
        if self.start_time < timezone.now():
            raise ValidationError("Boshlanish vaqti hozirgi vaqtdan oldin bo‘lishi mumkin emas")
        self.validate_filial_work_time(self.start_time)
        self.validate_filial_work_time(self.end_time)

    def calculate_cost(self):
        car = self.car
        duration = self.end_time - self.start_time
        total_hours = duration.total_seconds() / 3600
        total_days = duration.days + (1 if duration.seconds > 0 else 0)
        if car.cost_hour_tash and total_hours <= 24:
            base_cost = total_hours * car.cost_hour_tash
        else:
            base_cost = total_days * car.cost_day_tash
        if self.is_driver:
            base_cost += car.cost_driver
        if self.airport_VIP:
            base_cost += car.airport_VIP_cost
        now = timezone.now()
        active_discounts = car.discounts.filter(
            is_active=True,
            diedline__gte=now.date()
        )
        if active_discounts.exists():
            discount = active_discounts.latest('created_at')
            base_cost = base_cost * (1 - discount.discount / 100)
        if self.use_cashback:
            user_cashback = self.user.cashback_transactions.filter(
                type="earn"
            ).aggregate(
                total_earned=Sum("amount")
            )["total_earned"] or 0
            user_spent = self.user.cashback_transactions.filter(
                type="spend"
            ).aggregate(
                total_spent=Sum("amount")
            )["total_spent"] or 0
            available_cashback = user_cashback - user_spent
            if available_cashback > 0:
                cashback_to_use = min(base_cost, available_cashback)
                base_cost -= cashback_to_use
                CashbackTransaction.objects.update_or_create(
                    user=self.user,
                    order=self,
                    type="spend",
                    defaults={"amount": cashback_to_use}
                )
        return round(base_cost, 2)

    def save(self, *args, **kwargs):
        self.full_clean()
        self.cost = self.calculate_cost()
        super().save(*args, **kwargs)
        if not self.use_cashback:
            cashback_amount = self.cost * self.car.cashbeck / 100
            if cashback_amount > 0:
                CashbackTransaction.objects.update_or_create(
                    user=self.user,
                    order=self,
                    type="earn",
                    defaults={"amount": cashback_amount}
                )


class CashbackTransaction(models.Model):
    CASHBACK_TYPES = (
        ("earn", "Earned"),
        ("spend", "Spent"),
        ("refund", "Refund"),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="cashback_transactions"
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cashback_transactions"
    )
    amount = models.FloatField()
    type = models.CharField(max_length=20, choices=CASHBACK_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.amount} - {self.type}"


class Rate(models.Model):
    user = models.ForeignKey('user.User', on_delete = models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='rates_company')
    manager = models.ForeignKey(Manager, on_delete = models.CASCADE, related_name='rates_manager')
    rate_manager = models.FloatField()
    rate_company = models.FloatField()
    comment = models.TextField(null = True, blank = True)
    created_at = models.DateField(auto_now=True)

    class Meta:
        verbose_name = "Rate"
        verbose_name_plural = "Rates"
        permissions = [
            ("can_view_company_rates", "Can view company rates"),
            ("can_view_manager_rates", "Can view manager rates"),
            ("can_manage_rates", "Can manage rates"),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.company.name} - {self.manager.username}"
    
    def calculate_rate_company(self):
        """
        Ushbu kompaniyaga tegishli barcha managerlarning rate_manager larini olib,
        o‘rtacha qiymatni hisoblaydi va joriy obyektning rate_company qiymatini yangilaydi.
        """
        from django.db.models import Avg

        avg_rate = Rate.objects.filter(company=self.company).aggregate(avg=Avg('rate_manager'))['avg']
        if avg_rate is not None:
            self.rate_company = round(float(avg_rate), 2)
            self.save(update_fields=['rate_company'])
        return self.rate_company

    def calculate_rate_manager(self):
        """
        Ushbu manager uchun barcha userlar tomonidan berilgan rate_manager larni olib,
        o‘rtacha qiymatni hisoblaydi va joriy obyektning rate_manager qiymatini yangilaydi.
        """
        avg_rate = Rate.objects.filter(manager=self.manager).aggregate(avg=Avg('rate_manager'))['avg']
        if avg_rate is not None:
            self.rate_manager = round(float(avg_rate), 2)
            self.save(update_fields=['rate_manager'])
        return self.rate_manager
    
    def save(self, *args, **kwargs):
        """
        Model saqlanganda avtomatik ravishda manager va company uchun o‘rtacha baholarni hisoblaydi.
        """
        super().save(*args, **kwargs)  # avval obyektni saqlab qo'yamiz
        # So‘ng o‘rtacha reytinglarni yangilaymiz
        avg_manager = self.calculate_rate_manager()
        avg_company = self.calculate_rate_company()

        # Obyektdagi qiymatlarni yangilab, qayta saqlaymiz
        if self.rate_manager != avg_manager or self.rate_company != avg_company:
            self.rate_manager = avg_manager
            self.rate_company = avg_company
            super().save(update_fields=['rate_manager', 'rate_company'])


class CarRate(models.Model):
    car = models.ForeignKey("Car", on_delete=models.CASCADE, related_name="car_rates")
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="car_rates_user")
    
    # Rate 0 dan 10 gacha
    rate = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(10.0)
        ]
    )
    comment = models.TextField(null=True, blank=True)  # user comment
    created_at = models.DateField(auto_now=True)

    # ------------------ kompaniya javobi ------------------
    company_reply = models.TextField(null=True, blank=True)
    company_user = models.ForeignKey(
        "User",  # kompaniya user modeli
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_replies"
    )
    reply_created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('car', 'user')  # user bitta mashinaga faqat bir marta baho beradi

    def __str__(self):
        return f"{self.user.full_name} - {self.car.car_name}"

    def save(self, *args, **kwargs):
        """
        Saqlangandan so‘ng mashina o‘rtacha reytingini yangilaydi.
        """
        super().save(*args, **kwargs)
        self.update_car_average_rate()

    def update_car_average_rate(self):
        avg_rate = CarRate.objects.filter(car=self.car).aggregate(avg=Avg('rate'))['avg']
        if avg_rate is not None:
            self.car.average_rate = round(avg_rate, 2)
            self.car.save(update_fields=['average_rate'])


class Chat(models.Model):
    user = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='user_chats')
    manager = models.ForeignKey('Manager', on_delete=models.CASCADE, related_name='manager_chats')
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = "Chat"
        verbose_name_plural = "Chats"
        permissions = [
            ("can_view_company_chats", "Can view company chats"),   
            ("can_view_manager_chats", "Can view manager chats"),
            ("can_manage_chats", "Can manage chats"),
        ]
        
    def save(self, *args, **kwargs):
        # agar order bor bo'lsa manager ni avtomatik qo'yadi
        if self.order and self.order.manager:
            self.manager = self.order.manager
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.full_name} ↔ {self.manager.username}"


class ChatMessage(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    file = models.FileField(upload_to='chat/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.full_name}: {self.message[:30]}"
    
    def get_logo_url(self):
        name = self.sender.lower()
        return static(f'{name}.png')

class Notification(models.Model):
    user = models.ForeignKey('user.User', on_delete = models.CASCADE)
    manager = models.ForeignKey(Manager, on_delete = models.CASCADE, related_name='notifications')
    title = models.TextField()
    message = models.TextField()
    is_read = models.BooleanField(default = False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        permissions = [
            ("can_view_company_notifications", "Can view company notifications"),  
            ("can_view_manager_notifications", "Can view manager notifications"),
            ("can_manage_notifications", "Can manage notifications"),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.manager.username}"


class BotNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE)
    title = models.CharField(max_length=500)
    message = models.TextField()
    photo = models.FileField(upload_to="notifications/")
    is_read = models.BooleanField(default=False)
    created_at = models.DateField(auto_now=True)

    class Meta:
        verbose_name = "BotNotification"
        verbose_name_plural = "BotNotifications"
        permissions = [
            ("can_view_company_notifications", "Can view company notifications"),  
            ("can_view_manager_notifications", "Can view manager notifications"),
            ("can_manage_notifications", "Can manage notifications"),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.manager.username}"


# Keyinchalik Driver ham qo'shiladi hozircha kkmas bu

class Payment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="payments")
    amount = models.FloatField()
    status = models.CharField(max_length=500)
    orderid = models.BigIntegerField(null=True, blank=True)
    time = models.BigIntegerField(null=True, blank=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=100)  # Misol uchun: Click, Payme, Uzum va hokazo
    transaction_id = models.CharField(max_length=200, unique=True)
    xperform_time = models.BigIntegerField(null=True, default=0)
    cancel_time = models.BigIntegerField(null=True, default=0)
    state = models.IntegerField(null=True, default=1)
    reason = models.CharField(max_length=255, null=True, blank=True)
    created_at_ms = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        permissions = [
            ("can_view_company_payments", "Can view company payments"),  
            ("can_manage_payments", "Can manage payments"),
        ]

    def __str__(self):
        return f"Order {self.order.id} - Amount: {self.amount} - Method: {self.payment_method} - Company: {self.company.name}"
    

class CompanySubscription(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.CharField(max_length=20, choices=Plan)
    price = models.PositiveIntegerField(blank=True, null=True)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=True)  # Avtomatik to‘lov qo‘shish uchun

    class Meta:
        ordering = ['-start_date']

    def save(self, *args, **kwargs):
        # Plan narxini avtomatik belgilash
        if not self.price:
            self.price = PLAN_PRICES.get(self.plan, 0)
        # Agar end_date berilmagan bo‘lsa, 1 oy qo‘shamiz
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=30)

        super().save(*args, **kwargs)

    def check_active(self):
        """Aktivlikni tekshirish va yangilash"""
        today = timezone.now().date()
        if self.end_date < today:
            self.is_active = False
        else:
            self.is_active = True

        self.save()


class Transaction(models.Model):
    PROCESSING = 'processing'
    FINISHED = 'finished'
    CANCELED = 'canceled'
    STATUS = ((PROCESSING, PROCESSING), (FINISHED, FINISHED), (CANCELED, CANCELED))
    click_trans_id = models.CharField(max_length=255)
    merchant_trans_id = models.CharField(max_length=255)
    amount = models.CharField(max_length=255)
    action = models.CharField(max_length=255)
    sign_string = models.CharField(max_length=255)
    sign_datetime = models.DateTimeField(max_length=255)
    status = models.CharField(max_length=25, choices=STATUS, default=PROCESSING)

    def __str__(self):
        return self.click_trans_id


class ChekInOut(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    checked_in_at = models.DateTimeField(auto_now_add=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    depozite_user = models.FileField(upload_to="depozite_user/", null=True, blank=True)
    depozite_company = models.FileField(upload_to="depozite_company/", null=True, blank=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.car.car_name}"
    

class ImagesCheckIn(models.Model):
    checkin = models.ForeignKey(
        ChekInOut,
        on_delete=models.CASCADE,
        related_name="checkin_images"
    )
    image = models.FileField(upload_to='checkIn/')


class ImagesCheckOut(models.Model):
    checkin = models.ForeignKey(
        ChekInOut,
        on_delete=models.CASCADE,
        related_name="checkout_images"
    )
    image = models.FileField(upload_to="checkOut/")
