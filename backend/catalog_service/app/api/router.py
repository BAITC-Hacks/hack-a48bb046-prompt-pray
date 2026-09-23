from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from common.exceptions import UnauthorizedError

from .deps import get_current_user, get_optional_user, get_service
from ..db.session import db
from ..core.config import settings
from ..schemas.domain import (
    TaskDraftCreate, TaskDraftRead, ClarifyingQuestionRead, ClarifyingQuestionAnswer,
    TaskCardCreate, TaskCardUpdate, TaskCardRead, TaskCardConfirm, CatalogEntryRead,
    ProposalCreate, ProposalRead, SelectionDecisionCreate, SelectionDecisionRead,
)
from ..services.catalog import own, require_role

api_router = APIRouter(prefix="/catalog", tags=["catalog"])


@api_router.get("/health", dependencies=[Depends(get_current_user)])
async def catalog_health():
    """Authenticated readiness probe reachable through the gateway."""
    healthy = await db.ping()
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "error",
            "service": "catalog_service",
            "checks": {"database": "ok" if healthy else "error"},
        },
    )


@api_router.get("")
async def catalog(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                  service=Depends(get_service)):
    items, total = await service.repo.catalog(limit, offset)
    return {"items": [CatalogEntryRead.model_validate(item) for item in items],
            "total": total, "limit": limit, "offset": offset}


@api_router.post("/drafts", response_model=TaskDraftRead, status_code=201)
async def create_draft(payload: TaskDraftCreate, user=Depends(get_current_user), service=Depends(get_service)):
    return await service.create_draft(payload, user)


@api_router.get("/drafts", response_model=list[TaskDraftRead])
async def drafts(user=Depends(get_current_user), service=Depends(get_service)):
    require_role(user, "business")
    return await service.repo.drafts(user.id)


@api_router.get("/drafts/{key}", response_model=TaskDraftRead)
async def draft(key: UUID, user=Depends(get_current_user), service=Depends(get_service)):
    return await service.draft(key, user)


@api_router.post("/drafts/{key}/questions", response_model=list[ClarifyingQuestionRead])
async def generate_questions(key: UUID, request: Request, user=Depends(get_current_user), service=Depends(get_service)):
    return await service.questions(key, user, request.headers["Authorization"], settings)


@api_router.get("/drafts/{key}/questions", response_model=list[ClarifyingQuestionRead])
async def questions(key: UUID, user=Depends(get_current_user), service=Depends(get_service)):
    await service.draft(key, user)
    return await service.repo.questions(key)


@api_router.patch("/questions/{key}", response_model=ClarifyingQuestionRead)
async def answer(key: UUID, payload: ClarifyingQuestionAnswer, user=Depends(get_current_user), service=Depends(get_service)):
    return await service.answer(key, payload, user)


@api_router.post("/drafts/{key}/card", response_model=TaskCardRead, status_code=201)
async def assemble(key: UUID, payload: TaskCardCreate, user=Depends(get_current_user), service=Depends(get_service)):
    return await service.assemble(key, payload, user)


@api_router.get("/tasks/{key}", response_model=TaskCardRead)
async def card(key: UUID, user=Depends(get_optional_user), service=Depends(get_service)):
    result = await service.card(key)
    if not result.catalog_entry:
        if user is None:
            raise UnauthorizedError()
        own(result, user)
    return result


@api_router.patch("/tasks/{key}", response_model=TaskCardRead)
async def update_card(key: UUID, payload: TaskCardUpdate, user=Depends(get_current_user), service=Depends(get_service)):
    return await service.update(key, payload, user)


@api_router.post("/tasks/{key}/confirm", response_model=TaskCardRead)
async def confirm(key: UUID, payload: TaskCardConfirm, user=Depends(get_current_user), service=Depends(get_service)):
    return await service.confirm(key, user)


@api_router.post("/tasks/{key}/publish", response_model=CatalogEntryRead)
async def publish(key: UUID, user=Depends(get_current_user), service=Depends(get_service)):
    return await service.publish(key, user)


@api_router.post("/tasks/{key}/proposals", response_model=ProposalRead, status_code=201)
async def proposal(key: UUID, payload: ProposalCreate, user=Depends(get_current_user), service=Depends(get_service)):
    return await service.proposal(key, payload, user)


@api_router.get("/tasks/{key}/proposals", response_model=list[ProposalRead])
async def proposals(key: UUID, user=Depends(get_current_user), service=Depends(get_service)):
    own(await service.card(key), user)
    return await service.repo.proposals(key)


@api_router.post("/tasks/{key}/decisions", response_model=SelectionDecisionRead, status_code=201)
async def decide(key: UUID, payload: SelectionDecisionCreate, user=Depends(get_current_user), service=Depends(get_service)):
    return await service.decide(key, payload, user)


@api_router.get("/tasks/{key}/decisions", response_model=list[SelectionDecisionRead])
async def decisions(key: UUID, user=Depends(get_current_user), service=Depends(get_service)):
    own(await service.card(key), user)
    return await service.repo.decisions(key)
