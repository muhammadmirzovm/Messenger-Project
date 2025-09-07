# chat_app/routing.py
from django.urls import re_path
from .consumers import PresenceConsumer, RoomConsumer

websocket_urlpatterns = [
    re_path(r"^ws/presence/$", PresenceConsumer.as_asgi()),
    re_path(r"^ws/room/(?P<room_slug>[^/]+)/$", RoomConsumer.as_asgi()),
]
