import os
import tempfile
import uuid
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient

SECRET = "test-secret-key-test-secret-key-1234"
_db_file = os.path.join(tempfile.mkdtemp(), "catalog_test.db")
os.environ.update(
    ENV="development",
    JWT_SECRET_KEY=SECRET,
    DATABASE_URL=f"sqlite+aiosqlite:///{_db_file}",
)

from app.db.session import db  # noqa: E402
from app.main import app  # noqa: E402
from common.auth import ACCESS_TOKEN, create_token  # noqa: E402


def auth_headers() -> dict[str, str]:
    token = create_token(
        subject=str(uuid.uuid4()),
        token_type=ACCESS_TOKEN,
        expires_delta=timedelta(minutes=5),
        secret=SECRET,
        claims={"role": "business"},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client():
    await db.create_tables()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
