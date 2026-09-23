"""Catalog persistence. Cross-service identities deliberately have no foreign keys."""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Table,
    Text, UniqueConstraint, Uuid, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TaskDraft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "task_drafts"
    __table_args__ = (CheckConstraint("locale IN ('ru', 'kk', 'en')", name="ck_task_drafts_locale"),)

    business_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    description: Mapped[str] = mapped_column(Text)
    locale: Mapped[str] = mapped_column(String(2), nullable=False, default="ru", server_default="ru")
    questions: Mapped[list["ClarifyingQuestion"]] = relationship(
        back_populates="draft", cascade="all, delete-orphan", order_by="ClarifyingQuestion.position"
    )
    card: Mapped["TaskCard | None"] = relationship(back_populates="draft")

    @property
    def card_id(self) -> uuid.UUID | None:
        return self.card.id if self.card else None


class ClarifyingQuestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clarifying_questions"
    __table_args__ = (
        UniqueConstraint("draft_id", "position"),
        CheckConstraint("position >= 0"),
        CheckConstraint("field IN ('context', 'data', 'expected_result', 'success_criteria', "
                        "'constraints', 'users', 'business_contact')"),
    )

    draft_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_drafts.id"), index=True)
    field: Mapped[str] = mapped_column(String(32))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    draft: Mapped[TaskDraft] = relationship(back_populates="questions")


class TaskCard(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "task_cards"
    __table_args__ = (CheckConstraint("version >= 1", name="ck_task_cards_version"),)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    draft_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_drafts.id"), unique=True)
    business_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    title: Mapped[str] = mapped_column(String(200))
    topic: Mapped[str | None] = mapped_column(String(32))
    context: Mapped[str | None] = mapped_column(Text)
    data: Mapped[str | None] = mapped_column(Text)
    expected_result: Mapped[str | None] = mapped_column(Text)
    success_criteria: Mapped[str | None] = mapped_column(Text)
    constraints: Mapped[str | None] = mapped_column(Text)
    users: Mapped[str | None] = mapped_column(Text)
    business_contact: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    draft: Mapped[TaskDraft] = relationship(back_populates="card")
    rating: Mapped["RatingBreakdown | None"] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    catalog_entry: Mapped["CatalogEntry | None"] = relationship(back_populates="task")
    proposals: Mapped[list["Proposal"]] = relationship(back_populates="task")
    decisions: Mapped[list["SelectionDecision"]] = relationship(back_populates="task")


class RatingBreakdown(TimestampMixin, Base):
    """One snapshot per card; services must refresh it in the card's transaction."""
    __tablename__ = "rating_breakdowns"
    __table_args__ = tuple(
        CheckConstraint(f"{field} BETWEEN 0 AND {maximum}")
        for field, maximum in (
            ("context", 20), ("data", 20), ("expected_result", 15),
            ("success_criteria", 15), ("constraints", 10), ("users", 10),
            ("business_contact", 10),
        )
    )

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_cards.id"), primary_key=True)
    context: Mapped[int] = mapped_column(Integer, default=0)
    data: Mapped[int] = mapped_column(Integer, default=0)
    expected_result: Mapped[int] = mapped_column(Integer, default=0)
    success_criteria: Mapped[int] = mapped_column(Integer, default=0)
    constraints: Mapped[int] = mapped_column(Integer, default=0)
    users: Mapped[int] = mapped_column(Integer, default=0)
    business_contact: Mapped[int] = mapped_column(Integer, default=0)
    task: Mapped[TaskCard] = relationship(back_populates="rating")


class CatalogEntry(Base):
    __tablename__ = "catalog_entries"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_cards.id"), primary_key=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    task: Mapped[TaskCard] = relationship(back_populates="catalog_entry")


decision_proposals = Table(
    "selection_decision_proposals", Base.metadata,
    Column("decision_id", ForeignKey("selection_decisions.id"), primary_key=True),
    Column("proposal_id", ForeignKey("proposals.id"), primary_key=True),
)

decision_rejections = Table(
    "selection_decision_rejections", Base.metadata,
    Column("decision_id", ForeignKey("selection_decisions.id"), primary_key=True),
    Column("proposal_id", ForeignKey("proposals.id"), primary_key=True),
)


class Proposal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "proposals"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_cards.id"), index=True)
    team_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    idea: Mapped[str] = mapped_column(Text)
    plan: Mapped[str] = mapped_column(Text)
    prototype_url: Mapped[str | None] = mapped_column(String(2048))
    task: Mapped[TaskCard] = relationship(back_populates="proposals")


class SelectionDecision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Explicit decision history; an empty proposals collection means choose nobody."""
    __tablename__ = "selection_decisions"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_cards.id"), index=True)
    business_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    comment: Mapped[str | None] = mapped_column(Text)
    task: Mapped[TaskCard] = relationship(back_populates="decisions")
    selected_proposals: Mapped[list[Proposal]] = relationship(secondary=decision_proposals)
    rejected_proposals: Mapped[list[Proposal]] = relationship(secondary=decision_rejections)

    @property
    def selected_proposal_ids(self) -> list[uuid.UUID]:
        return [proposal.id for proposal in self.selected_proposals]

    @property
    def rejected_proposal_ids(self) -> list[uuid.UUID]:
        return [proposal.id for proposal in self.rejected_proposals]
