from uuid import UUID

from fastapi import APIRouter, Depends, Request

from common.exceptions import BadRequestError, ConflictError, NotFoundError
from .deps import get_current_user, get_service
from ..core.config import settings
from ..schemas.domain import ClarifyingQuestionRead
from ..services.catalog import own, WEIGHTS
from ..services.assistance import (
    Advice, GeneratedTitle, NextQuestion, SimilarTasks, ask, card_data,
)

router = APIRouter(prefix='/catalog', tags=['catalog AI'])


@router.post('/tasks/{key}/rating-advice', response_model=Advice)
async def rating_advice(key: UUID, request: Request, user=Depends(get_current_user), service=Depends(get_service)):
    card = own(await service.card(key), user)
    data = {'task': card_data(card), 'rating': {field: getattr(card.rating, field) for field in WEIGHTS}, 'weights': WEIGHTS}
    await service.session.rollback()
    return await ask(data,
        'Explain the current completeness score. Each nonempty field earns its full weight, otherwise zero. '
        'Give concrete, task-specific additions for missing fields with the exact available points. '
        'Distinguish quality improvements to existing fields (zero extra points). Never promise more than 100.',
        Advice, request.headers['Authorization'], settings)


@router.post('/tasks/{key}/proposals/{proposal_id}/analysis', response_model=Advice)
async def proposal_analysis(key: UUID, proposal_id: UUID, request: Request,
                            user=Depends(get_current_user), service=Depends(get_service)):
    card = own(await service.card(key), user)
    proposal = next((p for p in await service.repo.proposals(key) if p.id == proposal_id), None)
    if proposal is None:
        raise NotFoundError('Proposal not found')
    data = {'task': card_data(card), 'proposal': {
        'idea': proposal.idea, 'plan': proposal.plan, 'prototype_url': proposal.prototype_url,
    }}
    await service.session.rollback()
    return await ask(data,
        'Summarize alignment of the idea and plan with the task, strengths, gaps and questions for the team. '
        'A URL only establishes that a link was supplied; its contents and quality are unverified. '
        'Do not rank, score, select or reject teams. Business makes the final choice.',
        Advice, request.headers['Authorization'], settings)


@router.post('/drafts/{key}/title', response_model=GeneratedTitle)
async def title(key: UUID, request: Request, user=Depends(get_current_user), service=Depends(get_service)):
    draft = await service.draft(key, user)
    data = {'description': draft.description, 'answers': [q.answer for q in await service.repo.questions(key) if q.answer]}
    await service.session.rollback()
    return await ask(data, 'Suggest a short task title from the stated context and need. Do not add unstated results or technology.',
                     GeneratedTitle, request.headers['Authorization'], settings)


@router.post('/drafts/{key}/similar', response_model=SimilarTasks)
async def similar(key: UUID, request: Request, user=Depends(get_current_user), service=Depends(get_service)):
    draft = await service.draft(key, user)
    # MVP bounded scan: semantic comparison of up to 50 highest-rated public tasks.
    entries, _ = await service.repo.catalog(50, 0)
    candidates = [{'task_id': str(entry.task_id), 'title': entry.task.title[:200],
                   'context': (entry.task.context or '')[:200]} for entry in entries
                  if entry.task.draft_id != key]
    data = {'description': draft.description, 'catalog': candidates}
    await service.session.rollback()
    if not candidates:
        return SimilarTasks(matches=[])
    result = await ask(data,
        'Find semantic duplicates or closely related needs among the supplied catalog candidates. '
        'Return up to 5 strong matches with reasons, or an empty list. Shared generic words are insufficient. '
        'Use only candidate task_id values. Similarity is advisory and never blocks creating a task.',
        SimilarTasks, request.headers['Authorization'], settings)
    allowed = {item['task_id'] for item in candidates}
    matches = {m.task_id: m for m in result.matches if str(m.task_id) in allowed}
    result.matches = list(matches.values())
    return result


@router.post('/drafts/{key}/next-question', response_model=ClarifyingQuestionRead)
async def next_question(key: UUID, request: Request, user=Depends(get_current_user), service=Depends(get_service)):
    draft = await service.draft(key, user)
    if draft.card_id:
        raise ConflictError('Draft already has a card')
    questions = await service.repo.questions(key)
    target = next((q for q in questions if not q.answer), None)
    if target is None:
        raise BadRequestError('No unanswered questions remain')
    snapshot = [(q.id, q.field, q.question, q.answer) for q in questions]
    target_id = target.id
    data = {'description': draft.description, 'history': [
        {'field': q.field, 'question': q.question, 'answer': q.answer} for q in questions if q.answer
    ], 'target_field': target.field, 'remaining_fields': [q.field for q in questions if not q.answer]}
    await service.session.rollback()
    result = await ask(data,
        'Ask exactly one next question based on the original draft and previous answers. '
        'Target the most useful remaining missing detail. Avoid repeating answered questions. '
        'Refine target_field only; do not replace it with another remaining field.',
        NextQuestion, request.headers['Authorization'], settings)
    if result.field != data['target_field']:
        raise BadRequestError('AI question must preserve the target field')
    await service.repo.lock_draft(key)
    current = await service.repo.questions(key)
    latest_draft = await service.repo.draft(key)
    if (snapshot != [(q.id, q.field, q.question, q.answer) for q in current]
            or latest_draft.description != data['description'] or await service.repo.card_for_draft(key)):
        await service.session.rollback()
        raise ConflictError('Draft changed during AI generation; retry')
    target = next(q for q in current if q.id == target_id)
    target.question = result.question
    target.field = result.field
    return await service.save(target)
