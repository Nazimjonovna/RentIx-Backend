# utils.py or signals.py
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from datetime import datetime

def send_notification(user, manager, title, message):
    from User.models import Notification
    notif = Notification.objects.create(
        user=user,
        manager=manager,
        title=title,
        message=message,
        created_at=timezone.now()
    )

    # Real-time send through Channels
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notify_{user.id}',
        {
            'type': 'notify',
            'title': title,
            'message': message,
            'manager_name': manager.user.full_name,
            'created_at': str(notif.created_at),
        }
    )
    return notif


def is_within_work_hours(company, start_dt, end_dt):
    """
    Kompaniyaning ish vaqtini tekshiradi.
    start_dt va end_dt -> datetime obyektlar
    """
    if not hasattr(company, "work_days"):
        return True
    start_day = start_dt.strftime("%a").lower()[:3]
    end_day = end_dt.strftime("%a").lower()[:3]
    start_workday = company.work_days.filter(day=start_day).first()
    end_workday = company.work_days.filter(day=end_day).first()
    if not start_workday or not end_workday:
        return False
    if start_workday.is_24_7 or end_workday.is_24_7:
        return True
    if not start_workday.is_working or not end_workday.is_working:
        return False
    if start_dt.time() < start_workday.start_time or end_dt.time() > end_workday.end_time:
        return False
    return True
