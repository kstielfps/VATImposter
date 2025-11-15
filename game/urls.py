from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('create/', views.create_game, name='create_game'),
    path('join/', views.join_game, name='join_game'),
    path('game/<str:code>/', views.game_room, name='game_room'),
    path('create-admin/', views.create_admin_user, name='create_admin_user'),
]



