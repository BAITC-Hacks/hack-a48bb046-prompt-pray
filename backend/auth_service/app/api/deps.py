from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import TokenUser, token_user_dependency
from common.exceptions import ForbiddenError, UnauthorizedError

from ..core.config import settings
from ..db.session import get_session
from ..models import User
from ..repositories.user import UserRepository
from ..services.auth import AuthService

get_token_user = token_user_dependency(settings)


def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session)


async def get_current_user(
    token_user: TokenUser = Depends(get_token_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Пользователь из access-токена, сверенный с БД (учитывает блокировку и удаление)."""
    user = await UserRepository(session).get(token_user.id)
    if not user or not user.is_active:
        raise UnauthorizedError("User is not available", code="invalid_token")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise ForbiddenError("Admin privileges required")
    return user
