from channels.generic.websocket import AsyncWebsocketConsumer
import json

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            await self.channel_layer.group_add("notifications", self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("notifications", self.channel_name)

    async def send_notification(self, event):
        message = event['message']
        user = self.scope['user']

        data = json.loads(message)

        # Check if notification is for this user's role or all
        if data['target_roles'] == 'all' or data['target_roles'] == user.role:
            await self.send(text_data=message)
