@echo off
chcp 65001 > nul
cd /d "%~dp0"
rem Запуск всего бэкенда одним кликом: SQLite, без Docker, с hot reload.
rem Сам создаёт .venv, ставит зависимости и .env. Остановка: Ctrl+C или закрыть окно.
where py > nul 2>&1
if not errorlevel 1 goto run_py
where python > nul 2>&1
if not errorlevel 1 goto run_python
if exist ".venv\Scripts\python.exe" goto run_venv
echo Python 3.10+ required.
exit /b 1

:run_py
py -3 scripts\run_local.py %*
goto finish

:run_python
python scripts\run_local.py %*
goto finish

:run_venv
".venv\Scripts\python.exe" scripts\run_local.py %*

:finish
if errorlevel 1 (
    echo.
    echo Запуск завершился с ошибкой.
    pause
)
