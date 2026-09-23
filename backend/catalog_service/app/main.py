from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.app import create_app

from . import models  # noqa: F401  (регистрирует модели в Base.metadata)
from .api.router import api_router
from .core.config import settings
from .db.migrations import migrate_draft_locale
from .db.card_version_migration import migrate_card_version
from .db.session import db


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.wait_until_ready()
    await db.create_tables()
    await migrate_draft_locale(db.engine)
    await migrate_card_version(db.engine)
    yield
    await db.dispose()


app = create_app(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    service_name="catalog_service",
    settings=settings,
    lifespan=lifespan,
    health_checks={"database": db.ping},
)
app.include_router(api_router, prefix=settings.API_V1_STR)
