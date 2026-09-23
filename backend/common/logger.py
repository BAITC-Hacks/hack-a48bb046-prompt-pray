"""Единая настройка логирования для всех сервисов."""
import logging
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text

# ID текущего запроса: выставляется в RequestContextMiddleware
# и автоматически попадает в каждую строку лога.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

_FILE_FORMAT = "%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s"

# Цвет статуса ответа в access-логе: "GET /items -> 200 (3.1 ms)"
_STATUS_STYLES = (
    (r"-> 2\d\d", "bold green"),
    (r"-> 3\d\d", "cyan"),
    (r"-> 4\d\d", "bold yellow"),
    (r"-> 5\d\d|unhandled error", "bold red"),
    (r"\(\d+(\.\d+)? ms\)", "dim"),
)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class _ConsoleHandler(RichHandler):
    """Цветной вывод в консоль: время, уровень, request id, имя логгера и подсвеченное сообщение."""

    def render_message(self, record: logging.LogRecord, message: str) -> Text:
        text = Text()
        text.append(f"{getattr(record, 'request_id', '-')[:8]:<8} ", style="dim")
        name = "uvicorn" if record.name == "uvicorn.error" else record.name
        text.append(f"{name} ", style="cyan")
        body = super().render_message(record, message)
        if record.name.endswith(".access"):
            for pattern, style in _STATUS_STYLES:
                body.highlight_regex(pattern, style)
        text.append_text(body)
        return text


def setup_logging(service_name: str, level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """Настраивает root-логгер и возвращает логгер сервиса.

    Цвет включается только в терминале (или при `FORCE_COLOR=1`); в pipe/Docker без него вывод —
    чистый текст, `NO_COLOR` убирает цвета. В файл (`log_file`) всегда пишется обычный текст.
    """
    if hasattr(sys.stdout, "reconfigure"):
        # rich рисует рамки Unicode-символами; в консоли не на UTF-8 (cp1251) они не должны ронять логирование
        sys.stdout.reconfigure(errors="replace")
    # legacy_windows=False: иначе rich пытается рисовать через WinAPI даже в pipe (так запускает run_local.py)
    console = Console(soft_wrap=True, legacy_windows=False)
    console_handler = _ConsoleHandler(
        console=console, show_path=False, log_time_format="%H:%M:%S", omit_repeated_times=False,
        rich_tracebacks=True,
    )
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    handlers: list[logging.Handler] = [console_handler]

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))
        handlers.append(file_handler)

    request_filter = _RequestIdFilter()
    for handler in handlers:
        handler.addFilter(request_filter)

    logging.basicConfig(level=level.upper(), handlers=handlers, force=True)

    # Запросы логирует наш middleware, access-лог uvicorn только дублирует его
    logging.getLogger("uvicorn.access").disabled = True
    # Служебные сообщения uvicorn ("Started server process" и т. п.) — в тот же формат
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

    return logging.getLogger(service_name)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
