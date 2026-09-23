import pytest

from conftest import auth_headers

API = '/api/v1/catalog'


async def test_edit_draft_preserves_answers_and_assembles_updated_context(client, monkeypatch):
    from app.services.questions import AIUnavailable

    async def unavailable(*args, **kwargs):
        raise AIUnavailable()

    monkeypatch.setattr('app.services.catalog.generate_questions', unavailable)
    owner = auth_headers()
    draft = (await client.post(f'{API}/drafts', headers=owner,
                               json={'description': 'Original description'})).json()
    path = f"{API}/drafts/{draft['id']}"
    questions = (await client.post(f'{path}/questions', headers=owner)).json()
    question = questions[0]
    await client.patch(f"{API}/questions/{question['id']}", headers=owner,
                       json={'answer': 'Saved answer'})
    for other in [auth_headers(), auth_headers('student')]:
        assert (await client.patch(path, headers=other,
                                   json={'description': 'Forbidden'})).status_code == 403
    response = await client.patch(path, headers=owner, json={'description': 'Новое описание'})
    assert response.status_code == 200, response.text
    assert response.json()['locale'] == 'ru'
    assert (await client.get(path, headers=owner)).json()['description'] == 'Новое описание'
    assert (await client.get(f'{path}/questions', headers=owner)).json()[0]['answer'] == 'Saved answer'
    card = await client.post(f'{path}/card', headers=owner, json={'title': 'Title'})
    assert card.status_code == 201, card.text
    assert card.json()['context'].startswith('Новое описание')
    assert (await client.patch(path, headers=owner,
                               json={'description': 'Too late'})).status_code == 409


@pytest.mark.parametrize('description', ['', '   ', 'a' * 32001])
async def test_invalid_edit_keeps_saved_description(client, description):
    owner = auth_headers()
    draft = (await client.post(f'{API}/drafts', headers=owner,
                               json={'description': 'Original'})).json()
    path = f"{API}/drafts/{draft['id']}"
    assert (await client.patch(path, headers=owner,
                               json={'description': description})).status_code == 422
    assert (await client.get(path, headers=owner)).json()['description'] == 'Original'
