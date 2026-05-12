import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from .models import Chat, ChatMessage, Notification

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user", AnonymousUser())

        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        self.chat_id = self.scope["url_route"]["kwargs"].get("chat_id")
        self.chat_group_name = f"chat_{self.chat_id}"

        has_access = await self.check_chat_access(self.user.id, self.chat_id)

        if not has_access:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            self.chat_group_name,
            self.channel_name
        )

        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "connected",
            "message": "Chat WebSocket connected",
            "chat_id": self.chat_id,
            "user_id": self.user.id,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "chat_group_name"):
            await self.channel_layer.group_discard(
                self.chat_group_name,
                self.channel_name
            )

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
            return

        message = data.get("message")

        if not message or not str(message).strip():
            await self.send_error("Message is required")
            return

        chat_message = await self.save_message(
            user_id=self.user.id,
            chat_id=self.chat_id,
            message=message.strip()
        )

        if not chat_message:
            await self.send_error("Chat not found or message not saved")
            return

        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                "type": "chat_message",
                "message_id": chat_message["id"],
                "message": chat_message["message"],
                "sender_id": chat_message["sender_id"],
                "sender_name": chat_message["sender_name"],
                "created_at": chat_message["created_at"],
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message_id": event["message_id"],
            "message": event["message"],
            "sender_id": event["sender_id"],
            "sender_name": event["sender_name"],
            "created_at": event["created_at"],
        }))

    async def send_error(self, message):
        await self.send(text_data=json.dumps({
            "type": "error",
            "message": message,
        }))

    @database_sync_to_async
    def check_chat_access(self, user_id, chat_id):
        try:
            chat = Chat.objects.get(id=chat_id)

            # Agar Chat modelingizda user/manager/customer maydonlari boshqacha bo‘lsa,
            # shu joyni o‘zingizdagi field nomlariga moslang.

            if hasattr(chat, "user_id") and chat.user_id == user_id:
                return True

            if hasattr(chat, "manager_id") and chat.manager_id == user_id:
                return True

            if hasattr(chat, "customer_id") and chat.customer_id == user_id:
                return True

            if hasattr(chat, "users"):
                return chat.users.filter(id=user_id).exists()

            return True

        except Chat.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, user_id, chat_id, message):
        try:
            user = User.objects.get(id=user_id)
            chat = Chat.objects.get(id=chat_id)

            chat_message = ChatMessage.objects.create(
                chat=chat,
                sender=user,
                message=message
            )

            sender_name = (
                getattr(user, "full_name", None)
                or getattr(user, "username", None)
                or getattr(user, "phone", None)
                or str(user.id)
            )

            return {
                "id": chat_message.id,
                "message": chat_message.message,
                "sender_id": user.id,
                "sender_name": sender_name,
                "created_at": chat_message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }

        except Exception:
            return None


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user", AnonymousUser())

        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        self.group_name = f"notify_{self.user.id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        unread_notifications = await self.get_unread_notifications()

        await self.send(text_data=json.dumps({
            "type": "connected",
            "message": "Notification WebSocket connected",
            "user_id": self.user.id,
            "unread_count": len(unread_notifications),
            "notifications": unread_notifications,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
            return

        action = data.get("action")

        if action == "ping":
            await self.send(text_data=json.dumps({
                "type": "pong"
            }))

        elif action == "mark_as_read":
            notification_id = data.get("notification_id")

            if not notification_id:
                await self.send_error("notification_id is required")
                return

            updated = await self.mark_notification_as_read(notification_id)

            await self.send(text_data=json.dumps({
                "type": "notification_read",
                "notification_id": notification_id,
                "success": updated,
            }))

        elif action == "mark_all_as_read":
            count = await self.mark_all_notifications_as_read()

            await self.send(text_data=json.dumps({
                "type": "all_notifications_read",
                "updated_count": count,
            }))

        else:
            await self.send_error("Unknown action")

    async def notify(self, event):
        await self.send(text_data=json.dumps({
            "type": "notification",
            "id": event.get("id"),
            "title": event.get("title"),
            "message": event.get("message"),
            "manager": event.get("manager_name"),
            "created_at": event.get("created_at"),
            "source": event.get("source", "notification"),
        }))

    async def notification_event(self, event):
        data = event.get("data", {})

        await self.send(text_data=json.dumps(data))

    async def send_error(self, message):
        await self.send(text_data=json.dumps({
            "type": "error",
            "message": message,
        }))

    @database_sync_to_async
    def get_unread_notifications(self):
        notifications = Notification.objects.filter(
            user=self.user,
            is_read=False
        ).order_by("-id")[:50]

        result = []

        for item in notifications:
            manager_name = None

            if getattr(item, "manager", None):
                manager_user = getattr(item.manager, "user", None)
                manager_name = (
                    getattr(manager_user, "full_name", None)
                    or getattr(manager_user, "username", None)
                    or str(item.manager)
                )

            result.append({
                "id": item.id,
                "title": item.title,
                "message": item.message,
                "manager": manager_name,
                "is_read": item.is_read,
                "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if hasattr(item, "created_at") and item.created_at else None,
            })

        return result

    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        updated = Notification.objects.filter(
            id=notification_id,
            user=self.user
        ).update(is_read=True)

        return bool(updated)

    @database_sync_to_async
    def mark_all_notifications_as_read(self):
        return Notification.objects.filter(
            user=self.user,
            is_read=False
        ).update(is_read=True)