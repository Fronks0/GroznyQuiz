from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Sum, F, Max, FloatField, Window, When, Case
from decimal import Decimal
from django.db.models.functions import Coalesce


#Расчеты для таблицы команд(teams.hmtl)
class TeamQuerySet(models.QuerySet):
    def with_stats(self):
        return self.annotate(
            games_played_count=Count('gameresult', distinct=True),
            wins_count=Count('gameresult', filter=Q(gameresult__place=1), distinct=True),
            total_points_sum=Coalesce(Sum('gameresult__total_points', distinct=True), 0.0, output_field=FloatField()),
            last_game_date=Max('gameresult__tournament__date') 
        ).annotate(
            avg_points=Case(
                When(games_played_count=0, then=0.0),
                default=F('total_points_sum') / F('games_played_count'),
                output_field=FloatField()
            )
        )



#Город
class City(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название города")
    
    class Meta:
        verbose_name = "Город"
        verbose_name_plural = "Города"
    
    def __str__(self):
        return self.name


#Серия турнира
class TournamentSeries(models.Model):
    TOURNAMENT_TYPES = [
        ('cup', 'Кубковый турнир'),
        ('regular', 'Обычный турнир'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Название серии", unique=True)
    display_order = models.PositiveIntegerField(default=100, verbose_name="Порядок отображения")
    tournament_type = models.CharField(
        max_length=10, 
        choices=TOURNAMENT_TYPES, 
        default='regular', 
        verbose_name="Тип турнира"
    )
    
    class Meta:
        verbose_name = "Серия турниров"
        verbose_name_plural = "Серии турниров"
    
    def __str__(self):
        return self.name


#Тема
class Topic(models.Model):
    full_name = models.CharField(max_length=100, verbose_name="Полное название")
    short_name = models.CharField(max_length=20, verbose_name="Короткое название")
    
    class Meta:
        verbose_name = "Тема"
        verbose_name_plural = "Темы"
    
    def __str__(self):
        return f"{self.short_name} - {self.full_name}"


#Турнир
class Tournament(models.Model):
    series = models.ForeignKey(TournamentSeries, on_delete=models.CASCADE, verbose_name="Серия турнира")
    name = models.CharField(max_length=200, verbose_name="Название турнира")
    date = models.DateField(verbose_name="Дата проведения")
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name="Город проведения")
    topics = models.ManyToManyField(Topic, through='TournamentTopic', verbose_name="Темы турнира")



    class Meta:
        verbose_name = "Турнир"
        verbose_name_plural = "Турниры"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.name} ({self.date}, {self.city})"


class TournamentTopic(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок")

    # Автоматически определяет порядок отображения тем в таблице результатов.
    def save(self, *args, **kwargs):
        # Если это новая запись и порядок не указан
        if not self.pk and self.order == 0:
            # Находим максимальный порядок для этого турнира и добавляем 1
            last_order = TournamentTopic.objects.filter(
                tournament=self.tournament
            ).aggregate(Max('order'))['order__max'] or 0
            self.order = last_order + 1
        
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['order']
        unique_together = ['tournament', 'topic']


class Team(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название команды", unique=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name="Город команды")

    objects = TeamQuerySet.as_manager()
    
    class Meta:
        verbose_name = "Команда"
        verbose_name_plural = "Команды"

    def get_belt_info(self):
        return get_belt_info(self.total_points_sum or 0)

    # Подсчеты для секции "Достижения"
    def get_series_stats(self):
        return self.gameresult_set.values(
            'tournament__series__name',
            'tournament__series__display_order',
            'tournament__series__tournament_type',
        ).annotate(
            participations=Count('id'),
            wins=Count('id', filter=Q(place=1)),
            second_places=Count('id', filter=Q(place=2)),
            third_places=Count('id', filter=Q(place=3)),
        ).order_by('tournament__series__display_order') 

        
    # Рассчет среднего балла по темам
    def get_topic_statistics(self, results_qs=None):
        """
        Возвращает полную статистику по темам:
        - averages: средний балл по каждой теме {topic_id: average_score}
        - counts: количество игр по каждой теме {topic_id: games_count}
        - best_topic: информация о лучшей теме по среднему баллу
        """
        # 1. Получаем все результаты команды по темам (ВСЕ или ОТФИЛЬТРОВАННЫЕ)
        if results_qs is None:
            # Если не передан QuerySet, берем все игры команды
            topic_results = (
                TopicResult.objects
                .filter(game_result__team=self)
                .select_related('topic')
                .values('topic_id', 'topic__short_name', 'topic__full_name', 'points')
            )
        else:
            # ★ ЕСЛИ ПЕРЕДАН QuerySet - ФИЛЬТРУЕМ ПО НЕМУ ★
            topic_results = (
                TopicResult.objects
                .filter(game_result__in=results_qs)  # Фильтруем по переданным играм
                .select_related('topic')
                .values('topic_id', 'topic__short_name', 'topic__full_name', 'points')
            )
        
        # 2. Группируем данные по темам (остальное без изменений)
        topic_stats = {}
        for result in topic_results:
            topic_id = result['topic_id']
            if topic_id not in topic_stats:
                topic_stats[topic_id] = {
                    'points_sum': 0,
                    'games_count': 0,
                    'short_name': result['topic__short_name'],
                    'full_name': result['topic__full_name']
                }
            # Накопление суммы баллов
            topic_stats[topic_id]['points_sum'] += float(result['points'])
            # Увеличение счетчика игр 
            topic_stats[topic_id]['games_count'] += 1
        
        # 3. Рассчитываем средние баллы
        averages = {}
        counts = {}
        for topic_id, stats in topic_stats.items():
            averages[topic_id] = stats['points_sum'] / stats['games_count']
            counts[topic_id] = stats['games_count']
        
        # 4. Находим лучшую тему
        best_topic_info = None
        if averages:
            best_topic_id = max(averages, key=averages.get)
            best_topic_info = {
                'id': best_topic_id,
                'short_name': topic_stats[best_topic_id]['short_name'],
                'full_name': topic_stats[best_topic_id]['full_name'],
                'average_score': averages[best_topic_id],
                'games_count': counts[best_topic_id]
            }
        
        # 5. Возвращаем структурированные данные
        return {
            'averages': averages,
            'counts': counts,
            'best_topic': best_topic_info or {}
        }



    def __str__(self):
        return f"{self.name} ({self.city})"


class GameResult(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, verbose_name="Турнир")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, verbose_name="Команда")
    black_box_answer = models.CharField(max_length=100, blank=True, null=True, default='-', verbose_name="Ответ на черный ящик")
    black_box_points = models.DecimalField(max_digits=6, decimal_places=1, default=Decimal('0.0'), verbose_name="Очки за черный ящик")
    # Сигналы подсчитывают total_points
    total_points = models.FloatField(default=0.0, verbose_name="Всего очков")
    # Сигналы подсчитывают points
    place = models.PositiveIntegerField(default=0, verbose_name="Место в турнире")


    class Meta:
        verbose_name = "Результат игры"
        verbose_name_plural = "Результаты игры"
        unique_together = ['tournament', 'team']

    #Функции для game_modal
    def points_before_black_box(self):
        #Очки до черного ящика
        result = self.topicresult_set.filter(
            topic__tournamenttopic__tournament=self.tournament
        ).aggregate(total=Coalesce(Sum('points'), Decimal('0.0')))
        return result['total']
    
    @property
    def first_three_topics_points(self):
        # Очки за первые три темы турнира
        qs = self.topicresult_set.filter(
            topic__tournamenttopic__tournament=self.tournament
        ).select_related('topic').order_by('topic__tournamenttopic__order')[:3]
        return sum((tr.points or Decimal('0.0')) for tr in qs)

    def __str__(self):
        return f"{self.team} - {self.tournament}"

# Результаты по теме
class TopicResult(models.Model):
    game_result = models.ForeignKey(GameResult, on_delete=models.CASCADE, verbose_name="Результат игры")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, verbose_name="Тема")
    points = models.DecimalField(max_digits=4, decimal_places=1, verbose_name="Очки", default=0)
    
    class Meta:
        verbose_name = "Результат по теме"
        verbose_name_plural = "Результаты по темам"
        unique_together = ['game_result', 'topic']
    
    #Проверяем, не добавил ли администратор лишние темы для GameResults конкретного турнира
    def clean(self):
        if self.game_result and self.topic:
            if not self.game_result.tournament.topics.filter(id=self.topic.id).exists():
                raise ValidationError(
                    f'Тема "{self.topic}" не входит в список тем турнира "{self.game_result.tournament}"'
                )
    
    def __str__(self):
        return f"{self.game_result} - {self.topic}: {self.points}"



BELT_SYSTEM = [
    {
        'name': 'Белый',
        'color': '#F0F0F0',
        'min_score': 0,
        'max_score': 50,
        'levels': [
            {'min': 0, 'max': 10, 'name': 'Белый 0'},
            {'min': 10, 'max': 20, 'name': 'Белый 1'},
            {'min': 20, 'max': 30, 'name': 'Белый 2'},
            {'min': 30, 'max': 40, 'name': 'Белый 3'},
            {'min': 40, 'max': 50, 'name': 'Белый 4'}
        ]
    },
    {
        'name': 'Синий',
        'color': '#1E90FF',
        'min_score': 50,
        'max_score': 100,
        'levels': [
            {'min': 50, 'max': 60, 'name': 'Синий 0'},
            {'min': 60, 'max': 70, 'name': 'Синий 1'},
            {'min': 70, 'max': 80, 'name': 'Синий 2'},
            {'min': 80, 'max': 90, 'name': 'Синий 3'},
            {'min': 90, 'max': 100, 'name': 'Синий 4'}
        ]
    },
    {
        'name': 'Пурпурный',
        'color': '#800080',
        'min_score': 100,
        'max_score': 1500,
        'levels': [
            {'min': 100, 'max': 110, 'name': 'Пурпурный 0'},
            {'min': 110, 'max': 120, 'name': 'Пурпурный 1'},
            {'min': 120, 'max': 130, 'name': 'Пурпурный 2'},
            {'min': 130, 'max': 140, 'name': 'Пурпурный 3'},
            {'min': 140, 'max': 150, 'name': 'Пурпурный 4'}
        ]
    },
    {
        'name': 'Коричневый',
        'color': '#8B4513',
        'min_score': 150,
        'max_score': 200,
        'levels': [
            {'min': 150, 'max': 160, 'name': 'Коричневый 0'},
            {'min': 160, 'max': 170, 'name': 'Коричневый 1'},
            {'min': 170, 'max': 180, 'name': 'Коричневый 2'},
            {'min': 180, 'max': 190, 'name': 'Коричневый 3'},
            {'min': 190, 'max': 200, 'name': 'Коричневый 4'}
        ]
    },
    {
        'name': 'Чёрный',
        'color': '#000000',
        'min_score': 200,
        'max_score': 300,
        'levels': [
            {'min': 200, 'max': 220, 'name': 'Чёрный 0'},
            {'min': 220, 'max': 240, 'name': 'Чёрный 1'},
            {'min': 240, 'max': 260, 'name': 'Чёрный 2'},
            {'min': 260, 'max': 280, 'name': 'Чёрный 3'},
            {'min': 280, 'max': 300, 'name': 'Чёрный 4'}
        ]
    },
    {
        'name': 'Красный',
        'color': '#FF0000',
        'min_score': 3000,
        'max_score': float('inf'),
        'levels': [
            {'min': 3000, 'max': 3500, 'name': 'Красный 0'},
            {'min': 3500, 'max': 4000, 'name': 'Красный 1'},
            {'min': 4000, 'max': 4500, 'name': 'Красный 2'},
            {'min': 4500, 'max': 5000, 'name': 'Красный 3'},
            {'min': 5000, 'max': float('inf'), 'name': 'Красный 4'}
        ]
    }
]




# Функция определения пояса
def get_belt_info(score):
    score = score or 0 #Защита от None
    for belt in BELT_SYSTEM:
        if belt['min_score'] <= score < belt['max_score']: # Находим тот пояс, в диапазон которого попадает количество очков.
            for level in belt['levels']:
                if level['min'] <= score < level['max']: # Определяем количество линий (полосок) на поясе
                    stripes_count = belt['levels'].index(level)
                    
                    return {
                        'belt_name': belt['name'],
                        'belt_color': belt['color'],
                        'level_name': level['name'],
                        'current_score': score,
                        'progress': ((score - level['min']) / (level['max'] - level['min'])) * 100,
                        'next_level': level['max'],
                        'belt_progress': ((score - belt['min_score']) / (belt['max_score'] - belt['min_score'])) * 100,
                        'stripes_count': stripes_count,  # Добавляем количество полосок
                        'level_number': stripes_count + 1  # Номер уровня (1-5)
                    }
    # Для максимального уровня
    return {
        'belt_name': BELT_SYSTEM[-1]['name'],
        'belt_color': BELT_SYSTEM[-1]['color'],
        'level_name': BELT_SYSTEM[-1]['levels'][-1]['name'],
        'current_score': score,
        'progress': 100,
        'next_level': 'Максимум',
        'belt_progress': 100,
        'stripes_count': 4,  # 4 полоски для максимального уровня
        'level_number': 5
    }