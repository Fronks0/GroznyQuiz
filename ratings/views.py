from datetime import datetime
from django.shortcuts import get_object_or_404, render
from .models import Achievement, City, GameResult,Team, Tournament, TournamentSeries
from django.db.models import Count, Q
from django.db.models import Prefetch

from .utils import q_search

# поиск
# "Показать еще"(ограничить показываемую информацию)
# "Закрепить "thead" Турнирной таблицы при скроле.
#телефонное отоброжение настроить
# Кеширование
# Оптимизация запросов

def index(request):
    # ПОЛУЧЕНИЕ ПАРАМЕТРОВ
    search_query = request.GET.get('search', '')
    city = request.GET.get('city')
    # Фильтры для команд (сортировка)
    team_sort = request.GET.get('team_sort')
    # Фильтры для игр (по серии турниров)
    game_series = request.GET.get('game_series')
    # Какая страница активна (вкладка "Команды" или "Игры")
    active_tab = request.GET.get('active_tab', 'teams') # По умолчанию "teams"

    # Фиильтры дат
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Базовые queryset для команд и турниров
    teams = Team.objects.select_related('city')
    tournaments = Tournament.objects.select_related('series', 'city').prefetch_related(
    Prefetch(
        'gameresult_set',
        queryset=GameResult.objects.select_related('team'),
        to_attr='results'
    ),
    Prefetch(
        'achievements',
        queryset=Achievement.objects.filter(place=1).select_related('team'),
        to_attr='winner_achievements'
    )
    ).annotate(
        results_count=Count('gameresult', distinct=True)
    )

    # ПОИСК (ВЫСШИЙ ПРИОРИТЕТ)
    if search_query:
        results = q_search(search_query)
        teams = results['teams']
        tournaments = results['tournaments']
   
        # ФИЛЬТРАЦИЯ ПО ДАТЕ
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            teams = teams.filter(gameresult__tournament__date__gte=date_from_obj)
            tournaments = tournaments.filter(date__gte=date_from_obj)
        except (ValueError, TypeError):
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            teams = teams.filter(gameresult__tournament__date__lte=date_to_obj)
            tournaments = tournaments.filter(date__lte=date_to_obj)
        except (ValueError, TypeError):
            pass

    # Убираем дубликаты если применялись оба фильтра дат
    if date_from and date_to:
        teams = teams.distinct()

    # ФИЛЬТРАЦИЯ ПО ГОРОДУ 
    if city:
        teams = teams.filter(city__name=city)
        tournaments = tournaments.filter(city__name=city)

    teams = teams.with_stats()

    # СОРТИРОВКА КОМАНД 
    if team_sort == "wins":
        teams = teams.order_by('-wins_count')
    elif team_sort == "avg":
        teams = teams.order_by('-avg_points')
    else:
        teams = teams.order_by('-total_points_sum')

    # ФИЛЬТРАЦИЯ ПО СЕРИИ ТУРНИРОВ 
    if game_series:
        tournaments = tournaments.filter(series__name=game_series)

    # ФИНАЛЬНАЯ СОРТИРОВКА 
    tournaments = tournaments.order_by('-date')

    # КОНТЕКСТ
    context = {
        'teams': teams,
        'tournaments': tournaments,
        'all_series': TournamentSeries.objects.all(),
        'all_cities': City.objects.all().order_by('name'),
        'selected_city': city,
        'selected_team_sort': team_sort,
        'selected_game_series': game_series,
        'active_tab': active_tab,
        'search_query': search_query,
    }
    
    # Если это AJAX запрос - возвращаем только таблицы
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'ratings/includes/tables.html', context)
        # Если обычный запрос - возвращаем полную страницу
    return render(request, 'ratings/index.html', context)



def team_modal(request, team_id):
    team = Team.objects.with_stats().select_related('city').get(id=team_id)
    
    # 1. Последние игры с динамическими местами
    recent_games = team.gameresult_set.select_related(
        'tournament', 'tournament__city'
    ).with_dynamic_place().order_by('-tournament__date')[:5]
    
    # Подссчитываем достижения из модели достижений
    achievements = Achievement.objects.filter(team=team).values(
        'tournament__series__name'
    ).annotate(
        participations=Count('id'),
        gold=Count('id', filter=Q(place=1)),
        silver=Count('id', filter=Q(place=2)),
        bronze=Count('id', filter=Q(place=3)),
    ).order_by('tournament__series__name')
    
    context = {
        'team': team,
        'best_topic': team.best_topic,
        'achievements': achievements,
        'recent_games': recent_games
    }
    return render(request, 'ratings/includes/modals/team_modal.html', context)


def game_modal(request, game_id):
    # Получаем турнир
    tournament = get_object_or_404(Tournament, id=game_id)
    # Получаем темы в правильном порядке
    topics = tournament.topics.all().order_by('tournamenttopic__order')
    
    # Получаем результаты с динамическими местами + оптимизированные запросы
    results = GameResult.objects.filter(tournament=tournament)\
        .select_related('team')\
        .with_dynamic_place()\
        .order_by('dynamic_place')
    
    # Подгружаем topicresult_set
    results = results.prefetch_related('topicresult_set__topic')
    

    # Заполняет незаполненные поля в таблице(для незаполненных тем в результате, делаем прочерки)
    for result in results:
        # Создаем список ['-', '-', '-', ...] по количеству тем
        result.topic_points = ['-'] * topics.count()
        
        # Заполняем реальными данными
        for tr in result.topicresult_set.all():
            # Находим индекс темы в ordered topics
            for idx, topic in enumerate(topics):
                if tr.topic_id == topic.id:
                    result.topic_points[idx] = tr.points
                    break
    
    context = {
        'game': tournament,
        'results': results,
        'topics': topics,
    }
    
    return render(request, 'ratings/includes/modals/game_modal.html', context)

