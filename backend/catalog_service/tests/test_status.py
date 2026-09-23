from conftest import auth_headers


async def test_health_and_gateway_probe_route(client):
    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json()["checks"] == {"database": "ok"}

    assert (await client.get("/api/v1/catalog/status")).status_code == 401
    response = await client.get("/api/v1/catalog/status", headers=auth_headers())
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
