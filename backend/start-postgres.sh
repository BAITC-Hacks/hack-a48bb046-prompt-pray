#!/usr/bin/env bash
# То же, что start.sh, но на PostgreSQL (контейнер из docker-compose, нужен Docker).
set -euo pipefail
cd "$(dirname "$0")"
exec ./start.sh --db postgres "$@"
