"""Development fixtures through the API; never replace user edits or decisions."""
import argparse
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads(Path(__file__).with_name("demo_data.json").read_text(encoding="utf-8"))
PASSWORD = "password123"
ACCOUNTS = [("user1", "business"), *[(team["username"], "student") for team in DATA["teams"]]]


def proposal_payload(proposal, team, user_id, frontend_url):
    """Keep profile and deadline visible in the existing proposal contract."""
    return {
        "team_id": user_id,
        "idea": f"{team['name']}: {proposal['idea']}",
        "plan": (
            f"Учебная команда: {team['name']}. "
            f"Интересы: {', '.join(team['interests'])}. "
            f"Навыки: {', '.join(team['skills'])}. "
            f"Технологии: {', '.join(team['technologies'])}.\n\n"
            f"План: {proposal['plan']}\nСрок: {proposal['deadline']}.\n"
            "Ссылка ведёт на статический учебный макет, а не готовое решение."
        ),
        "prototype_url": frontend_url.rstrip("/") + proposal["prototype_path"],
    }


def seed_demo(base_url: str, *, frontend_url="http://127.0.0.1:3000", state_file=None) -> dict:
    """Add missing fixtures; remember IDs so editing descriptions doesn't duplicate them."""
    state_file = Path(state_file) if state_file is not None else ROOT / "data" / "demo-seed.json"
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
    registry = state.setdefault(base_url.rstrip("/"), {})

    def remember(key, entity_id):
        registry[key] = entity_id
        state_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = state_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(state_file)

    added = {"drafts": 0, "cards": 0, "proposals": 0}
    skipped = []
    with httpx.Client(base_url=base_url.rstrip("/") + "/api/v1", timeout=15) as client:
        def request(method, path, *, headers=None, **kwargs):
            response = client.request(method, path, headers=headers, **kwargs)
            if not response.is_success:
                # Never print response bodies containing account data or credentials.
                raise RuntimeError(f"Demo setup: {method} {path}: HTTP {response.status_code}")
            return response.json()

        accounts = {}
        for username, role in ACCOUNTS:
            email = f"{username}@demo.example.com"
            registered = client.post("/auth/register", json={
                "email": email, "username": username, "password": PASSWORD, "role": role,
            })
            if registered.status_code not in (201, 409):
                raise RuntimeError(f"Demo registration failed: HTTP {registered.status_code}")
            tokens = request("POST", "/auth/login", json={"email": email, "password": PASSWORD})
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            user = request("GET", "/users/me", headers=headers)
            if user["username"] != username or user["role"] != role:
                raise RuntimeError(f"Demo account {username} conflicts with an existing account; nothing overwritten")
            accounts[username] = (headers, user["id"])

        owner = accounts["user1"][0]
        drafts = request("GET", "/catalog/drafts", headers=owner)
        by_id = {draft["id"]: draft for draft in drafts}
        by_description = {draft["description"]: draft for draft in drafts}

        def ensure_draft(key, description):
            draft = by_id.get(registry.get(key)) or by_description.get(description)
            if draft is None:
                draft = request("POST", "/catalog/drafts", headers=owner, json={"description": description})
                added["drafts"] += 1
            by_id[draft["id"]] = draft
            by_description[draft["description"]] = draft
            remember(key, draft["id"])
            return draft

        cards = {}
        for fixture in DATA["cards"]:
            payload = fixture["fields"]
            draft = ensure_draft("card:" + fixture["key"], payload["context"])
            if draft["card_id"]:
                cards[fixture["key"]] = draft["card_id"]
                continue
            if draft["description"] != payload["context"]:
                skipped.append(fixture["key"])
                continue
            card = request("POST", f"/catalog/drafts/{draft['id']}/card", headers=owner, json=payload)
            path = f"/catalog/tasks/{card['id']}"
            # Labelled fixtures; no AI calls and no automatic team selection.
            card = request("POST", path + "/confirm", headers=owner, json={"confirmed": True, "expected_version": card["version"]})
            request("POST", path + "/publish", headers=owner, json={"expected_version": card["version"]})
            cards[fixture["key"]] = card["id"]
            added["cards"] += 1

        for fixture in DATA["drafts"]:
            ensure_draft("draft:" + fixture["key"], fixture["description"])

        teams = {team["username"]: team for team in DATA["teams"]}
        for fixture in DATA["proposals"]:
            card_id = cards.get(fixture["card"])
            if not card_id:
                skipped.append(fixture["key"])
                continue
            path = f"/catalog/tasks/{card_id}"
            # Never republish a fixture withdrawn by its owner.
            public = client.get(path)
            if public.status_code in (401, 404):
                skipped.append(fixture["key"])
                continue
            if not public.is_success:
                raise RuntimeError(f"Demo setup: GET {path}: HTTP {public.status_code}")
            existing = request("GET", path + "/proposals", headers=owner)
            headers, user_id = accounts[fixture["username"]]
            payload = proposal_payload(fixture, teams[fixture["username"]], user_id, frontend_url)
            key = "proposal:" + fixture["key"]
            proposal = next((item for item in existing if item["user_id"] == user_id and (
                item["id"] == registry.get(key) or item["idea"] == payload["idea"]
            )), None)
            if proposal is None:
                proposal = request("POST", path + "/proposals", headers=headers, json=payload)
                added["proposals"] += 1
            remember(key, proposal["id"])

    report = {"added": added, "preserved_or_unavailable": skipped}
    print("Демоданные готовы: user1 — бизнес; user2–user6 — студенты. Пароль: password123.", flush=True)
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Добавить учебные данные без очистки базы и вызовов AI.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Адрес gateway без /api/v1")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:3000", help="Адрес сайта для ссылок на учебные макеты")
    parser.add_argument("--state-file", type=Path, help="Реестр ID демоданных; по умолчанию backend/data/demo-seed.json")
    args = parser.parse_args()
    seed_demo(args.base_url, frontend_url=args.frontend_url, state_file=args.state_file)
