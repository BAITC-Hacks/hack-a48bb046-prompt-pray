"""Фабрика FastAPI-приложения: одинаковая «обвязка» для всех сервисов."""
from typing import Awaitable, Callable, Mapping, Optional, Sequence

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from common.exceptions import register_exception_handlers
from common.logger import setup_logging
from common.middleware import RequestContextMiddleware
from common.security import RateLimitMiddleware, SecurityHeadersMiddleware

HealthCheck = Callable[[], Awaitable[bool]]


def create_app(
    *,
    title: str,
    service_name: str,
    settings,
    description: str = "",
    lifespan=None,
    health_checks: Optional[Mapping[str, HealthCheck]] = None,
    register_health: bool = True,
    cors_origins: Sequence[str] = (),
    rate_limit_per_minute: Optional[int] = None,
    rate_limit_per_hour: int = 1000,
    trust_proxy_headers: bool = False,
) -> FastAPI:
    """
    Создаёт приложение с логированием, обработчиками ошибок, middleware и health-эндпоинтами.

    - /healthz — liveness: процесс жив, зависимости не проверяются;
    - /health  — readiness: выполняет `health_checks` (например, пинг БД), при сбое 503.

    Rate limiting включается только если передан `rate_limit_per_minute` — его место
    на gateway: внутри сети все запросы приходят с одного IP gateway.
    """
    logger = setup_logging(service_name, settings.LOG_LEVEL)
    docs_enabled = not settings.is_production
    prefix = settings.API_V1_STR

    app = FastAPI(
        title=title,
        description=description,
        version=settings.VERSION,
        lifespan=lifespan,
        openapi_url=f"{prefix}/openapi.json" if docs_enabled else None,
        docs_url=f"{prefix}/docs" if docs_enabled else None,
        redoc_url=f"{prefix}/redoc" if docs_enabled else None,
    )

    # Порядок важен: middleware, добавленный последним, выполняется первым (внешний слой).
    if rate_limit_per_minute is not None:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=rate_limit_per_minute,
            requests_per_hour=rate_limit_per_hour,
            trust_proxy_headers=trust_proxy_headers,
        )
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_production)
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(RequestContextMiddleware, service_name=service_name)

    register_exception_handlers(app)

    if register_health:
        checks = dict(health_checks or {})

        @app.get("/healthz", include_in_schema=False)
        async def healthz():
            return {"status": "ok", "service": service_name, "version": settings.VERSION}

        @app.get("/health", tags=["monitoring"])
        async def health():
            results = {name: await check() for name, check in checks.items()}
            healthy = all(results.values())
            return JSONResponse(
                status_code=200 if healthy else 503,
                content={
                    "status": "ok" if healthy else "error",
                    "service": service_name,
                    "version": settings.VERSION,
                    "checks": {name: "ok" if ok else "error" for name, ok in results.items()},
                },
            )

    logger.info("%s configured (env=%s, debug=%s)", service_name, settings.ENV, settings.DEBUG)
    return app
