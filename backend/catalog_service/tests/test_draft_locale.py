import json
from unittest.mock import AsyncMock

import httpx
import pytest

from conftest import auth_headers

API = "/api/v1/catalog"
LANGUAGES = [("ru", "Russian"), ("kk", "Kazakh"), ("en", "English")]
DESCRIPTIONS = {"ru": "Нужно сократить время обработки заявок", "kk": "Клиенттердің өтінімдерін өңдеу керек", "en": "We need to process customer requests faster"}
QUESTIONS = [
    {"field": field, "question": f"Clarify {field}", "position": index}
    for index, field in enumerate(["data", "users", "constraints"])
]


@pytest.mark.parametrize("text,expected", [
    ("Нужна CRM для обработки заявок", "ru"),
    ("Бізге өтінімдерді өңдеу керек", "kk"),
    ("Бизге сайт жасау керек", "kk"),
    ("We need a dashboard for customer requests", "en"),
    ("Нужен сайт https://example.com/very-long-english-path", "ru"),
])
def test_offline_language_follows_description(text, expected):
    from app.services.draft_language import detect_draft_locale
    assert detect_draft_locale(text) == expected


@pytest.fixture
def upstream(monkeypatch):
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.post.return_value = httpx.Response(
        200, json={"content": json.dumps({"questions": QUESTIONS})},
    )
    monkeypatch.setattr("app.services.questions.httpx.AsyncClient", lambda **kwargs: client)
    return client


@pytest.mark.parametrize("locale,language", LANGUAGES)
async def test_saved_locale_drives_questions_and_survives_reopening(client, upstream, locale, language):
    owner = auth_headers()
    description = DESCRIPTIONS[locale]
    response = await client.post(f"{API}/drafts", headers=owner,
                                 json={"description": description, "locale": "en" if locale != "en" else "ru"})
    assert response.status_code == 201, response.text
    draft = response.json()
    assert draft["locale"] == locale
    path = f"{API}/drafts/{draft['id']}"
    # A different UI language must not override the persisted draft locale.
    reopened = await client.get(path, headers={**owner, "Accept-Language": "en,ru,kk"})
    assert reopened.json()["locale"] == locale
    assert reopened.json()["description"] == description
    generated = await client.post(f"{path}/questions", headers=owner)
    assert generated.status_code == 200, generated.text
    assert len(generated.json()) >= 3
    request = upstream.post.call_args.kwargs["json"]
    assert request["prompt"] == description
    assert "same language for every question" in request["instructions"]
    assert "Never invent facts or answers" in request["instructions"]
    assert "at least 3" in request["instructions"]
    question = generated.json()[0]
    answer = "Ответ / Жауап / Answer"
    saved = await client.patch(f"{API}/questions/{question['id']}", headers=owner,
                               json={"answer": answer})
    assert saved.status_code == 200
    repeated = await client.post(f"{path}/questions", headers={**owner, "Accept-Language": "kk"})
    assert repeated.json()[0]["answer"] == answer
    assert repeated.json()[0]["question"] == question["question"]
    upstream.post.assert_awaited_once()
    drafts = await client.get(f"{API}/drafts", headers=owner)
    assert drafts.json()[0]["locale"] == locale


async def test_client_without_locale_infers_english(client, upstream):
    owner = auth_headers()
    response = await client.post(f"{API}/drafts", headers=owner, json={"description": "Old client"})
    assert response.status_code == 201
    assert response.json()["locale"] == "en"
    await client.post(f"{API}/drafts/{response.json()['id']}/questions", headers=owner)
    assert "same language for every question" in upstream.post.call_args.kwargs["json"]["instructions"]


@pytest.mark.parametrize("locale", ["de", "RU", "ru-RU", "", None, 1])
async def test_invalid_locale_returns_422_without_saving_draft(client, locale):
    owner = auth_headers()
    response = await client.post(f"{API}/drafts", headers=owner,
                                 json={"description": "Need help", "locale": locale})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "locale"]
    assert (await client.get(f"{API}/drafts", headers=owner)).json() == []


@pytest.mark.parametrize("locale,language", LANGUAGES)
@pytest.mark.parametrize("failure", ["too_few", "invalid_json", 429, 500, 502, 503, 504, "timeout", "connection"])
async def test_locale_generation_errors_use_saved_fallback(client, upstream, locale, language, failure):
    owner = auth_headers()
    response = await client.post(f"{API}/drafts", headers=owner,
                                 json={"description": DESCRIPTIONS[locale]})
    path = f"{API}/drafts/{response.json()['id']}"
    if failure == "too_few":
        upstream.post.return_value = httpx.Response(200, json={"content": json.dumps({"questions": QUESTIONS[:2]})})
    elif failure == "invalid_json":
        upstream.post.return_value = httpx.Response(200, json={"content": "secret provider diagnostics"})
    elif isinstance(failure, int):
        upstream.post.return_value = httpx.Response(failure, text="secret provider diagnostics")
    elif failure == "connection":
        upstream.post.side_effect = httpx.ConnectError("secret provider diagnostics")
    else:
        upstream.post.side_effect = httpx.ReadTimeout("secret provider diagnostics")
    failed = await client.post(f"{path}/questions", headers=owner)
    assert failed.status_code == 200
    from app.services.fallback_questions import QUESTIONS as FALLBACK
    assert [q["question"] for q in failed.json()] == list(FALLBACK[locale])
    assert all(q["answer"] is None for q in failed.json())
    assert "secret" not in failed.text
    restored = (await client.get(path, headers=owner)).json()
    assert restored["locale"] == locale
    assert restored["description"] == DESCRIPTIONS[locale]
    assert (await client.get(f"{path}/questions", headers=owner)).json() == failed.json()
    question = failed.json()[0]
    saved = await client.patch(f"{API}/questions/{question['id']}", headers=owner,
                               json={"answer": "Business supplied data"})
    assert saved.status_code == 200
    upstream.post.side_effect = None
    upstream.post.return_value = httpx.Response(200, json={"content": json.dumps({"questions": QUESTIONS})})
    retried = await client.post(f"{path}/questions", headers=owner)
    assert retried.status_code == 200
    assert len(retried.json()) >= 3
    assert [q["id"] for q in retried.json()] == [q["id"] for q in failed.json()]
    assert retried.json()[0]["answer"] == "Business supplied data"
    upstream.post.assert_awaited_once()
    assert "same language for every question" in upstream.post.call_args.kwargs["json"]["instructions"]
