from django.db.models import Q
from .models import Team, Tournament

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