import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.schemas.domain import TaskDraftCreate, TaskCardCreate, SelectionDecisionCreate
from app.services.catalog import CatalogService
from common.auth import TokenUser
from common.db import Base


async def test_decisions_stay_ordered_with_frozen_clock_and_concurrent_writers(tmp_path, monkeypatch):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 23, 10, 0, tzinfo=timezone.utc)

    monkeypatch.setattr('app.services.catalog.datetime', FrozenDateTime)
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'decisions.db').as_posix()}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        user = TokenUser(id=uuid4(), role='business')
        async with sessions() as session:
            service = CatalogService(session)
            draft = await service.create_draft(TaskDraftCreate(description='Need help'), user)
            card = await service.assemble(draft.id, TaskCardCreate(title='Task'), user)
            key = card.id

        async def decide(comment):
            async with sessions() as session:
                return await CatalogService(session).decide(key,
                    SelectionDecisionCreate(selected_proposal_ids=[], comment=comment), user)

        first = await decide('First')
        second = await decide('Second')
        assert second.created_at > first.created_at
        concurrent = await asyncio.gather(decide('Concurrent A'), decide('Concurrent B'))
        assert concurrent[0].created_at != concurrent[1].created_at
        async with sessions() as session:
            decisions = await CatalogService(session).repo.decisions(key)
            assert decisions[0].created_at == max(item.created_at for item in concurrent)
            assert [item.comment for item in decisions[-2:]] == ['Second', 'First']
    finally:
        await engine.dispose()
