# from modeltranslation.translator import register, TranslationOptions
# from .models import (
#     Viloyatlar,
#     Car,
#     Rate,
#     CarRate,
#     Notification,
#     BotNotification,
# )

# @register(Viloyatlar)
# class ViloyatlarTranslationOptions(TranslationOptions):
#     fields = (
#         'viloyat',
#     )


# @register(Car)
# class CarTranslationOptions(TranslationOptions):
#     fields = (
#         'car_name',
#         'baggage',
#     )



# @register(Rate)
# class RateTranslationOptions(TranslationOptions):
#     fields = (
#         'comment',
#     )


# @register(CarRate)
# class CarRateTranslationOptions(TranslationOptions):
#     fields = (
#         'comment',
#     )

# @register(Notification)
# class NotificationTranslationOptions(TranslationOptions):
#     fields = (
#         'title',
#         'message',
#     )


# @register(BotNotification)
# class BotNotificationTranslationOptions(TranslationOptions):
#     fields = (
#         'title',
#         'message',
#     )


# translation.py
# Bu faylni app papkasiga joylashtiring (models.py bilan bir qatorda)

from modeltranslation.translator import register, TranslationOptions
from .models import (
    Company, Filial, Car, Discount, 
    Notification, BotNotification, CarRate
)


@register(Company)
class CompanyTranslationOptions(TranslationOptions):
    fields = ('name',)  # Tarjima qilinadigan fieldlar


@register(Filial)
class FilialTranslationOptions(TranslationOptions):
    fields = ('name', 'address')


# @register(Car)
# class CarTranslationOptions(TranslationOptions):
#     fields = ('car_name', 'commit')


@register(Discount)
class DiscountTranslationOptions(TranslationOptions):
    # Agar Discount modelida title/description bo'lsa qo'shing
    fields = ()  # Bo'sh qoldiring yoki kerakli fieldlarni qo'shing


@register(Notification)
class NotificationTranslationOptions(TranslationOptions):
    fields = ('title', 'message')


@register(BotNotification)
class BotNotificationTranslationOptions(TranslationOptions):
    fields = ('title', 'message')


@register(CarRate)
class CarRateTranslationOptions(TranslationOptions):
    fields = ('comment', 'company_reply')
