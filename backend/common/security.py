"""Защитные middleware: заголовки безопасности и rate limiting."""
import time
from collections import deque
from typing import Callable, Iterable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from common.logger import get_logger

logger = get_logger("common.security")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Добавляет базовые заголовки безопасности ко всем ответам."""

    def __init__(self, app, hsts: bool = False):
        super().__init__(app)
        self.hsts = hsts

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if self.hsts:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Ограничение частоты запросов по IP (скользящее окно, хранение в памяти процесса).

    Подходит для одного экземпляра gateway. При нескольких репликах нужен общий
    счётчик (например, Redis). Заголовку X-Forwarded-For верим только при
    trust_proxy_headers=True, то есть когда перед gateway стоит доверенный прокси.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        exclude_paths: Iterable[str] = ("/health", "/healthz"),
        trust_proxy_headers: bool = False,
    ):
        super().__init__(app)
        self.per_minute = requests_per_minute
        self.per_hour = requests_per_hour
        self.exclude_paths = tuple(exclude_paths)
        self.trust_proxy_headers = trust_proxy_headers
        self._hits: dict[str, deque[float]] = {}
        self._last_sweep = time.monotonic()

    def _client_ip(self, request: Request) -> str:
        if self.trust_proxy_headers:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _sweep(self, now: float) -> None:
        """Раз в минуту выбрасывает IP, от которых давно не было запросов."""
        if now - self._last_sweep < 60:
            return
        self._last_sweep = now
        for ip in [ip for ip, hits in self._hits.items() if not hits or now - hits[-1] > 3600]:
            del self._hits[ip]

    async def dispatch(self, request: Request, call_next: Callable):
        if request.method == "OPTIONS" or request.url.path.startswith(self.exclude_paths):
            return await call_next(request)

        now = time.monotonic()
        self._sweep(now)
        hits = self._hits.setdefault(self._client_ip(request), deque())
        while hits and now - hits[0] > 3600:
            hits.popleft()

        in_last_minute = sum(1 for t in reversed(hits) if now - t <= 60)
        if in_last_minute >= self.per_minute or len(hits) >= self.per_hour:
            logger.warning("Rate limit exceeded for %s", self._client_ip(request))
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests", "code": "rate_limited"},
                headers={"Retry-After": "60"},
            )

        hits.append(now)
        return await call_next(request)
