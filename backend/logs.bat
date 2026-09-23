@echo off
chcp 65001 > nul
cd /d "%~dp0"

rem Логи всех сервисов или одного: logs.bat auth_service
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f --tail=100 %*
