#!/usr/bin/env bash
# Останавливает контейнеры (данные БД сохраняются). Полная очистка вместе с БД: ./down.sh -v
set -euo pipefail
cd "$(dirname "$0")"

docker compose -f docker-compose.yml -f docker-compose.dev.yml down "$@"
