from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from .models import Team, Tournament

from django.db.models import Q


def q_search(query):
    query = query.strip()
    if not query:
        return {'teams': Team.objects.none(), 'tournaments': Tournament.objects.none()}
    
    # Используем websearch для лучшей обработки дефисов и фраз
    search_query = SearchQuery(query, search_type='websearch')
    
    # ПОИСК ПО КОМАНДАМ
    teams = Team.objects.annotate(
        rank=SearchRank(SearchVector('name'), search_query)
    ).filter(
        Q(rank__gt=0) |  # полнотекстовый поиск
        Q(name__icontains=query)  # обычный поиск для точных совпадений
    ).order_by('-rank', 'name')
    
    # ПОИСК ПО ТУРНИРАМ (включая команды-участники)
    tournaments = Tournament.objects.annotate(
        rank=SearchRank(
            SearchVector('name') + 
            SearchVector('gameresult__team__name'),  # ← поиск по командам тоже
            search_query
        )
    ).filter(
        Q(rank__gt=0) |
        Q(name__icontains=query) |
        Q(gameresult__team__name__icontains=query)  # ← поиск по названиям команд
    ).distinct().order_by('-rank', '-date')
    
    return {
        'teams': teams,
        'tournaments': tournaments
    }