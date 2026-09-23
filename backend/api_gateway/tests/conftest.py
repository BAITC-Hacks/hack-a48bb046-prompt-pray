import os
import uuid
from datetime import timedelta

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

# Настройки должны быть заданы ДО импорта приложения
SECRET = "test-secret-key-test-secret-key-1234"
os.environ.update(ENV="development", JWT_SECRET_KEY=SECRET)

from app.main import app  # noqa: E402
from common.auth import ACCESS_TOKEN, REFRESH_TOKEN, create_token  # noqa: E402


def bearer(token_type: str = ACCESS_TOKEN) -> dict[str, str]:
    token = create_token(
        subject=str(uuid.uuid4()),
        token_type=token_type,
        expires_delta=timedelta(minutes=5),
        secret=SECRET,
    )
    return {"Authorization": f"Bearer {token}"}


class Upstream:
    """Подменяет сервисы: запоминает пришедшие запросы и отвечает заданным handler."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.handler = lambda request: httpx.Response(200, json={"ok": True})

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.handler(request)


@pytest.fixture
def upstream() -> Upstream:
    return Upstream()


@pytest.fixture
async def client(upstream):
    app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://gateway") as c:
        yield c
    await app.state.http_client.aclose()


__all__ = ["bearer", "REFRESH_TOKEN"]
