import os
import uuid
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient

SECRET = "test-secret-key-test-secret-key-1234"
os.environ.update(
    ENV="development", JWT_SECRET_KEY=SECRET,
    DATABASE_URL="sqlite+aiosqlite:///:memory:",
)

from app.db.session import db  # noqa: E402
from app.main import app  # noqa: E402
from common.auth import ACCESS_TOKEN, create_token  # noqa: E402
from common.db import Base  # noqa: E402


def auth_headers(role="business", user_id=None):
    token = create_token(
        subject=str(user_id or uuid.uuid4()), token_type=ACCESS_TOKEN,
        expires_delta=timedelta(minutes=5), secret=SECRET,
        claims={"role": role},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client():
    await db.create_tables()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    async with db.engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await db.dispose()
