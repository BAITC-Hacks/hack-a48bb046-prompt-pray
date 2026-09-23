import os
import uuid
from datetime import timedelta

import httpx
import pytest

SECRET = "test-secret-key-test-secret-key-1234"
os.environ.update(
    ENV="development", JWT_SECRET_KEY=SECRET, OPENAI_API_KEY="test-openai-key",
    OPENAI_MODEL="test-model", OPENAI_MAX_OUTPUT_TOKENS="2048",
)

from app.main import app
from common.auth import create_token


def bearer(token_type="access"):
    token = create_token(subject=str(uuid.uuid4()), token_type=token_type,
                         expires_delta=timedelta(minutes=5), secret=SECRET)
    return {"Authorization": f"Bearer {token}"}


class Provider:
    def __init__(self):
        self.requests = []
        self.data = {
            "id": "resp_test", "model": "test-model", "status": "completed",
            "output": [{"type": "reasoning"}, {"type": "message", "content": [
                {"type": "output_text", "text": "Готовый текст"},
            ]}],
            "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        }
        self.status = 200
        self.error = None

    def __call__(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        return httpx.Response(self.status, json=self.data)


@pytest.fixture
def provider():
    return Provider()


@pytest.fixture
async def client(provider):
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as mocked:
            app.state.openai_client = mocked
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://ai") as client:
                yield client
