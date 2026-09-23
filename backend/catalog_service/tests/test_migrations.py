"""Run PostgreSQL cases with CATALOG_TEST_POSTGRES_URL pointing at a test server."""
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.migrate import upgrade
from app.db.migrations.baseline import (
    CatalogEntry, ClarifyingQuestion, Proposal, RatingBreakdown,
    SelectionDecision, TaskCard, TaskDraft,
)
from common.db import Base
from app.db.migrations.baseline import Base as LegacyBase


@pytest.fixture(params=["sqlite", "postgresql"])
async def migration_engine(request, tmp_path):
    schema = "migration_test_" + uuid4().hex
    admin = None
    if request.param == "postgresql":
        url = os.environ.get("CATALOG_TEST_POSTGRES_URL")
        if not url:
            pytest.skip("Set CATALOG_TEST_POSTGRES_URL to run PostgreSQL migration tests")
        admin = create_async_engine(url)
        async with admin.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    else:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'catalog.db'}")
    try:
        yield engine
    finally:
        await engine.dispose()
        if admin:
            async with admin.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            await admin.dispose()


async def snapshot(engine):
    async with engine.connect() as connection:
        return {
            table.name: sorted(repr(tuple(row)) for row in (await connection.execute(select(table))).all())
            for table in LegacyBase.metadata.sorted_tables
        }


async def assert_head(engine):
    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "0003_catalog_decisions"
        assert await connection.run_sync(
            lambda conn: compare_metadata(MigrationContext.configure(conn), Base.metadata)
        ) == []


async def test_new_database_and_repeat_upgrade(migration_engine):
    await upgrade(migration_engine)
    await upgrade(migration_engine)
    await assert_head(migration_engine)


async def test_legacy_upgrade_preserves_every_row_and_relationship(migration_engine):
    async with migration_engine.begin() as connection:
        await connection.run_sync(LegacyBase.metadata.create_all)
    async with async_sessionmaker(migration_engine)() as session:
        business = uuid4()
        draft = TaskDraft(business_id=business, description="Исходное описание")
        draft.questions = [ClarifyingQuestion(field="data", question="Данные?", answer="CSV", position=0)]
        card = TaskCard(draft=draft, business_id=business, title="Задача", data="CSV")
        card.rating = RatingBreakdown(data=20)
        proposal = Proposal(task=card, team_id=uuid4(), user_id=uuid4(), idea="Идея", plan="План")
        decisions = [SelectionDecision(task=card, business_id=business, selected_proposals=items)
                     for items in ([], [proposal])]
        session.add_all([CatalogEntry(task=card), proposal, *decisions])
        await session.commit()
    before = await snapshot(migration_engine)
    assert all(before.values())
    await upgrade(migration_engine)
    await upgrade(migration_engine)
    await assert_head(migration_engine)
    assert await snapshot(migration_engine) == before


async def test_legacy_decisions_keep_rejections_but_not_future_proposals(migration_engine):
    async with migration_engine.begin() as connection:
        await connection.run_sync(LegacyBase.metadata.create_all)
    now = datetime.now(timezone.utc)
    async with async_sessionmaker(migration_engine, expire_on_commit=False)() as session:
        business = uuid4()
        draft = TaskDraft(business_id=business, description='Existing task')
        card = TaskCard(draft=draft, business_id=business, title='Existing card')
        proposals = [Proposal(task=card, team_id=uuid4(), user_id=uuid4(), idea='Idea', plan='Plan',
                             created_at=now + timedelta(seconds=offset)) for offset in [-2, -1, 1]]
        decision = SelectionDecision(task=card, business_id=business, created_at=now,
                                     selected_proposals=proposals[:1])
        session.add_all([*proposals, decision])
        await session.commit()
    await upgrade(migration_engine)
    await upgrade(migration_engine)
    from app.models.domain import decision_rejections
    async with migration_engine.connect() as connection:
        rows = (await connection.execute(select(decision_rejections))).all()
        assert rows == [(decision.id, proposals[1].id)]


@pytest.mark.parametrize("damage", ["partial", "column"])
async def test_unknown_legacy_schema_is_not_stamped(migration_engine, damage):
    async with migration_engine.begin() as connection:
        if damage == "partial":
            await connection.run_sync(lambda conn: LegacyBase.metadata.tables["task_drafts"].create(conn))
        else:
            await connection.run_sync(LegacyBase.metadata.create_all)
            await connection.execute(text("ALTER TABLE task_drafts ADD COLUMN unexpected TEXT"))
        await connection.execute(text("INSERT INTO task_drafts (id, business_id, description) VALUES (:id, :business, 'keep')"),
                                 {"id": uuid4().hex, "business": uuid4().hex})
    with pytest.raises(RuntimeError, match="baseline mismatch"):
        await upgrade(migration_engine)
    async with migration_engine.connect() as connection:
        assert await connection.scalar(text("SELECT description FROM task_drafts")) == "keep"
        tables = await connection.run_sync(lambda conn: inspect(conn).get_table_names())
        if "alembic_version" in tables:
            assert await connection.scalar(text("SELECT count(*) FROM alembic_version")) == 0
