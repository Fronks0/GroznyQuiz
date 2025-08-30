# ratings/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal
from django.db.models import Sum
from django.db.models.functions import Coalesce

from .models import Achievement, GameResult, Tournament, TopicResult

# Сигнал для подсчета Total_points в game_results
@receiver(post_save, sender=TopicResult)
@receiver(post_delete, sender=TopicResult)
def update_game_result_on_topic_change(sender, instance, **kwargs):
    """Обновляет total_points при изменении TopicResult"""
    game_result = instance.game_result
    update_game_result_total(game_result)

@receiver(post_save, sender=GameResult)
def update_game_result_on_save(sender, instance, **kwargs):
    """Обновляет total_points при изменении GameResult"""
    update_game_result_total(instance)

def update_game_result_total(game_result):
    """Общая функция для обновления total_points"""
    # Вычисляем сумму очков по темам
    points_before = game_result.topicresult_set.aggregate(
        total=Coalesce(Sum('points'), Decimal('0.0'))
    )['total']
    
    # Суммируем с очками черного ящика
    black_box = game_result.black_box_points or Decimal('0.0')
    new_total = float(points_before) + float(black_box)
    
    # Обновляем только если значение изменилось
    if game_result.total_points != new_total:
        game_result.total_points = new_total
        game_result.save(update_fields=['total_points'])

# Обновляет Achivement модель.
def calculate_places(points_list):
    # Рассчитывает места с учетом ничьих
    if not points_list:
        return []
    
    places = []
    current_place = 1
    prev_points = points_list[0]
    skip_counter = 0
    
    for i, points in enumerate(points_list):
        if i == 0:
            places.append(current_place)
        elif points == prev_points:
            places.append(current_place)
            skip_counter += 1
        else:
            current_place += 1 + skip_counter
            places.append(current_place)
            prev_points = points
            skip_counter = 0
    
    return places


@receiver(post_save, sender=GameResult)
@receiver(post_delete, sender=GameResult)
def update_achievements(sender, instance, **kwargs):
    # Обновляет достижения при изменении результатов турнира
    tournament = instance.tournament
    
    # Получаем отсортированные результаты
    results = GameResult.objects.filter(tournament=tournament)\
        .select_related('team')\
        .order_by('-total_points')
    
    # Рассчитываем места с учетом ничьи
    places = calculate_places([r.total_points for r in results])
    
    # Удаляем старые достижения турнира
    Achievement.objects.filter(tournament=tournament).delete()
    
    # Создаем новые достижения для призовых мест
    for result, place in zip(results, places):
        if place <= 3:  # Только 1-3 места
            Achievement.objects.create(
                team=result.team,
                tournament=tournament, 
                place=place
            )