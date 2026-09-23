#!/usr/bin/env bash
# Запуск всего бэкенда одной командой: SQLite, без Docker, с hot reload.
# Сам создаёт .venv, ставит зависимости и .env. Флаги: ./start.sh --help
set -euo pipefail
cd "$(dirname "$0")"
PY="$(command -v python3 || command -v python)" || { echo "Не найден Python 3.10+"; exit 1; }
exec "$PY" scripts/run_local.py "$@"
