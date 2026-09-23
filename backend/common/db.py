"""
Асинхронная работа с БД (SQLAlchemy 2.0 + asyncpg).

Каждый сервис владеет своей БД: создаёт один экземпляр `Database` в `app/db/session.py`.
Транзакции коммитит слой сервисов/репозиториев явно — зависимость `get_session`
только выдаёт и закрывает сессию.
"""
import asyncio
import uuid
from datetime import datetime
from typing import AsyncIterator

from sqlalchemy import DateTime, Uuid, func, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from common.logger import get_logger


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей."""


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Database:
    def __init__(self, settings, service_name: str):
        self.service_name = service_name
        self.logger = get_logger(f"{service_name}.db")

        url = settings.SQLALCHEMY_DATABASE_URI
        engine_kwargs: dict = {"echo": settings.DB_ECHO, "pool_pre_ping": True}
        if not url.startswith("sqlite"):  # SQLite не поддерживает параметры пула
            engine_kwargs.update(
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_recycle=settings.DB_POOL_RECYCLE,
            )
        self.engine = create_async_engine(url, **engine_kwargs)
        self.session_factory = async_sessionmaker(
            self.engine, expire_on_commit=False, autoflush=False
        )

    async def get_session(self) -> AsyncIterator[AsyncSession]:
        """FastAPI-зависимость: `session: AsyncSession = Depends(db.get_session)`."""
        async with self.session_factory() as session:
            yield session

    async def ping(self) -> bool:
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            self.logger.error("Database ping failed: %s", exc)
            return False

    async def wait_until_ready(self, retries: int = 15, delay: float = 2.0) -> None:
        """Ждёт, пока БД начнёт принимать соединения (актуально при старте в Docker)."""
        for attempt in range(1, retries + 1):
            if await self.ping():
                return
            self.logger.warning("Database is not ready (attempt %d/%d)", attempt, retries)
            await asyncio.sleep(delay)
        raise RuntimeError(f"Database for {self.service_name} is unavailable")

    async def create_tables(self) -> None:
        """Создаёт таблицы по моделям. Для эволюции схемы в проде подключите Alembic."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        await self.engine.dispose()
