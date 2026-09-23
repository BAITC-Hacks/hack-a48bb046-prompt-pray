API = "/api/v1"
USER = {"email": "Alice@Example.com", "username": "alice", "password": "s3cret-pass"}


async def register_and_login(client):
    resp = await client.post(f"{API}/auth/register", json=USER)
    assert resp.status_code == 201, resp.text
    resp = await client.post(f"{API}/auth/login", json={"email": USER["email"], "password": USER["password"]})
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_register_login_me(client):
    tokens = await register_and_login(client)

    resp = await client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "alice@example.com"  # email нормализуется
    assert body["is_admin"] is False
    assert "hashed_password" not in body


async def test_duplicate_registration_conflicts(client):
    await client.post(f"{API}/auth/register", json=USER)
    resp = await client.post(f"{API}/auth/register", json=USER)
    assert resp.status_code == 409
    assert resp.json()["code"] == "email_taken"


async def test_wrong_password_and_unknown_user_look_the_same(client):
    await client.post(f"{API}/auth/register", json=USER)
    wrong = await client.post(f"{API}/auth/login", json={"email": USER["email"], "password": "nope-nope-nope"})
    unknown = await client.post(f"{API}/auth/login", json={"email": "who@example.com", "password": "nope-nope-nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


async def test_refresh_issues_new_pair_and_rejects_access_token(client):
    tokens = await register_and_login(client)

    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    assert resp.json()["access_token"]

    # access-токен нельзя использовать как refresh
    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert resp.status_code == 401


async def test_protected_routes_require_auth_and_admin(client):
    assert (await client.get(f"{API}/users/me")).status_code == 401
    tokens = await register_and_login(client)
    resp = await client.get(f"{API}/users", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert resp.status_code == 403


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["checks"] == {"database": "ok"}
