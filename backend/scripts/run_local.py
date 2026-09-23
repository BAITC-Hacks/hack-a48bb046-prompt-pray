#!/usr/bin/env python3
"""
Запуск всего бэкенда одной командой, без Docker.

    start.bat / ./start.sh                  # SQLite, hot reload (двойной клик по start.bat)
    start-postgres.bat / ./start-postgres.sh  # то же, но на PostgreSQL в контейнере
    python scripts/run_local.py --help

При первом запуске сам создаёт `.venv`, ставит зависимости и создаёт `.env` из `.env.example`.
Поднимает api_gateway и все сервисы отдельными процессами; Ctrl+C останавливает всё.

Хранилище выбирается флагом `--db` или `DB_BACKEND` в `.env`:
  sqlite    — файлы `data/<сервис>.db`, ничего устанавливать не нужно (по умолчанию)
  postgres  — контейнер postgres из docker-compose (нужен Docker), БД и пользователи
              берутся из `<PREFIX>_DB_*` в `.env`, как и в docker-compose
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import venv
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT / ".venv"
VENV_PYTHON = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
DEPS_STAMP = VENV_DIR / ".requirements.sha256"
DATA_DIR = ROOT / "data"


@dataclass(frozen=True)
class Service:
    directory: str
    port_var: str
    default_port: int
    db_key: str | None = None  # префикс переменных БД: AUTH → AUTH_DB_NAME/USER/PASSWORD
    url_var: str | None = None  # переменная gateway с адресом сервиса


# Чтобы запускать новый сервис, добавьте его сюда (как и в docker-compose и api_gateway/app/core/config.py)
SERVICES = (
    Service("auth_service", "AUTH_SERVICE_PORT", 8001, db_key="AUTH", url_var="AUTH_SERVICE_URL"),
    Service("example_service", "EXAMPLE_SERVICE_PORT", 8002, db_key="EXAMPLE", url_var="EXAMPLE_SERVICE_URL"),
    Service("catalog_service", "CATALOG_SERVICE_PORT", 8004, db_key="CATALOG", url_var="CATALOG_SERVICE_URL"),
    Service("ai_service", "AI_SERVICE_PORT", 8003, url_var="AI_SERVICE_URL"),
)
GATEWAY = Service("api_gateway", "API_GATEWAY_PORT", 8000)


def fail(message: str) -> None:
    print(f"\nОшибка: {message}", file=sys.stderr)
    sys.exit(1)


# --------------------------------------------------------------------------- окружение

def in_project_venv() -> bool:
    return Path(sys.prefix).resolve() == VENV_DIR.resolve()


def deps_digest() -> str:
    files = sorted([*ROOT.glob("requirements*.txt"), *ROOT.glob("*/requirements*.txt")])
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode() + path.read_bytes())
    return digest.hexdigest()


def venv_runs() -> bool:
    return subprocess.call([str(VENV_PYTHON), "-c", "pass"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0


def repair_venv() -> None:
    """.venv, привезённый с другой машины, ссылается на чужой Python: правим pyvenv.cfg или пересоздаём."""
    cfg = VENV_DIR / "pyvenv.cfg"
    text = cfg.read_text(encoding="utf-8") if cfg.exists() else ""
    match = re.search(r"^version\s*=\s*(\d+)\.(\d+)", text, re.M)
    same_version = bool(match) and (int(match[1]), int(match[2])) == sys.version_info[:2]

    if same_version and not venv_runs():
        base = Path(sys._base_executable)
        fixed = []
        for line in text.splitlines():
            key = line.split("=")[0].strip()
            if key == "home":
                line = f"home = {base.parent}"
            elif key == "executable":
                line = f"executable = {base}"
            fixed.append(line)
        cfg.write_text("\n".join(fixed) + "\n", encoding="utf-8")

    if not (same_version and venv_runs()):
        print("Виртуальное окружение .venv не подходит этой машине (другой Python) — пересоздаю …", flush=True)
        venv.EnvBuilder(with_pip=True, clear=True).create(VENV_DIR)


def bootstrap_venv() -> int:
    """Создаёт .venv, ставит зависимости и перезапускает этот же скрипт уже внутри .venv."""
    if VENV_PYTHON.exists():
        repair_venv()
    if not VENV_PYTHON.exists():
        print("Создаю виртуальное окружение .venv …", flush=True)
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)

    digest = deps_digest()
    if not DEPS_STAMP.exists() or DEPS_STAMP.read_text().strip() != digest:
        print("Устанавливаю зависимости (первый запуск или изменился requirements) …", flush=True)
        pip = [str(VENV_PYTHON), "-m", "pip", "install", "--disable-pip-version-check", "-q",
               "-r", str(ROOT / "requirements-local.txt")]
        if subprocess.call(pip, cwd=ROOT) != 0:
            fail("не удалось установить зависимости (см. вывод pip выше)")
        DEPS_STAMP.write_text(digest)

    return subprocess.call([str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])


def ensure_env_file() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        shutil.copyfile(ROOT / ".env.example", env_file)
        print("Создан .env из .env.example (dev-значения)")


def load_dotenv(path: Path) -> dict[str, str]:
    """Минимальный разбор .env: KEY=VALUE, комментарии после `#`, значения в кавычках."""
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) > 1 and value[0] in "\"'" and value.endswith(value[0]):
            value = value[1:-1]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        values[key.strip()] = value
    return values


# --------------------------------------------------------------------------- БД

def sqlite_env(service: Service) -> dict[str, str]:
    DATA_DIR.mkdir(exist_ok=True)
    return {"DATABASE_URL": f"sqlite+aiosqlite:///{(DATA_DIR / f'{service.directory}.db').as_posix()}"}


def postgres_env(service: Service, config: dict[str, str]) -> dict[str, str]:
    key = service.db_key
    password = config.get(f"{key}_DB_PASSWORD")
    if not password:
        fail(f"в .env не задан {key}_DB_PASSWORD")
    return {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": config.get("POSTGRES_PORT") or "5432",
        "POSTGRES_DB": config.get(f"{key}_DB_NAME") or f"{key.lower()}_db",
        "POSTGRES_USER": config.get(f"{key}_DB_USER") or f"{key.lower()}_user",
        "POSTGRES_PASSWORD": password,
    }


def start_postgres_container() -> None:
    if shutil.which("docker") is None:
        fail("Docker не найден. Установите Docker Desktop или запустите на SQLite: start.bat")
    print("Поднимаю PostgreSQL (docker compose) …", flush=True)
    cmd = ["docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.dev.yml",
           "up", "-d", "--wait", "postgres"]
    if subprocess.call(cmd, cwd=ROOT) != 0:
        fail("не удалось поднять PostgreSQL. Убедитесь, что Docker запущен, или используйте SQLite: start.bat")


# --------------------------------------------------------------------------- процессы

def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def kill_tree(proc: subprocess.Popen, sig: int | None = None) -> None:
    """Останавливает процесс вместе с потомками (uvicorn --reload порождает воркер)."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            os.killpg(os.getpgid(proc.pid), sig or signal.SIGKILL)
        except ProcessLookupError:
            pass


def stop_all(procs: list[tuple[str, subprocess.Popen]], wait: float) -> None:
    running = [p for _, p in procs if p.poll() is None]
    if os.name != "nt":
        for proc in running:
            kill_tree(proc, signal.SIGTERM)
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline and any(p.poll() is None for p in running):
        time.sleep(0.1)
    for proc in running:
        if proc.poll() is None:
            kill_tree(proc)


def use_color() -> bool:
    """Цвет — в терминале или при FORCE_COLOR; NO_COLOR отключает (https://no-color.org)."""
    if "NO_COLOR" in os.environ:
        return False
    return bool(os.environ.get("FORCE_COLOR")) or sys.stdout.isatty()


# 256-цветные коды префиксов [gateway] / [auth] / [example]
TAG_COLORS = {"gateway": 208, "auth": 141, "example": 205}
TAG_WIDTH = 9  # "[example]"


def pump_output(tag: str, proc: subprocess.Popen, color: bool) -> None:
    label = f"[{tag}]".ljust(TAG_WIDTH)
    if color:
        label = f"\033[1;38;5;{TAG_COLORS.get(tag, 250)}m{label}\033[0m"
    for line in proc.stdout:
        print(f"{label} {line.rstrip()}", flush=True)


def spawn(service: Service, port: int, host: str, env: dict[str, str], reload: bool,
          color: bool) -> subprocess.Popen:
    cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port), "--no-access-log"]
    if color:
        cmd.append("--use-colors")
    if reload:
        cmd += ["--reload", "--reload-dir", "app", "--reload-dir", "../common"]
    return subprocess.Popen(
        cmd,
        cwd=ROOT / service.directory,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=(os.name != "nt"),
    )


def wait_until_healthy(url: str, procs: list[tuple[str, subprocess.Popen]], timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for name, proc in procs:
            if proc.poll() is not None:
                fail(f"процесс {name} завершился с кодом {proc.returncode} (причина — в логах выше)")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)
    return False


# --------------------------------------------------------------------------- main

def main() -> None:
    parser = argparse.ArgumentParser(description="Запуск бэкенда без Docker: gateway + все сервисы.")
    parser.add_argument("--db", choices=("sqlite", "postgres"),
                        help="хранилище (по умолчанию DB_BACKEND из .env, иначе sqlite)")
    parser.add_argument("--no-reload", action="store_true", help="без автоперезапуска при изменении кода")
    parser.add_argument("--host", default="127.0.0.1", help="адрес привязки (по умолчанию только localhost)")
    parser.add_argument("--reset-db", action="store_true", help="удалить файлы SQLite в data/ перед стартом")
    args = parser.parse_args()

    ensure_env_file()
    config = {**load_dotenv(ROOT / ".env"), **os.environ}
    backend = args.db or config.get("DB_BACKEND", "").lower() or "sqlite"
    if backend not in ("sqlite", "postgres"):
        fail(f"DB_BACKEND должен быть sqlite или postgres, получено: {backend!r}")

    if args.reset_db:
        for db_file in DATA_DIR.glob("*.db"):
            db_file.unlink()
            print(f"Удалена БД {db_file.relative_to(ROOT)}")

    ports = {s.directory: int(config.get(s.port_var) or s.default_port) for s in (*SERVICES, GATEWAY)}
    busy = [f"{name} (порт {port})" for name, port in ports.items() if port_in_use("127.0.0.1", port)]
    if busy:
        fail("порты заняты: " + ", ".join(busy) + ". Остановите другие копии (dev.bat/down.bat) "
             "или измените порты в .env")

    if backend == "postgres":
        start_postgres_container()

    color = use_color()
    base_env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    if color:
        # Вывод сервисов идёт через pipe, поэтому сами они цвет не включат: просим явно
        # и говорим им ширину терминала за вычетом префикса [сервис]
        base_env["FORCE_COLOR"] = "1"
        base_env["COLUMNS"] = str(max(60, shutil.get_terminal_size().columns - TAG_WIDTH - 1))
    if backend == "postgres":
        base_env.pop("DATABASE_URL", None)  # иначе он перекрыл бы POSTGRES_*

    procs: list[tuple[str, subprocess.Popen]] = []
    interrupted = False
    try:
        for service in (*SERVICES, GATEWAY):
            env = dict(base_env)
            if service.directory == "catalog_service":
                env["AI_SERVICE_URL"] = f"http://127.0.0.1:{ports['ai_service']}"
            if service.db_key:
                env.update(sqlite_env(service) if backend == "sqlite" else postgres_env(service, config))
            elif service == GATEWAY:  # gateway: адреса сервисов на localhost
                env.update({s.url_var: f"http://127.0.0.1:{ports[s.directory]}" for s in SERVICES})
            proc = spawn(service, ports[service.directory], args.host, env, reload=not args.no_reload, color=color)
            procs.append((service.directory, proc))
            tag = service.directory.replace("_service", "").replace("api_", "")
            threading.Thread(target=pump_output, args=(tag, proc, color), daemon=True).start()

        gateway_port = ports[GATEWAY.directory]
        if not wait_until_healthy(f"http://127.0.0.1:{gateway_port}/health", procs, timeout=90):
            fail("сервисы не стали готовыми за 90 секунд (см. логи выше)")

        db_note = ("SQLite, файлы в data/" if backend == "sqlite"
                   else f"PostgreSQL localhost:{config.get('POSTGRES_PORT') or 5432}")
        green, reset = ("\033[1;32m", "\033[0m") if color else ("", "")
        print(f"""
{green}Бэкенд запущен{reset} ({db_note}):
  API Gateway:  http://localhost:{gateway_port}/api/v1/…
  Состояние:    http://localhost:{gateway_port}/health
  Swagger:      http://localhost:{ports['auth_service']}/api/v1/docs (auth), \
http://localhost:{ports['example_service']}/api/v1/docs (example)
Остановка: Ctrl+C
""", flush=True)

        while all(proc.poll() is None for _, proc in procs):
            time.sleep(0.5)
        crashed = next(name for name, proc in procs if proc.poll() is not None)
        print(f"\nПроцесс {crashed} остановился — останавливаю остальные.", flush=True)
    except KeyboardInterrupt:
        interrupted = True
        print("\nОстанавливаю сервисы …", flush=True)
    finally:
        stop_all(procs, wait=5 if interrupted else 1)
        if backend == "postgres":
            print("PostgreSQL остаётся запущенным (данные сохраняются); остановить: down.bat / ./down.sh")


if __name__ == "__main__":
    if sys.version_info < (3, 10):
        fail("нужен Python 3.10 или новее")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    if os.name == "nt":
        os.system("")  # включает обработку ANSI-цветов в консоли Windows
    if not in_project_venv():
        sys.exit(bootstrap_venv())
    main()
