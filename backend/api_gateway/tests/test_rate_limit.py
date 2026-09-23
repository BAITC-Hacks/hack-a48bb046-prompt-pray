import httpx
from fastapi import FastAPI

from common.security import RateLimitMiddleware


async def test_proxy_visitors_have_separate_limits_and_untrusted_headers_are_ignored():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, requests_per_minute=1,
                       trusted_proxy_ips=["127.0.0.1/32"])

    @app.get("/test")
    async def endpoint():
        return {"ok": True}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 123)),
                                base_url="http://test") as proxy:
        assert (await proxy.get("/test", headers={"X-Forwarded-For": "192.0.2.1"})).status_code == 200
        assert (await proxy.get("/test", headers={"X-Forwarded-For": "192.0.2.2"})).status_code == 200
        assert (await proxy.get("/test", headers={"X-Forwarded-For": "192.0.2.1"})).status_code == 429
        # A forged prefix cannot hide the real client at the end of the chain.
        assert (await proxy.get("/test", headers={"X-Forwarded-For": "198.51.100.1, 192.0.2.1"})).status_code == 429
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("192.0.2.3", 123)),
                                base_url="http://test") as direct:
        assert (await direct.get("/test", headers={"X-Forwarded-For": "192.0.2.4"})).status_code == 200
        assert (await direct.get("/test", headers={"X-Forwarded-For": "192.0.2.5"})).status_code == 429
