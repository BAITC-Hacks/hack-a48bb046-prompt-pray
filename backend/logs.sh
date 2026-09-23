#!/usr/bin/env bash
# Логи всех сервисов или одного: ./logs.sh auth_service
set -euo pipefail
cd "$(dirname "$0")"

docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f --tail=100 "$@"
