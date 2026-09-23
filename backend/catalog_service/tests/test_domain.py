from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import event, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from common.db import Database
from app.models import (
    CatalogEntry, ClarifyingQuestion, Proposal, RatingBreakdown,
    SelectionDecision, TaskCard, TaskDraft,
)
from app.schemas import (
    CatalogEntryRead, ClarifyingQuestionsCreate, ProposalCreate, RatingBreakdownRead,
    SelectionDecisionCreate, SelectionDecisionRead, TaskCardConfirm,
    TaskCardCreate, TaskCardUpdate, TaskDraftCreate,
)


@pytest.fixture
async def db():
    database = Database(SimpleNamespace(
        SQLALCHEMY_DATABASE_URI="sqlite+aiosqlite:///:memory:", DB_ECHO=False,
    ), "catalog_service")

    @event.listens_for(database.engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    await database.create_tables()
    yield database
    await database.dispose()


async def test_tables_relationships_and_serialization(db):
    async with db.engine.connect() as connection:
        tables = await connection.run_sync(lambda conn: inspect(conn).get_table_names())
    assert set(tables) == {
        "task_drafts", "clarifying_questions", "task_cards", "rating_breakdowns",
        "catalog_entries", "proposals", "selection_decisions", "selection_decision_proposals",
    }
    business_id = uuid4()
    async with db.session_factory() as session:
        draft = TaskDraft(business_id=business_id, description="Нужен прогноз спроса")
        draft.questions = [
            ClarifyingQuestion(field=field, question="Уточните поле", position=index)
            for index, field in enumerate(["data", "users", "constraints"])
        ]
        task = TaskCard(draft=draft, business_id=business_id, title="Прогноз спроса")
        task.rating = RatingBreakdown(context=20)
        # ORM stores state; publication permission and confirmation belong to services.
        entry = CatalogEntry(task=task)
        proposals = [
            Proposal(task=task, team_id=uuid4(), user_id=uuid4(), idea="Идея", plan="План")
            for _ in range(2)
        ]
        decisions = [
            SelectionDecision(task=task, business_id=business_id, selected_proposals=selection)
            for selection in ([], proposals[:1], proposals)
        ]
        session.add_all([entry, *proposals, *decisions])
        await session.commit()
        task_id = task.id

    async with db.session_factory() as session:
        entry = await session.scalar(select(CatalogEntry).options(
            selectinload(CatalogEntry.task).selectinload(TaskCard.rating)
        ))
        result = CatalogEntryRead.model_validate(entry)
        assert result.task_id == task_id
        assert result.task.context is None
        assert result.task.rating.total == 20
        assert result.task.rating.readiness == "черновик"
        assert result.model_dump()["task"]["rating"]["readiness_code"] == "draft"
        stored = (await session.scalars(select(SelectionDecision).options(
            selectinload(SelectionDecision.selected_proposals)
        ))).all()
        assert sorted(len(SelectionDecisionRead.model_validate(d).selected_proposal_ids)
                      for d in stored) == [0, 1, 2]


async def test_database_rejects_orphans_duplicate_cards_and_invalid_scores(db):
    async with db.session_factory() as session:
        session.add(CatalogEntry(task_id=uuid4()))
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
        draft = TaskDraft(business_id=uuid4(), description="Описание")
        session.add(draft)
        await session.commit()
        draft_id, business_id = draft.id, draft.business_id
        task = TaskCard(draft_id=draft_id, business_id=business_id, title="Задача")
        session.add(task)
        await session.commit()
        task_id = task.id
        session.add(TaskCard(draft_id=draft_id, business_id=business_id, title="Дубликат"))
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
        session.add(RatingBreakdown(task_id=task_id, context=21))
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_service_startup_creates_domain_tables(monkeypatch):
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("JWT_SECRET_KEY", "catalog-test-secret-key-1234567890123456")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    from app.main import app, db as service_db

    async with app.router.lifespan_context(app):
        assert await service_db.ping()
        async with service_db.engine.connect() as connection:
            tables = await connection.run_sync(lambda conn: inspect(conn).get_table_names())
        assert {"task_drafts", "task_cards", "selection_decisions"} <= set(tables)


@pytest.mark.parametrize("score,level,code", [
    (0, "черновик", "draft"), (39, "черновик", "draft"),
    (40, "рабочая", "working"), (69, "рабочая", "working"),
    (70, "готовая", "ready"), (89, "готовая", "ready"),
    (90, "приоритетная", "priority"), (100, "приоритетная", "priority"),
])
def test_rating_boundaries(score, level, code):
    remaining = score
    values = {}
    for field, maximum in zip(RatingBreakdownRead.model_fields, [20, 20, 15, 15, 10, 10, 10]):
        values[field] = min(remaining, maximum)
        remaining -= values[field]
    rating = RatingBreakdownRead(**values)
    assert rating.model_dump()["total"] == score
    assert rating.model_dump()["readiness"] == level
    assert rating.model_dump(mode="json")["readiness_code"] == code
    with pytest.raises(ValidationError):
        RatingBreakdownRead(**{**values, "users": 11})


def test_patch_distinguishes_omitted_and_cleared_fields():
    assert TaskCardUpdate(expected_version=1).model_dump(exclude_unset=True) == {"expected_version": 1}
    assert TaskCardUpdate(expected_version=1, context=None).model_dump(exclude_unset=True) == {"context": None, "expected_version": 1}
    assert TaskCardCreate(title="  Задача  ").title == "Задача"
    for payload in ({"title": None}, {"title": "  "}, {"rating": 100}, {"business_id": str(uuid4())}):
        with pytest.raises(ValidationError):
            TaskCardUpdate(expected_version=1, **payload)
    with pytest.raises(ValidationError):
        TaskDraftCreate(description="   ")


def test_questions_require_three_and_unique_positions():
    questions = [{"field": "data", "question": "Какие данные?", "position": n} for n in range(3)]
    assert len(ClarifyingQuestionsCreate(questions=questions).questions) == 3
    for invalid in (questions[:2], [questions[0]] * 3):
        with pytest.raises(ValidationError):
            ClarifyingQuestionsCreate(questions=invalid)


def test_decision_is_explicit_and_prototype_is_http_url():
    assert SelectionDecisionCreate(selected_proposal_ids=[]).selected_proposal_ids == []
    proposal_id = uuid4()
    for payload in ({}, {"selected_proposal_ids": [proposal_id, proposal_id]}):
        with pytest.raises(ValidationError):
            SelectionDecisionCreate(**payload)
    with pytest.raises(ValidationError):
        TaskCardConfirm(confirmed=False, expected_version=1)
    assert TaskCardConfirm(confirmed=True, expected_version=1).confirmed
    proposal = dict(team_id=uuid4(), idea="Идея", plan="План")
    assert ProposalCreate(**proposal).prototype_url is None
    with pytest.raises(ValidationError):
        ProposalCreate(**proposal, prototype_url="javascript:alert(1)")
