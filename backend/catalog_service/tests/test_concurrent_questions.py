import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.schemas.domain import ClarifyingQuestionCreate, TaskDraftCreate
from app.services.catalog import CatalogService
from common.auth import TokenUser
from common.db import Base


async def test_concurrent_generation_persists_one_question_set(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'concurrent.db').as_posix()}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        user = TokenUser(id=uuid4(), role="business")
        async with sessions() as session:
            draft = await CatalogService(session).create_draft(TaskDraftCreate(description="Need help"), user)
            key = draft.id
        both_generating = asyncio.Event()
        arrived = 0

        async def generate(*args):
            nonlocal arrived
            arrived += 1
            if arrived == 2:
                both_generating.set()
            await asyncio.wait_for(both_generating.wait(), timeout=5)
            return [ClarifyingQuestionCreate(field=field, question="Clarify", position=i)
                    for i, field in enumerate(['context', 'data', 'users'])]

        monkeypatch.setattr('app.services.catalog.generate_questions', generate)

        async def request():
            async with sessions() as session:
                result = await CatalogService(session).questions(key, user, 'Bearer token', None)
                return [question.id for question in result]

        first, second = await asyncio.gather(request(), request())
        assert len(first) == 3
        assert first == second
        async with sessions() as session:
            assert len(await CatalogService(session).repo.questions(key)) == 3
    finally:
        await engine.dispose()
