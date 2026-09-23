#!/usr/bin/env bash
# Запуск prod-like конфигурации: наружу опубликован только api_gateway.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
    echo "Нет файла .env. Создайте его из .env.example и задайте секреты (python scripts/generate_secrets.py)." >&2
    exit 1
fi

# Переменные оболочки приоритетнее .env — так prod нельзя случайно запустить в dev-режиме
ENV=production DEBUG=false docker compose -f docker-compose.yml up --build -d

echo
echo "Prod-конфигурация запущена. Статус: docker compose ps   Логи: ./logs.sh"
