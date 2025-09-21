from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Sum, F, Max, FloatField, Window, When, Case
from decimal import Decimal
from django.db.models.functions import Coalesce, DenseRank


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









