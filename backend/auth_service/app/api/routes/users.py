from typing import Sequence

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import ConflictError

from ...db.session import get_session
from ...models import User
from ...repositories.user import UserRepository
from ...schemas.user import UserRead, UserUpdate
from ..deps import get_current_user, require_admin

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def read_me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserRead)
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if data.username and data.username != user.username:
        if await UserRepository(session).get_by_username(data.username):
            raise ConflictError("Username already taken", code="username_taken")
        user.username = data.username
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ConflictError("Username already taken", code="username_taken")
    return user


@router.get("", response_model=list[UserRead])
async def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> Sequence[User]:
    return await UserRepository(session).list(limit=limit, offset=offset)
