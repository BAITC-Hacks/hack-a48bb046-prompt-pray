"""
JWT: выпуск и проверка токенов, зависимости FastAPI.

Токены выпускает только auth_service. Остальные сервисы (и gateway) лишь
проверяют подпись общим секретом JWT_SECRET_KEY.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Literal, Optional

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from common.exceptions import ForbiddenError, UnauthorizedError

ACCESS_TOKEN = "access"
REFRESH_TOKEN = "refresh"

_bearer = HTTPBearer(auto_error=False)


class TokenUser(BaseModel):
    """Данные пользователя из access-токена."""

    id: uuid.UUID
    email: Optional[str] = None
    is_admin: bool = False
    role: Literal["business", "student"] | None = None


def create_token(
    *,
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    secret: str,
    algorithm: str = "HS256",
    claims: Optional[dict[str, Any]] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        **(claims or {}),
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, *, secret: str, algorithm: str = "HS256", token_type: str = ACCESS_TOKEN) -> dict[str, Any]:
    """Проверяет подпись, срок действия и тип токена. При ошибке — 401."""
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid or expired token", code="invalid_token")
    if payload.get("type") != token_type:
        raise UnauthorizedError("Invalid token type", code="invalid_token")
    return payload


def token_user_dependency(settings) -> Callable[..., Awaitable[TokenUser]]:
    """
    Фабрика зависимости «текущий пользователь по access-токену» (без обращения к БД).

        get_current_user = token_user_dependency(settings)

        @router.get("/me")
        async def me(user: TokenUser = Depends(get_current_user)): ...
    """

    async def get_token_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> TokenUser:
        if credentials is None:
            raise UnauthorizedError()
        payload = decode_token(
            credentials.credentials,
            secret=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        try:
            return TokenUser(
                id=payload["sub"], email=payload.get("email"),
                is_admin=bool(payload.get("is_admin")), role=payload.get("role"),
            )
        except ValueError:
            raise UnauthorizedError("Invalid token subject", code="invalid_token")

    return get_token_user


def ensure_admin(user: TokenUser) -> TokenUser:
    if not user.is_admin:
        raise ForbiddenError("Admin privileges required")
    return user
