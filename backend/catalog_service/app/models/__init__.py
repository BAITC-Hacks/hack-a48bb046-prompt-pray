"""Import this package before Database.create_tables() to register all domain tables."""
from .domain import (
    CatalogEntry, ClarifyingQuestion, Proposal, RatingBreakdown,
    SelectionDecision, TaskCard, TaskDraft,
)

__all__ = [
    "CatalogEntry", "ClarifyingQuestion", "Proposal", "RatingBreakdown",
    "SelectionDecision", "TaskCard", "TaskDraft",
]
