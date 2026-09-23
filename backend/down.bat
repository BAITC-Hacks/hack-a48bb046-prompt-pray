@echo off
chcp 65001 > nul
cd /d "%~dp0"

rem Останавливает контейнеры (данные БД сохраняются). Полная очистка вместе с БД: down.bat -v
docker compose -f docker-compose.yml -f docker-compose.dev.yml down %*
