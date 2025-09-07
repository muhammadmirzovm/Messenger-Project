# chat_app/models.py
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
import uuid


class Room(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')
    members = models.ManyToManyField(User, through='RoomMembership', related_name='joined_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) + '-' + str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)

    def get_online_members(self):
        """Simple heuristic; replace with real presence when ready."""
        return self.members.filter(last_login__gte=timezone.now() - timedelta(minutes=5))

    @property
    def member_count(self):
        return self.members.count()


class RoomMembership(models.Model):
    """User<->Room with per-room nickname & flags"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="memberships")
    nickname = models.CharField(max_length=50, blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_muted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'room')

    def __str__(self):
        return self.nickname or self.user.username

    @property
    def display_name(self):
        return self.nickname or self.user.username


class UserPresence(models.Model):
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('away', 'Away'),
        ('busy', 'Busy'),
        ('offline', 'Offline'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='presence')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='offline')
    last_seen = models.DateTimeField(default=timezone.now)
    is_online = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.status}"

    class Meta:
        verbose_name = "User Presence"
        verbose_name_plural = "User Presences"

class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages")
    text = models.TextField()
    nickname = models.CharField(max_length=50, blank=True, null=True)  # snapshot of per-room nickname at send time
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        who = self.nickname or self.user.username
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {who}: {self.text[:30]}"

    def as_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username,
            "nickname": self.nickname or self.user.username,
            "message": self.text,
            "created_at": self.created_at.isoformat(),
        }