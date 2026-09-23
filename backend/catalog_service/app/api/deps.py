from common.auth import token_user_dependency
from common.exceptions import UnauthorizedError
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from ..db.session import get_session
from ..services.catalog import CatalogService

from ..core.config import settings

# Пользователь берётся из access-токена (подпись проверяется общим секретом),
# в auth_service сервис за каждым запросом не ходит.
get_current_user = token_user_dependency(settings)


async def get_service(session=Depends(get_session)):
    return CatalogService(session)


async def get_optional_user(request: Request):
    if not request.headers.get("Authorization"):
        return None
    scheme, _, token = request.headers['Authorization'].partition(' ')
    if scheme.lower() != 'bearer' or not token:
        raise UnauthorizedError()
    return await get_current_user(HTTPAuthorizationCredentials(scheme=scheme, credentials=token))
