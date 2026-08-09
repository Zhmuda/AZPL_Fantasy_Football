# AZPL Fantasy Football

Фэнтези-футбол по Азербайджанской Премьер-лиге. Пользователи собирают состав из 15 реальных игроков лиги, каждый тур получают очки за реальную статистику матчей, соревнуются в общем рейтинге и в приватных мини-лигах с друзьями.

Данные об игроках, клубах, матчах и статистике синхронизируются автоматически с SofaScore.

## Возможности

- Регистрация/логин, JWT-аутентификация
- Сборка состава: 15 игроков (2 ВРТ / 5 ЗАЩ / 5 ПЗН / 3 НАП), бюджет £100m, максимум 3 игрока из одного клуба, схемы 4-4-2 / 4-3-3 / 5-2-3
- Капитан (×2 очков) и вице-капитан (×2, если капитан не сыграл), замены игроков между стартом и скамейкой — доступны в любой момент до дедлайна тура без ограничений
- Трансферы — до 3 в тур, отдельно от обычного управления составом
- Автоматический подсчёт очков после каждого матча (голы, передачи, сухие матчи, сейвы, пенальти, карточки — веса зависят от позиции), с разбивкой по событиям в карточке игрока
- Динамическое ценообразование игроков на основе очков/голов/передач текущего сезона, с учётом места клуба в прошлом сезоне для игроков с малой выборкой матчей
- Общий рейтинг + приватные мини-лиги по коду-приглашению
- Страница правил с полным описанием начисления очков и цен
- Админ-панель (sqladmin) с логами синхронизации и ручным повтором упавших задач
- 3 языка интерфейса: русский, английский, азербайджанский

## Стек технологий

| Слой | Технологии |
|---|---|
| Backend API | FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Alembic, JWT, slowapi (rate limiting), sqladmin |
| Сборщик данных | Celery + Redis, curl_cffi / datafc (SofaScore) |
| Frontend | React 18, Vite, react-router, react-i18next |
| Инфраструктура | Docker Compose, nginx (на хосте, вне докера) |

## Структура проекта

```
backend/      FastAPI-приложение: API, модели, схемы, миграции, админка
collector/    Celery-воркер: синхронизация данных SofaScore, подсчёт очков, цены
frontend/     React SPA
nginx/        конфиг для сценария с выделенным сервером (сейчас не используется)
docker-compose.yml         дев-окружение
docker-compose.prod.yml    прод (без nginx/certbot — фронт отдаёт nginx на хосте)
Makefile      шорткаты для частых команд (см. ниже)
```

## Быстрый старт (локально)

```bash
cp .env.example .env
# отредактируй .env — минимум SECRET_KEY и ADMIN_PASSWORD

make up            # поднимает postgres, redis, backend, collector, scheduler, frontend, adminer
make migrate        # применяет миграции БД
make sync-seasons   # первичная синхронизация сезонов/туров с SofaScore
make sync-squads    # синхронизация составов клубов
make set-prices     # первичный расчёт цен игроков
```

- Frontend: http://localhost:5173
- Backend API + Swagger: http://localhost:8000/api/docs
- Админ-панель: http://localhost:8000/admin
- Adminer (просмотр БД): http://localhost:8080

## Переменные окружения

Полный список — в `.env.example`. Основное:

| Переменная | Описание |
|---|---|
| `POSTGRES_*` | подключение к БД |
| `REDIS_URL` | брокер Celery |
| `SECRET_KEY` | подпись JWT |
| `ADMIN_PASSWORD` | пароль входа в `/admin` (независим от `SECRET_KEY`) |
| `ALLOWED_ORIGINS` | CORS, через запятую |
| `SOFASCORE_TOURNAMENT_ID` | ID турнира на SofaScore (по умолчанию — АПЛ Азербайджана) |

Источник данных SofaScore (`legacy` / `datafc`) переключается не через `.env`, а через `SystemSetting.sofascore_provider` в БД (редактируется в админке).

## Миграции БД

```bash
make migrate                    # применить все миграции
make revision m="описание"      # создать новую (autogenerate)
```

## Фоновые задачи (Celery)

Часть задач крутится по расписанию (`collector/beat_schedule.py`), часть — только вручную:

| Команда | Что делает | Расписание |
|---|---|---|
| `make sync-seasons` | сезоны и туры | ежедневно в 03:00 |
| `make sync-round` (`tasks.sync_matches.sync_current_round`) | матчи текущего тура | ежечасно |
| `make sync-squads` | составы клубов | ежедневно в 04:00 |
| `tasks.sync_stats.sync_finished_matches` | статистика завершённых матчей → подсчёт очков | каждые 30 минут |
| `make set-prices` | пересчёт цен игроков | только вручную |

Любую задачу можно запустить руками:

```bash
docker compose exec collector celery -A celery_app call <task.path>
```

## Админ-панель

`/admin`, логин `admin` / пароль из `ADMIN_PASSWORD`. Модели, статистика по матчам, фэнтези-команды, логи синхронизации с возможностью повторить упавшую задачу.

## Продакшн

`docker-compose.prod.yml` — без dockerized nginx/certbot: `backend`/`frontend` слушают только `127.0.0.1`, публичный трафик и TLS обслуживает nginx на самом хосте (см. `nginx/nginx.prod.conf` как референс конфига).

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```
