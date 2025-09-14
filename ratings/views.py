from datetime import datetime
from django.shortcuts import get_object_or_404, render
from .models import City, GameResult,Team, Topic, Tournament, TournamentSeries
from django.db.models import Count, Prefetch
from django.core.paginator import Paginator

from .utils import q_search


# Внешний вид диаграммы настроить. устаногвить максимальное значение среднего балла и настроить центральные линии и рассширить
# Настроить статистику в зависимости от выбранного турнира
# Добавить фильтр труниров
# Выбранный фильтр в основной таблице, должен влиять на выбранный фильтр в модалке.
# настроить расчет статистики в модалке только выбранного периода в teams
# убрать фильтр все города
# внешний вид фильтров настроить
# Даны или пояса как сила для рейтинга вместо города
# в "Достижение" исрапавить кубки и медали. Там где должны быть кубки ставим кубки, там где медали, медали.
# Попровить Переход мжду вкладками, а именно Надпись "Загрузка" которая появляется.
# добавить шрифты которые Ислам просил
# Привести все в зависимости от данных и видов блоков к единым цветам, чтоб все не было разноцветным.
# телефонное отоброжение настроить
# Убрать Header и сделать "Вернуться на сайт"
# Кеширование
# Оптимизация запросов
# Добавление данных в проект настроить.


def index(request):
    # ПОЛУЧЕНИЕ ПАРАМЕТРОВ из URL
    search_query = request.GET.get('search', '')
    city = request.GET.get('city')
    team_sort = request.GET.get('team_sort')
    game_series = request.GET.get('game_series')
    active_tab = request.GET.get('active_tab', 'teams')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Базовые queryset для команд и турниров (еще без фильтров)
    teams = Team.objects.select_related('city')  # Оптимизация: сразу подгружаем город
    tournaments = Tournament.objects.select_related('series', 'city').prefetch_related(
        # Prefetch для победителей турнира (команды с 1 местом)
        Prefetch(
            'gameresult_set',
            queryset=GameResult.objects.filter(place=1).select_related('team'),
            to_attr='winners'  # Сохраняем в отдельное поле winners
        )
    ).annotate(
        results_count=Count('gameresult', distinct=True)  # Считаем количество команд-участников
    )

    # ПОИСК - применяем первым, но сохраняя аннотации
    if search_query:
        # Получаем ID найденных команд и турниров
        search_results = q_search(search_query)
        
        # Фильтруем базовые queryset по найденным ID (сохраняем аннотации!)
        team_ids = search_results['teams'].values_list('id', flat=True)
        tournament_ids = search_results['tournaments'].values_list('id', flat=True)
        
        teams = teams.filter(id__in=team_ids)
        tournaments = tournaments.filter(id__in=tournament_ids)
    
    # ФИЛЬТРАЦИЯ ПО ДАТЕ - применяем после поиска
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            # Для команд: фильтруем по дате турниров, в которых они участвовали
            teams = teams.filter(gameresult__tournament__date__gte=date_from_obj)
            # Для турниров: фильтруем по прямой дате
            tournaments = tournaments.filter(date__gte=date_from_obj)
        except (ValueError, TypeError):
            pass  # Если дата некорректная - игнорируем фильтр

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            teams = teams.filter(gameresult__tournament__date__lte=date_to_obj)
            tournaments = tournaments.filter(date__lte=date_to_obj)
        except (ValueError, TypeError):
            pass

    # Убираем дубликаты команд (могут появиться из-за фильтрации по дате через related field)
    if date_from and date_to:
        teams = teams.distinct()

    # ФИЛЬТРАЦИЯ ПО ГОРОДУ
    if city:
        teams = teams.filter(city__name=city)
        tournaments = tournaments.filter(city__name=city)

    # Считаем статистику команд ПОСЛЕ всех фильтров (важно для корректных расчетов!)
    teams = teams.with_stats()

    # СОРТИРОВКА КОМАНД по выбранному критерию
    if team_sort == "wins":
        teams = teams.order_by('-wins_count')  # По количеству побед
    elif team_sort == "avg":
        teams = teams.order_by('-avg_points')  # По среднему баллу
    else:
        teams = teams.order_by('-total_points_sum')  # По умолчанию: по общему количеству очков

    # ФИЛЬТРАЦИЯ ПО СЕРИИ ТУРНИРОВ
    if game_series:
        tournaments = tournaments.filter(series__name=game_series)

    # ФИНАЛЬНАЯ СОРТИРОВКА турниров по дате (новые сверху)
    tournaments = tournaments.order_by('-date')

    # ПАГИНАЦИЯ
    page = request.GET.get('page', 1)
    items_per_page = 100
    
    if active_tab == 'teams':
        paginator = Paginator(teams, items_per_page) # Разбивает teams по 5 элементов на страницу
        teams_page = paginator.get_page(page) # Получить первую страницу
        tournaments_page = []  
        current_page = teams_page
    else:
        paginator = Paginator(tournaments, items_per_page) # Разбивает games по 5 элементов на страницу
        teams_page = []
        tournaments_page = paginator.get_page(page) # Получить первую страницу
        current_page = tournaments_page
    
    context = {
        'teams': teams_page,  # пагинированные команды
        'tournaments': tournaments_page,  # пагинированные турниры
        'page_obj': current_page,  # текущая страница пагинации
        'paginator': paginator,  # пагинатор
        'all_series': TournamentSeries.objects.all(),  # Все серии для фильтра
        'all_cities': City.objects.all().order_by('name'),  # Все города для фильтра
        'selected_city': city,
        'selected_team_sort': team_sort,
        'selected_game_series': game_series,
        'active_tab': active_tab,
        'search_query': search_query,  # Сохраняем запрос для отображения в поле поиска
    }
    
    # Обработка AJAX запросов (только таблицы) vs обычных запросов (полная страница)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'ratings/includes/tables.html', context)
    return render(request, 'ratings/index.html', context)



def team_modal(request, team_id):
    # Получаем команду
    team = Team.objects.with_stats().select_related('city').get(id=team_id)
    
    # Получаем результаты последних 5 игр
    recent_games = team.gameresult_set.select_related(
        'tournament', 'tournament__city'
    ).order_by('-tournament__date')[:5]
    
    # Получаем статистику по сериям турниров для Достижений
    series_stats = team.get_series_stats()
    
    # Радар
    # Получаем статистику
    topic_stats = team.get_topic_statistics()

    # Формируем данные для радара
    radar_data = {'labels': [],'data': [], 'full_names': []}

    # Преобразуем averages в arrays для Chart.js
    for topic in Topic.objects.all().order_by('full_name'):  # сортируем по алфавиту
        if topic.id in topic_stats['averages']:
            radar_data['labels'].append(topic.short_name)
            radar_data['data'].append(topic_stats['averages'][topic.id])
            radar_data['full_names'].append(topic.full_name)
    
    context = {
        'team': team,
        'best_topic': topic_stats['best_topic'],  # Лучшая тема
        'radar_data': radar_data,    # Данные для диаграммы
        'series_stats': series_stats,
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

