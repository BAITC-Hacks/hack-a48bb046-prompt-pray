#!/bin/bash
# Выполняется контейнером postgres ОДИН раз — при первой инициализации тома.
# Создаёт для каждого сервиса отдельные БД и пользователя; чужие БД ему недоступны.
#
# Добавили новый сервис после первого запуска? Скрипт повторно не сработает —
# выполните create_db вручную (см. README, раздел «Добавление сервиса»).
set -euo pipefail

create_db() {
    local db="$1" user="$2" password="$3"
    if [ -z "$db" ] || [ -z "$user" ] || [ -z "$password" ]; then
        echo "create_db: не заданы имя БД, пользователь или пароль" >&2
        exit 1
    fi

    # \gexec выполняет результат SELECT как SQL; format(%I/%L) безопасно экранирует имена и пароль
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
         -v db="$db" -v usr="$user" -v pwd="$password" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'usr', :'pwd')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'usr') \gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'db', :'usr')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'db') \gexec

SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'db') \gexec
SQL
    echo "База $db (владелец $user) готова"
}

create_db "$AUTH_DB_NAME"    "$AUTH_DB_USER"    "$AUTH_DB_PASSWORD"
create_db "$EXAMPLE_DB_NAME" "$EXAMPLE_DB_USER" "$EXAMPLE_DB_PASSWORD"
create_db "$CATALOG_DB_NAME" "$CATALOG_DB_USER" "$CATALOG_DB_PASSWORD"
