PostgreSQL нужно себе установить

1. Клонируем репозиторий:
   ```bash
   git clone https://github.com/USERNAME/GroznyQuiz.git
   cd GroznyQui

2.
Создай виртуальное окружение:
python -m venv .venv
Активируй виртуальное окружение
.venv\Scripts\activate  

3.
установи зависимости(т.е. все нужные фреймворки и т.д.)
pip install -r requirements.txt

4.
Применяем миграции чтоб создалась БД:
python manage.py migrate

5.
Запускаем сервер локально
python manage.py runserver

6.
Перед публикацией нужно настроить settings вставляю туда:
# Django settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Database (PostgreSQL)
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

но данные не должны быть публичными. их нужно вписать в cp .env.example .env, а они дальше вставляются в settings.py.