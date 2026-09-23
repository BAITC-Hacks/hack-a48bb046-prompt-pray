"""Exercise the development seeder against the real catalog API and isolated SQLite."""
import json
import uuid
from functools import partial
from pathlib import Path

import anyio
import httpx
import pytest

from conftest import auth_headers
from scripts import seed_demo


@pytest.fixture
def demo_runner(client, monkeypatch, tmp_path):
    accounts = {}
    sessions = {}
    original_client = httpx.Client

    async def forward(request):
        return await client.request(
            request.method, request.url.path, headers=dict(request.headers), content=request.content,
        )

    def handle(request):
        path = request.url.path
        if path == "/api/v1/auth/register":
            data = json.loads(request.content)
            if data["email"] in accounts:
                return httpx.Response(409)
            accounts[data["email"]] = {"id": str(uuid.uuid4()), "username": data["username"], "role": data["role"]}
            return httpx.Response(201, json={})
        if path == "/api/v1/auth/login":
            user = accounts[json.loads(request.content)["email"]]
            authorization = auth_headers(user["role"], user["id"])["Authorization"]
            sessions[authorization] = user
            return httpx.Response(200, json={"access_token": authorization.removeprefix("Bearer ")})
        if path == "/api/v1/users/me":
            return httpx.Response(200, json=sessions[request.headers["Authorization"]])
        assert path.startswith("/api/v1/catalog"), "Seeder must not call AI"
        response = anyio.from_thread.run(forward, request)
        return httpx.Response(response.status_code, headers=response.headers, content=response.content)

    monkeypatch.setattr(seed_demo.httpx, "Client", lambda **kwargs: original_client(
        **kwargs, transport=httpx.MockTransport(handle),
    ))

    async def run():
        return await anyio.to_thread.run_sync(partial(
            seed_demo.seed_demo, "http://test", state_file=tmp_path / "seed.json",
        ))

    return run, accounts


async def test_demo_volume_links_ratings_and_repeat_run(client, demo_runner):
    run, accounts = demo_runner
    report = await run()
    assert report == {"added": {"drafts": 10, "cards": 5, "proposals": 5}, "preserved_or_unavailable": []}
    assert len(accounts) == 6
    owner = auth_headers("business", accounts["user1@demo.example.com"]["id"])
    drafts = (await client.get("/api/v1/catalog/drafts", headers=owner)).json()
    standalone = [draft for draft in drafts if draft["card_id"] is None]
    assert len(standalone) == 5
    assert {draft["locale"] for draft in standalone} == {"ru", "kk", "en"}
    entries = (await client.get("/api/v1/catalog")).json()["items"]
    assert [entry["task"]["rating"]["total"] for entry in entries] == [100, 80, 60, 40, 20]
    proposals = []
    prototype_html = (Path(__file__).resolve().parents[3] / "frontend/public/demo/prototypes.html").read_text(encoding="utf-8")
    for entry in entries:
        path = f"/api/v1/catalog/tasks/{entry['task_id']}"
        items = (await client.get(path + "/proposals", headers=owner)).json()
        if entry["task"]["rating"]["total"] == 20:
            assert len(items) == 1  # Low readiness doesn't block an application.
        proposals.extend(items)
        assert (await client.get(path + "/decisions", headers=owner)).json() == []
    assert len(proposals) == 5
    assert len({proposal["team_id"] for proposal in proposals}) == 5
    for proposal in proposals:
        assert "Срок:" in proposal["plan"] and "Технологии:" in proposal["plan"]
        assert f'id="{proposal["prototype_url"].split("#")[1]}"' in prototype_html
    assert (await run())["added"] == {"drafts": 0, "cards": 0, "proposals": 0}


async def test_repeat_preserves_edited_draft_withdrawn_card_and_decision(client, demo_runner):
    run, accounts = demo_runner
    await run()
    owner = auth_headers("business", accounts["user1@demo.example.com"]["id"])
    drafts = (await client.get("/api/v1/catalog/drafts", headers=owner)).json()
    draft = next(item for item in drafts if item["card_id"] is None)
    response = await client.patch(f"/api/v1/catalog/drafts/{draft['id']}", headers=owner,
                                  json={"description": "Мой отредактированный черновик"})
    assert response.status_code == 200
    coffee = (await client.get("/api/v1/catalog")).json()["items"][0]["task"]
    path = f"/api/v1/catalog/tasks/{coffee['id']}"
    proposals = (await client.get(path + "/proposals", headers=owner)).json()
    decision = await client.post(path + "/decisions", headers=owner,
                                json={"selected_proposal_ids": [proposals[0]["id"]]})
    assert decision.status_code == 201
    response = await client.patch(path, headers=owner, json={"title": "Моя правка", "expected_version": coffee["version"]})
    assert response.status_code == 200
    before = response.json()
    report = await run()
    assert report["added"] == {"drafts": 0, "cards": 0, "proposals": 0}
    assert set(report["preserved_or_unavailable"]) == {"coffee-dashboard", "coffee-report"}
    after = (await client.get(path, headers=owner)).json()
    assert after == before
    assert (await client.get(path)).status_code == 401
    assert (await client.get(path + "/decisions", headers=owner)).json() == [decision.json()]
    drafts = (await client.get("/api/v1/catalog/drafts", headers=owner)).json()
    assert len(drafts) == 10
    assert next(item for item in drafts if item["id"] == draft["id"])["description"] == "Мой отредактированный черновик"
