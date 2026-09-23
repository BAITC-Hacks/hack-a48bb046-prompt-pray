from datetime import date, datetime, timezone
from uuid import uuid4
import pytest

from conftest import auth_headers
from test_workflow import API, make_card, publish
from app.services.rewards import streaks


async def stats(client, owner, month=None):
    response = await client.get(f"{API}/gamification", headers=owner,
                                params={"month": month or datetime.now(timezone.utc).strftime("%Y-%m")})
    assert response.status_code == 200, response.text
    return response.json()


async def test_rewards_thresholds_repeat_publication_and_calendar(client):
    owner = auth_headers()
    card = await make_card(client, owner)
    key = card['id']
    await publish(client, owner, key)
    assert (await stats(client, owner))['coins'] == 5
    for fields, expected in [
        (dict(data='CSV', expected_result='Report', success_criteria='Accuracy'), (70, 10)),
        (dict(constraints='One month', users='Sales'), (110, 20)),
        (dict(data=None), (110, 20)),
        (dict(data='CSV'), (110, 20)),
    ]:
        current = (await client.get(f"{API}/tasks/{key}", headers=owner)).json()
        response = await client.patch(f"{API}/tasks/{key}", headers=owner,
                                      json={**fields, 'expected_version': current['version']})
        assert response.status_code == 200
        await publish(client, owner, key)
        await publish(client, owner, key)
        result = await stats(client, owner)
        assert (result['coins'], result['reputation']) == expected
    assert result['active_days'] == 0
    assert result['action_days'] == 1
    assert sum(day['coins'] for day in result['days']) == 110
    assert sum(len(day['events']) for day in result['days']) == 8
    assert (await stats(client, auth_headers()))['coins'] == 0
    historic = await stats(client, owner, '2024-02')
    assert len(historic['days']) == 29
    assert historic['active_days'] == 0
    assert historic['coins'] == 110


async def test_only_first_nonempty_authorized_decision_is_rewarded(client):
    owner, other, student = auth_headers(), auth_headers(), auth_headers('student')
    key = (await make_card(client, owner))['id']
    await publish(client, owner, key)
    proposal = await client.post(f'{API}/tasks/{key}/proposals', headers=student,
                                json=dict(team_id=str(uuid4()), idea='Dashboard', plan='Test it'))
    proposal_id = proposal.json()['id']
    for headers, ids, status in [(other, [proposal_id], 403), (owner, [str(uuid4())], 400),
                                (owner, [], 201)]:
        response = await client.post(f'{API}/tasks/{key}/decisions', headers=headers,
                                     json={'selected_proposal_ids': ids})
        assert response.status_code == status
    assert (await stats(client, owner))['coins'] == 5
    for ids in [[proposal_id], [], [proposal_id]]:
        response = await client.post(f'{API}/tasks/{key}/decisions', headers=owner,
                                     json={'selected_proposal_ids': ids})
        assert response.status_code == 201
    result = await stats(client, owner)
    assert (result['coins'], result['reputation']) == (25, 5)
    assert sum(len(day['events']) for day in result['days']) == 2


async def test_progress_auth_and_month_validation(client):
    url = f'{API}/gamification'
    assert (await client.get(url, params={'month': '2026-09'})).status_code == 401
    assert (await client.get(url, headers=auth_headers('student'), params={'month': '2026-09'})).status_code == 200
    for month in ['2026-13', '0000-01', '26-09', '2026-1']:
        assert (await client.get(url, headers=auth_headers(), params={'month': month})).status_code == 422
    assert len((await stats(client, auth_headers(), '9999-12'))['days']) == 31


@pytest.mark.parametrize('role', ['business', 'student'])
async def test_daily_visits_are_idempotent_and_isolated(client, monkeypatch, role):
    owner = auth_headers(role)
    for day in [date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 2), date(2026, 9, 3)]:
        monkeypatch.setattr('app.services.rewards.today_utc', lambda: day)
        response = await client.post(f'{API}/gamification/check-in', headers=owner)
        assert response.status_code == 200
    result = await stats(client, owner, '2026-09')
    assert result['active_days'] == result['current_streak'] == result['best_streak'] == 3
    assert result['coins'] == result['reputation'] == 0
    assert result['days'][1]['visited'] is True
    assert (await stats(client, auth_headers(), '2026-09'))['active_days'] == 0
    monkeypatch.setattr('app.services.rewards.today_utc', lambda: date(2026, 9, 5))
    assert (await stats(client, owner, '2026-09'))['current_streak'] == 0
    await client.post(f'{API}/gamification/check-in', headers=owner)
    result = await stats(client, owner, '2026-09')
    assert result['current_streak'] == 1
    assert result['best_streak'] == 3
    assert (await client.post(f'{API}/gamification/check-in')).status_code == 401


def test_streak_crosses_month_and_year_boundaries():
    days = [date(2025, 12, 30), date(2025, 12, 31), date(2026, 1, 1)]
    assert streaks(days, date(2026, 1, 2)) == (3, 3)
    assert streaks(days, date(2026, 1, 3)) == (0, 3)
    assert streaks([], date(2026, 1, 3)) == (0, 0)


async def test_leaderboard_uses_latest_manual_decision(client):
    owner, student = auth_headers(), auth_headers('student')
    key = (await make_card(client, owner))['id']
    await publish(client, owner, key)
    team_id = str(uuid4())
    proposal = (await client.post(f'{API}/tasks/{key}/proposals', headers=student,
                                 json=dict(team_id=team_id, idea='Idea', plan='Plan'))).json()
    url = f'{API}/gamification/leaderboard'
    for ids, wins in [([proposal['id']], 1), ([], 0), ([proposal['id']], 1)]:
        await client.post(f'{API}/tasks/{key}/decisions', headers=owner, json={'selected_proposal_ids': ids})
        response = await client.get(url, headers=owner)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['teams'] == [dict(id=team_id, proposals=1, selected_tasks=wins)]
        assert result['businesses'][0]['is_you'] is True
        assert result['businesses'][0]['reputation'] == 5
        assert result['businesses'][0]['coins'] == 25
    assert (await client.get(url, headers=student)).status_code == 200
    assert (await client.get(url)).status_code == 401
