import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from app.schemas import ClarifyingQuestionCreate
from app.services.assistance import Advice, GeneratedTitle, NextQuestion, SimilarTasks, ask
from app.services.questions import AIInvalidResponse, AIUnavailable
from conftest import auth_headers
from test_workflow import API, make_card, publish


async def test_advice_is_owner_only_and_does_not_mutate_card(client, monkeypatch):
    owner = auth_headers()
    card = await make_card(client, owner)
    ai = AsyncMock(return_value=Advice(summary='Add available data for 20 points.', suggestions=['Describe your sales table.']))
    monkeypatch.setattr('app.api.assistance.ask', ai)
    path = f"{API}/tasks/{card['id']}/rating-advice"
    for headers, code in [({}, 401), (auth_headers(), 403), (auth_headers('student'), 403)]:
        assert (await client.post(path, headers=headers)).status_code == code
    ai.assert_not_called()
    response = await client.post(path, headers=owner)
    assert response.status_code == 200, response.text
    assert ai.call_args.args[0]['rating']['data'] == 0
    assert (await client.get(f"{API}/tasks/{card['id']}", headers=owner)).json() == card


async def test_proposal_summary_never_selects_team(client, monkeypatch):
    owner = auth_headers()
    card = await make_card(client, owner)
    await publish(client, owner, card['id'])
    proposal = (await client.post(f"{API}/tasks/{card['id']}/proposals", headers=auth_headers('student'),
        json={'team_id': str(uuid4()), 'idea': 'Dashboard', 'plan': 'Interview then prototype', 'prototype_url': 'https://example.com'})).json()
    ai = AsyncMock(return_value=Advice(summary='A phased plan.', suggestions=['Clarify delivery dates.']))
    monkeypatch.setattr('app.api.assistance.ask', ai)
    path = f"{API}/tasks/{card['id']}/proposals/{proposal['id']}/analysis"
    assert (await client.post(path, headers=auth_headers())).status_code == 403
    assert (await client.post(path, headers=owner)).status_code == 200
    assert 'unverified' in ai.call_args.args[1]
    assert (await client.get(f"{API}/tasks/{card['id']}/decisions", headers=owner)).json() == []
    assert (await client.post(f"{API}/tasks/{card['id']}/proposals/{uuid4()}/analysis", headers=owner)).status_code == 404


async def test_keyword_sort_happens_before_pagination_and_keeps_all_tasks(client):
    owner = auth_headers()
    match = await make_card(client, owner, 'Python analytics')
    other = await make_card(client, owner, 'Design')
    await publish(client, owner, match['id'])
    await publish(client, owner, other['id'])
    result = (await client.get(API, params={'skills': 'PYTHON', 'limit': 1})).json()
    assert result['total'] == 2
    assert result['items'][0]['task_id'] == match['id']
    result = (await client.get(API, params={'skills': 'PYTHON', 'limit': 1, 'offset': 1})).json()
    assert result['items'][0]['task_id'] == other['id']


async def test_title_and_duplicates_are_suggestions_from_public_catalog_only(client, monkeypatch):
    owner = auth_headers()
    public = await make_card(client, owner)
    await publish(client, owner, public['id'])
    private = await make_card(client, owner, 'Private task')
    draft = (await client.post(f'{API}/drafts', headers=owner, json={'description': 'Need reporting'})).json()
    path = f"{API}/drafts/{draft['id']}"
    ai = AsyncMock(return_value=GeneratedTitle(title='Reporting'))
    monkeypatch.setattr('app.api.assistance.ask', ai)
    assert (await client.post(path + '/title', headers=owner)).json() == {'title': 'Reporting'}
    ai.return_value = SimilarTasks(matches=[{'task_id': public['id'], 'reason': 'Same need'},
                                            {'task_id': private['id'], 'reason': 'Invalid ID'}])
    response = await client.post(path + '/similar', headers=owner)
    assert response.json()['matches'] == [{'task_id': public['id'], 'reason': 'Same need'}]
    assert str(private['id']) not in json.dumps(ai.call_args.args[0])
    assert (await client.get(path, headers=owner)).json()['card_id'] is None


async def test_dialogue_uses_answers_preserves_three_questions_and_rejects_stale_result(client, monkeypatch):
    owner = auth_headers()
    draft = (await client.post(f'{API}/drafts', headers=owner, json={'description': 'Need reports'})).json()
    path = f"{API}/drafts/{draft['id']}"
    monkeypatch.setattr('app.services.catalog.generate_questions', AsyncMock(return_value=[
        ClarifyingQuestionCreate(field=field, question='Describe ' + field, position=i)
        for i, field in enumerate(['data', 'users', 'constraints'])]))
    questions = (await client.post(path + '/questions', headers=owner)).json()
    await client.patch(f"{API}/questions/{questions[0]['id']}", headers=owner, json={'answer': 'CSV sales'})
    ai = AsyncMock(return_value=NextQuestion(field='users', question='Who reads the CSV reports?'))
    monkeypatch.setattr('app.api.assistance.ask', ai)
    response = await client.post(path + '/next-question', headers=owner)
    assert response.status_code == 200, response.text
    assert response.json()['id'] == questions[1]['id']
    assert ai.call_args.args[0]['history'][0]['answer'] == 'CSV sales'
    assert len((await client.get(path + '/questions', headers=owner)).json()) == 3

    async def edit_during_generation(*args):
        await client.patch(f"{API}/questions/{questions[1]['id']}", headers=owner, json={'answer': 'Sales managers'})
        return NextQuestion(field='users', question='Stale question')
    ai.side_effect = edit_during_generation
    response = await client.post(path + '/next-question', headers=owner)
    assert response.status_code == 409, response.text
    current = (await client.get(path + '/questions', headers=owner)).json()
    assert current[1]['answer'] == 'Sales managers'
    assert current[1]['question'] != 'Stale question'


@pytest.mark.parametrize('body', [{'content': 'not JSON'}, {'content': '{"summary":"fake","suggestions":[],"selected_team":"x"}'}, {}])
async def test_ai_output_is_validated(monkeypatch, body):
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.post.return_value = httpx.Response(200, json=body)
    monkeypatch.setattr('app.services.assistance.httpx.AsyncClient', lambda **kwargs: client)
    with pytest.raises(AIInvalidResponse):
        await ask({'context': 'test'}, 'Explain', Advice, 'Bearer test',
                  SimpleNamespace(AI_TIMEOUT=5, AI_SERVICE_URL='http://ai', API_V1_STR='/api/v1'))


async def test_ai_errors_are_sanitized_and_identity_forwarded(monkeypatch):
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.post.return_value = httpx.Response(500, text='secret diagnostic')
    monkeypatch.setattr('app.services.assistance.httpx.AsyncClient', lambda **kwargs: client)
    with pytest.raises(AIUnavailable) as error:
        await ask({'context': 'test'}, 'Explain', Advice, 'Bearer test',
                  SimpleNamespace(AI_TIMEOUT=5, AI_SERVICE_URL='http://ai', API_V1_STR='/api/v1'))
    assert 'secret' not in error.value.detail
    assert client.post.call_args.kwargs['headers'] == {'Authorization': 'Bearer test'}
