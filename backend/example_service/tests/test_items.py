import uuid

from conftest import auth_headers

API = "/api/v1/items"


async def test_crud_cycle(client):
    headers = auth_headers()

    created = await client.post(API, json={"title": "First", "description": "hello"}, headers=headers)
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    assert (await client.get(f"{API}/{item_id}", headers=headers)).json()["title"] == "First"
    assert len((await client.get(API, headers=headers)).json()) == 1

    patched = await client.patch(f"{API}/{item_id}", json={"title": "Renamed"}, headers=headers)
    assert patched.status_code == 200
    assert patched.json()["title"] == "Renamed"
    assert patched.json()["description"] == "hello"  # не переданные поля не затираются

    assert (await client.delete(f"{API}/{item_id}", headers=headers)).status_code == 204
    assert (await client.get(f"{API}/{item_id}", headers=headers)).status_code == 404


async def test_items_are_isolated_between_users(client):
    owner, stranger = auth_headers(), auth_headers()
    item_id = (await client.post(API, json={"title": "Private"}, headers=owner)).json()["id"]

    assert (await client.get(f"{API}/{item_id}", headers=stranger)).status_code == 404
    assert (await client.delete(f"{API}/{item_id}", headers=stranger)).status_code == 404
    assert (await client.get(API, headers=stranger)).json() == []


async def test_requires_valid_token(client):
    assert (await client.get(API)).status_code == 401
    assert (await client.get(API, headers={"Authorization": "Bearer garbage"})).status_code == 401
    assert (await client.get(f"{API}/{uuid.uuid4()}", headers=auth_headers())).status_code == 404


async def test_validation(client):
    resp = await client.post(API, json={"title": ""}, headers=auth_headers())
    assert resp.status_code == 422


async def test_error_contract(client):
    missing = await client.get(f"{API}/{uuid.uuid4()}", headers=auth_headers())
    assert missing.json() == {"detail": "Item not found", "code": "not_found"}
    unauthorized = await client.get(API)
    assert unauthorized.status_code == 401
    assert set(unauthorized.json()) == {"detail", "code"}
    assert unauthorized.json()["code"] == "unauthorized"
    invalid = await client.post(API, json={"title": ""}, headers=auth_headers())
    assert invalid.status_code == 422
    assert isinstance(invalid.json()["detail"], list)
