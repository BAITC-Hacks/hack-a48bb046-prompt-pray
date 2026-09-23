import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Item


class ItemRepository:
    """
    Доступ к таблице items. Все выборки ограничены владельцем: чужая запись
    для пользователя неотличима от несуществующей.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, item_id: uuid.UUID, owner_id: uuid.UUID) -> Item | None:
        result = await self.session.execute(
            select(Item).where(Item.id == item_id, Item.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def list(self, owner_id: uuid.UUID, *, limit: int, offset: int) -> Sequence[Item]:
        result = await self.session.execute(
            select(Item)
            .where(Item.owner_id == owner_id)
            .order_by(Item.created_at.desc(), Item.id)
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    def add(self, item: Item) -> Item:
        self.session.add(item)
        return item

    async def delete(self, item: Item) -> None:
        await self.session.delete(item)
