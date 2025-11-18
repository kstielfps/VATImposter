from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('create/', views.create_game, name='create_game'),
    path('join/', views.join_game, name='join_game'),
    path('game/<str:code>/', views.game_room, name='game_room'),
    path('create-admin/', views.create_admin_user, name='create_admin_user'),
    path('api/game/<str:code>/state/', views.game_state_api, name='game_state_api'),
    path('api/game/<str:code>/start/', views.start_game_api, name='start_game_api'),
    path('api/game/<str:code>/hint/', views.submit_hint_api, name='submit_hint_api'),
    path('api/game/<str:code>/vote/', views.submit_vote_api, name='submit_vote_api'),
    path('api/game/<str:code>/palhaco-guess/', views.submit_palhaco_guess_api, name='submit_palhaco_guess_api'),
    path('api/game/<str:code>/chaos-power/', views.use_chaos_power_api, name='use_chaos_power_api'),
    path('api/game/<str:code>/restart/', views.restart_game_api, name='restart_game_api'),
    path('api/game/<str:code>/close/', views.close_room_api, name='close_room_api'),
    path('api/game/<str:code>/kick/', views.kick_player_api, name='kick_player_api'),
    path('api/game/<str:code>/nudge/', views.nudge_player_api, name='nudge_player_api'),
]



