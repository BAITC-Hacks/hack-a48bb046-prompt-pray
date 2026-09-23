from sqlalchemy import case, func, select, update
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
        return await self.session.scalar(select(TaskCard).where(TaskCard.id == key).execution_options(
            populate_existing=True,
        ).options(
            selectinload(TaskCard.rating), selectinload(TaskCard.catalog_entry)
        ))

    async def claim_card_version(self, key, business_id, expected_version):
        # The conditional UPDATE acquires a write lock in SQLite and PostgreSQL.
        # Keep it until content/rating/publication changes commit together.
        result = await self.session.execute(update(TaskCard).where(
            TaskCard.id == key, TaskCard.business_id == business_id,
            TaskCard.version == expected_version,
        ).values(version=TaskCard.version + 1).execution_options(synchronize_session=False))
        return result.rowcount == 1

    async def card_for_draft(self, key):
        return await self.session.scalar(select(TaskCard).where(TaskCard.draft_id == key))

    async def catalog(self, limit, offset, terms=None, topic=None, readiness=None):
        rating = sum(getattr(RatingBreakdown, name) for name in (
            'context', 'data', 'expected_result', 'success_criteria',
            'constraints', 'users', 'business_contact',
        ))
        query = select(CatalogEntry).join(TaskCard).join(RatingBreakdown)
        if topic:
            query = query.where(TaskCard.topic.is_(None) if topic == 'unspecified' else TaskCard.topic == topic)
        if readiness:
            minimum, maximum = {'draft': (0, 39), 'working': (40, 69),
                                'ready': (70, 89), 'priority': (90, 100)}[readiness]
            query = query.where(rating.between(minimum, maximum))
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        order = []
        if terms:
            # Bound parameters and autoescape keep profile text out of SQL syntax.
            text = func.lower(func.coalesce(TaskCard.title, '') + ' ' + func.coalesce(TaskCard.context, '')
                              + ' ' + func.coalesce(TaskCard.expected_result, '') + ' ' + func.coalesce(TaskCard.constraints, ''))
            relevance = sum(case((text.contains(term, autoescape=True), 1), else_=0) for term in terms)
            order.append(relevance.desc())
        items = (await self.session.scalars(query
            .options(selectinload(CatalogEntry.task).selectinload(TaskCard.rating))
            .order_by(*order, rating.desc(), CatalogEntry.published_at.desc(), CatalogEntry.task_id)
            .limit(limit).offset(offset))).all()
        return items, total

    async def proposals(self, task_id, user_id=None):
        query = select(Proposal).where(Proposal.task_id == task_id)
        if user_id is not None:
            query = query.where(Proposal.user_id == user_id)
        return (await self.session.scalars(query
            .order_by(Proposal.created_at, Proposal.id))).all()

    async def decisions(self, task_id, limit=None):
        query = select(SelectionDecision).where(
            SelectionDecision.task_id == task_id
        ).options(selectinload(SelectionDecision.selected_proposals), selectinload(SelectionDecision.rejected_proposals))
        query = query.order_by(SelectionDecision.created_at.desc(), SelectionDecision.id)
        if limit is not None:
            query = query.limit(limit)
        return (await self.session.scalars(query)).all()

    async def latest_decision_time(self, task_id):
        return await self.session.scalar(select(func.max(SelectionDecision.created_at)).where(
            SelectionDecision.task_id == task_id
        ))
