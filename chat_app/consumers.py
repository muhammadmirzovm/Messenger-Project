import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, RoomMembership, User, Message


ONLINE_USERS = set()                 

ROOM_USERS = {}                      
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, RoomMembership, User

ONLINE_USERS = set()
ROOM_USERS = {}  


class PresenceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return


        self.room_slug = self.scope['url_route']['kwargs'].get('room_slug')
        self.room_group_name = f"room_{self.room_slug}" if self.room_slug else "presence_global"


        if self.room_slug and not await self.is_room_member():
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()


        await self.add_user_presence()

        if not self.room_slug:

            usernames = await self.get_global_usernames()
            await self.send(text_data=json.dumps({
                "type": "online_count",
                "count": len(ONLINE_USERS),
                "users": usernames,
            }))

            await self.channel_layer.group_send("presence_global", {
                "type": "update_count",
                "count": len(ONLINE_USERS),
            })
        else:
            await self.channel_layer.group_send(self.room_group_name, {"type": "room_presence_update"})

    async def disconnect(self, close_code):
        await self.remove_user_presence()
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        if not self.room_slug:
            await self.channel_layer.group_send("presence_global", {
                "type": "update_count",
                "count": len(ONLINE_USERS),
            })
        else:
            await self.channel_layer.group_send(self.room_group_name, {"type": "room_presence_update"})

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except Exception:
            return

        msg_type = data.get("type")
        if msg_type == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))


        if msg_type == "get_online_count" and not self.room_slug:
            usernames = await self.get_global_usernames()
            await self.send(text_data=json.dumps({
                "type": "online_count",
                "count": len(ONLINE_USERS),
                "users": usernames,
            }))


    async def update_count(self, event):
        usernames = await self.get_global_usernames()
        await self.send(text_data=json.dumps({
            "type": "online_count",
            "count": event["count"],
            "users": usernames,
        }))

    async def room_presence_update(self, event):
        usernames = await self.get_online_usernames()
        await self.send(text_data=json.dumps({
            "type": "room_presence",
            "count": len(usernames),
            "users": usernames,
        }))


    async def add_user_presence(self):
        if self.room_slug:
            ROOM_USERS.setdefault(self.room_slug, set()).add(self.user.id)
        else:
            ONLINE_USERS.add(self.user.id)

    async def remove_user_presence(self):
        if self.room_slug and self.room_slug in ROOM_USERS:
            ROOM_USERS[self.room_slug].discard(self.user.id)
            if not ROOM_USERS[self.room_slug]:
                del ROOM_USERS[self.room_slug]
        else:
            ONLINE_USERS.discard(self.user.id)

    @database_sync_to_async
    def get_online_usernames(self):
        ids_ = ROOM_USERS.get(self.room_slug, set())
        return list(User.objects.filter(id__in=ids_).values_list('username', flat=True))

    @database_sync_to_async
    def get_global_usernames(self):
        return list(User.objects.filter(id__in=ONLINE_USERS).values_list('username', flat=True))

    @database_sync_to_async
    def is_room_member(self):
        try:
            room = Room.objects.get(slug=self.room_slug)
            return RoomMembership.objects.filter(user=self.user, room=room).exists()
        except Room.DoesNotExist:
            return False

class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        self.room_slug = self.scope['url_route']['kwargs'].get('room_slug')
        if not self.room_slug:
            await self.close()
            return

        self.room_group_name = f"room_{self.room_slug}"


        if not await self.is_room_member():
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()


        await self.add_user_presence()


        await self.channel_layer.group_send(self.room_group_name, {"type": "room_presence_update"})


        history = await self.get_last_messages(limit=50)
        await self.send(json.dumps({
            "type": "chat_history",
            "messages": history,
        }))

    async def disconnect(self, close_code):
        await self.remove_user_presence()
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.channel_layer.group_send(self.room_group_name, {"type": "room_presence_update"})

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type == "ping":
            await self.send(json.dumps({"type": "pong"}))
            return

        if msg_type == "chat_message":
            message = (data.get("message") or "").strip()
            if not message:
                return


            saved = await self.save_message(message)


            await self.channel_layer.group_send(self.room_group_name, {
                "type": "broadcast_message",
                "payload": saved,
            })


    async def room_presence_update(self, event):
        users = await self.get_room_user_dicts()
        await self.send(json.dumps({
            "type": "room_presence",
            "count": len(users),
            "users": users,
        }))

    async def broadcast_message(self, event):
        """Send a single new chat message to clients (already serialized)."""
        await self.send(json.dumps({
            "type": "chat_message",
            **event["payload"],
        }))


    @database_sync_to_async
    def get_last_messages(self, limit=50):
        room = Room.objects.get(slug=self.room_slug)
        qs = Message.objects.filter(room=room).select_related("user").order_by("-created_at")[:limit]

        items = [m.as_dict() for m in reversed(list(qs))]
        return items

    @database_sync_to_async
    def save_message(self, text: str):
        room = Room.objects.get(slug=self.room_slug)

        try:
            m = RoomMembership.objects.select_related("user", "room").get(room=room, user=self.user)
            nick = m.nickname or self.user.username
        except RoomMembership.DoesNotExist:
            nick = self.user.username

        msg = Message.objects.create(room=room, user=self.user, text=text, nickname=nick)
        return msg.as_dict()

    @database_sync_to_async
    def get_room_user_dicts(self):
        user_ids = ROOM_USERS.get(self.room_slug, set())
        if not user_ids:
            return []
        qs = RoomMembership.objects.filter(room__slug=self.room_slug, user_id__in=user_ids).select_related("user")
        return [{"id": m.user.id, "username": m.user.username, "nickname": (m.nickname or m.user.username)} for m in qs]

    @database_sync_to_async
    def is_room_member(self):
        try:
            room = Room.objects.get(slug=self.room_slug)
            return RoomMembership.objects.filter(user=self.user, room=room).exists()
        except Room.DoesNotExist:
            return False


    async def add_user_presence(self):
        ROOM_USERS.setdefault(self.room_slug, set()).add(self.user.id)

    async def remove_user_presence(self):
        if self.room_slug in ROOM_USERS:
            ROOM_USERS[self.room_slug].discard(self.user.id)
            if not ROOM_USERS[self.room_slug]:
                del ROOM_USERS[self.room_slug]
