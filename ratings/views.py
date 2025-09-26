from datetime import datetime
from django.shortcuts import get_object_or_404, render
from .models import City, GameResult,Team, Topic, Tournament, TournamentSeries, BELT_SYSTEM
from django.db.models import Count, Prefetch
from django.core.paginator import Paginator

from .utils import filter_team_and_tournament





# Даны и пояса добавить
# Центрировать значения в таблицах
# Огрнаичить радар 5 средним баллом.



# телефонное отоброжение настроить
# Убрать Header и сделать "Вернуться на сайт"
# Кеширование
# Оптимизация запросов
# Добавление данных в проект настроить.

# Попросить проверить шрифт и загрузку у Ислама

def index(request):
    search_query = request.GET.get('search', '')
    team_sort = request.GET.get('team_sort')
    active_tab = request.GET.get('active_tab', 'teams')

    # Базовые queryset
    teams = Team.objects.select_related('city')
    tournaments = Tournament.objects.select_related('series', 'city').prefetch_related(
        Prefetch(
            'gameresult_set',
            queryset=GameResult.objects.filter(place=1).select_related('team'),
            to_attr='winners'
        )
    ).annotate(
        results_count=Count('gameresult', distinct=True)
    )

    #  Применяем фильтры через utils 
    teams, tournaments = filter_team_and_tournament(request.GET, teams, tournaments, active_tab)

    #  Статистика и сортировка 
    teams = teams.with_stats()
    tournaments = tournaments.order_by('-date')

    if team_sort == "wins":
        teams = teams.order_by('-wins_count')
    elif team_sort == "avg":
        teams = teams.order_by('-avg_points')
    else:
        teams = teams.order_by('-total_points_sum')

    # === Пагинация ===
    page = request.GET.get('page', 1)
    items_per_page = 100

    if active_tab == 'teams':
        paginator = Paginator(teams, items_per_page)
        teams_page = paginator.get_page(page)
        tournaments_page = []
        current_page = teams_page
    else:
        paginator = Paginator(tournaments, items_per_page)
        teams_page = []
        tournaments_page = paginator.get_page(page)
        current_page = tournaments_page

    context = {
        'teams': teams_page,
        'tournaments': tournaments_page,
        'page_obj': current_page,
        'paginator': paginator,
        'all_series': TournamentSeries.objects.all(),
        'all_cities': City.objects.all().order_by('name'),
        'selected_city': request.GET.get('city'),
        'selected_team_sort': team_sort,
        'selected_game_series': request.GET.get('game_series'),
        'active_tab': active_tab,
        'search_query': search_query,
        'belt_system': BELT_SYSTEM
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'ratings/includes/tables.html', context)
    return render(request, 'ratings/index.html', context)



def team_modal(request, team_id):
    team = Team.objects.filter(id=team_id).select_related('city')

    # Получаем результаты последних 5 игр(Без фильтров)
    recent_games =  team.first().gameresult_set.select_related(
        'tournament', 'tournament__city'
    ).order_by('-tournament__date')[:5]

    # Достижения(Без фильтров)
    series_stats = team.first().get_series_stats()

    # Применяем фильтр к команде, чтобы получить статистику которая соответствует фильтрации в teams
    team_filtered, _ = filter_team_and_tournament(request.GET, team, None, 'teams')
    team = team_filtered.with_stats()
    
    # Получаем все турниры, которые отфильтрованны по серии и дате(если есть)
    _, tournaments_filtered = filter_team_and_tournament(request.GET, Team.objects.none(),Tournament.objects.all(),'games')
    
    # получаем только те игры команды, которые были в этих отфильтрованных турнирах
    filtered_games = GameResult.objects.filter(
        team_id=team_id, # Игры нашей команды
        tournament__in=tournaments_filtered # Только в отфильтрованных турнирах
    )
    # Статистику для радара получаем
    topic_stats = team.first().get_topic_statistics(results_qs=filtered_games)
    
    # Формируем данные для радара
    radar_data = {'labels': [],'data': [], 'full_names': []}
    
    for topic in Topic.objects.all().order_by('full_name'):
        if topic.id in topic_stats['averages']:
            radar_data['labels'].append(topic.short_name)
            radar_data['data'].append(topic_stats['averages'][topic.id])
            radar_data['full_names'].append(topic.full_name)
    
    context = {
        'team': team.first(),
        'best_topic': topic_stats['best_topic'],
        'radar_data': radar_data,
        'series_stats': series_stats,
        'recent_games': recent_games,
        'active_filters': {
            'game_series': request.GET.get('game_series'),
            'date_from': request.GET.get('date_from'),
            'date_to': request.GET.get('date_to'),
        }
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
        .prefetch_related('topicresult_set__topic')\
        .order_by('place')
    

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

