from datetime import date
from uuid import uuid4

from conftest import auth_headers
from test_rewards import stats
from test_workflow import API, make_card, publish


async def send(client, student, task_id):
    response = await client.post(f"{API}/tasks/{task_id}/proposals", headers=student,
                                 json=dict(team_id=str(uuid4()), idea="Idea", plan="Plan"))
    assert response.status_code == 201, response.text
    return response.json()


async def test_student_rewards_are_personal_and_once_per_task_even_with_multiple_teams(client):
    owner, student, other = auth_headers(), auth_headers("student"), auth_headers("student")
    card = await make_card(client, owner)
    key = card["id"]
    # Rejected requests must never mint coins.
    response = await client.post(f"{API}/tasks/{key}/proposals", headers=student,
                                 json=dict(team_id=str(uuid4()), idea="Idea", plan="Plan"))
    assert response.status_code == 404
    assert (await stats(client, student))["coins"] == 0
    await publish(client, owner, key)
    proposals = [await send(client, student, key), await send(client, student, key)]
    assert (await stats(client, student))["wallet"]["balance"] == 10
    assert (await stats(client, other))["coins"] == 0
    for ids in [[p["id"] for p in proposals], [], [proposals[0]["id"]]]:
        response = await client.post(f"{API}/tasks/{key}/decisions", headers=owner,
                                     json={"selected_proposal_ids": ids})
        assert response.status_code == 201, response.text
    result = await stats(client, student)
    assert result["coins"] == 110
    assert result["wallet"]["owner_type"] == "student"
    events = [event for day in result["days"] for event in day["events"]]
    assert sorted(event["kind"] for event in events) == ["proposal_accepted", "proposal_sent"]
    assert all(event["task_id"] == key and event["created_at"] for event in events)
    assert result["reputation"] == 0
    # A distinct task may earn its own bonus.
    next_card = await make_card(client, owner)
    await publish(client, owner, next_card["id"])
    await send(client, student, next_card["id"])
    assert (await stats(client, student))["coins"] == 120


async def test_only_actions_extend_streak_and_passive_acceptance_does_not(client, monkeypatch):
    owner, student = auth_headers(), auth_headers("student")
    monkeypatch.setattr("app.services.rewards.today_utc", lambda: date(2026, 8, 31))
    card = await make_card(client, owner)
    await publish(client, owner, card["id"])
    first = await send(client, student, card["id"])
    monkeypatch.setattr("app.services.rewards.today_utc", lambda: date(2026, 9, 1))
    await send(client, student, card["id"])
    await send(client, student, card["id"])
    result = await stats(client, student, "2026-09")
    assert (result["action_current_streak"], result["action_best_streak"], result["action_days"]) == (2, 2, 1)
    assert result["current_streak"] == 0  # No visit recorded through check-in.
    assert result["coins"] == 10
    monkeypatch.setattr("app.services.rewards.today_utc", lambda: date(2026, 9, 3))
    await client.post(f"{API}/tasks/{card['id']}/decisions", headers=owner,
                      json={"selected_proposal_ids": [first["id"]]})
    result = await stats(client, student, "2026-09")
    assert result["coins"] == 110
    assert result["current_streak"] == 0
    assert result["last_action_date"] == "2026-09-01"
    await send(client, student, card["id"])
    result = await stats(client, student, "2026-09")
    assert (result["action_current_streak"], result["action_best_streak"]) == (1, 2)


async def test_failed_and_empty_edits_do_not_earn_rewards_or_extend_streak(client, monkeypatch):
    owner = auth_headers()
    monkeypatch.setattr("app.services.rewards.today_utc", lambda: date(2026, 9, 1))
    card = await make_card(client, owner)
    monkeypatch.setattr("app.services.rewards.today_utc", lambda: date(2026, 9, 3))
    for headers, version, status in [(auth_headers(), card["version"], 403),
                                      (owner, card["version"] + 10, 409)]:
        response = await client.patch(f"{API}/tasks/{card['id']}", headers=headers,
                                      json={"expected_version": version, "data": "CSV"})
        assert response.status_code == status, response.text
    response = await client.patch(f"{API}/tasks/{card['id']}", headers=owner,
                                  json={"expected_version": card["version"]})
    assert response.status_code == 200, response.text
    result = await stats(client, owner, "2026-09")
    assert result["coins"] == 5
    assert result["current_streak"] == 0
    assert result["last_action_date"] == "2026-09-01"
