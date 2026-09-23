# backend — микросервисный бэкенд на FastAPI

Основа для быстрого старта: **API Gateway + сервис авторизации + эталонный CRUD-сервис**,
общий пакет `common/`, PostgreSQL (своя БД на каждый сервис), Docker Compose.
Структура и подход взяты из `CompEduX/server`.

```
Клиент ──► api_gateway :8000 ──► auth_service     ──► auth_db
           (JWT, CORS,           example_service  ──► example_db
            rate limit,          (свои сервисы…)
            маршрутизация)
```

## Быстрый старт

Нужен только Python 3.10+. Docker для разработки не требуется.

**Windows — двойной клик по `start.bat`** (Linux/macOS — `./start.sh`).

При первом запуске скрипт сам создаёт `.venv`, ставит зависимости (около минуты) и создаёт `.env`
из `.env.example`, затем поднимает gateway и все сервисы с автоперезапуском при изменении кода.
Данные лежат в SQLite-файлах `data/<сервис>.db`. Остановка — `Ctrl+C` (или закрыть окно).

| Команда                            | Что делает                                              |
|------------------------------------|---------------------------------------------------------|
| `start.bat` / `./start.sh`         | всё на SQLite, без Docker                               |
| `start-postgres.bat` / `./start-postgres.sh` | то же, но БД — PostgreSQL в контейнере (нужен Docker) |
| `dev.bat` / `./dev.sh`             | всё в Docker Compose (PostgreSQL, hot reload)           |
| `start.bat --reset-db`             | очистить SQLite-базы перед стартом                      |
| `start.bat --no-reload`            | без автоперезапуска                                     |

Хранилище по умолчанию задаёт `DB_BACKEND=sqlite|postgres` в `.env`, флаг `--db` его перекрывает.
Переход на PostgreSQL не требует правок кода: сервисы выбирают драйвер по настройкам
(`DATABASE_URL` или `POSTGRES_*`), а оба драйвера — `aiosqlite` и `asyncpg` — уже в зависимостях.
`start-postgres` поднимает только контейнер `postgres` из `docker-compose.yml`, а сервисы запускает локально;
данные Postgres хранятся в docker-томе и остаются после остановки (`./down.sh -v` — удалить).

| Что            | Адрес                                  |
|----------------|----------------------------------------|
| API (единственный вход) | http://localhost:8000/api/v1/… |
| Состояние всех сервисов | http://localhost:8000/health   |
| Swagger auth_service    | http://localhost:8001/api/v1/docs (только dev) |
| Swagger example_service | http://localhost:8002/api/v1/docs (только dev) |
| PostgreSQL              | localhost:5432 (только `start-postgres` и `dev`) |

Swagger каждого сервиса — на его собственном порту: проксируемые gateway методы в его схему
не попадают (в Swagger gateway, `/api/v1/docs`, только служебный `/health`).

Проверка руками:

```bash
curl -X POST localhost:8000/api/v1/auth/register -H 'Content-Type: application/json' \
     -d '{"email":"me@example.com","username":"myuser","password":"long-enough-pass"}'
curl -X POST localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' \
     -d '{"email":"me@example.com","password":"long-enough-pass"}'      # → access_token
curl localhost:8000/api/v1/items -H "Authorization: Bearer <access_token>"
```

Для Docker-режима (`dev.*`): остановка — `./down.sh` (`./down.sh -v` — вместе с данными БД), логи — `./logs.sh [сервис]`.

## Структура

```
backend/
├── common/                  общий код (импортируется как `common.*`)
│   ├── app.py                 create_app(): middleware, обработчики ошибок, /health, /healthz
│   ├── config.py              BaseServiceSettings, DatabaseSettings (валидация секретов)
│   ├── db.py                  Base, миксины, Database (async SQLAlchemy)
│   ├── auth.py                выпуск/проверка JWT, зависимость «текущий пользователь»
│   ├── exceptions.py          AppException → {"detail", "code"}
│   ├── security.py            rate limit, заголовки безопасности
│   ├── middleware.py          X-Request-ID + лог запросов
│   └── logger.py              логирование с request id
├── api_gateway/             вход: проверка JWT, проксирование, агрегированный /health
├── auth_service/            регистрация, вход, refresh, /users/me
├── example_service/         эталон CRUD (items) — копируйте для новых сервисов
├── postgres-init/           создание БД и пользователей при первом старте
├── scripts/                 run_local.py (запуск без Docker), generate_secrets.py, run_tests.py
├── start.bat / start.sh     запуск одним кликом (SQLite); start-postgres.* — то же на Postgres
├── docker-compose.yml       prod-like: наружу только gateway
├── docker-compose.dev.yml   надстройка для разработки: reload, порты, монтирование кода
└── .env.example
```

Внутри сервиса слои идут сверху вниз:
`api/ (роуты, deps)` → `services/` (бизнес-логика, коммиты) → `repositories/` (запросы) → `models/` (ORM);
`schemas/` — Pydantic-модели запросов и ответов.

## Как это работает

- **Авторизация.** Токены выпускает только `auth_service` (access — 30 мин, refresh — 7 дней).
  Gateway проверяет подпись access-токена и отбрасывает невалидные запросы, не дойдя до сервисов;
  публичны лишь `POST /auth/register|login|refresh` (список — `PUBLIC_ENDPOINTS` в `api_gateway/app/core/config.py`).
  Токен пересылается дальше, и сервисы проверяют его сами (общий `JWT_SECRET_KEY`) — обход gateway внутри сети ничего не даёт.
  Обычные сервисы в `auth_service` за каждым запросом не ходят: пользователь берётся из токена
  (отозвать доступ можно только истечением токена). Сам `auth_service` дополнительно сверяет пользователя
  с БД, поэтому заблокированный пользователь теряет доступ к `/users/*` сразу.
- **Маршрутизация.** `/api/v1/<prefix>/…` → сервис, владеющий префиксом; путь пересылается без изменений.
  Таблица — `SERVICES` в `api_gateway/app/core/config.py`.
- **Ошибки** везде одного формата: `{"detail": "...", "code": "not_found"}`.
- **БД.** У каждого сервиса своя база и свой пользователь Postgres, чужие базы ему недоступны.
  Таблицы создаются при старте (`create_all`). Для эволюции схемы в проде подключите Alembic.
  В разработке и тестах можно использовать SQLite (`DATABASE_URL=sqlite+aiosqlite:///…`), в production он запрещён валидацией.
- **Health.** `/healthz` — процесс жив; `/health` — готовность (у сервисов проверяет БД, у gateway — все сервисы; 503 при сбое).

## Добавление сервиса

1. Скопируйте `example_service/` → `orders_service/`, переименуйте модели/схемы/эндпоинты, в `main.py`
   и `db/session.py` поменяйте `service_name`.
2. **Gateway** — `api_gateway/app/core/config.py`: поле `ORDERS_SERVICE_URL` в `Settings` и запись
   `ServiceRoute("orders", settings.ORDERS_SERVICE_URL, prefixes=("orders",))` в `SERVICES`.
3. **Compose** — в `docker-compose.yml` скопируйте блок `example_service` (БД `ORDERS_DB_*`, healthcheck),
   добавьте `ORDERS_SERVICE_URL: http://orders_service:8000` в окружение gateway и зависимость от нового сервиса;
   в `docker-compose.dev.yml` — порт и монтирование кода.
4. **БД** — `ORDERS_DB_*` в `.env.example`/`.env`, строка `create_db …` в `postgres-init/01-create-databases.sh`,
   переменные `ORDERS_DB_*` в окружении контейнера `postgres`.
   Скрипт срабатывает только на пустом томе; для уже созданного окружения либо `./down.sh -v` (данные пропадут),
   либо создайте БД вручную:
   `docker compose exec postgres psql -U postgres -c "CREATE ROLE orders_user LOGIN PASSWORD '…'" -c "CREATE DATABASE orders_db OWNER orders_user"`.
5. Добавьте имя сервиса в `SERVICES` в `scripts/run_tests.py` и `scripts/run_local.py` (запуск `start.*`).

## Тесты

```bash
pip install -r requirements-dev.txt
python scripts/run_tests.py                 # все сервисы (по отдельности: пакет `app` у всех одинаков)
python scripts/run_tests.py auth_service    # один сервис
```

Тесты идут на SQLite (`DATABASE_URL=sqlite+aiosqlite://…`), Docker не нужен;
gateway тестируется с подменённым upstream (`httpx.MockTransport`).

## Запуск без Docker вручную

`start.bat` делает следующее сам; вручную (например, в отладчике IDE) — из корня, по одному процессу на сервис:

```bash
export JWT_SECRET_KEY=$(python scripts/generate_secrets.py | grep JWT | cut -d= -f2)
export DATABASE_URL=sqlite+aiosqlite:///./auth.db      # или POSTGRES_HOST/PORT/DB/USER/PASSWORD
(cd auth_service    && PYTHONPATH=.. python -m uvicorn app.main:app --port 8001 --reload)
# так же example_service (--port 8002, свой DATABASE_URL) и api_gateway (--port 8000);
# у gateway по умолчанию AUTH_SERVICE_URL=http://localhost:8001, EXAMPLE_SERVICE_URL=http://localhost:8002
```

На Windows задайте переменные через `$env:NAME='…'` (PowerShell) и `set PYTHONPATH=..` (cmd).
Новый сервис для `start.*` добавляется в кортеж `SERVICES` в `scripts/run_local.py`.

## Production

1. `python scripts/generate_secrets.py` → значения в `.env`; `ENV=production`, укажите `BACKEND_CORS_ORIGINS`.
2. `./prod.sh` (Windows: `prod.bat`) — наружу публикуется только gateway; Swagger отключён.
3. Сервисы **откажутся стартовать** с `dev-only` секретами, коротким `JWT_SECRET_KEY`, слабым паролем БД
   или CORS без явных origin'ов — это намеренная защита от запуска dev-конфигурации в prod.
4. Поставьте перед gateway reverse proxy с TLS (nginx, Traefik, облачный балансировщик) и только тогда
   включайте `TRUST_PROXY_HEADERS=true`.
5. SQLite в production запрещён: при `ENV=production` без `POSTGRES_*` или с `sqlite…` в `DATABASE_URL` сервис не стартует.
6. Rate limit хранится в памяти процесса — при нескольких репликах gateway нужен общий счётчик (Redis).

## Клиент (фронтенд)

Парный проект — [`../frontend`](../frontend/README.md) (Nuxt 4). Сейчас он к API не подключён.
Для подключения: фронтенд ходит только на gateway (`:8000`), а его origin (dev — `http://localhost:3000`)
нужно добавить в `BACKEND_CORS_ORIGINS`, если запросы идут из браузера напрямую. Меняя контракт API
(схемы в `*/app/schemas/`, префиксы в `SERVICES`), обновляйте клиент в том же наборе изменений.

## Работа с git

Общие правила команды (ветки, коммиты, что нельзя коммитить) — в [`AI.md`](../AI.md#git-работаем-через-ветки).
Для бэкенда дополнительно: `.env`, `data/`, `*.db`, `.venv/` в git не попадают (см. `.gitignore`);
изменение схемы БД или публичного контракта API — отдельный коммит с пояснением в теле сообщения.

## Чем отличается от CompEduX/server

- Образы собираются с контекстом в корне, поэтому `common/` попадает в контейнеры
  (в оригинале Dockerfile сервисов не видят `common/`).
- Токены проверяются локально по подписи, без HTTP-запроса `verify-token` на каждый вызов.
- Секретов по умолчанию нет; в prod слабые значения запрещены. Порты БД и сервисов в prod не публикуются.
- Rate limit только на gateway (внутри сети все запросы приходят с его IP, на сервисах он бы душил всех сразу).
- Убраны предметные части (курсы, комнаты, статистика, друзья) и Rich-логгер с перехватчиками.
