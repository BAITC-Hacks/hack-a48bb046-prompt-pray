from unittest.mock import AsyncMock
from uuid import uuid4

from app.schemas.domain import ClarifyingQuestionCreate
from conftest import auth_headers

API = "/api/v1/catalog"


async def test_assembly_preserves_long_draft_and_all_answers(client, monkeypatch):
    owner = auth_headers()
    description = "A" * 32000
    draft = (await client.post(f"{API}/drafts", json={"description": description}, headers=owner)).json()
    generated = [ClarifyingQuestionCreate(field=field, question="Please clarify", position=index)
                 for index, field in enumerate(['context', 'data', 'data'])]
    monkeypatch.setattr('app.services.catalog.generate_questions', AsyncMock(return_value=generated))
    questions = (await client.post(f"{API}/drafts/{draft['id']}/questions", headers=owner)).json()
    for index, question in enumerate(questions):
        await client.patch(f"{API}/questions/{question['id']}", json={"answer": f"Answer {index}"}, headers=owner)
    response = await client.post(f"{API}/drafts/{draft['id']}/card", json={"title": "Complete facts"}, headers=owner)
    assert response.status_code == 201, response.text
    card = response.json()
    assert card['context'] == description + '\nAnswer 0'
    assert card['data'] == 'Answer 1\nAnswer 2'
    assert card['rating']['total'] == 40


async def test_zero_rating_task_is_public_and_accepts_proposals(client):
    owner = auth_headers()
    draft = (await client.post(f"{API}/drafts", json={"description": "Need help"}, headers=owner)).json()
    card = (await client.post(f"{API}/drafts/{draft['id']}/card",
        json={"title": "Early task", "context": None}, headers=owner)).json()
    assert card['rating']['total'] == 0
    assert card['rating']['readiness'] == 'черновик'
    key = card['id']
    assert (await client.post(f"{API}/tasks/{key}/confirm", json={"confirmed": True}, headers=owner)).status_code == 200
    assert (await client.post(f"{API}/tasks/{key}/publish", headers=owner)).status_code == 200
    assert (await client.get(API)).json()['items'][0]['task']['rating']['total'] == 0
    proposal = await client.post(f"{API}/tasks/{key}/proposals", headers=auth_headers('student'),
        json={"team_id": str(uuid4()), "idea": "Discuss requirements", "plan": "Interview owner"})
    assert proposal.status_code == 201, proposal.text
