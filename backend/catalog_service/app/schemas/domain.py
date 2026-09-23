"""Domain contracts; request schemas never accept server-owned identity or rating."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, computed_field, field_validator

CardField = Literal[
    "context", "data", "expected_result", "success_criteria",
    "constraints", "users", "business_contact",
]
Content = Annotated[str, Field(min_length=1, max_length=10_000)]
Title = Annotated[str, Field(min_length=1, max_length=200)]


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Read(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EntityRead(Read):
    id: UUID
    created_at: datetime
    updated_at: datetime


class TaskDraftCreate(Request):
    description: Annotated[str, Field(min_length=1, max_length=32_000)]


class TaskDraftRead(EntityRead):
    business_id: UUID
    description: str
    card_id: UUID | None


class ClarifyingQuestionCreate(Request):
    field: CardField
    question: Content
    position: int = Field(ge=0)


class ClarifyingQuestionsCreate(Request):
    questions: list[ClarifyingQuestionCreate] = Field(min_length=3)

    @field_validator("questions")
    @classmethod
    def unique_positions(cls, questions):
        if len({question.position for question in questions}) != len(questions):
            raise ValueError("Question positions must be unique")
        return questions


class ClarifyingQuestionAnswer(Request):
    answer: Content


class ClarifyingQuestionRead(EntityRead):
    draft_id: UUID
    field: CardField
    question: str
    answer: str | None
    position: int


class CardFields(Request):
    # Missing data stays absent; low completeness must not block publication/proposals.
    context: Content | None = None
    data: Content | None = None
    expected_result: Content | None = None
    success_criteria: Content | None = None
    constraints: Content | None = None
    users: Content | None = None
    business_contact: Content | None = None


class TaskCardCreate(CardFields):
    title: Title


class TaskCardUpdate(CardFields):
    title: Title | None = None

    @field_validator("title")
    @classmethod
    def title_cannot_be_cleared(cls, value):
        if value is None:
            raise ValueError("Title cannot be null")
        return value


class TaskCardConfirm(Request):
    confirmed: Literal[True]


class RatingBreakdownRead(Read):
    context: int = Field(ge=0, le=20)
    data: int = Field(ge=0, le=20)
    expected_result: int = Field(ge=0, le=15)
    success_criteria: int = Field(ge=0, le=15)
    constraints: int = Field(ge=0, le=10)
    users: int = Field(ge=0, le=10)
    business_contact: int = Field(ge=0, le=10)

    @computed_field
    @property
    def total(self) -> int:
        return sum(getattr(self, name) for name in type(self).model_fields)

    @computed_field
    @property
    def readiness(self) -> Literal["черновик", "рабочая", "готовая", "приоритетная"]:
        if self.total < 40:
            return "черновик"
        if self.total < 70:
            return "рабочая"
        if self.total < 90:
            return "готовая"
        return "приоритетная"


class TaskCardRead(EntityRead):
    draft_id: UUID
    business_id: UUID
    title: str
    context: str | None
    data: str | None
    expected_result: str | None
    success_criteria: str | None
    constraints: str | None
    users: str | None
    business_contact: str | None
    confirmed_at: datetime | None
    rating: RatingBreakdownRead | None


class CatalogEntryRead(Read):
    task_id: UUID
    published_at: datetime
    task: TaskCardRead


class ProposalCreate(Request):
    team_id: UUID
    idea: Content
    plan: Content
    prototype_url: Annotated[HttpUrl, Field(max_length=2048)] | None = None


class ProposalRead(EntityRead):
    task_id: UUID
    team_id: UUID
    user_id: UUID
    idea: str
    plan: str
    prototype_url: str | None


class SelectionDecisionCreate(Request):
    # Required even when empty: selecting nobody must be an explicit choice.
    selected_proposal_ids: list[UUID]
    comment: Content | None = None

    @field_validator("selected_proposal_ids")
    @classmethod
    def unique_proposals(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Selected proposals must be unique")
        return value


class SelectionDecisionRead(EntityRead):
    task_id: UUID
    business_id: UUID
    selected_proposal_ids: list[UUID]
    comment: str | None
