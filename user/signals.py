import logging
import requests

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from django.conf import settings
from django.db import transaction
from django.db.models import F, Value
from django.db.models.functions import Coalesce
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from googletrans import Translator

from .models import (
    User,
    Order,
    ChekInOut,
    Company,
    Filial,
    Car,
    Discount,
    Notification,
    BotNotification,
    CarRate,
    CarModel,
    CarBrand,
)

from .services import create_default_filial_and_workdays


logger = logging.getLogger(__name__)
translator = Translator()



TELEGRAM_BOT_TOKEN = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
TELEGRAM_API_URL = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    if TELEGRAM_BOT_TOKEN
    else None
)


def get_manager_name(manager):
    if not manager:
        return None
    manager_user = getattr(manager, "user", None)
    if manager_user:
        return (
            getattr(manager_user, "full_name", None)
            or getattr(manager_user, "username", None)
            or getattr(manager_user, "phone", None)
            or str(manager_user.id)
        )
    return str(manager)


def get_user_name(user):
    if not user:
        return None
    return (
        getattr(user, "full_name", None)
        or getattr(user, "username", None)
        or getattr(user, "phone", None)
        or str(user.id)
    )


def send_ws_notification_to_user(notification):
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("Channel layer topilmadi. Redis/Channels settingsni tekshiring.")
        return False
    user_id = getattr(notification, "user_id", None)
    if not user_id:
        logger.warning(f"Notification user_id yo'q. notification_id={getattr(notification, 'id', None)}")
        return False
    manager_name = get_manager_name(getattr(notification, "manager", None))
    created_at = None
    if getattr(notification, "created_at", None):
        created_at = notification.created_at.strftime("%Y-%m-%d %H:%M:%S")
    async_to_sync(channel_layer.group_send)(
        f"notify_{user_id}",
        {
            "type": "notify",
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "manager_name": manager_name,
            "created_at": created_at,
            "source": "notification",
        }
    )
    return True


def send_telegram_message(user, text):
    if not TELEGRAM_API_URL:
        logger.warning("TELEGRAM_BOT_TOKEN topilmadi. Telegram xabar yuborilmadi.")
        return False
    telegram_id = getattr(user, "telegram_id", None)
    if not telegram_id:
        return False
    payload = {
        "chat_id": telegram_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    try:
        response = requests.post(
            TELEGRAM_API_URL,
            json=payload,
            timeout=5
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram xabar yuborishda xato. user_id={user.id}, error={e}")
        return False


def translate_text(text, dest_lang):
    if not text or not str(text).strip():
        return text
    try:
        return translator.translate(
            text,
            src="auto",
            dest=dest_lang
        ).text
    except Exception as e:
        logger.error(f"Tarjima xatosi. lang={dest_lang}, error={e}")
        return text


@receiver(post_save, sender=Notification)
def send_notification_ws(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        send_ws_notification_to_user(instance)
    except Exception as e:
        logger.error(
            f"WebSocket notification yuborishda xato. "
            f"notification_id={instance.id}, error={e}"
        )


@receiver(post_save, sender=BotNotification)
def send_bot_notification_to_users(sender, instance, created, **kwargs):
    if not created:
        return
    text = f"*{instance.title}*\n\n{instance.message}"
    users = User.objects.all()
    for user in users:
        try:
            Notification.objects.create(
                user=user,
                manager=instance.manager,
                title=instance.title,
                message=instance.message,
            )
            send_telegram_message(user, text)
        except Exception as e:
            logger.error(
                f"BotNotification yuborishda xato. "
                f"user_id={user.id}, bot_notification_id={instance.id}, error={e}"
            )


@receiver(post_save, sender=Order)
def update_user_order_count_and_role(sender, instance, created, **kwargs):
    if not created:
        return
    user = getattr(instance, "user", None)
    if not user:
        return
    try:
        with transaction.atomic():
            User.objects.filter(id=user.id).update(
                order_count=Coalesce(F("order_count"), Value(0)) + 1
            )
            user.refresh_from_db(fields=["order_count", "role"])
            if user.order_count >= 2 and user.role != "regular customer":
                user.role = "regular customer"
                user.save(update_fields=["role"])
    except Exception as e:
        logger.error(
            f"Order count update qilishda xato. "
            f"order_id={instance.id}, user_id={getattr(user, 'id', None)}, error={e}"
        )


@receiver(post_save, sender=Order)
def send_order_created_notification(sender, instance, created, **kwargs):
    if not created:
        return
    user = getattr(instance, "user", None)
    if not user:
        return
    try:
        Notification.objects.create(
            user=user,
            manager=getattr(instance, "manager", None),
            title="Order yaratildi",
            message="Sizning buyurtmangiz muvaffaqiyatli yaratildi."
        )
    except Exception as e:
        logger.error(
            f"Order notification yaratishda xato. "
            f"order_id={instance.id}, user_id={getattr(user, 'id', None)}, error={e}"
        )


@receiver(post_save, sender=ChekInOut)
def set_car_unavailable(sender, instance, created, **kwargs):
    if not created:
        return
    car = getattr(instance, "car", None)
    if not car:
        return
    try:
        car.status = "unavailable"
        car.save(update_fields=["status"])
    except Exception as e:
        logger.error(
            f"Car status unavailable qilishda xato. "
            f"check_id={instance.id}, car_id={getattr(car, 'id', None)}, error={e}"
        )


@receiver(pre_save, sender=CarBrand)
def car_brand_auto_translate(sender, instance, **kwargs):
    if instance.name:
        if not instance.name_ru:
            instance.name_ru = translate_text(instance.name, "ru")
        if not instance.name_en:
            instance.name_en = translate_text(instance.name, "en")


@receiver(pre_save, sender=CarModel)
def car_model_auto_translate(sender, instance, **kwargs):
    if instance.name:
        if not instance.name_ru:
            instance.name_ru = translate_text(instance.name, "ru")
        if not instance.name_en:
            instance.name_en = translate_text(instance.name, "en")


@receiver(pre_save, sender=Car)
def car_auto_translate(sender, instance, **kwargs):
    if instance.commit:
        if not instance.commit_ru:
            instance.commit_ru = translate_text(instance.commit, "ru")
        if not instance.commit_en:
            instance.commit_en = translate_text(instance.commit, "en")


@receiver(pre_save, sender=Company)
def auto_translate_company(sender, instance, **kwargs):
    if instance.name:
        if not instance.name_ru:
            instance.name_ru = translate_text(instance.name, "ru")
        if not instance.name_en:
            instance.name_en = translate_text(instance.name, "en")


@receiver(pre_save, sender=Filial)
def auto_translate_filial(sender, instance, **kwargs):
    if instance.name:
        if not instance.name_ru:
            instance.name_ru = translate_text(instance.name, "ru")
        if not instance.name_en:
            instance.name_en = translate_text(instance.name, "en")
    if instance.address:
        if not instance.address_ru:
            instance.address_ru = translate_text(instance.address, "ru")
        if not instance.address_en:
            instance.address_en = translate_text(instance.address, "en")


@receiver(pre_save, sender=Discount)
def auto_translate_discount(sender, instance, **kwargs):
    if hasattr(instance, "title") and instance.title:
        if not instance.title_ru:
            instance.title_ru = translate_text(instance.title, "ru")
        if not instance.title_en:
            instance.title_en = translate_text(instance.title, "en")
    if hasattr(instance, "description") and instance.description:
        if not instance.description_ru:
            instance.description_ru = translate_text(instance.description, "ru")
        if not instance.description_en:
            instance.description_en = translate_text(instance.description, "en")


@receiver(pre_save, sender=Notification)
def auto_translate_notification(sender, instance, **kwargs):
    if instance.title:
        if not instance.title_ru:
            instance.title_ru = translate_text(instance.title, "ru")
        if not instance.title_en:
            instance.title_en = translate_text(instance.title, "en")
    if instance.message:
        if not instance.message_ru:
            instance.message_ru = translate_text(instance.message, "ru")
        if not instance.message_en:
            instance.message_en = translate_text(instance.message, "en")


@receiver(pre_save, sender=BotNotification)
def auto_translate_bot_notification(sender, instance, **kwargs):
    if instance.title:
        if not instance.title_ru:
            instance.title_ru = translate_text(instance.title, "ru")
        if not instance.title_en:
            instance.title_en = translate_text(instance.title, "en")
    if instance.message:
        if not instance.message_ru:
            instance.message_ru = translate_text(instance.message, "ru")
        if not instance.message_en:
            instance.message_en = translate_text(instance.message, "en")


@receiver(pre_save, sender=CarRate)
def auto_translate_car_rate(sender, instance, **kwargs):
    if instance.comment:
        if not instance.comment_ru:
            instance.comment_ru = translate_text(instance.comment, "ru")
        if not instance.comment_en:
            instance.comment_en = translate_text(instance.comment, "en")
    if instance.company_reply:
        if not instance.company_reply_ru:
            instance.company_reply_ru = translate_text(instance.company_reply, "ru")
        if not instance.company_reply_en:
            instance.company_reply_en = translate_text(instance.company_reply, "en")



@receiver(post_save, sender=Company)
def create_company_default_data(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        create_default_filial_and_workdays(instance)
    except Exception as e:
        logger.error(
            f"Company default data yaratishda xato. "
            f"company_id={instance.id}, error={e}"
        )