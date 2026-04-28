from django.contrib import admin
from .models import (
    Notification, ChatMessage, Chat, Rate, Order, Car, CarImage, UserImage,
    Manager, Verification, ValidatedCode, User, CompanyWorkDay, Company,
    CompanySubscription, Transaction, Viloyatlar, CarRate, BotNotification, Filial
)


# ============== COMPANY ADMIN ==============
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'login', 'created_at']
    search_fields = ['name', 'name_ru', 'name_en', 'login']
    list_filter = ['created_at']

    fieldsets = (
        ("Asosiy ma'lumotlar", {
            'fields': (
                'name',
                'login',
                'password',
                'owner',
                'INN',
                'diedline_zalog',
            )
        }),
        ("Rus tili (Avtomatik to‘ldiriladi)", {
            'fields': ('name_ru',),
            'classes': ('collapse',),
        }),
        ("Ingliz tili (Avtomatik to‘ldiriladi)", {
            'fields': ('name_en',),
            'classes': ('collapse',),
        }),
        ("To‘lov tizimlari", {
            'fields': (
                'click_id',
                'payme_id',
                'payme_callback_url',
                'payme_key',
                'uzum_id',
            ),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ['name_ru', 'name_en']



# ============== FILIAL ADMIN ==============
@admin.register(Filial)
class FilialAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'phone']
    search_fields = ['name', 'name_ru', 'name_en', 'phone']
    list_filter = ['company']
    
    fieldsets = (
        ('O\'zbek tili (Asosiy)', {
            'fields': ('name', 'company', 'address', 'phone')
        }),
        ('Rus tili (Avtomatik)', {
            'fields': ('name_ru', 'address_ru'),
            'classes': ('collapse',)
        }),
        ('Ingliz tili (Avtomatik)', {
            'fields': ('name_en', 'address_en'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['name_ru', 'name_en', 'address_ru', 'address_en']


# ============== CAR ADMIN ==============
@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('car_name', 'car_model', 'status', 'created')
    search_fields = ('car_name',)
    list_filter = ('status',)

    readonly_fields = ()  # bu yerda RU/EN yo‘Q

    fieldsets = (
        ("Asosiy ma'lumotlar", {
            'fields': (
                'car_name',
                'car_model',
                'car_number',
                'commit',
            )
        }),
    )



# ============== NOTIFICATION ADMIN ==============
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'manager', 'title', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['title', 'title_ru', 'title_en', 'message']
    
    fieldsets = (
        ('O\'zbek tili', {
            'fields': ('user', 'manager', 'title', 'message', 'is_read')
        }),
        ('Rus tili (Avtomatik)', {
            'fields': ('title_ru', 'message_ru'),
            'classes': ('collapse',)
        }),
        ('Ingliz tili (Avtomatik)', {
            'fields': ('title_en', 'message_en'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['title_ru', 'title_en', 'message_ru', 'message_en']


# ============== BOT NOTIFICATION ADMIN ==============
@admin.register(BotNotification)
class BotNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'manager', 'title', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['title', 'title_ru', 'title_en', 'message']
    
    fieldsets = (
        ('O\'zbek tili', {
            'fields': ('user', 'manager', 'title', 'message', 'photo', 'is_read')
        }),
        ('Rus tili (Avtomatik)', {
            'fields': ('title_ru', 'message_ru'),
            'classes': ('collapse',)
        }),
        ('Ingliz tili (Avtomatik)', {
            'fields': ('title_en', 'message_en'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['title_ru', 'title_en', 'message_ru', 'message_en']


# ============== CAR RATE ADMIN ==============
@admin.register(CarRate)
class CarRateAdmin(admin.ModelAdmin):
    list_display = ['car', 'user', 'rate', 'created_at']
    list_filter = ['rate', 'created_at']
    search_fields = ['comment', 'comment_ru', 'comment_en', 'company_reply']
    
    fieldsets = (
        ('Asosiy', {
            'fields': ('car', 'user', 'rate', 'created_at')
        }),
        ('Izoh (O\'zbek)', {
            'fields': ('comment',)
        }),
        ('Izoh tarjimasi (Avtomatik)', {
            'fields': ('comment_ru', 'comment_en'),
            'classes': ('collapse',)
        }),
        ('Kompaniya javobi (O\'zbek)', {
            'fields': ('company_reply', 'company_user', 'reply_created_at')
        }),
        ('Javob tarjimasi (Avtomatik)', {
            'fields': ('company_reply_ru', 'company_reply_en'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'comment_ru', 'comment_en', 
                       'company_reply_ru', 'company_reply_en']


# ============== QOLGAN MODELLAR (oddiy registratsiya) ==============
admin.site.register(ChatMessage)
admin.site.register(Chat)
admin.site.register(Rate)
admin.site.register(Order)
admin.site.register(CarImage)
admin.site.register(UserImage)
admin.site.register(Manager)
admin.site.register(Verification)
admin.site.register(ValidatedCode)
admin.site.register(User)
admin.site.register(CompanyWorkDay)
admin.site.register(CompanySubscription)
admin.site.register(Viloyatlar)

# Transaction admin (agar kerak bo'lsa uncommment qiling)
# class TransactionAdmin(admin.ModelAdmin):
#     list_display = ('id', 'click_trans_id', 'merchant_trans_id', 'amount', 'action', 'status', 'sign_datetime')
#     list_display_links = ('id',)
#     list_filter = ('status',)
#     search_fields = ['status', 'id', 'merchant_trans_id']
# admin.site.register(Transaction, TransactionAdmin)
