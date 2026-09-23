"""Exercise the live gateway and persist uniquely named smoke-test demo data."""
import argparse
import json
import shutil
import subprocess
import sys
import uuid

import httpx


def run(base_url: str) -> bool:
    prefix = uuid.uuid4().hex[:12]
    password = uuid.uuid4().hex
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=90) as client:
        def request(method, path, expected=200, headers=None, **kwargs):
            response = client.request(method, path, headers=headers, **kwargs)
            if response.status_code != expected:
                # Bodies may contain submitted credentials; never print them.
                raise RuntimeError(f"{method} {path}: HTTP {response.status_code}, expected {expected}")
            return response.json() if response.content else None

        request("GET", "/health")
        accounts = {}
        for role in ("business", "student"):
            email = f"smoke-{prefix}-{role}@example.com"
            user = request("POST", "/api/v1/auth/register", expected=201, json={
                "email": email, "username": f"smoke-{prefix}-{role}",
                "password": password, "role": role,
            })
            assert user["role"] == role
            tokens = request("POST", "/api/v1/auth/login", json={"email": email, "password": password})
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            assert request("GET", "/api/v1/users/me", headers=headers)["role"] == role
            accounts[role] = headers
        business, student = accounts["business"], accounts["student"]
        api = "/api/v1/catalog"
        request("GET", f"{api}/health", headers=business)
        curl = shutil.which("curl.exe") or shutil.which("curl")
        if curl:
            # Keep the token out of both process arguments and console output.
            config = "\n".join([
                "silent", "show-error",
                f"url = {json.dumps(base_url.rstrip('/') + api + '/health')}",
                f"header = {json.dumps('Authorization: ' + business['Authorization'])}",
                'write-out = "\\n%{http_code}"',
            ])
            probe = subprocess.run([curl, "--config", "-"], input=config, capture_output=True, text=True, timeout=15)
            if probe.returncode or not probe.stdout.rstrip().endswith("\n200"):
                raise RuntimeError("Authenticated curl catalog health probe failed")
            print("Authenticated catalog health (curl): passed")
        request("POST", f"{api}/drafts", expected=403, headers=student, json={"description": "Forbidden smoke draft"})
        draft = request("POST", f"{api}/drafts", expected=201, headers=business,
                        json={"description": "Smoke test: prepare a sales dashboard from a CSV file."})
        draft_path = f"{api}/drafts/{draft['id']}"
        response = client.post(f"{draft_path}/questions", headers=business)
        ai_complete = response.status_code == 200
        if ai_complete:
            questions = response.json()
            assert len(questions) >= 3
            for question in questions:
                request("PATCH", f"{api}/questions/{question['id']}", headers=business,
                        json={"answer": f"Smoke test answer for {question['field']}"})
            print("AI questions: passed")
        elif response.status_code in (502, 503, 504):
            print(f"AI questions: unavailable (HTTP {response.status_code}); AI validation incomplete")
        else:
            raise RuntimeError(f"AI questions: unexpected HTTP {response.status_code}")
        card = request("POST", f"{draft_path}/card", expected=201, headers=business,
                       json={"title": f"Smoke sales dashboard {prefix}"})
        task_path = f"{api}/tasks/{card['id']}"
        request("POST", f"{task_path}/publish", expected=400, headers=business, json={"expected_version": card["version"]})
        fields = {
            "context": "Sales reporting", "data": "CSV example", "expected_result": "Dashboard",
            "success_criteria": "Totals match CSV", "constraints": "Two weeks",
            "users": "Sales team", "business_contact": "Smoke business account",
        }
        updated = request("PATCH", task_path, headers=business, json={**fields, "expected_version": card["version"]})
        assert updated["rating"]["total"] == 100
        confirmed = request("POST", f"{task_path}/confirm", headers=business, json={"confirmed": True, "expected_version": updated["version"]})
        published = request("POST", f"{task_path}/publish", headers=business, json={"expected_version": confirmed["version"]})
        request("POST", f"{task_path}/publish", headers=business, json={"expected_version": published["task"]["version"]})
        assert request("GET", task_path)["id"] == card["id"]
        catalog = request("GET", api, params={"limit": 200})
        ratings = [entry["task"]["rating"]["total"] for entry in catalog["items"]]
        assert ratings == sorted(ratings, reverse=True)
        assert catalog["total"] >= 1
        proposal = request("POST", f"{task_path}/proposals", expected=201, headers=student, json={
            "team_id": str(uuid.uuid4()), "idea": "Build dashboard", "plan": "Import CSV and verify totals",
            "prototype_url": "https://example.com/smoke-prototype",
        })
        assert request("GET", f"{task_path}/decisions", headers=business) == []
        request("POST", f"{task_path}/decisions", expected=403, headers=student,
                json={"selected_proposal_ids": [proposal["id"]]})
        for selected in ([proposal["id"]], []):
            decision = request("POST", f"{task_path}/decisions", expected=201, headers=business,
                               json={"selected_proposal_ids": selected})
            assert decision["selected_proposal_ids"] == selected
        print(f"Gateway workflow: passed; task {card['id']}")
        return ai_complete


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    arguments = parser.parse_args()
    try:
        complete = run(arguments.base_url)
    except (httpx.HTTPError, RuntimeError, AssertionError, KeyError, TypeError, ValueError,
            OSError, subprocess.TimeoutExpired) as error:
        print(f"Smoke failed: {error if isinstance(error, RuntimeError) else type(error).__name__}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0 if complete else 2)
