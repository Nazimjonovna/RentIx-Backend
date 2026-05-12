from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def send_ws_notification(user_id, title, message, notification_id=None, extra_data=None):
    channel_layer = get_channel_layer()

    if channel_layer is None:
        return False

    data = {
        "type": "notification",
        "id": notification_id,
        "title": title,
        "message": message,
    }

    if extra_data:
        data.update(extra_data)

    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "notification.event",
            "data": data,
        }
    )

    return True