"""
Базовые настройки, общие для всех сервисов.

Значения читаются из переменных окружения, а при локальном запуске —
из корневого файла `.env` (см. `.env.example`).
"""
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent

_PLACEHOLDER_SECRET_PREFIXES = ("change_me", "dev-only")
_MIN_SECRET_LENGTH = 32
_MIN_DB_PASSWORD_LENGTH = 16


class BaseServiceSettings(BaseSettings):
    """Настройки, которые нужны каждому сервису."""

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: str = "development"  # development | staging | production
    DEBUG: bool = False
    VERSION: str = "0.1.0"
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/api/v1"

    # Общий секрет подписи JWT: токены выпускает auth_service,
    # проверяют gateway и остальные сервисы. Значения по умолчанию нет намеренно.
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    @model_validator(mode="after")
    def _validate_jwt_secret(self):
        if self.is_production:
            secret = self.JWT_SECRET_KEY
            if len(secret) < _MIN_SECRET_LENGTH or secret.lower().startswith(_PLACEHOLDER_SECRET_PREFIXES):
                raise ValueError(
                    f"JWT_SECRET_KEY в production должен быть случайной строкой "
                    f"не короче {_MIN_SECRET_LENGTH} символов "
                    f"(python scripts/generate_secrets.py)"
                )
        return self


class DatabaseSettings(BaseServiceSettings):
    """Настройки сервиса, у которого есть собственная БД PostgreSQL."""

    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Полный URL имеет приоритет (нужен, например, для тестов на SQLite)
    DATABASE_URL: Optional[str] = None

    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    @model_validator(mode="after")
    def _validate_database(self):
        if self.DATABASE_URL:
            if self.is_production and self.DATABASE_URL.lower().startswith("sqlite"):
                raise ValueError("SQLite не предназначен для production — используйте PostgreSQL (POSTGRES_*)")
            return self
        missing = [
            name
            for name in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")
            if not getattr(self, name)
        ]
        if missing:
            raise ValueError(f"Не заданы переменные окружения БД: {', '.join(missing)}")
        if self.is_production and (
            len(self.POSTGRES_PASSWORD) < _MIN_DB_PASSWORD_LENGTH
            or self.POSTGRES_PASSWORD.lower().startswith(_PLACEHOLDER_SECRET_PREFIXES)
        ):
            raise ValueError(
                f"POSTGRES_PASSWORD в production должен быть случайным и не короче "
                f"{_MIN_DB_PASSWORD_LENGTH} символов (python scripts/generate_secrets.py)"
            )
        return self

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        user = quote(self.POSTGRES_USER, safe="")
        password = quote(self.POSTGRES_PASSWORD, safe="")
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
