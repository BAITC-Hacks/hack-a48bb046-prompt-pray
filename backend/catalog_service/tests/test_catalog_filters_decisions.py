from uuid import uuid4

import pytest

from conftest import auth_headers
from test_workflow import API, make_card, publish


async def test_filters_combine_before_pagination_and_personalized_sort(client):
    owner = auth_headers()
    expected = {}
    fields = dict(data='CSV', expected_result='Dashboard', success_criteria='Accuracy',
                  constraints='Deadline', users='Managers', business_contact='Owner')
    # 20, 40, 70 and 100 cover all four readiness levels.
    for readiness, extra in [('draft', {}), ('working', dict(data='CSV')),
                             ('ready', dict(data='CSV', expected_result='Dashboard', success_criteria='Accuracy')),
                             ('priority', fields)]:
        for topic in ['analytics', 'automation', None]:
            card = await make_card(client, owner, f'{readiness} {topic}')
            response = await client.patch(f"{API}/tasks/{card['id']}", headers=owner,
                json={'expected_version': card['version'], 'topic': topic, **extra})
            assert response.status_code == 200, response.text
            assert response.json()['rating']['readiness_code'] == readiness
            await publish(client, owner, card['id'])
            expected[readiness, topic] = card['id']

    for readiness in ['draft', 'working', 'ready', 'priority']:
        response = (await client.get(API, params={'readiness': readiness, 'limit': 1, 'offset': 1})).json()
        assert response['total'] == 3
        assert len(response['items']) == 1
        assert response['items'][0]['task']['rating']['readiness_code'] == readiness
        for topic in ['analytics', 'automation', 'unspecified']:
            response = (await client.get(API, params={
                'topic': topic, 'readiness': readiness, 'skills': 'Dashboard', 'interests': 'CSV', 'limit': 1,
            })).json()
            assert response['total'] == 1
            assert response['items'][0]['task_id'] == expected[readiness, None if topic == 'unspecified' else topic]
    assert (await client.get(API, params={'topic': 'marketing'})).json()['total'] == 0
    assert (await client.get(API)).json()['total'] == 12
    assert (await client.get(API, params={'readiness': 'invalid'})).status_code == 422
    assert (await client.get(API, params={'topic': 'invalid'})).status_code == 422


async def test_explicit_decisions_are_private_persistent_and_do_not_reject_new_proposals(client):
    owner, stranger = auth_headers(), auth_headers()
    students = [auth_headers('student') for _ in range(3)]
    card = await make_card(client, owner)
    await publish(client, owner, card['id'])
    path = f"{API}/tasks/{card['id']}"
    shared_team = str(uuid4())

    async def submit(student):
        response = await client.post(f'{path}/proposals', headers=student, json={
            'team_id': shared_team, 'idea': 'Idea', 'plan': 'Plan',
        })
        assert response.status_code == 201, response.text
        assert response.json()['status'] == 'pending'
        return response.json()['id']

    ids = [await submit(student) for student in students[:2]]

    async def statuses(headers):
        response = await client.get(f'{path}/proposals', headers=headers)
        assert response.status_code == 200, response.text
        return {item['id']: item['status'] for item in response.json()}

    assert await statuses(owner) == dict.fromkeys(ids, 'pending')
    assert await statuses(students[0]) == {ids[0]: 'pending'}
    assert await statuses(students[2]) == {}  # Matching team_id cannot expose another student's proposal.
    assert (await client.get(f'{path}/proposals', headers=stranger)).status_code == 403
    assert (await client.get(f'{path}/proposals')).status_code == 401
    assert (await client.get(f'{path}/decisions', headers=students[0])).status_code == 403

    for selected, rejected, states in [
        ([ids[0]], [], ['selected', 'pending']),
        ([ids[0]], [ids[1]], ['selected', 'rejected']),
        (ids, [], ['selected', 'selected']),
        ([], ids, ['rejected', 'rejected']),
        ([], [], ['pending', 'pending']),
    ]:
        response = await client.post(f'{path}/decisions', headers=owner, json={
            'selected_proposal_ids': selected, 'rejected_proposal_ids': rejected,
        })
        assert response.status_code == 201, response.text
        assert set(response.json()['rejected_proposal_ids']) == set(rejected)
        assert await statuses(owner) == dict(zip(ids, states))
        for student, key, status in zip(students, ids, states):
            assert await statuses(student) == {key: status}

    # Legacy clients still save a full selection snapshot; new proposals stay pending.
    assert (await client.post(f'{path}/decisions', headers=owner,
        json={'selected_proposal_ids': []})).status_code == 201
    third = await submit(students[2])
    assert await statuses(owner) == {ids[0]: 'rejected', ids[1]: 'rejected', third: 'pending'}
    assert await statuses(students[2]) == {third: 'pending'}

    for headers in [stranger, students[0]]:
        assert (await client.post(f'{path}/decisions', headers=headers, json={
            'selected_proposal_ids': [], 'rejected_proposal_ids': ids,
        })).status_code == 403
    for selected, rejected in [([ids[0]], [ids[0]]), ([], [ids[0], ids[0]])]:
        assert (await client.post(f'{path}/decisions', headers=owner, json={
            'selected_proposal_ids': selected, 'rejected_proposal_ids': rejected,
        })).status_code == 422
    assert (await client.post(f'{path}/decisions', headers=owner, json={
        'selected_proposal_ids': [], 'rejected_proposal_ids': [str(uuid4())],
    })).status_code == 400


@pytest.mark.parametrize('score,level', [(0, 'draft'), (39, 'draft'), (40, 'working'), (69, 'working'),
                                         (70, 'ready'), (89, 'ready'), (90, 'priority'), (100, 'priority')])
async def test_filter_readiness_boundaries(client, score, level):
    from app.db.session import db
    from app.models import RatingBreakdown
    from app.services.catalog import WEIGHTS
    from uuid import UUID

    owner = auth_headers()
    card = await make_card(client, owner)
    await publish(client, owner, card['id'])
    async with db.session_factory() as session:
        rating = await session.get(RatingBreakdown, UUID(card['id']))
        remaining = score
        for field, maximum in WEIGHTS.items():
            points = min(remaining, maximum)
            setattr(rating, field, points)
            remaining -= points
        await session.commit()
    for candidate in ['draft', 'working', 'ready', 'priority']:
        page = (await client.get(API, params={'readiness': candidate})).json()
        assert page['total'] == (1 if candidate == level else 0)
