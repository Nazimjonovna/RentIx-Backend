# yourappname/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Chat, ChatMessage, Notification
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'

        # Guruhga ulanamiz
        await self.channel_layer.group_add(
            self.chat_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Guruhdan chiqish
        await self.channel_layer.group_discard(
            self.chat_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Client'dan yangi xabar kelganda
        """
        data = json.loads(text_data)
        message = data['message']
        user_id = self.scope['user'].id

        if user_id:
            chat_message = await self.save_message(user_id, self.chat_id, message)
            sender_name = chat_message.sender.full_name

            # Guruhdagi barcha client'ga yuborish
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_name': sender_name,
                    'created_at': chat_message.created_at.strftime("%H:%M:%S"),
                }
            )

    async def chat_message(self, event):
        """
        Guruhdagi xabarlarni frontend'ga yuborish
        """
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender_name': event['sender_name'],
            'created_at': event['created_at'],
        }))

    @database_sync_to_async
    def save_message(self, user_id, chat_id, message):
        user = User.objects.get(id=user_id)
        chat = Chat.objects.get(id=chat_id)
        return ChatMessage.objects.create(chat=chat, sender=user, message=message)


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        # Each user has their own notification group
        self.group_name = f"notify_{self.user.id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notify(self, event):
        # Called when a new notification is sent to this user's group
        await self.send(text_data=json.dumps({
            'title': event['title'],
            'message': event['message'],
            'manager': event['manager_name'],
            'created_at': event['created_at'],
        }))