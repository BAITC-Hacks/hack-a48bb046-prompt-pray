"""Text generation through OpenAI Responses API; no prompts or keys in logs."""
import httpx
from pydantic import ValidationError

from common.exceptions import AppException

from ..core.config import Settings
from ..schemas import GenerateRequest, GenerateResponse


async def generate_content(
    payload: GenerateRequest, client: httpx.AsyncClient, settings: Settings,
) -> GenerateResponse:
    key = settings.OPENAI_API_KEY.get_secret_value().strip()
    if not key:
        raise AppException("AI generation is not configured", status_code=503, code="ai_not_configured")
    if payload.max_output_tokens and payload.max_output_tokens > settings.OPENAI_MAX_OUTPUT_TOKENS:
        raise AppException("Requested token limit exceeds the service limit", status_code=422, code="ai_token_limit")

    body = {
        "model": settings.OPENAI_MODEL,
        "input": payload.prompt,
        "max_output_tokens": payload.max_output_tokens or settings.OPENAI_MAX_OUTPUT_TOKENS,
        "store": False,
    }
    if payload.instructions is not None:
        body["instructions"] = payload.instructions
    if settings.OPENAI_MODEL == "gpt-5-nano":
        body["reasoning"] = {"effort": "minimal"}
    try:
        response = await client.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {key}"},
            json=body,
        )
    except httpx.TimeoutException:
        raise AppException("AI generation timed out", status_code=504, code="ai_timeout") from None
    except httpx.HTTPError:
        raise AppException("AI provider is unavailable", status_code=503, code="ai_unavailable") from None

    # Never expose provider error bodies (they may contain request data).
    if response.status_code == 429:
        raise AppException("AI provider rate limit exceeded", status_code=429, code="ai_rate_limit")
    if response.status_code in (401, 403):
        raise AppException("AI provider credentials are unavailable or invalid", status_code=503, code="ai_configuration_error")
    if not response.is_success:
        raise AppException("AI provider rejected the request", status_code=502, code="ai_provider_error")

    try:
        data = response.json()
        if data.get("status") == "incomplete":
            raise AppException("AI generation was incomplete; adjust the prompt or token limit", status_code=502, code="ai_incomplete")
        if data.get("status") != "completed":
            raise ValueError("Unexpected response status")
        parts = [
            part
            for item in data.get("output", []) if item.get("type") == "message"
            for part in item.get("content", [])
        ]
        if any(part.get("type") == "refusal" for part in parts):
            raise AppException("AI provider declined to generate this content", status_code=422, code="ai_refusal")
        content = "".join(part["text"] for part in parts if part.get("type") == "output_text")
        if not content.strip():
            raise ValueError("Empty output")
        return GenerateResponse(id=data["id"], model=data["model"], content=content, usage=data.get("usage"))
    except (ValueError, KeyError, TypeError, AttributeError, ValidationError):
        raise AppException("Invalid response from AI provider", status_code=502, code="ai_invalid_response") from None
