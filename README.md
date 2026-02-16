# aiogram-base-template

Базовый шаблон Telegram-бота на `aiogram 3` + `aiogram-dialog` + `SQLAlchemy` + `Alembic` + `Redis`.

Цель проекта: быстро запускать новые боты без сборки инфраструктуры с нуля.  
В шаблоне уже есть:
- точка входа и сборка приложения;
- middleware для аутентификации, контроля доступа и обработки блокировок;
- модель пользователей и Unit of Work слой;
- диалог админки для просмотра/поиска пользователей и управления ролями;
- миграции БД;
- Docker окружение;
- линтеры и type-check.

## 1. Быстрый обзор

### Что это дает из коробки
- Автоматическое создание пользователя в БД при первом входе.
- Передача `current_user` в хендлеры через middleware.
- Гибкий контроль доступа к хендлерам через `flags={"access": [...]}`.
- Разделение команд на обычные и админские.
- FSM-хранилище в Redis (или Memory fallback).
- Основа для масштабирования по модулям (`users`, `integration`, и т.д.).

### Для чего использовать
- Как стартовую точку для нового бота.
- Как “скелет” для проектов с несколькими ролями пользователей.
- Как основу для проектов, где нужна админка через Telegram-интерфейс.

## 2. Структура проекта

```text
src/
  main.py                    # Точка входа
  core/
    config.py                # Pydantic Settings из .env
    setup.py                 # Создание Bot/Dispatcher, подключение middleware/router/dialogs
    commands.py              # Регистрация команд бота
    middleware.py            # Основная логика middleware
    logging_setup.py         # Конфиг логирования
    infrastructure/
      redis_client.py        # Подключение Redis
  database/
    base.py                  # Declarative Base
    engine.py                # Async engine/sessionmaker
    repository.py            # Базовый AbstractRepository
    unit_of_work.py          # Базовый AbstractUnitOfWork
  users/
    handlers.py              # Команды /start, /users, /test_error
    router.py                # Сборка users роутера
    states.py                # FSM состояния
    dialogs/
      dialogs.py             # Окна aiogram-dialog
      getters.py             # Получение данных для окон
      handlers.py            # Обработчики кнопок/инпутов диалога
    database/
      models.py              # SQLAlchemy модель Users
      schemas.py             # Pydantic UserSchema
      repository.py          # UserRepository
      uow.py                 # UserUnitOfWork
migrations/                 # Alembic миграции
docker-compose.yml          # Базовый compose
docker-compose.dev.yml      # dev compose
```

## 3. Технологии

- Python `3.12+`
- aiogram `3.24+`
- aiogram-dialog `2.4+`
- SQLAlchemy `2.x`
- Alembic
- Redis
- PostgreSQL
- Ruff + MyPy + pre-commit
- uv (менеджер окружения/зависимостей)

## 4. Конфигурация (`.env`)

Проект читает настройки из `.env` через `src/core/config.py`.

Основные переменные:

### Bot
- `TELEGRAM_TOKEN` - токен бота
- `LOG_LEVEL` - уровень логов (`DEBUG/INFO/WARNING/...`)
- `ADMIN_IDS` - список Telegram ID админов, например: `[123456789, 987654321]`
- `SHOW_ALERT` - показывать alert при отказе в доступе (`AccessByFlagsMiddleware`)
- `SHOW_AUTH_USERS` - уведомлять админов о новых пользователях (`AuthenticationMiddleware`)
- `DROP_PENDING_UPDATES` - удалять накопленные апдейты при старте

### Database
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`

### Redis
- `REDIS_URL` (если пусто, будет MemoryStorage)

### Proxy (опционально)
- `PROXY_IP`
- `PROXY_PORT`
- `PROXY_USER`
- `PROXY_PASSWORD`

## 5. Запуск проекта

### Вариант A: локально через uv

```bash
uv sync
uv run alembic upgrade head
uv run -m src.main
```

### Вариант B: Docker Compose (dev)

```bash
docker compose -f docker-compose.dev.yml up --build
```

Сервисы:
- `bot`
- `db` (PostgreSQL)
- `redis`
- `redis-insight` (в dev)

### Вариант C: Docker Compose (базовый)

```bash
docker compose up --build
```

## 6. Миграции Alembic

Команды:

```bash
uv run alembic revision --autogenerate -m "your message"
uv run alembic upgrade head
uv run alembic downgrade -1
```

В `migrations/env.py` URL БД берется из `settings.get_db_url_for_alembic()`, то есть из `.env`.

## 7. Базовые команды бота

Команды задаются в `src/core/commands.py`.

- `/start`
  - базовая точка входа пользователя;
  - поддерживает deep-link аргумент (например `cmd_users-<user_id>`), чтобы открыть карточку пользователя.

- `/users` (только для superuser через middleware flags)
  - без аргументов: открывает список пользователей;
  - с `ID`: открывает конкретного пользователя;
  - с `@username`: ищет/открывает по username;
  - с произвольной строкой: поиск по username/first_name/last_name.

- `/test_error`
  - специально бросает `RuntimeError` для проверки error middleware.

## 8. Middleware (ключевой раздел)

Файл: `src/core/middleware.py`  
Подключение: `src/core/setup.py` -> `setup_middlewares(dp)`.

### Порядок подключения сейчас

1. `AuthenticationMiddleware` для `message`
2. `AuthenticationMiddleware` для `callback_query`
3. `AccessByFlagsMiddleware` для `message`
4. `AccessByFlagsMiddleware` для `callback_query`
5. `UserBlockMiddleware` для `update`

Отключены (закомментированы):
- `VerificationMiddleware`
- `ErrorReportingMiddleware`

### 8.1 AuthenticationMiddleware

Назначение:
- получает пользователя из входящего события;
- ищет в БД по `telegram_id`;
- если не найден - создает запись;
- кладет пользователя в `data["current_user"]`.

Что влияет на логику:
- аргумент конструктора `show_auth_users` (`AuthenticationMiddleware(settings.show_auth_users)`);
- `settings.admin_ids` (кому отправлять уведомление о новом пользователе);
- наличие/отсутствие пользователя в БД.

Что добавляет в `data`:
- `current_user` (`UserSchema`).

Где это использовать:
- в хендлере можно принимать `current_user` как аргумент функции:
```python
@router.message(CommandStart())
async def cmd_start(message: Message, current_user: UserSchema):
    ...
```

### 8.2 AccessByFlagsMiddleware

Назначение:
- проверяет флаг `access` у хендлера;
- пускает только если у пользователя есть нужные права;
- иначе отправляет отказ и не вызывает хендлер.

Как задавать доступ:

```python
@router.message(Command("users"), flags={"access": ["superuser"]})
async def cmd_users(...):
    ...
```

Поддерживаемые права (сейчас):
- `superuser` -> `current_user.is_superuser`
- `verified` -> `current_user.is_verified`

Правило проверки:
- OR-логика (`any`) по списку флагов.

Важно:
- передавайте список: `["superuser"]`, `["verified"]`, `["superuser", "verified"]`;
- строка `"superuser"` технически тоже iterable, но в текущей реализации это даст посимвольную проверку и неверное поведение.

Что влияет на логику:
- `flags={"access": ...}` в конкретном хендлере;
- поля `is_superuser` / `is_verified` у `current_user`;
- `show_alert` в конструкторе middleware (`settings.show_alert`).

### 8.3 VerificationMiddleware (сейчас выключен)

Назначение:
- пропускать только `is_verified=True`.

Текущее состояние:
- в `setup_middlewares` закомментирован;
- если включить, ставить после `AuthenticationMiddleware`.

### 8.4 UserBlockMiddleware

Назначение:
- обрабатывает `my_chat_member`;
- при `kicked` -> `is_active=False`;
- при `member` -> `is_active=True`.

Что влияет на логику:
- апдейт типа `my_chat_member`;
- статус `new_chat_member.status`.

Практический смысл:
- можно безопасно исключать неактивных пользователей из рассылок.

### 8.5 ErrorReportingMiddleware (сейчас выключен)

Назначение:
- ловить ошибки и слать traceback админам.

Текущее состояние:
- в `setup_middlewares` закомментирован.

## 9. Данные пользователя и роли

Модель `Users` (`src/users/database/models.py`) хранит:
- `telegram_id`
- `username`
- `first_name`
- `last_name`
- `is_active`
- `is_superuser`
- `is_verified`
- `created_at`, `updated_at`

Ключевая логика ролей:
- `is_superuser=True` дает доступ к `/users` и админским командам;
- `is_verified=True` используется в middleware/флагах для верифицированного доступа;
- `is_active=False` ставится если пользователь заблокировал бота.

## 10. Dialogs и админский сценарий `/users`

Реализация: `src/users/dialogs/*`.

Что есть:
- список пользователей с пагинацией;
- поиск по ID/username/имени;
- карточка пользователя;
- кнопки переключения `is_superuser` и `is_verified`.

Важная особенность:
- при изменении `is_superuser` вызывается `set_user_commands(...)`, чтобы обновить команды прямо у конкретного пользователя.

## 11. Логирование

Файл: `src/core/logging_setup.py`.

- Поток + файл `logs/app.log`
- RotatingFileHandler: `10MB`, `backupCount=3`
- Формат стандартный (и предусмотрен JSON formatter)
- Уровень через `LOG_LEVEL`

## 12. Контроль качества кода

### pre-commit

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Что запускается:
- Ruff (`--fix`)
- MyPy

### Ручной запуск

```bash
uv run ruff check src tests --fix
uv run mypy src tests
```

## 13. Как использовать этот шаблон для нового проекта

1. Скопируйте/форкните репозиторий.
2. Переименуйте проект и контейнеры при необходимости.
3. Подготовьте новый `.env`.
4. Поднимите инфраструктуру (`docker compose ...`) или локально запустите БД/Redis.
5. Примените миграции `alembic upgrade head`.
6. Запустите бота.
7. Создайте новый модуль по аналогии с `users`:
   - `src/<module>/handlers.py`
   - `src/<module>/router.py`
   - при необходимости `database/`, `dialogs/`, `states.py`
8. Подключите роутер в `src/core/setup.py`.
9. Добавьте команды в `src/core/commands.py`.
10. Зафиксируйте требования доступа через `flags={"access": [...]}`.

## 14. Чеклист при старте нового проекта

- [ ] Токен бота и `ADMIN_IDS` заполнены
- [ ] БД и Redis доступны
- [ ] Миграции применены
- [ ] `AuthenticationMiddleware` и `AccessByFlagsMiddleware` подключены
- [ ] Команды (`/start`, админские) выставляются без ошибок
- [ ] Логи пишутся в `logs/app.log`
- [ ] pre-commit настроен

## 15. Текущие ограничения/заметки

- В проекте пока нет тестов в `tests/`.
- `VerificationMiddleware` и `ErrorReportingMiddleware` по умолчанию не активны.
- Для флага доступа используйте список, а не строку.
