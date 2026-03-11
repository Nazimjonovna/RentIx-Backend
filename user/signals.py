import requests
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BotNotification, ChekInOut, User, Order
from django.db.models.signals import pre_save
from django.dispatch import receiver
from googletrans import Translator
from .models import (
    Company, Filial, Car, Discount, 
    Notification, BotNotification, CarRate
)

# Google Translator instance
translator = Translator()


TELEGRAM_API_URL = f"https://t.me/RentiixBot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"


@receiver(post_save, sender=Order)
def update_user_order_count_and_role(sender, instance, created, **kwargs):
    """
    Har safar yangi Order yaratildi:
    - user.order_count +1 bo'ladi
    - agar order_count >= 2 bo'lsa, role 'regular customer' ga o'zgaradi
    """
    if created:
        user = instance.user
        # order_count +1 (oldingi qiymat bo'lmasa 0)
        user.order_count = (user.order_count or 0) + 1
        # Agar order_count 2 yoki undan ko'p bo'lsa role o'zgartirish
        if user.order_count >= 2:
            user.role = "regular customer"
        user.save()


@receiver(post_save, sender=BotNotification)
def send_notification_to_users(sender, instance, created, **kwargs):
    if not created:
        return

    users = User.objects.all()

    text = f"📢 *{instance.title}*\n\n{instance.message}"

    for user in users:
        payload = {
            "chat_id": user.telegram_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(TELEGRAM_API_URL, json=payload, timeout=5)
        except Exception as e:
            print(f"Failed to send to {user.telegram_id}: {e}")


@receiver(post_save, sender=ChekInOut)
def set_car_unavailable(sender, instance, created, **kwargs):
    if created:
        car = instance.car
        car.status = "unavailable"
        car.save(update_fields=["status"])


def finish_checkout(request, pk):
    check = ChekInOut.objects.get(pk=pk)

    # checkout images yuklandi deb hisoblaymiz
    if check.checkout_images.exists():
        car = check.car
        car.status = "available"
        car.save()

    return requests.Response({"status": "completed"})

#Til bo'yicha konfiguratsiya



def translate_text(text, dest_lang):
    if not text or not text.strip():
        return text
    try:
        return translator.translate(
            text,
            src='auto',   
            dest=dest_lang
        ).text
    except Exception as e:
        print("Tarjima xatosi:", e)
        
        return text


@receiver(pre_save, sender=Car)
def car_auto_translate(sender, instance, **kwargs):
    print(">>> Pre-save signal ishlayapti <<<")
    # car_name
    if instance.car_name:
        instance.car_name_ru = translate_text(instance.car_name, 'ru')
        instance.car_name_en = translate_text(instance.car_name, 'en')

    # commit
    if instance.commit:
        instance.commit_ru = translate_text(instance.commit, 'ru')
        instance.commit_en = translate_text(instance.commit, 'en')

# ============== COMPANY MODEL TRANSLATION ==============
@receiver(pre_save, sender=Company)
def auto_translate_company(sender, instance, **kwargs):
    """Company modelini avtomatik tarjima qiladi"""
    if instance.name and not instance.name_ru:
        instance.name_ru = translate_text(instance.name, 'ru')
        instance.name_en = translate_text(instance.name, 'en')


# ============== FILIAL MODEL TRANSLATION ==============
@receiver(pre_save, sender=Filial)
def auto_translate_filial(sender, instance, **kwargs):
    """Filial modelini avtomatik tarjima qiladi"""
    if instance.name and not instance.name_ru:
        instance.name_ru = translate_text(instance.name, 'ru')
        instance.name_en = translate_text(instance.name, 'en')
    
    if instance.address and not instance.address_ru:
        instance.address_ru = translate_text(instance.address, 'ru')
        instance.address_en = translate_text(instance.address, 'en')


# # ============== CAR MODEL TRANSLATION ==============
# @receiver(pre_save, sender=Car)
# def auto_translate_car(sender, instance, **kwargs):
#     """Car modelini avtomatik tarjima qiladi"""
#     if instance.car_name and not instance.car_name_ru:
#         instance.car_name_ru = translate_text(instance.car_name, 'ru')
#         instance.car_name_en = translate_text(instance.car_name, 'en')
    
#     if instance.commit and not instance.commit_ru:
#         instance.commit_ru = translate_text(instance.commit, 'ru')
#         instance.commit_en = translate_text(instance.commit, 'en')


# ============== DISCOUNT MODEL TRANSLATION ==============
@receiver(pre_save, sender=Discount)
def auto_translate_discount(sender, instance, **kwargs):
    """Discount modelida title yoki description bo'lsa tarjima qiladi"""
    if hasattr(instance, 'title') and instance.title and not instance.title_ru:
        instance.title_ru = translate_text(instance.title, 'ru')
        instance.title_en = translate_text(instance.title, 'en')
    
    if hasattr(instance, 'description') and instance.description and not instance.description_ru:
        instance.description_ru = translate_text(instance.description, 'ru')
        instance.description_en = translate_text(instance.description, 'en')


# ============== NOTIFICATION MODEL TRANSLATION ==============
@receiver(pre_save, sender=Notification)
def auto_translate_notification(sender, instance, **kwargs):
    """Notification modelini avtomatik tarjima qiladi"""
    if instance.title and not instance.title_ru:
        instance.title_ru = translate_text(instance.title, 'ru')
        instance.title_en = translate_text(instance.title, 'en')
    
    if instance.message and not instance.message_ru:
        instance.message_ru = translate_text(instance.message, 'ru')
        instance.message_en = translate_text(instance.message, 'en')


# ============== BOT NOTIFICATION MODEL TRANSLATION ==============
@receiver(pre_save, sender=BotNotification)
def auto_translate_bot_notification(sender, instance, **kwargs):
    """BotNotification modelini avtomatik tarjima qiladi"""
    if instance.title and not instance.title_ru:
        instance.title_ru = translate_text(instance.title, 'ru')
        instance.title_en = translate_text(instance.title, 'en')
    
    if instance.message and not instance.message_ru:
        instance.message_ru = translate_text(instance.message, 'ru')
        instance.message_en = translate_text(instance.message, 'en')


# ============== CAR RATE (Comment) MODEL TRANSLATION ==============
@receiver(pre_save, sender=CarRate)
def auto_translate_car_rate(sender, instance, **kwargs):
    """CarRate modelidagi comment va company_reply ni tarjima qiladi"""
    if instance.comment and not instance.comment_ru:
        instance.comment_ru = translate_text(instance.comment, 'ru')
        instance.comment_en = translate_text(instance.comment, 'en')
    
    if instance.company_reply and not instance.company_reply_ru:
        instance.company_reply_ru = translate_text(instance.company_reply, 'ru')
        instance.company_reply_en = translate_text(instance.company_reply, 'en')
