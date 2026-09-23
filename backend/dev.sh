#!/usr/bin/env bash
# Запуск в режиме разработки: hot reload, порты сервисов и БД доступны с localhost.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Создан .env из .env.example (dev-значения). Для prod сгенерируйте секреты: python scripts/generate_secrets.py"
fi

docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

# Порты читаем из .env, не выполняя его как shell-скрипт
port() { grep -E "^$1=" .env | head -n1 | cut -d= -f2 | cut -d'#' -f1 | tr -d '[:space:]'; }
GATEWAY_PORT="$(port API_GATEWAY_PORT)"; GATEWAY_PORT="${GATEWAY_PORT:-8000}"

echo
echo "Сервисы запущены:"
echo "  API Gateway:   http://localhost:${GATEWAY_PORT}"
echo "  Состояние:     http://localhost:${GATEWAY_PORT}/health"
echo "  Swagger:       http://localhost:8001/api/v1/docs (auth), http://localhost:8002/api/v1/docs (example)"
echo "  Логи:          ./logs.sh [сервис]     Остановка: ./down.sh"
