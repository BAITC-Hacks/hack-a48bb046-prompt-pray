import asyncio

import httpx

from .config import SERVICES, ServiceRoute

_CHECK_TIMEOUT = 2.0


async def _check(client: httpx.AsyncClient, service: ServiceRoute) -> tuple[str, bool]:
    try:
        response = await client.get(f"{service.url.rstrip('/')}{service.health_path}", timeout=_CHECK_TIMEOUT)
        return service.name, response.status_code == 200
    except httpx.HTTPError:
        return service.name, False


async def check_services(client: httpx.AsyncClient) -> dict[str, bool]:
    """Параллельно опрашивает /health всех сервисов. {имя_сервиса: доступен}."""
    return dict(await asyncio.gather(*(_check(client, service) for service in SERVICES)))
