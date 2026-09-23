import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

# Настройки должны быть заданы ДО импорта приложения
_db_file = os.path.join(tempfile.mkdtemp(), "auth_test.db")
os.environ.update(
    ENV="development",
    JWT_SECRET_KEY="test-secret-key-test-secret-key-1234",
    DATABASE_URL=f"sqlite+aiosqlite:///{_db_file}",
)

from app.db.session import db  # noqa: E402
from app.main import app  # noqa: E402
from common.db import Base  # noqa: E402


@pytest.fixture
async def client():
    """Клиент к приложению; таблицы создаются и удаляются для каждого теста."""
    await db.create_tables()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
