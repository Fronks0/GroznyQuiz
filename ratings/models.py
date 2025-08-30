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
            wins_count=Count('achievements', filter=Q(achievements__place=1)),
            total_points_sum=Coalesce(Sum('gameresult__total_points', distinct=True), 0.0, output_field=FloatField()),
            last_game_date=Max('gameresult__tournament__date') 
        ).annotate(
            avg_points=Case(
                When(games_played_count=0, then=0.0),
                default=F('total_points_sum') / F('games_played_count'),
                output_field=FloatField()
            )
        )


class GameResultQuerySet(models.QuerySet):
    def with_dynamic_place(self):
        # Добавляет динамическое место в турнире(game_modal) с учетом одинаковых очков
        return self.annotate(
            dynamic_place=Window(
                expression=DenseRank(),  # DenseRank учитывает ничьи (1,2,2,3)
                order_by=F('total_points').desc()  # Сортировка по убыванию очков
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
    name = models.CharField(max_length=100, verbose_name="Название серии", unique=True)
    display_order = models.PositiveIntegerField(default=100, verbose_name="Порядок отображения")
    
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


    #Лучшай тема на основе очков
    @property
    def best_topic(self):
        topic_stats = (
            TopicResult.objects
            .filter(game_result__team=self)
            .values('topic__short_name', 'topic__full_name')
            .annotate(total_points=Sum('points'))
            .order_by('-total_points')
        )
        
        if topic_stats:
            best_topic_info = topic_stats[0]
            return {
                'short_name': best_topic_info['topic__short_name'],
                'full_name': best_topic_info['topic__full_name'],
            }
        return {'short_name': '-', 'full_name': 'Нет данных'}

    def __str__(self):
        return f"{self.name} ({self.city})"


class GameResult(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, verbose_name="Турнир")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, verbose_name="Команда")
    black_box_answer = models.CharField(max_length=100, blank=True, null=True, default='-', verbose_name="Ответ на черный ящик")
    black_box_points = models.DecimalField(max_digits=6, decimal_places=1, default=Decimal('0.0'), verbose_name="Очки за черный ящик")
    # Сигналы подсчитывают total_points
    total_points = models.FloatField(default=0.0, verbose_name="Всего очков")

    objects = GameResultQuerySet.as_manager()

    class Meta:
        verbose_name = "Результат игры"
        verbose_name_plural = "Результаты игры"

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



class Achievement(models.Model):
    PLACE_CHOICES = [
        (1, '🥇 1 место'),
        (2, '🥈 2 место'), 
        (3, '🥉 3 место'),
    ]
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='achievements')
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='achievements')
    place = models.PositiveIntegerField(choices=PLACE_CHOICES)
    achieved_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['team', 'tournament']
        ordering = ['tournament__date', 'place']

    def __str__(self):
        return f"{self.team} - {self.tournament} ({self.get_place_display()})"










