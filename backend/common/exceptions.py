"""Общие исключения и их обработчики. Формат ошибки: {"detail": ..., "code": ...}."""
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from common.logger import get_logger

logger = get_logger("common.exceptions")


class AppException(Exception):
    """Базовое прикладное исключение — превращается в JSON-ответ."""

    status_code = 500
    code = "error"
    default_detail = "Internal server error"

    def __init__(
        self,
        detail: Optional[str] = None,
        *,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ):
        self.detail = detail or self.default_detail
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        self.headers = headers
        super().__init__(self.detail)


class BadRequestError(AppException):
    status_code, code, default_detail = 400, "bad_request", "Bad request"


class UnauthorizedError(AppException):
    status_code, code, default_detail = 401, "unauthorized", "Not authenticated"

    def __init__(self, detail: Optional[str] = None, **kwargs):
        kwargs.setdefault("headers", {"WWW-Authenticate": "Bearer"})
        super().__init__(detail, **kwargs)


class ForbiddenError(AppException):
    status_code, code, default_detail = 403, "forbidden", "Forbidden"


class NotFoundError(AppException):
    status_code, code, default_detail = 404, "not_found", "Not found"


class ConflictError(AppException):
    status_code, code, default_detail = 409, "conflict", "Conflict"


async def _app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
        headers=exc.headers,
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "internal_error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, _app_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
