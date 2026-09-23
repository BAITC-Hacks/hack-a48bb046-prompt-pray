from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from ..models import (
    CatalogEntry, ClarifyingQuestion, Proposal, RatingBreakdown,
    SelectionDecision, TaskCard, TaskDraft,
)


class CatalogRepository:
    def __init__(self, session):
        self.session = session

    async def draft(self, key):
        return await self.session.scalar(select(TaskDraft).where(TaskDraft.id == key)
            .options(selectinload(TaskDraft.card)))

    async def drafts(self, business_id):
        return (await self.session.scalars(select(TaskDraft).where(
            TaskDraft.business_id == business_id
        ).options(selectinload(TaskDraft.card)).order_by(TaskDraft.created_at.desc()))).all()

    async def questions(self, draft_id):
        return (await self.session.scalars(select(ClarifyingQuestion).where(
            ClarifyingQuestion.draft_id == draft_id
        ).order_by(ClarifyingQuestion.position))).all()

    async def lock_draft(self, draft_id):
        # A no-op row update serializes writers in both PostgreSQL and SQLite.
        # SELECT FOR UPDATE alone would be ignored by SQLite.
        await self.session.execute(update(TaskDraft).where(TaskDraft.id == draft_id).values(
            description=TaskDraft.description, updated_at=TaskDraft.updated_at,
        ))

    async def card(self, key):
        return await self.session.scalar(select(TaskCard).where(TaskCard.id == key).options(
            selectinload(TaskCard.rating), selectinload(TaskCard.catalog_entry)
        ))

    async def card_for_draft(self, key):
        return await self.session.scalar(select(TaskCard).where(TaskCard.draft_id == key))

    async def catalog(self, limit, offset):
        total = await self.session.scalar(select(func.count()).select_from(CatalogEntry))
        rating = sum(getattr(RatingBreakdown, name) for name in (
            'context', 'data', 'expected_result', 'success_criteria',
            'constraints', 'users', 'business_contact',
        ))
        items = (await self.session.scalars(select(CatalogEntry).join(TaskCard).join(RatingBreakdown)
            .options(selectinload(CatalogEntry.task).selectinload(TaskCard.rating))
            .order_by(rating.desc(), CatalogEntry.published_at.desc(), CatalogEntry.task_id)
            .limit(limit).offset(offset))).all()
        return items, total

    async def proposals(self, task_id):
        return (await self.session.scalars(select(Proposal).where(Proposal.task_id == task_id)
            .order_by(Proposal.created_at, Proposal.id))).all()

    async def decisions(self, task_id):
        return (await self.session.scalars(select(SelectionDecision).where(
            SelectionDecision.task_id == task_id
        ).options(selectinload(SelectionDecision.selected_proposals))
            .order_by(SelectionDecision.created_at.desc(), SelectionDecision.id))).all()
