import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .agent import agent_respond

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'chat_room'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        # Use authenticated user's pk or username if available
        user = self.scope.get('user')
        if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            user_id = user.pk or user.username
            print(f"pk: {user.pk}")
            print(f"username: {user.username}")
        else:
            # Fallback to email from session if available
            creds = self.scope['session'].get('google_credentials', {})
            user_id = creds.get('user_email', 'anonymous')
        creds_data = self.scope['session'].get('google_credentials')
        response = agent_respond(user_id, message, creds_data=creds_data)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': response,
            }
        )

    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        })) 