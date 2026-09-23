from unittest.mock import AsyncMock
from uuid import uuid4

from app.schemas import ClarifyingQuestionCreate
from conftest import auth_headers

API = "/api/v1/catalog"


async def make_card(client, headers, title="Task"):
    draft = await client.post(f"{API}/drafts", json={"description": "Business context"}, headers=headers)
    assert draft.status_code == 201, draft.text
    card = await client.post(f"{API}/drafts/{draft.json()['id']}/card", json={"title": title}, headers=headers)
    assert card.status_code == 201, card.text
    return card.json()


async def publish(client, headers, key):
    card = (await client.get(f"{API}/tasks/{key}", headers=headers)).json()
    confirmed = await client.post(f"{API}/tasks/{key}/confirm", json={"confirmed": True, "expected_version": card["version"]}, headers=headers)
    assert confirmed.status_code == 200, confirmed.text
    response = await client.post(f"{API}/tasks/{key}/publish", json={"expected_version": confirmed.json()["version"]}, headers=headers)
    assert response.status_code in (200, 201), response.text


async def test_full_workflow_rating_publication_and_manual_selection(client, monkeypatch):
    owner, other, student = auth_headers(), auth_headers(), auth_headers("student")
    questions = [ClarifyingQuestionCreate(field=field, question=f"Describe {field}", position=i)
                 for i, field in enumerate(["data", "expected_result", "success_criteria"])]
    generator = AsyncMock(return_value=questions)
    monkeypatch.setattr("app.services.catalog.generate_questions", generator)
    draft = await client.post(f"{API}/drafts", json={"description": "Need a sales report"}, headers=owner)
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]
    assert draft.json()["card_id"] is None
    assert (await client.get(f"{API}/drafts/{draft_id}", headers=other)).status_code == 403
    generated = await client.post(f"{API}/drafts/{draft_id}/questions", headers=owner)
    assert generated.status_code in (200, 201), generated.text
    assert len(generated.json()) == 3
    for question in generated.json():
        response = await client.patch(f"{API}/questions/{question['id']}", json={"answer": f"Answer {question['field']}"}, headers=owner)
        assert response.status_code == 200, response.text
    await client.post(f"{API}/drafts/{draft_id}/questions", headers=owner)
    generator.assert_awaited_once()
    response = await client.post(f"{API}/drafts/{draft_id}/card", json={"title": "Sales report"}, headers=owner)
    assert response.status_code == 201, response.text
    card = response.json()
    key = card["id"]
    restored = await client.get(f"{API}/drafts/{draft_id}", headers=owner)
    assert restored.json()["card_id"] == key
    own_drafts = await client.get(f"{API}/drafts", headers=owner)
    assert own_drafts.json()[0]["card_id"] == key
    assert (await client.get(f"{API}/drafts", headers=other)).json() == []
    assert (await client.get(f"{API}/tasks/{key}")).status_code == 401
    assert (await client.get(f"{API}/tasks/{key}", headers=other)).status_code == 403
    duplicate = await client.post(f"{API}/drafts/{draft_id}/card", json={"title": "Duplicate"}, headers=owner)
    assert duplicate.status_code == 409
    assert card["rating"]["total"] == 70
    assert card["rating"]["readiness_code"] == "ready"
    assert card["rating"]["readiness"] == "готовая"
    assert card["data"] == "Answer data"
    assert card["users"] is None  # No invented facts.
    assert (await client.post(f"{API}/tasks/{key}/publish", json={"expected_version": card["version"]}, headers=owner)).status_code == 400
    updated = await client.patch(f"{API}/tasks/{key}", json={"expected_version": card["version"], "users": "Sales team", "constraints": "Two weeks", "business_contact": "Owner"}, headers=owner)
    assert updated.status_code == 200, updated.text
    assert updated.json()["rating"]["total"] == 100
    assert updated.json()["rating"]["readiness_code"] == "priority"
    await publish(client, owner, key)
    current = (await client.get(f"{API}/tasks/{key}", headers=owner)).json()
    repeated = await client.post(f"{API}/tasks/{key}/publish", json={"expected_version": current["version"]}, headers=owner)
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["task_id"] == key
    low_card = await make_card(client, owner, "Low completeness")
    assert low_card["rating"]["total"] == 20
    assert low_card["rating"]["readiness_code"] == "draft"
    await publish(client, owner, low_card["id"])
    catalog = await client.get(API, headers=student, params={"limit": 1, "offset": 0})
    assert catalog.status_code == 200, catalog.text
    assert catalog.json()["total"] == 2
    assert catalog.json()["items"][0]["task_id"] == key
    page = await client.get(API, headers=student, params={"limit": 1, "offset": 1})
    assert page.json()["items"][0]["task_id"] == low_card["id"]
    assert page.json()["items"][0]["task"]["rating"]["readiness_code"] == "draft"
    proposal_payload = {"team_id": str(uuid4()), "idea": "Dashboard", "plan": "Prepare and test", "prototype_url": "https://example.com/demo"}
    proposal_ids = []
    for _ in range(2):
        proposal = await client.post(f"{API}/tasks/{key}/proposals", json={**proposal_payload, "team_id": str(uuid4())}, headers=auth_headers("student"))
        assert proposal.status_code == 201, proposal.text
        proposal_ids.append(proposal.json()["id"])
    low_proposal = await client.post(f"{API}/tasks/{low_card['id']}/proposals", json=proposal_payload, headers=student)
    assert low_proposal.status_code == 201  # Low rating never blocks proposals.
    decisions = await client.get(f"{API}/tasks/{key}/decisions", headers=owner)
    assert decisions.json() == []  # No automatic selection after proposals.
    for headers in [other, student]:
        assert (await client.post(f"{API}/tasks/{key}/decisions", json={"selected_proposal_ids": proposal_ids}, headers=headers)).status_code == 403
    invalid = await client.post(f"{API}/tasks/{key}/decisions", json={"selected_proposal_ids": [low_proposal.json()["id"]]}, headers=owner)
    assert invalid.status_code == 400
    for selected in [proposal_ids, []]:
        decision = await client.post(f"{API}/tasks/{key}/decisions", json={"selected_proposal_ids": selected}, headers=owner)
        assert decision.status_code == 201, decision.text
        assert set(decision.json()["selected_proposal_ids"]) == set(selected)
    changed = await client.patch(f"{API}/tasks/{key}", json={"data": None, "expected_version": repeated.json()["task"]["version"]}, headers=owner)
    assert changed.status_code == 200, changed.text
    assert changed.json()["rating"]["total"] == 80
    assert changed.json()["confirmed_at"] is None
    assert (await client.post(f"{API}/tasks/{key}/publish", json={"expected_version": changed.json()["version"]}, headers=owner)).status_code == 400
    assert (await client.get(API, headers=student)).json()["total"] == 1


async def test_roles_ownership_and_server_owned_fields(client):
    owner, stranger, student = auth_headers(), auth_headers(), auth_headers("student")
    assert (await client.post(f"{API}/drafts", json={"description": "Need help"})).status_code == 401
    assert (await client.post(f"{API}/drafts", json={"description": "Need help"}, headers=student)).status_code == 403
    forged = await client.post(f"{API}/drafts", json={"description": "Need help", "business_id": str(uuid4())}, headers=owner)
    assert forged.status_code == 422
    card = await make_card(client, owner)
    key = card["id"]
    assert (await client.patch(f"{API}/tasks/{key}", json={"title": "Stolen", "expected_version": card["version"]}, headers=stranger)).status_code == 403
    assert (await client.post(f"{API}/tasks/{key}/confirm", json={"confirmed": True, "expected_version": card["version"]}, headers=student)).status_code == 403
    assert (await client.patch(f"{API}/tasks/{key}", json={"rating": {"total": 100}}, headers=owner)).status_code == 422
    assert (await client.post(f"{API}/tasks/{key}/confirm", json={"confirmed": False}, headers=owner)).status_code == 422
    payload = {"team_id": str(uuid4()), "idea": "Idea", "plan": "Plan"}
    assert (await client.post(f"{API}/tasks/{key}/proposals", json=payload, headers=student)).status_code == 404
    await publish(client, owner, key)
    assert (await client.post(f"{API}/tasks/{key}/proposals", json=payload, headers=owner)).status_code == 403
    assert (await client.get(f"{API}/tasks/{key}")).status_code == 200
    assert (await client.get(API)).status_code == 200


async def test_ai_failure_preserves_draft_and_can_be_retried(client, monkeypatch):
    from app.services.questions import AIUnavailable

    owner, stranger = auth_headers(), auth_headers()
    draft = await client.post(f"{API}/drafts", json={"description": "Original requirement"}, headers=owner)
    key = draft.json()["id"]
    generator = AsyncMock(side_effect=AIUnavailable())
    monkeypatch.setattr("app.services.catalog.generate_questions", generator)
    failed = await client.post(f"{API}/drafts/{key}/questions", headers=owner)
    assert failed.status_code == 503
    assert failed.json()["code"] == "ai_unavailable"
    assert (await client.get(f"{API}/drafts/{key}", headers=owner)).json()["description"] == "Original requirement"
    assert (await client.get(f"{API}/drafts/{key}/questions", headers=owner)).json() == []
    generator.side_effect = None
    generator.return_value = [ClarifyingQuestionCreate(field=field, question=f"Describe {field}", position=i)
                              for i, field in enumerate(["data", "users", "constraints"])]
    response = await client.post(f"{API}/drafts/{key}/questions", headers=owner)
    assert response.status_code == 200
    question = response.json()[0]
    assert (await client.patch(f"{API}/questions/{question['id']}", json={"answer": "Forged"}, headers=stranger)).status_code == 403
    assert (await client.get(f"{API}/drafts/{key}/questions", headers=stranger)).status_code == 403
    assert (await client.get(f"{API}/drafts/{key}/questions", headers=owner)).json()[0]["answer"] is None
