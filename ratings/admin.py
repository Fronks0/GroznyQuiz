from django.contrib import admin
from .models import *

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(TournamentSeries)
class TournamentSeriesAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['short_name', 'full_name']
    search_fields = ['short_name', 'full_name']

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'city']
    list_filter = ['city']
    search_fields = ['name']



class TournamentTopicInline(admin.TabularInline):
    model = TournamentTopic
    extra = 8
    verbose_name = "Тема турнира"
    verbose_name_plural = "Темы турнира"

@admin.register(Tournament)  # ← Используем декоратор здесь
class TournamentAdmin(admin.ModelAdmin):
    list_display = ['name', 'series', 'date', 'city']
    list_filter = ['series', 'city', 'date']
    search_fields = ['name']
    ordering = ['-date']
    inlines = [TournamentTopicInline]



class TopicResultInline(admin.TabularInline):
    model = TopicResult
    extra = 7
    verbose_name = "Результат по теме"
    verbose_name_plural = "Результаты по темам"

@admin.register(GameResult) 
class GameResultAdmin(admin.ModelAdmin):
    list_display = ['tournament', 'team', 'black_box_answer', 'black_box_points']
    list_filter = ['tournament__series', 'tournament__city', 'tournament__date']
    search_fields = ['team__name', 'tournament__name']
    exclude = ('total_points',)
    inlines = [TopicResultInline]
    


