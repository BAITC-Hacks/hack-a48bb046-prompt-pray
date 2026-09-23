from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.services.questions import AIInvalidResponse, AIUnavailable, generate_questions


@pytest.fixture
def ai(monkeypatch):
    client = AsyncMock()
    client.__aenter__.return_value = client
    monkeypatch.setattr("app.services.questions.httpx.AsyncClient", lambda **kwargs: client)
    return client


SETTINGS = SimpleNamespace(AI_TIMEOUT=5, AI_SERVICE_URL="http://ai", API_V1_STR="/api/v1")


async def test_questions_forward_identity_and_validate_shape(ai):
    import json
    questions = [{"field": field, "question": "What is missing?", "position": index}
                 for index, field in enumerate(["data", "users", "constraints"])]
    ai.post.return_value = httpx.Response(200, json={"content": json.dumps({"questions": questions})})
    result = await generate_questions("Raw draft", "Bearer token", SETTINGS)
    assert len(result) == 3
    kwargs = ai.post.call_args.kwargs
    assert kwargs['headers'] == {"Authorization": "Bearer token"}
    assert kwargs['json']['prompt'] == "Raw draft"


@pytest.mark.parametrize("body", [
    {"content": "not json"}, {"content": '{"questions":[]}'}, {},
    {"content": '{"questions":[{"field":"invented","question":"?","position":0}]}'},
])
async def test_bad_ai_response_is_controlled_error(ai, body):
    ai.post.return_value = httpx.Response(200, json=body)
    with pytest.raises(AIInvalidResponse):
        await generate_questions("Draft", "Bearer token", SETTINGS)


async def test_provider_failure_body_is_not_exposed(ai):
    ai.post.return_value = httpx.Response(500, text="secret provider diagnostics")
    with pytest.raises(AIUnavailable) as error:
        await generate_questions("Draft", "Bearer token", SETTINGS)
    assert "secret" not in error.value.detail


async def test_network_failure_is_controlled(ai):
    ai.post.side_effect = httpx.ConnectError("connection refused")
    with pytest.raises(AIUnavailable):
        await generate_questions("Draft", "Bearer token", SETTINGS)
