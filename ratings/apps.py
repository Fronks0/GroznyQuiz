# ratings/apps.py
from django.apps import AppConfig

class RatingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ratings'
    
    def ready(self):
        # Импортируем и подключаем сигналы
        import ratings.signals