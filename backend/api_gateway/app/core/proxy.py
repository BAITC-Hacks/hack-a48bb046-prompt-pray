"""Проксирование запросов к downstream-сервисам."""
import httpx
from fastapi import Request, Response

from common.exceptions import AppException
from common.logger import get_logger
from common.middleware import REQUEST_ID_HEADER

from .config import ServiceRoute

logger = get_logger("api_gateway.proxy")

# Заголовки «hop-by-hop» относятся к одному TCP-соединению и не пересылаются дальше (RFC 9110)
_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade",
}
# Host и Content-Length клиент httpx выставит сам; X-Forwarded-For собираем заново
_DROP_REQUEST_HEADERS = _HOP_BY_HOP | {"host", "content-length", "x-forwarded-for"}
# httpx уже распаковал тело, поэтому Content-Encoding/Content-Length от сервиса неактуальны
_DROP_RESPONSE_HEADERS = _HOP_BY_HOP | {"content-length", "content-encoding"}


def create_http_client(timeout: float) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout,
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        follow_redirects=False,
    )


def _forwarded_for(request: Request, trust_proxy_headers: bool) -> str:
    client_ip = request.client.host if request.client else "unknown"
    incoming = request.headers.get("x-forwarded-for")
    return f"{incoming}, {client_ip}" if incoming and trust_proxy_headers else client_ip


async def forward(
    request: Request,
    service: ServiceRoute,
    client: httpx.AsyncClient,
    *,
    trust_proxy_headers: bool = False,
) -> Response:
    """Пересылает запрос сервису «как есть» (тот же путь, метод, тело, query) и возвращает его ответ."""
    # raw_path сохраняет исходное percent-кодирование пути
    raw_path = request.scope.get("raw_path")
    path = raw_path.decode("ascii", "ignore") if raw_path else request.url.path
    url = f"{service.url.rstrip('/')}{path}"
    query_string = request.scope.get("query_string", b"").decode("latin-1")
    if query_string:
        url = f"{url}?{query_string}"  # query пересылается без перекодирования

    headers = {k: v for k, v in request.headers.items() if k.lower() not in _DROP_REQUEST_HEADERS}
    headers["X-Forwarded-For"] = _forwarded_for(request, trust_proxy_headers)
    headers[REQUEST_ID_HEADER] = getattr(request.state, "request_id", "-")

    try:
        upstream = await client.request(
            request.method,
            url,
            headers=headers,
            content=await request.body(),
            **({"timeout": service.timeout} if service.timeout is not None else {}),
        )
    except httpx.TimeoutException:
        logger.error("Timeout from %s: %s %s", service.name, request.method, path)
        raise AppException("Upstream service timed out", status_code=504, code="upstream_timeout")
    except httpx.ConnectError:
        logger.error("Cannot connect to %s (%s)", service.name, service.url)
        raise AppException("Upstream service is unavailable", status_code=503, code="upstream_unavailable")
    except httpx.HTTPError as exc:
        logger.error("Bad response from %s: %s", service.name, exc)
        raise AppException("Bad response from upstream service", status_code=502, code="bad_gateway")

    response = Response(content=upstream.content, status_code=upstream.status_code)
    for key, value in upstream.headers.multi_items():  # multi_items сохраняет повторяющиеся Set-Cookie
        if key.lower() not in _DROP_RESPONSE_HEADERS:
            response.headers.append(key, value)
    return response
