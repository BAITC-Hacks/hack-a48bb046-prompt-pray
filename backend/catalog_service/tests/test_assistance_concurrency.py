import asyncio
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.auth import TokenUser
from common.db import Base
from common.exceptions import ConflictError
from app.api.assistance import next_question
from app.models import ClarifyingQuestion
from app.schemas.domain import TaskDraftCreate
from app.services.assistance import NextQuestion
from app.services.catalog import CatalogService


async def test_two_ai_refinements_only_one_can_update_history(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'ai-race.db').as_posix()}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    user = TokenUser(id=uuid4(), role='business')
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with sessions() as session:
            service = CatalogService(session)
            draft = await service.create_draft(TaskDraftCreate(description='Sales reporting'), user)
            key = draft.id
            for position, field in enumerate(['data', 'users', 'constraints']):
                session.add(ClarifyingQuestion(draft_id=key, field=field, question='Describe ' + field, position=position))
            await session.commit()

        ready = asyncio.Event()
        arrived = 0

        async def generate(*args):
            nonlocal arrived
            arrived += 1
            number = arrived
            if arrived == 2:
                ready.set()
            await asyncio.wait_for(ready.wait(), timeout=5)
            return NextQuestion(field='data', question=f'Which sales data is available? Variant {number}')

        monkeypatch.setattr('app.api.assistance.ask', generate)

        async def request():
            async with sessions() as session:
                try:
                    question = await next_question(key, SimpleNamespace(headers={'Authorization': 'Bearer test'}),
                                                   user=user, service=CatalogService(session))
                    return question.question
                except ConflictError:
                    return 'conflict'

        results = await asyncio.wait_for(asyncio.gather(request(), request()), timeout=10)
        assert results.count('conflict') == 1
        winner = next(result for result in results if result != 'conflict')
        async with sessions() as session:
            questions = await CatalogService(session).repo.questions(key)
            assert len(questions) == 3
            assert questions[0].question == winner
            assert [q.field for q in questions] == ['data', 'users', 'constraints']
            assert all(q.answer is None for q in questions)
    finally:
        await engine.dispose()
