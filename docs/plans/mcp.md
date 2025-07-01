# Django MCP Chatbot Integration Guide

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Django App    │────▶│  Django Channels │────▶│    Frontend     │
│   with MCP      │     │   (WebSockets)   │     │  (HTMX/React)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                                                 │
         │                                                 │
         ▼                                                 ▼
┌─────────────────┐                             ┌─────────────────┐
│   MCP Server    │                             │   Chat UI       │
│  (Tools/APIs)   │                             │   Components    │
└─────────────────┘                             └─────────────────┘
```

## Step-by-Step Implementation

### 1. Install Required Packages

```bash
pip install django-mcp-server channels channels-redis django-rest-framework
pip install mcp anthropic python-dotenv
```

### 2. Configure Django Settings

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'mcp_server',
    'rest_framework',
    'chatbot',  # your chatbot app
]

# Django Channels
ASGI_APPLICATION = 'myproject.asgi.application'

# Channel layers configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# MCP Configuration
DJANGO_MCP_AUTHENTICATION_CLASSES = [
    'rest_framework.authentication.SessionAuthentication',
]

# Optional: OAuth2 for production
# DJANGO_MCP_AUTHENTICATION_CLASSES = [
#     'oauth2_provider.contrib.rest_framework.OAuth2Authentication'
# ]
```

### 3. Create MCP Tools

```python
# chatbot/mcp.py
from mcp_server import ModelQueryToolset, MCPToolset
from .models import Conversation, Message

class ConversationQueryTool(ModelQueryToolset):
    model = Conversation

    def get_queryset(self):
        """Filter conversations for the current user"""
        return super().get_queryset().filter(user=self.request.user)

class ChatbotTool(MCPToolset):
    """Custom tools for chatbot operations"""

    def get_conversation_history(self, conversation_id: str) -> str:
        """Retrieve conversation history"""
        messages = Message.objects.filter(
            conversation_id=conversation_id
        ).order_by('created_at')

        return "\n".join([
            f"{msg.sender}: {msg.content}"
            for msg in messages
        ])

    def analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of user message"""
        # Your sentiment analysis logic here
        return "positive"  # Example response
```

### 4. Set Up Django Channels Consumer

```python
# chatbot/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from mcp.client import ClientSession
from .models import Message, Conversation

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Initialize MCP session
        self.mcp_session = await self.create_mcp_session()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        if hasattr(self, 'mcp_session'):
            await self.mcp_session.close()

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Save user message
        await self.save_message(self.scope['user'], message, 'user')

        # Process with MCP
        response = await self.process_with_mcp(message)

        # Save bot response
        await self.save_message(self.scope['user'], response, 'bot')

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': response,
                'sender': 'bot'
            }
        )

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender']
        }))

    async def create_mcp_session(self):
        # Initialize MCP client session
        # This would connect to your MCP server
        pass

    async def process_with_mcp(self, message):
        # Process message using MCP tools
        # Return bot response
        return "Bot response based on MCP processing"

    @database_sync_to_async
    def save_message(self, user, content, sender):
        conversation = Conversation.objects.get_or_create(
            user=user,
            room_name=self.room_name
        )[0]

        Message.objects.create(
            conversation=conversation,
            content=content,
            sender=sender
        )
```

### 5. Create Beautiful Chat UI

```html
<!-- templates/chatbot/chat.html -->
<!DOCTYPE html>
<html>
<head>
    <title>AI Chatbot</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .chat-container {
            height: 600px;
            display: flex;
            flex-direction: column;
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
        }
        .message {
            margin-bottom: 1rem;
            animation: fadeIn 0.3s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .typing-indicator {
            display: none;
        }
        .typing-indicator.active {
            display: flex;
        }
        .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #718096;
            margin: 0 2px;
            animation: bounce 1.4s infinite ease-in-out both;
        }
        .dot:nth-child(1) { animation-delay: -0.32s; }
        .dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
    </style>
</head>
<body class="bg-gray-50">
    <div class="container mx-auto max-w-4xl p-4">
        <div class="bg-white rounded-lg shadow-lg chat-container">
            <div class="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4 rounded-t-lg">
                <h1 class="text-2xl font-bold">AI Assistant</h1>
                <p class="text-sm opacity-90">Powered by MCP</p>
            </div>

            <div id="messages" class="messages bg-gray-50">
                <!-- Messages will appear here -->
            </div>

            <div class="typing-indicator p-4" id="typing-indicator">
                <div class="flex items-center space-x-2">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
            </div>

            <form id="chat-form" class="p-4 border-t"
                  ws-send
                  hx-ext="ws"
                  ws-connect="/ws/chat/{{ room_name }}/">
                <div class="flex space-x-2">
                    <input type="text"
                           id="message-input"
                           name="message"
                           class="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                           placeholder="Type your message..."
                           autocomplete="off">
                    <button type="submit"
                            class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
                        Send
                    </button>
                </div>
            </form>
        </div>
    </div>

    <script>
        const messagesDiv = document.getElementById('messages');
        const messageInput = document.getElementById('message-input');
        const typingIndicator = document.getElementById('typing-indicator');
        const chatSocket = new WebSocket(
            'ws://' + window.location.host + '/ws/chat/{{ room_name }}/'
        );

        chatSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            typingIndicator.classList.remove('active');

            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';

            if (data.sender === 'bot') {
                messageDiv.innerHTML = `
                    <div class="flex items-start space-x-2">
                        <div class="w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
                            AI
                        </div>
                        <div class="flex-1">
                            <div class="bg-white p-3 rounded-lg shadow-sm">
                                ${data.message}
                            </div>
                        </div>
                    </div>
                `;
            } else {
                messageDiv.innerHTML = `
                    <div class="flex items-start space-x-2 justify-end">
                        <div class="flex-1">
                            <div class="bg-blue-500 text-white p-3 rounded-lg shadow-sm">
                                ${data.message}
                            </div>
                        </div>
                        <div class="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center">
                            👤
                        </div>
                    </div>
                `;
            }

            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        };

        document.getElementById('chat-form').onsubmit = function(e) {
            e.preventDefault();
            const message = messageInput.value;
            if (message) {
                chatSocket.send(JSON.stringify({
                    'message': message
                }));

                // Show user message immediately
                const userMessageDiv = document.createElement('div');
                userMessageDiv.className = 'message';
                userMessageDiv.innerHTML = `
                    <div class="flex items-start space-x-2 justify-end">
                        <div class="flex-1">
                            <div class="bg-blue-500 text-white p-3 rounded-lg shadow-sm">
                                ${message}
                            </div>
                        </div>
                        <div class="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center">
                            👤
                        </div>
                    </div>
                `;
                messagesDiv.appendChild(userMessageDiv);

                messageInput.value = '';
                typingIndicator.classList.add('active');
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
        };
    </script>
</body>
</html>
```

### 6. Configure URL Routing

```python
# chatbot/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>\w+)/$', consumers.ChatConsumer.as_asgi()),
]

# myproject/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chatbot.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chatbot.routing.websocket_urlpatterns
        )
    ),
})
```

### 7. Create Django Views

```python
# chatbot/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import uuid

@login_required
def chat_room(request):
    # Generate a unique room name for the user
    room_name = str(uuid.uuid4())[:8]
    return render(request, 'chatbot/chat.html', {
        'room_name': room_name
    })
```

## Advanced Features

### 1. Streaming Responses
For streaming AI responses character by character:

```python
async def stream_response(self, response_text):
    for char in response_text:
        await self.send(text_data=json.dumps({
            'message': char,
            'sender': 'bot',
            'streaming': True
        }))
        await asyncio.sleep(0.02)  # Adjust speed as needed
```

### 2. File Upload Support
Add file handling to your MCP tools:

```python
class FileTool(MCPToolset):
    def process_file(self, file_path: str) -> str:
        """Process uploaded files"""
        # Your file processing logic
        return "File processed successfully"
```

### 3. Authentication & Security
- Use Django's built-in authentication
- Implement rate limiting
- Add CSRF protection for WebSocket connections
- Use OAuth2 for production MCP endpoints

## Production Considerations

1. **Use Redis for Channel Layer**: Essential for production scalability
2. **Deploy with ASGI Server**: Use Daphne or Uvicorn
3. **SSL/TLS**: Secure WebSocket connections (wss://)
4. **Load Balancing**: Configure sticky sessions for WebSocket connections
5. **Monitoring**: Add logging and monitoring for MCP requests

## Resources

- [Django-MCP-Server Documentation](https://github.com/omarbenhamid/django-mcp-server)
- [Django Channels Documentation](https://channels.readthedocs.io/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [HTMX WebSocket Extension](https://htmx.org/extensions/web-sockets/)

## Example Projects
- [Django-Firebase-MCP](https://github.com/raghavdasila/django-firebase-mcp) - Production-ready example with Firebase integration
- [Django Chatbot with Celery](https://github.com/slyapustin/django-chatbot) - Example using Celery for background tasks
