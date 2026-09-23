"""Provider failures must stay within our API contract and never leak bodies."""
import httpx
import pytest

from app.core.config import Settings
from app.schemas import GenerateRequest
from app.services.generation import generate_content
from common.app import create_app


@pytest.mark.parametrize(
    "provider_status, expected_status, code",
    [
        (429, 429, "ai_rate_limit"),
        (401, 503, "ai_configuration_error"),
        (403, 503, "ai_configuration_error"),
        (400, 502, "ai_provider_error"),
        (500, 502, "ai_provider_error"),
        (302, 502, "ai_provider_error"),
    ],
)
async def test_provider_error_contract(provider_status, expected_status, code):
    response = httpx.Response(provider_status, text="private prompt and provider credentials")
    result = await request_generation(response)
    assert result.status_code == expected_status
    assert set(result.json()) == {"detail", "code"}
    assert result.json()["code"] == code
    assert "private" not in result.text


async def request_generation(response=None, error=None, configured=True, payload=None):
    settings = Settings(OPENAI_API_KEY="test-provider-secret" if configured else "")

    def upstream(request):
        if error:
            raise error
        return response

    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as provider:
        app = create_app(title="Test", service_name="ai_test", settings=settings)

        @app.post("/generate")
        async def generate():
            return await generate_content(payload or GenerateRequest(prompt="Business need"), provider, settings)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/generate")


@pytest.mark.parametrize(
    "error, status, code",
    [
        (httpx.ReadTimeout("private upstream data"), 504, "ai_timeout"),
        (httpx.ConnectError("private upstream data"), 503, "ai_unavailable"),
    ],
)
async def test_network_errors(error, status, code):
    result = await request_generation(error=error)
    assert result.status_code == status
    assert result.json()["code"] == code
    assert "private" not in result.text


@pytest.mark.parametrize(
    "body, code",
    [
        ([], "ai_invalid_response"),
        ({"status": "completed", "output": []}, "ai_invalid_response"),
        ({"status": "completed", "output": [None]}, "ai_invalid_response"),
        ({"status": "failed", "error": "private"}, "ai_invalid_response"),
        ({"status": "incomplete"}, "ai_incomplete"),
        ({"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "private"}]}]}, "ai_refusal"),
    ],
)
async def test_unusable_provider_output(body, code):
    result = await request_generation(httpx.Response(200, json=body))
    assert result.status_code == (422 if code == "ai_refusal" else 502)
    assert result.json()["code"] == code
    assert "private" not in result.text


async def test_non_json_provider_output():
    result = await request_generation(httpx.Response(200, text="private invalid json"))
    assert result.status_code == 502
    assert result.json()["code"] == "ai_invalid_response"


async def test_missing_configuration():
    result = await request_generation(configured=False)
    assert result.status_code == 503
    assert result.json()["code"] == "ai_not_configured"


async def test_token_limit():
    result = await request_generation(payload=GenerateRequest(prompt="Need", max_output_tokens=32768))
    assert result.status_code == 422
    assert result.json()["code"] == "ai_token_limit"
