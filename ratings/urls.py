from django.urls import path
from . import views


app_name = 'rating'

urlpatterns = [
    path('', views.index, name='index'),
    path('team/<int:team_id>/modal/', views.team_modal, name='team_modal'),
    path('game/<int:game_id>/modal/', views.game_modal, name='game_modal'),
]