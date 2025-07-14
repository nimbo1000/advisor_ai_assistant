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
        user = self.scope.get('user')
        user_id = None
        if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            user_id = user.pk
            print(f"pk: {user.pk}")
            print(f"username: {user.username}")
        creds_data = self.scope['session'].get('google_credentials')
        if not user_id and creds_data:
            # Try to get user id from session if available (e.g., after login)
            user_id = creds_data.get('user_id')
        if not user_id:
            # Fallback: do not proceed if user_id is not available
            await self.send(text_data=json.dumps({'error': 'User not authenticated'}))
            return
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