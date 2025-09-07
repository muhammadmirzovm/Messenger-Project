# chat_app/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CreateRoomForm, JoinRoomForm
from .models import Room, RoomMembership


@login_required
def room_list(request):
    """Display list of available rooms (all public)"""
    rooms = Room.objects.all()
    user_rooms = request.user.joined_rooms.all()
    return render(request, 'chat/room_list.html', {
        'public_rooms': rooms,
        'user_rooms': user_rooms,
    })


@login_required
def create_room(request):
    """Create a new chat room (always public) and set creator's nickname immediately."""
    if request.method == 'POST':
        form = CreateRoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.created_by = request.user
            room.save()

            creator_nickname = form.cleaned_data["nickname"].strip()

            # Creator joins as admin with the chosen nickname
            RoomMembership.objects.create(
                user=request.user,
                room=room,
                nickname=creator_nickname,
                is_admin=True,
            )

            messages.success(request, f'Room "{room.name}" created! You joined as "{creator_nickname}".')
            return redirect('chat_app:room_detail', slug=room.slug)
    else:
        form = CreateRoomForm()

    return render(request, 'chat/create_room.html', {'form': form})

@login_required
def room_detail(request, slug):
    room = get_object_or_404(Room, slug=slug)

    membership = RoomMembership.objects.filter(user=request.user, room=room).select_related('user', 'room').first()
    if not membership:
        return redirect('chat_app:join_room', slug=slug)

    memberships = RoomMembership.objects.filter(room=room).select_related('user')

    return render(request, 'chat/room_detail.html', {
        'room': room,
        'membership': membership,
        'memberships': memberships,
        'hide_navbar': True,
    })


@login_required
def join_room(request, slug):
    """Join a chat room with per-room nickname (no password needed)"""
    room = get_object_or_404(Room, slug=slug)

    if RoomMembership.objects.filter(user=request.user, room=room).exists():
        return redirect('chat_app:room_detail', slug=room.slug)

    if request.method == 'POST':
        form = JoinRoomForm(request.POST)
        if form.is_valid():
            nickname = form.cleaned_data['nickname'].strip()
            RoomMembership.objects.create(
                user=request.user,
                room=room,
                nickname=nickname or request.user.username
            )
            messages.success(
                request,
                f'Successfully joined "{room.name}" as {nickname or request.user.username}!'
            )
            return redirect('chat_app:room_detail', slug=room.slug)
    else:
        form = JoinRoomForm()

    return render(request, 'chat/join_room.html', {'room': room, 'form': form})


@login_required
def leave_room(request, slug):
    """Leave a chat room"""
    room = get_object_or_404(Room, slug=slug)
    try:
        membership = RoomMembership.objects.get(user=request.user, room=room)
        membership.delete()
        messages.success(request, f'Left room "{room.name}".')
    except RoomMembership.DoesNotExist:
        messages.error(request, 'You are not a member of this room.')
    return redirect('chat_app:room_list')
