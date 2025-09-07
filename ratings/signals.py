from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal
from django.db.models import Sum
from django.db.models.functions import Coalesce

from .models import GameResult, TopicResult

# Функция для обновления total_points
def update_game_result_total(game_result):
    """Обновляет total_points для GameResult"""
    points_before = game_result.topicresult_set.aggregate(
        total=Coalesce(Sum('points'), Decimal('0.0'))
    )['total']
    
    black_box = game_result.black_box_points or Decimal('0.0')
    new_total = float(points_before) + float(black_box)
    
    if game_result.total_points != new_total:
        game_result.total_points = new_total
        game_result.save(update_fields=['total_points'])

# Функция для расчета мест
def calculate_places(points_list):
    if not points_list:
        return []
    
    places = []
    current_place = 1
    
    for i, points in enumerate(points_list):
        if i == 0:
            places.append(current_place)
        elif points == points_list[i-1]:
            places.append(current_place)
        else:
            current_place += 1
            places.append(current_place)
    
    return places

# Функция для обновления мест в турнире
def update_tournament_places(tournament):
    """Обновляет поле place для всех GameResult в турнире"""
    results = GameResult.objects.filter(tournament=tournament)\
        .select_related('team')\
        .order_by('-total_points')
    
    points_list = [result.total_points for result in results]
    places = calculate_places(points_list)
    
    # Обновляем места для каждого результата
    for result, place in zip(results, places):
        if result.place != place:
            result.place = place
            # Сохраняем только поле place чтобы избежать рекурсии
            GameResult.objects.filter(id=result.id).update(place=place)

# Основные сигналы
@receiver(post_save, sender=TopicResult)
@receiver(post_delete, sender=TopicResult)
def update_on_topic_change(sender, instance, **kwargs):
    """Обновляет все при изменении TopicResult"""
    game_result = instance.game_result
    tournament = game_result.tournament
    
    # 1. Обновляем total_points
    update_game_result_total(game_result)
    
    # 2. Обновляем места во всем турнире
    update_tournament_places(tournament)

@receiver(post_save, sender=GameResult)
@receiver(post_delete, sender=GameResult)  
def update_on_game_result_change(sender, instance, **kwargs):
    """Обновляет места ВСЕХ команд турнира при изменении ЛЮБОГО GameResult"""
    tournament = instance.tournament
    
    # Получаем ВСЕ результаты турнира и пересчитываем места
    results = GameResult.objects.filter(tournament=tournament)\
        .select_related('team')\
        .order_by('-total_points')
    
    points_list = [result.total_points for result in results]
    places = calculate_places(points_list)
    
    # Обновляем места для ВСЕХ результатов турнира
    for result, place in zip(results, places):
        if result.place != place:
            result.place = place
            # Сохраняем только поле place чтобы избежать рекурсии
            GameResult.objects.filter(id=result.id).update(place=place)