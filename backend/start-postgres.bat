@echo off
rem То же, что start.bat, но на PostgreSQL ^(контейнер из docker-compose, нужен Docker^).
call "%~dp0start.bat" --db postgres %*
