"""Middleware: контекст запроса (request id) и логирование запросов."""
import time
import uuid
from typing import Callable, Iterable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from common.logger import get_logger, request_id_ctx

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Берёт X-Request-ID из запроса (его проставляет gateway) или генерирует новый,
    кладёт в контекст логов и возвращает в заголовке ответа.
    """

    def __init__(self, app, service_name: str, exclude_paths: Iterable[str] = ("/health", "/healthz")):
        super().__init__(app)
        self.logger = get_logger(f"{service_name}.access")
        self.exclude_paths = tuple(exclude_paths)

    async def dispatch(self, request: Request, call_next: Callable):
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            self.logger.error(
                "%s %s -> unhandled error (%.1f ms)",
                request.method, request.url.path, (time.perf_counter() - started) * 1000,
            )
            raise
        finally:
            request_id_ctx.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        if not request.url.path.startswith(self.exclude_paths):
            self.logger.info(
                "%s %s -> %d (%.1f ms)",
                request.method, request.url.path, response.status_code,
                (time.perf_counter() - started) * 1000,
            )
        return response
