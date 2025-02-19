"""
ASGI config for socket_chess project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "socket_chess.settings")
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from chess_game import routing as chess_routing

application = ProtocolTypeRouter({
    "http" : get_asgi_application(),
    "websocket" : AuthMiddlewareStack(
        URLRouter(
            chess_routing.websocket_urlpatterns
        )
    ),
})
