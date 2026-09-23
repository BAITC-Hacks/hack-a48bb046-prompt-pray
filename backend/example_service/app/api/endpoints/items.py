import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import TokenUser
from common.exceptions import NotFoundError

from ...db.session import get_session
from ...models import Item
from ...repositories.item import ItemRepository
from ...schemas.item import ItemCreate, ItemRead, ItemUpdate
from ..deps import get_current_user

router = APIRouter()


async def _get_owned_item(item_id: uuid.UUID, user: TokenUser, session: AsyncSession) -> Item:
    item = await ItemRepository(session).get(item_id, user.id)
    if item is None:
        raise NotFoundError("Item not found")
    return item


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    data: ItemCreate,
    user: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    item = ItemRepository(session).add(Item(owner_id=user.id, **data.model_dump()))
    await session.commit()
    await session.refresh(item)
    return item


@router.get("", response_model=list[ItemRead])
async def list_items(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Sequence[Item]:
    return await ItemRepository(session).list(user.id, limit=limit, offset=offset)


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(
    item_id: uuid.UUID,
    user: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await _get_owned_item(item_id, user, session)


@router.patch("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: uuid.UUID,
    data: ItemUpdate,
    user: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    item = await _get_owned_item(item_id, user, session)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await session.commit()
    await session.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: uuid.UUID,
    user: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    item = await _get_owned_item(item_id, user, session)
    await ItemRepository(session).delete(item)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
