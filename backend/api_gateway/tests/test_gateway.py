import httpx
from conftest import REFRESH_TOKEN, bearer

API = "/api/v1"


async def test_healthz(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["service"] == "api_gateway"


async def test_health_reports_degraded_when_service_down(client, upstream):
    upstream.handler = lambda request: (
        httpx.Response(200) if request.url.host == "localhost" and request.url.port == 8001 else httpx.Response(503)
    )
    resp = await client.get("/health")
    assert resp.status_code == 503
    assert resp.json()["services"] == {"auth": "ok", "example": "error", "ai": "error", "catalog": "error"}


async def test_catalog_route_forwards_through_gateway(client, upstream):
    response = await client.get(f"{API}/catalog/status", headers=bearer())
    assert response.status_code == 200
    assert str(upstream.requests[0].url) == "http://localhost:8004/api/v1/catalog/status"


async def test_unknown_route_is_404(client, upstream):
    resp = await client.get(f"{API}/nope", headers=bearer())
    assert resp.status_code == 404
    assert upstream.requests == []


async def test_protected_route_requires_valid_access_token(client, upstream):
    assert (await client.get(f"{API}/items")).status_code == 401
    assert (await client.get(f"{API}/items", headers={"Authorization": "Bearer junk"})).status_code == 401
    # refresh-токен не годится для доступа к API
    assert (await client.get(f"{API}/items", headers=bearer(REFRESH_TOKEN))).status_code == 401
    assert upstream.requests == []  # до сервисов невалидные запросы не доходят


async def test_public_endpoints_skip_auth(client, upstream):
    resp = await client.post(f"{API}/auth/login", json={"email": "a@b.co", "password": "x"})
    assert resp.status_code == 200
    assert str(upstream.requests[0].url) == "http://localhost:8001/api/v1/auth/login"
    # публичен только POST, а не любой метод на том же пути
    assert (await client.get(f"{API}/auth/login")).status_code == 401


async def test_forwards_request_and_response(client, upstream):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            201,
            json={"echo": request.content.decode()},
            headers=[("X-Custom", "1"), ("Set-Cookie", "a=1"), ("Set-Cookie", "b=2"), ("Connection", "close")],
        )

    upstream.handler = handler
    resp = await client.post(
        f"{API}/items?limit=5&q=a%20b",
        content=b'{"title":"x"}',
        headers={**bearer(), "Content-Type": "application/json", "X-Forwarded-For": "6.6.6.6"},
    )

    assert resp.status_code == 201
    assert resp.json() == {"echo": '{"title":"x"}'}
    assert resp.headers["x-custom"] == "1"
    assert resp.headers.get_list("set-cookie") == ["a=1", "b=2"]
    assert "connection" not in resp.headers

    sent = upstream.requests[0]
    assert str(sent.url) == "http://localhost:8002/api/v1/items?limit=5&q=a%20b"
    assert sent.headers["authorization"].startswith("Bearer ")
    assert sent.headers["x-request-id"] == resp.headers["x-request-id"]
    # подделанному X-Forwarded-For не доверяем, пока не включён TRUST_PROXY_HEADERS
    assert sent.headers["x-forwarded-for"] != "6.6.6.6"


async def test_path_traversal_is_rejected(client, upstream):
    # Литеральное `..` клиент схлопнул бы сам, а `%2e%2e` доходит до gateway как есть
    resp = await client.get(f"{API}/items/%2e%2e/auth/login", headers=bearer())
    assert resp.status_code == 400
    assert upstream.requests == []


async def test_upstream_errors_are_mapped(client, upstream):
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    def slow(request):
        raise httpx.ReadTimeout("slow", request=request)

    upstream.handler = refuse
    assert (await client.get(f"{API}/items", headers=bearer())).status_code == 503
    upstream.handler = slow
    assert (await client.get(f"{API}/items", headers=bearer())).status_code == 504


async def test_upstream_error_status_is_passed_through(client, upstream):
    upstream.handler = lambda request: httpx.Response(404, json={"detail": "Item not found", "code": "not_found"})
    resp = await client.get(f"{API}/items/123", headers=bearer())
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"
