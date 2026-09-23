import json

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings, settings
from conftest import bearer

URL = "/api/v1/ai/generate"


async def test_generation(client, provider):
    response = await client.post(URL, headers=bearer(), json={
        "prompt": "Напиши пост", "instructions": "На русском", "max_output_tokens": 1000,
    })
    assert response.status_code == 200
    assert response.json()["content"] == "Готовый текст"
    assert response.json()["usage"]["total_tokens"] == 15
    sent = provider.requests[0]
    assert str(sent.url) == "https://api.openai.com/v1/responses"
    assert sent.headers["authorization"] == "Bearer test-openai-key"
    assert json.loads(sent.content) == {
        "model": "test-model", "input": "Напиши пост", "instructions": "На русском",
        "max_output_tokens": 1000, "store": False,
    }


async def test_authentication(client, provider):
    for headers in ({}, {"Authorization": "Bearer invalid"}, bearer("refresh")):
        assert (await client.post(URL, headers=headers, json={"prompt": "Hello"})).status_code == 401
    assert not provider.requests


async def test_nano_limits_reasoning_to_leave_room_for_questions(client, provider, monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_MODEL", "gpt-5-nano")
    response = await client.post(URL, headers=bearer(), json={"prompt": "Ask clarifying questions"})
    assert response.status_code == 200
    sent = json.loads(provider.requests[0].content)
    assert sent["model"] == "gpt-5-nano"
    assert sent["reasoning"] == {"effort": "minimal"}


@pytest.mark.parametrize("payload", [
    {}, {"prompt": "   "}, {"prompt": "x" * 32001},
    {"prompt": "Hello", "max_output_tokens": 0},
    {"prompt": "Hello", "max_output_tokens": 2049},
    {"prompt": "Hello", "model": "arbitrary-model"},
])
async def test_validation(client, provider, payload):
    assert (await client.post(URL, headers=bearer(), json=payload)).status_code == 422
    assert not provider.requests


async def test_missing_key(client, provider, monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", SecretStr(""))
    response = await client.post(URL, headers=bearer(), json={"prompt": "Hello"})
    assert response.status_code == 503
    assert response.json()["code"] == "ai_not_configured"
    assert not provider.requests
    assert (await client.get("/health")).status_code == 200


@pytest.mark.parametrize("status,expected", [(401, 503), (403, 503), (429, 429), (500, 502), (400, 502)])
async def test_provider_errors_are_sanitized(client, provider, status, expected):
    provider.status = status
    provider.data = {"error": "secret prompt test-openai-key"}
    response = await client.post(URL, headers=bearer(), json={"prompt": "Hello"})
    assert response.status_code == expected
    assert "test-openai-key" not in response.text
    assert "secret prompt" not in response.text


@pytest.mark.parametrize("error,expected", [(httpx.ReadTimeout("secret"), 504), (httpx.ConnectError("secret"), 503)])
async def test_network_errors(client, provider, error, expected):
    provider.error = error
    response = await client.post(URL, headers=bearer(), json={"prompt": "Hello"})
    assert response.status_code == expected
    assert "secret" not in response.text


@pytest.mark.parametrize("data,code", [
    ({"status": "incomplete"}, "ai_incomplete"),
    ({"status": "completed", "output": []}, "ai_invalid_response"),
    ({"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal"}]}]}, "ai_refusal"),
    ({"status": "failed"}, "ai_invalid_response"),
    (None, "ai_invalid_response"),
])
async def test_unusable_output(client, provider, data, code):
    provider.data = data
    response = await client.post(URL, headers=bearer(), json={"prompt": "Hello"})
    assert response.status_code in (422, 502)
    assert response.json()["code"] == code


def test_settings_load_dotenv(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=key-from-env-file\n", encoding="utf-8")
    config = Settings(_env_file=env)
    assert config.OPENAI_API_KEY.get_secret_value() == "key-from-env-file"
    assert "key-from-env-file" not in repr(config)
