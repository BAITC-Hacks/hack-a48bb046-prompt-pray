# catalog_service — доменный слой (T-3)

T-3 реализует `app/models/` и `app/schemas/`. Конфигурация, запуск сервиса,
роуты и регистрация в gateway добавляются параллельно в T-2. Доменных API в T-3 нет.

Модели используют `common.db.Base`, UUID и временные метки. `app/main.py` импортирует
`app.models` и выполняет Alembic upgrade до `head` в startup — так
регистрируются все семь сущностей и таблица связи решений с откликами.
`business_id`, `team_id`, `user_id` — внешние идентификаторы без FK между сервисами.

Поля карточки: `context`, `data`, `expected_result`, `success_criteria`, `constraints`,
`users`, `business_contact`. Они допускают `null`: низкая полнота не запрещает публикацию.
PATCH нужно применять через `model_dump(exclude_unset=True)`: отсутствующее поле
сохраняется, явный `null` очищает поле; заголовок очищать нельзя.

`RatingBreakdown` хранит семь компонентов с ограничениями 20/20/15/15/10/10/10.
Итог и уровень вычисляются схемой ответа, отдельно в БД не дублируются.
Слой services (T-5) обязан пересчитывать компоненты в одной транзакции с изменением
карточки, проверять владельца и явное подтверждение перед публикацией.

`SelectionDecision` хранит историю ручных решений. Обязательный список
`selected_proposal_ids` может содержать ноль, один или несколько UUID откликов.
Слой services (T-7) обязан проверить владельца задачи и принадлежность всех
выбранных откликов этой задаче, а также право пользователя выступать от имени команды.
ORM-связи загружаются явно (`selectinload`) перед сериализацией async-объектов:
для карточки — `rating`, для каталога — `task.rating`, для решения — `selected_proposals`.
HTTP URL из `ProposalCreate` сохраняется как строка (либо `null`).

Проверки из `backend/`:

```sh
python scripts/run_tests.py catalog_service
python scripts/run_tests.py
```

Тесты домена вызывают настоящий `Database.create_tables()` на SQLite с включёнными FK.
Каркас T-2 подключает каталог к общему списку сервисов в `scripts/run_tests.py`.

## Миграции схемы (T-15)

Сервис применяет версии из `app/db/migrations/versions/` перед приёмом запросов.
`0001_catalog` создаёт новую базу из замороженного снимка `baseline.py`.
Для существующей базы, созданной старым `create_all`, миграция сравнивает таблицы,
колонки, типы, nullable, индексы, unique/FK, первичные ключи и количество CHECK.
При соответствии добавляется только запись в `alembic_version`: строки доменных
таблиц не переписываются. Частичная или несовместимая схема вызывает ошибку запуска;
не обходите её ручным `stamp`. Проверка не доказывает эквивалентность вручную изменённых
CHECK-выражений; такие базы следует отдельно сверять со снимком.
Повторный upgrade пропускает применённые версии. PostgreSQL использует транзакционную
advisory-блокировку между процессами миграций. SQLite запускайте одним процессом.

Перед обновлением остановите записи в каталог и сделайте резервную копию.
Команды ниже выполняются из `backend/` с активированным `.venv` и настройками JWT/БД
в `.env` или окружении. URL должен указывать именно на БД каталога.

SQLite (после остановки сервиса, стандартный путь локального запуска):

```powershell
python -c "import sqlite3; src=sqlite3.connect('data/catalog_service.db'); dst=sqlite3.connect('data/catalog_service.before-upgrade.db'); src.backup(dst); dst.close(); src.close()"
$env:DATABASE_URL = 'sqlite+aiosqlite:///C:/absolute/path/backend/data/catalog_service.db'
$env:PYTHONPATH = (Get-Location).Path
Set-Location catalog_service
python -m app.db.migrate
```

Для восстановления SQLite остановите сервис, сохраните неисправную базу отдельно,
удалите относящиеся к ней оставшиеся `-wal`/`-shm` после закрытия всех соединений
и замените файл базы проверенной резервной копией. Верните прежнюю версию приложения
перед запуском. Не копируйте только основной файл работающей WAL-базы.

PostgreSQL: используйте `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE` и `.pgpass` для
утилит PostgreSQL, а `DATABASE_URL=postgresql+asyncpg://...` для приложения.

```sh
pg_dump --format=custom --file=catalog.before-upgrade.dump
# Из backend/catalog_service, PYTHONPATH указывает на backend:
python -m app.db.migrate
```

Восстановление PostgreSQL выполняйте в отдельную пустую базу:

```sh
createdb catalog_restored
pg_restore --exit-on-error --single-transaction --dbname=catalog_restored catalog.before-upgrade.dump
```

Проверьте восстановленные данные, переключите DATABASE_URL на восстановленную базу
и запустите прежнюю версию приложения. Автоматический destructive downgrade запрещён.
В Docker отдельный upgrade: `docker compose run --rm --no-deps catalog_service python -m app.db.migrate`
из `backend/`; миграции входят в образ и dev mount вместе с `app/`.

Будущие изменения оформляйте отдельной Alembic-ревизией с `down_revision`, ссылающейся
на предыдущую. Не меняйте `0001_catalog`/`baseline.py` вслед за ORM-моделями.
Для SQLite при ALTER используйте batch-операции Alembic. Добавляйте тест обновления
с предыдущей версии и сохранения данных перед включением миграции в startup.

Проверки на обеих СУБД (PostgreSQL — только тестовый сервер; тесты создают и удаляют
собственные изолированные схемы, пользователь должен иметь право CREATE SCHEMA):

```powershell
$env:CATALOG_TEST_POSTGRES_URL = 'postgresql+asyncpg://test_user@127.0.0.1:55435/postgres'
python scripts/run_tests.py
```

Без `CATALOG_TEST_POSTGRES_URL` PostgreSQL-проверки пропускаются, SQLite выполняется всегда.
