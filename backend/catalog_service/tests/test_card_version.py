import asyncio
from itertools import product
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import get_service
from app.main import app
from app.repositories.catalog import CatalogRepository
from app.schemas.domain import TaskCardUpdate
from app.services.catalog import CatalogService
from common.auth import TokenUser
from common.db import Base
from conftest import auth_headers
from test_workflow import API, make_card


@pytest.fixture
async def parallel_db(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'concurrent-cards.db').as_posix()}")
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def service():
        async with sessions() as session:
            yield CatalogService(session)

    app.dependency_overrides[get_service] = service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, sessions
    finally:
        app.dependency_overrides.pop(get_service, None)
        await engine.dispose()


@pytest.mark.parametrize("first,second", list(product(["edit", "confirm", "publish"], repeat=2)))
async def test_two_independent_sessions_only_one_can_use_a_version(parallel_db, monkeypatch, first, second):
    client, _ = parallel_db
    owner = auth_headers()
    card = await make_card(client, owner)
    path = f"{API}/tasks/{card['id']}"
    confirmed = await client.post(f"{path}/confirm", headers=owner,
                                  json={"confirmed": True, "expected_version": card["version"]})
    version = confirmed.json()["version"]
    arrived = 0
    ready = asyncio.Event()
    original = CatalogRepository.claim_card_version

    async def rendezvous(self, *args):
        nonlocal arrived
        arrived += 1
        if arrived == 2:
            ready.set()
        await asyncio.wait_for(ready.wait(), timeout=5)
        return await original(self, *args)

    monkeypatch.setattr(CatalogRepository, "claim_card_version", rendezvous)

    async def mutate(operation, text):
        body = {"expected_version": version}
        if operation == "edit":
            return await client.patch(path, headers=owner, json={**body, "title": text, "data": text})
        if operation == "confirm":
            body["confirmed"] = True
        return await client.post(f"{path}/{operation}", headers=owner, json=body)

    responses = await asyncio.gather(mutate(first, "First editor"), mutate(second, "Second editor"))
    assert sorted(response.status_code for response in responses) == [200, 409], [r.text for r in responses]
    winner = next(index for index, response in enumerate(responses) if response.status_code == 200)
    loser = responses[1 - winner]
    assert loser.json()["code"] == "catalog_version_conflict"
    current = (await client.get(path, headers=owner)).json()
    assert current["version"] == version + 1
    operation = [first, second][winner]
    if operation == "edit":
        assert current["title"] == ["First editor", "Second editor"][winner]
        assert current["data"] == current["title"]
        assert current["rating"]["total"] == 40
        assert current["confirmed_at"] is None
    else:
        assert current["title"] == "Task"
        assert current["data"] is None
        assert current["rating"]["total"] == 20
        assert current["confirmed_at"] is not None
    entries = (await client.get(API)).json()["items"]
    assert bool(entries) == (operation == "publish")


@pytest.mark.parametrize("operation", ["edit", "confirm", "publish"])
async def test_stale_request_cannot_change_published_card(client, operation):
    owner = auth_headers()
    card = await make_card(client, owner)
    path = f"{API}/tasks/{card['id']}"
    confirmed = await client.post(f"{path}/confirm", headers=owner,
                                  json={"confirmed": True, "expected_version": 1})
    entry = await client.post(f"{path}/publish", headers=owner,
                              json={"expected_version": confirmed.json()["version"]})
    before = entry.json()["task"]
    if operation == "edit":
        response = await client.patch(path, headers=owner, json={"expected_version": 1, "data": "Lost update"})
    else:
        body = {"expected_version": 1}
        if operation == "confirm":
            body["confirmed"] = True
        response = await client.post(f"{path}/{operation}", headers=owner, json=body)
    assert response.status_code == 409
    assert response.json()["code"] == "catalog_version_conflict"
    assert (await client.get(path, headers=owner)).json() == before
    assert (await client.get(API)).json()["total"] == 1


@pytest.mark.parametrize("version", [None, 0, -1, True, "1", 1.5])
async def test_mutations_require_positive_integer_version(client, version):
    owner = auth_headers()
    card = await make_card(client, owner)
    path = f"{API}/tasks/{card['id']}"
    body = {} if version is None else {"expected_version": version}
    for suffix, payload in [("", {**body, "title": "Change"}), ("/confirm", {**body, "confirmed": True}), ("/publish", body)]:
        response = await client.request("PATCH" if not suffix else "POST", path + suffix, headers=owner, json=payload)
        assert response.status_code == 422
    assert (await client.get(path, headers=owner)).json() == card


async def test_failure_rolls_back_version_rating_confirmation_and_publication(parallel_db, monkeypatch):
    client, sessions = parallel_db
    user_id = uuid4()
    owner = auth_headers(user_id=user_id)
    card = await make_card(client, owner)
    path = f"{API}/tasks/{card['id']}"
    await client.post(f"{path}/confirm", headers=owner, json={"confirmed": True, "expected_version": 1})
    before = (await client.post(f"{path}/publish", headers=owner, json={"expected_version": 2})).json()["task"]
    async with sessions() as session:
        service = CatalogService(session)
        original = service.repo.card
        reads = 0

        async def fail_after_flush(key):
            nonlocal reads
            reads += 1
            if reads == 2:
                raise RuntimeError("Failure after flushing all changes")
            return await original(key)

        monkeypatch.setattr(service.repo, "card", fail_after_flush)
        with pytest.raises(RuntimeError, match="Failure after flushing"):
            await service.update(UUID(card["id"]), TaskCardUpdate(expected_version=3, data="New data"),
                                 TokenUser(id=user_id, role="business"))
    assert (await client.get(path, headers=owner)).json() == before
    assert (await client.get(API)).json()["total"] == 1
    saved = await client.patch(path, headers=owner, json={"expected_version": 3, "data": "New data"})
    assert saved.status_code == 200
    assert saved.json()["version"] == 4
    assert saved.json()["rating"]["total"] == 40
    assert saved.json()["confirmed_at"] is None
    assert (await client.get(API)).json()["total"] == 0
