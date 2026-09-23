import json
from dataclasses import dataclass
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import NoDecode

from common.config import BaseServiceSettings


@dataclass(frozen=True)
class ServiceRoute:
    """Описание downstream-сервиса, доступного через gateway."""

    name: str
    url: str
    # Первые сегменты пути после /api/v1, которые обслуживает сервис
    prefixes: tuple[str, ...]
    health_path: str = "/health"
    timeout: float | None = None


class Settings(BaseServiceSettings):
    PROJECT_NAME: str = "API Gateway"
    DESCRIPTION: str = "Единая точка входа: проверка JWT и маршрутизация запросов к сервисам"

    # Адреса сервисов внутри docker-сети (для локального запуска — localhost)
    AUTH_SERVICE_URL: str = "http://localhost:8001"
    EXAMPLE_SERVICE_URL: str = "http://localhost:8002"
    AI_SERVICE_URL: str = "http://localhost:8003"
    CATALOG_SERVICE_URL: str = "http://localhost:8004"
    AI_UPSTREAM_TIMEOUT: float = Field(default=65.0, gt=0)
    CATALOG_UPSTREAM_TIMEOUT: float = Field(default=75.0, gt=0)
    UPSTREAM_TIMEOUT: float = 10.0

    # Список через запятую или JSON-массив. В production обязателен и без "*".
    BACKEND_CORS_ORIGINS: Annotated[list[str], NoDecode] = []

    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    # Включать, только если gateway стоит за доверенным прокси (nginx, Traefik, облачный LB)
    TRUST_PROXY_HEADERS: bool = False

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                return json.loads(value)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _validate_cors(self):
        if self.is_production:
            if not self.BACKEND_CORS_ORIGINS or "*" in self.BACKEND_CORS_ORIGINS:
                raise ValueError("BACKEND_CORS_ORIGINS в production должен содержать конкретные origin'ы, без '*'")
        elif not self.BACKEND_CORS_ORIGINS:
            # Типичные адреса dev-серверов фронтенда (Nuxt/Next — 3000, Vite — 5173)
            self.BACKEND_CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
        return self


settings = Settings()

# Таблица маршрутизации: чтобы подключить новый сервис, добавьте его URL в Settings и сюда.
SERVICES: tuple[ServiceRoute, ...] = (
    ServiceRoute("auth", settings.AUTH_SERVICE_URL, prefixes=("auth", "users")),
    ServiceRoute("example", settings.EXAMPLE_SERVICE_URL, prefixes=("items",)),
    ServiceRoute("ai", settings.AI_SERVICE_URL, prefixes=("ai",), timeout=settings.AI_UPSTREAM_TIMEOUT),
    ServiceRoute("catalog", settings.CATALOG_SERVICE_URL, prefixes=("catalog",), timeout=settings.CATALOG_UPSTREAM_TIMEOUT),
)

PREFIX_TO_SERVICE: dict[str, ServiceRoute] = {p: s for s in SERVICES for p in s.prefixes}

# Эндпоинты, доступные без access-токена: (метод, путь)
PUBLIC_ENDPOINTS: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", f"{settings.API_V1_STR}/auth/register"),
        ("POST", f"{settings.API_V1_STR}/auth/login"),
        ("POST", f"{settings.API_V1_STR}/auth/refresh"),
        ("GET", f"{settings.API_V1_STR}/catalog"),
    }
)
