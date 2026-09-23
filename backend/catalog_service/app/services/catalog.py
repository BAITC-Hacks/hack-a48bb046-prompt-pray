from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from common.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from ..models import CatalogEntry, ClarifyingQuestion, Proposal, RatingBreakdown, SelectionDecision, TaskCard, TaskDraft
from ..repositories.catalog import CatalogRepository
from .questions import generate_questions

WEIGHTS = dict(context=20, data=20, expected_result=15, success_criteria=15,
               constraints=10, users=10, business_contact=10)


def require_role(user, role):
    if user.role != role:
        raise ForbiddenError(f"{role} role required")


def own(entity, user):
    require_role(user, "business")
    if entity.business_id != user.id:
        raise ForbiddenError("This task belongs to another business")
    return entity


class CatalogService:
    def __init__(self, session):
        self.session = session
        self.repo = CatalogRepository(session)

    async def save(self, entity):
        self.session.add(entity)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Resource already exists or was changed") from exc
        await self.session.refresh(entity)
        return entity

    async def draft(self, key, user):
        draft = await self.repo.draft(key)
        if not draft:
            raise NotFoundError("Draft not found")
        return own(draft, user)

    async def card(self, key):
        card = await self.repo.card(key)
        if not card:
            raise NotFoundError("Task not found")
        return card

    async def create_draft(self, payload, user):
        require_role(user, "business")
        return await self.save(TaskDraft(business_id=user.id, description=payload.description))

    async def questions(self, key, user, authorization, settings):
        draft = await self.draft(key, user)
        existing = await self.repo.questions(key)
        if existing:
            return existing
        description = draft.description
        # Do not hold a database transaction while waiting for the AI provider.
        await self.session.rollback()
        questions = await generate_questions(description, authorization, settings)
        await self.repo.lock_draft(key)
        # Another request may have completed generation during our AI call.
        existing = await self.repo.questions(key)
        if existing:
            await self.session.commit()
            return existing
        for question in questions:
            self.session.add(ClarifyingQuestion(draft_id=key, **question.model_dump()))
        await self.session.commit()
        return await self.repo.questions(key)

    async def answer(self, key, payload, user):
        question = await self.session.get(ClarifyingQuestion, key)
        if not question:
            raise NotFoundError("Question not found")
        await self.draft(question.draft_id, user)
        question.answer = payload.answer
        return await self.save(question)

    def rate(self, card):
        if card.rating is None:
            card.rating = RatingBreakdown()
        for name, points in WEIGHTS.items():
            setattr(card.rating, name, points if (getattr(card, name) or '').strip() else 0)

    async def assemble(self, key, payload, user):
        draft = await self.draft(key, user)
        if await self.repo.card_for_draft(key):
            raise ConflictError("Draft already has a card")
        fields = dict(context=draft.description)
        for question in await self.repo.questions(key):
            if question.answer:
                previous = fields.get(question.field)
                fields[question.field] = f"{previous}\n{question.answer}" if previous else question.answer
        fields.update(payload.model_dump(exclude_unset=True))
        card = TaskCard(draft_id=key, business_id=user.id, rating=RatingBreakdown(), **fields)
        self.rate(card)
        await self.save(card)
        return await self.card(card.id)

    async def update(self, key, payload, user):
        card = own(await self.card(key), user)
        for name, value in payload.model_dump(exclude_unset=True).items():
            setattr(card, name, value)
        self.rate(card)
        # Changed content requires fresh human confirmation before publication.
        card.confirmed_at = None
        if card.catalog_entry:
            await self.session.delete(card.catalog_entry)
            card.catalog_entry = None
        await self.save(card)
        return await self.card(key)

    async def confirm(self, key, user):
        card = own(await self.card(key), user)
        card.confirmed_at = datetime.now(timezone.utc)
        await self.save(card)
        return await self.card(key)

    async def publish(self, key, user):
        card = own(await self.card(key), user)
        if not card.confirmed_at:
            raise BadRequestError("Confirm the card before publishing")
        if card.catalog_entry:
            card.catalog_entry.task = card
            return card.catalog_entry
        entry = CatalogEntry(task_id=key, task=card)
        await self.save(entry)
        await self.session.refresh(entry, ['task'])
        await self.session.refresh(entry.task, ['rating'])
        return entry

    async def proposal(self, key, payload, user):
        require_role(user, "student")
        card = await self.card(key)
        if not card.catalog_entry:
            raise NotFoundError("Published task not found")
        values = payload.model_dump()
        if values['prototype_url'] is not None:
            values['prototype_url'] = str(values['prototype_url'])
        return await self.save(Proposal(task_id=key, user_id=user.id, **values))

    async def decide(self, key, payload, user):
        own(await self.card(key), user)
        proposals = {p.id: p for p in await self.repo.proposals(key)}
        if any(key not in proposals for key in payload.selected_proposal_ids):
            raise BadRequestError("Selected proposals must belong to this task")
        decision = SelectionDecision(task_id=key, business_id=user.id, comment=payload.comment,
            selected_proposals=[proposals[key] for key in payload.selected_proposal_ids])
        await self.save(decision)
        await self.session.refresh(decision, ['selected_proposals'])
        return decision
