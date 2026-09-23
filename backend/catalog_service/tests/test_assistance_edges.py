"""Failure, authorization and stale-generation regression coverage."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from common.exceptions import BadRequestError
from app.schemas.domain import ClarifyingQuestionCreate
from app.services.assistance import Advice, NextQuestion, ask
from app.services.questions import AIInvalidResponse, AIUnavailable
from conftest import auth_headers
from test_workflow import API, make_card, publish

SETTINGS = SimpleNamespace(AI_TIMEOUT=5, AI_SERVICE_URL='http://ai/', API_V1_STR='/api/v1')


@pytest.fixture
def provider(monkeypatch):
    mock = AsyncMock()
    mock.__aenter__.return_value = mock
    monkeypatch.setattr('app.services.assistance.httpx.AsyncClient', lambda **kwargs: mock)
    return mock


@pytest.mark.parametrize('body', [None, [], 'text', 1, {'content': None}, {'content': []},
    {'content': '{}'}, {'content': '{"summary":"   ","suggestions":[]}'},
    {'content': json.dumps({'summary': 'ok', 'suggestions': ['x'] * 8})},
    {'content': json.dumps({'summary': 'x' * 3001, 'suggestions': []})}])
async def test_malformed_provider_response(provider, body):
    provider.post.return_value = httpx.Response(200, content=json.dumps(body), headers={'content-type': 'application/json'})
    with pytest.raises(AIInvalidResponse):
        await ask({}, 'Explain', Advice, 'Bearer test', SETTINGS)


@pytest.mark.parametrize('status', [301, 401, 403, 429, 500, 503])
async def test_provider_status_does_not_leak_body(provider, status):
    provider.post.return_value = httpx.Response(status, text='private source text and credentials')
    with pytest.raises(AIUnavailable) as error:
        await ask({}, 'Explain', Advice, 'Bearer test', SETTINGS)
    assert 'private' not in error.value.detail


@pytest.mark.parametrize('code,status', [
    ('ai_not_configured', 503), ('ai_configuration_error', 503),
    ('ai_rate_limit', 429), ('ai_timeout', 504), ('ai_incomplete', 502),
    ('ai_refusal', 422), ('ai_provider_error', 502), ('ai_token_limit', 422),
    ('ai_invalid_response', 502),
])
async def test_known_ai_errors_preserve_safe_diagnostics(provider, code, status):
    from app.services.questions import generate_questions

    provider.post.return_value = httpx.Response(status, json={
        'code': code, 'detail': 'private source text and credentials',
    })
    for call in (
        lambda: ask({}, 'Explain', Advice, 'Bearer test', SETTINGS),
        lambda: generate_questions('Draft', 'Bearer test', SETTINGS),
    ):
        with pytest.raises(AIUnavailable) as error:
            await call()
        assert error.value.code == code
        assert error.value.status_code == status
        assert 'private' not in error.value.detail


@pytest.mark.parametrize('body', [[], None, {'code': []}, {'code': 'private'}])
async def test_unknown_ai_errors_are_sanitized(provider, body):
    provider.post.return_value = httpx.Response(503, content=json.dumps(body))
    with pytest.raises(AIUnavailable) as error:
        await ask({}, 'Explain', Advice, 'Bearer test', SETTINGS)
    assert error.value.code == 'ai_unavailable'


@pytest.mark.parametrize('failure', [httpx.ReadTimeout('secret'), httpx.ConnectError('secret')])
async def test_transport_failure(provider, failure):
    provider.post.side_effect = failure
    with pytest.raises(AIUnavailable):
        await ask({}, 'Explain', Advice, 'Bearer test', SETTINGS)


async def test_prompt_boundary_and_no_silent_truncation(provider):
    provider.post.return_value = httpx.Response(200, json={'content': '{"summary":"ok","suggestions":[]}'})
    overhead = len(json.dumps({'text': ''}))
    data = {'text': 'я' * (32000 - overhead)}
    await ask(data, 'Explain', Advice, 'Bearer test', SETTINGS)
    request = provider.post.call_args.kwargs['json']
    assert len(request['prompt']) == 32000
    assert json.loads(request['prompt']) == data
    provider.post.reset_mock()
    with pytest.raises(BadRequestError):
        await ask({'text': data['text'] + 'я'}, 'Explain', Advice, 'Bearer test', SETTINGS)
    provider.post.assert_not_called()


async def draft_questions(client, monkeypatch, owner):
    draft = (await client.post(f'{API}/drafts', headers=owner, json={'description': 'Reports'})).json()
    path = f"{API}/drafts/{draft['id']}"
    monkeypatch.setattr('app.services.catalog.generate_questions', AsyncMock(return_value=[
        ClarifyingQuestionCreate(field=field, question='Describe ' + field, position=i)
        for i, field in enumerate(['data', 'users', 'constraints'])]))
    questions = (await client.post(path + '/questions', headers=owner)).json()
    return path, questions


@pytest.mark.parametrize('endpoint', ['title', 'similar', 'next-question'])
async def test_draft_ai_permissions_before_provider_call(client, monkeypatch, endpoint):
    owner = auth_headers()
    path, _ = await draft_questions(client, monkeypatch, owner)
    ai = AsyncMock()
    monkeypatch.setattr('app.api.assistance.ask', ai)
    for headers, expected in [({}, 401), (auth_headers(), 403), (auth_headers('student'), 403)]:
        assert (await client.post(path + '/' + endpoint, headers=headers)).status_code == expected
    ai.assert_not_called()


async def test_empty_catalog_avoids_paid_call(client, monkeypatch):
    owner = auth_headers()
    path, _ = await draft_questions(client, monkeypatch, owner)
    ai = AsyncMock()
    monkeypatch.setattr('app.api.assistance.ask', ai)
    assert (await client.post(path + '/similar', headers=owner)).json() == {'matches': []}
    ai.assert_not_called()


@pytest.mark.parametrize('state', ['answered', 'assembled'])
async def test_finished_dialogue_avoids_paid_call(client, monkeypatch, state):
    owner = auth_headers()
    path, questions = await draft_questions(client, monkeypatch, owner)
    if state == 'answered':
        for question in questions:
            await client.patch(f"{API}/questions/{question['id']}", headers=owner, json={'answer': 'Known'})
    else:
        await client.post(path + '/card', headers=owner, json={'title': 'Reports'})
    ai = AsyncMock()
    monkeypatch.setattr('app.api.assistance.ask', ai)
    assert (await client.post(path + '/next-question', headers=owner)).status_code == (400 if state == 'answered' else 409)
    ai.assert_not_called()


@pytest.mark.parametrize('change', ['description', 'card'])
async def test_changes_during_generation_reject_stale_question(client, monkeypatch, change):
    owner = auth_headers()
    path, original = await draft_questions(client, monkeypatch, owner)

    async def generate(*args):
        if change == 'description':
            response = await client.patch(path, headers=owner, json={'description': 'Changed business need'})
        else:
            response = await client.post(path + '/card', headers=owner, json={'title': 'Reports'})
        assert response.status_code in (200, 201)
        return NextQuestion(field='data', question='Obsolete question')

    monkeypatch.setattr('app.api.assistance.ask', generate)
    response = await client.post(path + '/next-question', headers=owner)
    assert response.status_code == 409, response.text
    assert (await client.get(path + '/questions', headers=owner)).json() == original


async def test_refinement_cannot_replace_another_field_and_lose_coverage(client, monkeypatch):
    owner = auth_headers()
    path, original = await draft_questions(client, monkeypatch, owner)
    monkeypatch.setattr('app.api.assistance.ask', AsyncMock(return_value=NextQuestion(field='users', question='Who uses it?')))
    response = await client.post(path + '/next-question', headers=owner)
    assert response.status_code == 400
    assert (await client.get(path + '/questions', headers=owner)).json() == original


@pytest.mark.parametrize('query', [{'skills': 'x' * 501}, {'interests': 'x' * 501}, {'limit': 201}, {'offset': -1}])
async def test_catalog_rejects_invalid_recommendation_queries(client, query):
    assert (await client.get(API, params=query)).status_code == 422


async def test_recommendations_keep_low_rating_and_exclude_private_tasks(client):
    owner = auth_headers()
    low = await make_card(client, owner, 'Python')
    high = await make_card(client, owner, 'Design')
    await make_card(client, owner, 'Python private')
    await client.patch(f"{API}/tasks/{high['id']}", headers=owner, json={
        'expected_version': high['version'], 'data': 'Data', 'users': 'Designers'})
    await publish(client, owner, low['id'])
    await publish(client, owner, high['id'])
    ranked = (await client.get(API)).json()
    assert ranked['items'][0]['task_id'] == high['id']
    tailored = (await client.get(API, params={'skills': 'Python Python'})).json()
    assert tailored['total'] == 2
    assert [e['task_id'] for e in tailored['items']] == [low['id'], high['id']]
    fallback = (await client.get(API, params={'skills': 'unknown'})).json()
    assert fallback == ranked
