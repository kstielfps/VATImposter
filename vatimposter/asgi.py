"""
ASGI config for vatimposter project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack

# Configurar Django antes de importar qualquer coisa que dependa dele
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vatimposter.settings')
django.setup()

# Agora podemos importar após configurar Django
from django.core.asgi import get_asgi_application
import game.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": SessionMiddlewareStack(
        AuthMiddlewareStack(
            URLRouter(
                game.routing.websocket_urlpatterns
            )
        )
    ),
})



