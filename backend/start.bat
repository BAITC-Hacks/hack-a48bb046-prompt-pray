@echo off
chcp 65001 > nul
cd /d "%~dp0"
rem Запуск всего бэкенда одним кликом: SQLite, без Docker, с hot reload.
rem Сам создаёт .venv, ставит зависимости и .env. Остановка: Ctrl+C или закрыть окно.
where py > nul 2>&1 && (set "PY=py -3") || (set "PY=python")
%PY% scripts\run_local.py %*
if errorlevel 1 (
    echo.
    echo Запуск завершился с ошибкой.
    pause
)
