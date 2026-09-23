from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
import logging

from sqlalchemy.exc import IntegrityError

from common.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from ..models import CatalogEntry, ClarifyingQuestion, Proposal, RatingBreakdown, SelectionDecision, TaskCard, TaskDraft
from ..repositories.catalog import CatalogRepository
from .questions import AIInvalidResponse, AIUnavailable, generate_questions
from .fallback_questions import fallback_questions
from .draft_language import detect_draft_locale

logger = logging.getLogger(__name__)

WEIGHTS = dict(context=20, data=20, expected_result=15, success_criteria=15,
               constraints=10, users=10, business_contact=10)


class CardVersionConflict(ConflictError):
    code = "catalog_version_conflict"
    default_detail = "Card changed. Load the latest version before saving, confirming or publishing."


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
        draft = await self.save(TaskDraft(
            business_id=user.id, description=payload.description, locale=detect_draft_locale(payload.description),
        ))
        return await self.repo.draft(draft.id)

    async def update_draft(self, key, payload, user):
        draft = await self.draft(key, user)
        if await self.repo.card_for_draft(key):
            raise ConflictError("Draft already has a card")
        draft.description = payload.description
        draft.locale = detect_draft_locale(payload.description)
        await self.save(draft)
        return await self.repo.draft(key)

    async def questions(self, key, user, authorization, settings):
        draft = await self.draft(key, user)
        existing = await self.repo.questions(key)
        if existing:
            return existing
        description = draft.description
        locale = detect_draft_locale(description)
        # Do not hold a database transaction while waiting for the AI provider.
        await self.session.rollback()
        try:
            questions = await generate_questions(description, authorization, settings, locale)
        except (AIUnavailable, AIInvalidResponse) as exc:
            # Log only the stable error code; provider bodies can contain secrets.
            logger.warning("Using fallback clarification questions: %s", exc.code)
            questions = fallback_questions(locale)
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

    @asynccontextmanager
    async def mutate_card(self, key, expected_version, user):
        require_role(user, "business")
        try:
            if not await self.repo.claim_card_version(key, user.id, expected_version):
                own(await self.card(key), user)  # Preserve 404/403 for missing/foreign cards.
                raise CardVersionConflict()
            card = await self.card(key)
            yield card
            await self.session.flush()
            # Load server timestamps and relations before releasing the write lock.
            await self.repo.card(key)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def update(self, key, payload, user):
        async with self.mutate_card(key, payload.expected_version, user) as card:
            for name, value in payload.model_dump(exclude_unset=True, exclude={"expected_version"}).items():
                setattr(card, name, value)
            self.rate(card)
            card.confirmed_at = None
            if card.catalog_entry:
                await self.session.delete(card.catalog_entry)
                card.catalog_entry = None
        return card

    async def confirm(self, key, expected_version, user):
        async with self.mutate_card(key, expected_version, user) as card:
            card.confirmed_at = datetime.now(timezone.utc)
        return card

    async def publish(self, key, expected_version, user):
        async with self.mutate_card(key, expected_version, user) as card:
            if not card.confirmed_at:
                raise BadRequestError("Confirm the card before publishing")
            entry = card.catalog_entry
            if entry is None:
                entry = CatalogEntry(task=card)
                self.session.add(entry)
            else:
                entry.task = card
        entry.task = card  # populate_existing reloads the entry; avoid lazy IO during serialization.
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
        card = own(await self.card(key), user)
        # Serialize decisions for this task, including SQLite writers.
        await self.repo.lock_draft(card.draft_id)
        proposals = {p.id: p for p in await self.repo.proposals(key)}
        if any(key not in proposals for key in payload.selected_proposal_ids):
            raise BadRequestError("Selected proposals must belong to this task")
        previous = await self.repo.latest_decision_time(key)
        created_at = datetime.now(timezone.utc)
        if previous is not None:
            # SQLite returns naive datetimes; all persisted timestamps are UTC.
            previous = previous.replace(tzinfo=timezone.utc) if previous.tzinfo is None else previous
            created_at = max(created_at, previous + timedelta(microseconds=1))
        decision = SelectionDecision(task_id=key, business_id=user.id, comment=payload.comment,
            created_at=created_at,
            selected_proposals=[proposals[key] for key in payload.selected_proposal_ids])
        await self.save(decision)
        await self.session.refresh(decision, ['selected_proposals'])
        return decision
