import httpx
from fastapi import APIRouter, Request, Response

from common.auth import decode_token
from common.exceptions import BadRequestError, NotFoundError, UnauthorizedError

from ...core.config import PREFIX_TO_SERVICE, PUBLIC_ENDPOINTS, settings
from ...core.proxy import forward

router = APIRouter()

_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


def _authenticate(request: Request) -> None:
    """Пропускает публичные эндпоинты, для остальных требует валидный access-токен."""
    path = request.url.path.rstrip("/")
    if (request.method, path) in PUBLIC_ENDPOINTS:
        return
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError()
    decode_token(token, secret=settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@router.api_route("/{service_prefix}", methods=_METHODS, include_in_schema=False)
@router.api_route("/{service_prefix}/{path:path}", methods=_METHODS, include_in_schema=False)
async def proxy(service_prefix: str, request: Request, path: str = "") -> Response:
    service = PREFIX_TO_SERVICE.get(service_prefix)
    if service is None:
        raise NotFoundError("Unknown API route")
    if ".." in request.url.path.split("/"):
        raise BadRequestError("Invalid path")

    _authenticate(request)

    client: httpx.AsyncClient = request.app.state.http_client
    return await forward(request, service, client, trust_proxy_headers=settings.TRUST_PROXY_HEADERS)
