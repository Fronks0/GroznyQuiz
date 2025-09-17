from django.db.models import Q
from .models import Team, Tournament
from datetime import datetime


def q_search(query):
    if not query:
        return {
            'teams': Team.objects.all(),
            'tournaments': Tournament.objects.all()
        }
    
    # Нормализуем запрос - убираем лишние пробелы и приводим к нижнему регистру
    normalized_query = ' '.join(query.lower().split())
    
    # Создаем условия для поиска команд
    team_conditions = Q()
    
    # Ищем точное совпадение (без учета регистра)
    team_conditions |= Q(name__iexact=normalized_query)
    
    # Ищем совпадение начала названия
    team_conditions |= Q(name__istartswith=normalized_query)
    
    # Ищем совпадение любой части названия
    team_conditions |= Q(name__icontains=normalized_query)
    
    # Для запросов из нескольких слов ищем совпадение всех слов
    words = normalized_query.split()
    if len(words) > 1:
        # Ищем команды, которые содержат все слова из запроса
        all_words_condition = Q()
        for word in words:
            all_words_condition &= Q(name__icontains=word)
        team_conditions |= all_words_condition
        
        # Ищем команды, которые начинаются с первого слова
        team_conditions |= Q(name__istartswith=words[0])
    
    # Поиск для турниров
    tournament_conditions = Q()
    tournament_conditions |= Q(name__icontains=normalized_query)
    tournament_conditions |= Q(name__iexact=normalized_query)
    tournament_conditions |= Q(name__istartswith=normalized_query)
    
    # Также ищем по командам-участникам турнира
    tournament_conditions |= Q(gameresult__team__name__icontains=normalized_query)
    
    # Для запросов из нескольких слов
    if len(words) > 1:
        all_words_tournament = Q()
        for word in words:
            all_words_tournament &= (Q(name__icontains=word) | Q(gameresult__team__name__icontains=word))
        tournament_conditions |= all_words_tournament
    
    teams = Team.objects.filter(team_conditions).distinct()
    tournaments = Tournament.objects.filter(tournament_conditions).distinct()
    
    return {
        'teams': teams,
        'tournaments': tournaments
    }



def filter_team_and_tournament(params, teams, tournaments=None, active_tab='teams'):
    # для team_modal при дате
    if tournaments is None:
        tournaments = Tournament.objects.all()

    search_query = params.get('search', '')
    city = params.get('city')
    game_series = params.get('game_series')
    date_from = params.get('date_from')
    date_to = params.get('date_to')

    # === ПОИСК ===
    if search_query:
        search_results = q_search(search_query)

        team_ids = search_results['teams'].values_list('id', flat=True)
        tournament_ids = search_results['tournaments'].values_list('id', flat=True)

        teams = teams.filter(id__in=team_ids)
        tournaments = tournaments.filter(id__in=tournament_ids)

    # === ФИЛЬТР ДАТЫ ===
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

    if date_from and date_to:
        teams = teams.distinct()

    # === ФИЛЬТР ГОРОДА ===
    if city:
        teams = teams.filter(city__name=city)
        tournaments = tournaments.filter(city__name=city)

    # === ФИЛЬТР ПО СЕРИИ ТУРНИРОВ ===
    if game_series:
        if active_tab == 'teams':
            teams = teams.filter(
                gameresult__tournament__series__name=game_series
            ).distinct()
        elif active_tab == 'games':
            tournaments = tournaments.filter(series__name=game_series)

    return teams, tournaments