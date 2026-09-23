@echo off
chcp 65001 > nul
cd /d "%~dp0"

if not exist .env (
    echo Нет файла .env. Создайте его из .env.example и задайте секреты ^(python scripts\generate_secrets.py^).
    exit /b 1
)

rem Переменные оболочки приоритетнее .env - так prod нельзя случайно запустить в dev-режиме
set ENV=production
set DEBUG=false
docker compose -f docker-compose.yml up --build -d
if errorlevel 1 exit /b 1

echo.
echo Prod-конфигурация запущена. Статус: docker compose ps   Логи: logs.bat
