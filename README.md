# Богатей. The Game

Задания 8 и 9. Игрок собирает монеты, сохраняет прогресс, покупает предметы и попадает в рейтинг. В задании 8 реализован четвёртый дополнительный вариант: магазин игровых предметов.

## Запуск на Windows

Python 3.12. Команды PowerShell из каталога проекта:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_game
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Откройте http://127.0.0.1:8000/ и зарегистрируйте обычного игрока. Начните игру, пять раз нажмите на монету, откройте магазин, купите медное кольцо и вернитесь к сохранению. Завершите игру и откройте рейтинг. На Windows при запуске без Docker используется SQLite.

## Docker и PostgreSQL

Скопируйте `.env.example` в `.env`, заполните `DJANGO_SECRET_KEY` и `POSTGRES_PASSWORD` своими случайными значениями. Секрет для Django можно получить командой `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Для пароля БД выполните команду ещё раз.

```powershell
docker compose up -d --build --wait
docker compose exec web python manage.py createsuperuser
docker compose logs web
docker compose down
```

Игра открывается по http://127.0.0.1:8000/. Если изменили `WEB_PORT`, используйте указанный порт. Миграции и заполнение магазина запускаются автоматически. База и аватары остаются в томах после обычной остановки. Для размещения за HTTPS укажите домен и HTTPS-адрес в `DJANGO_ALLOWED_HOSTS` и `DJANGO_CSRF_TRUSTED_ORIGINS`, включите `DJANGO_HTTPS=1` и настройте HTTPS на обратном прокси.

## Администрирование

Войдите по адресу `/admin/`. В игровых сессиях отметьте записи → «Выгрузить выбранные игры в XLSX» → выберите столбцы → «Скачать XLSX». У игрока в разделе профилей можно назначить достижения. У пользователя в разделе пользователей можно изменить пароль.

## API

Защищённым запросам нужен заголовок `Authorization: Bearer ACCESS_TOKEN`.

| Запрос | Действие |
|---|---|
| POST `/api/register/` | Регистрация с `username` и `password` |
| POST `/api/token/` | Вход: `username` и `password`, выдаёт `access` и `refresh` |
| POST `/api/token/refresh/` | Получить новый `access` по `refresh` |
| GET `/api/players/{username}/` | Публичный профиль |
| GET, PATCH `/api/profile/` | Свой профиль; аватар через `avatar_upload` в форме с файлом |
| GET, POST `/api/games/` | Список, создание; `difficulty`: easy, medium, hard |
| GET `/api/games/latest/` | Последнее сохранение |
| GET, DELETE `/api/games/{id}/` | Открыть или удалить своё сохранение |
| POST `/api/games/{id}/click/` | Собрать монету и сохранить состояние |
| POST `/api/games/{id}/finish/` | Завершить игру и обновить рейтинг |
| GET `/api/leaderboard/` | Рейтинг; параметры `difficulty`, `since=ГГГГ-ММ-ДД` |
| GET `/api/achievements/` | Мои достижения |
| GET `/api/items/` | Магазин и купленные предметы |
| POST `/api/items/{id}/buy/` | Покупка за игровые монеты |

## Тесты

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv\Scripts\python.exe -m coverage run --source=game,richgame manage.py test
.\.venv\Scripts\python.exe -m coverage report --omit "*/migrations/*"
```

В Docker: `docker compose exec web python manage.py test`. Результаты и ручной чек-лист — в [TESTING.md](TESTING.md).
