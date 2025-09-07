from django.urls import path
from . import views

app_name = 'chat_app'

urlpatterns = [
    path('', views.room_list, name='room_list'),
    path('create/', views.create_room, name='create_room'),
    path('room/<slug:slug>/', views.room_detail, name='room_detail'),
    path('room/<slug:slug>/join/', views.join_room, name='join_room'),
    path('room/<slug:slug>/leave/', views.leave_room, name='leave_room'),
]
