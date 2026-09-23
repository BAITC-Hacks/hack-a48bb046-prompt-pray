from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from common.app import create_app
from common.logger import get_logger

from .api.router import api_router
from .core.config import SERVICES, settings
from .core.health import check_services
from .core.proxy import create_http_client

logger = get_logger("api_gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = create_http_client(settings.UPSTREAM_TIMEOUT)
    logger.info("Routing to services: %s", {s.name: s.url for s in SERVICES})
    yield
    await app.state.http_client.aclose()


app = create_app(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    service_name="api_gateway",
    settings=settings,
    lifespan=lifespan,
    register_health=False,  # у gateway своя, агрегирующая проверка
    cors_origins=settings.BACKEND_CORS_ORIGINS,
    rate_limit_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    rate_limit_per_hour=settings.RATE_LIMIT_PER_HOUR,
    trust_proxy_headers=settings.TRUST_PROXY_HEADERS,
)


@app.get("/healthz", include_in_schema=False)
async def healthz():
    """Liveness: жив ли сам gateway (сервисы не опрашиваются)."""
    return {"status": "ok", "service": "api_gateway", "version": settings.VERSION}


@app.get("/health", tags=["monitoring"])
async def health(request: Request):
    """Readiness: gateway + доступность каждого сервиса. 503, если недоступен хотя бы один."""
    services = await check_services(request.app.state.http_client)
    healthy = all(services.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "version": settings.VERSION,
            "services": {name: "ok" if ok else "error" for name, ok in services.items()},
        },
    )


app.include_router(api_router, prefix=settings.API_V1_STR)
