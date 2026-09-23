@echo off
chcp 65001 > nul
cd /d "%~dp0"

if not exist .env (
    copy .env.example .env > nul
    echo Создан .env из .env.example ^(dev-значения^). Для prod сгенерируйте секреты: python scripts\generate_secrets.py
)

docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
if errorlevel 1 exit /b 1

set GATEWAY_PORT=8000
for /f "usebackq tokens=1,* delims==" %%a in (`findstr /b "API_GATEWAY_PORT=" .env`) do (
    for /f "tokens=1" %%p in ("%%b") do set GATEWAY_PORT=%%p
)

echo.
echo Сервисы запущены:
echo   API Gateway:   http://localhost:%GATEWAY_PORT%
echo   Состояние:     http://localhost:%GATEWAY_PORT%/health
echo   Swagger:       http://localhost:8001/api/v1/docs ^(auth^), http://localhost:8002/api/v1/docs ^(example^)
echo   Логи:          logs.bat [сервис]     Остановка: down.bat
