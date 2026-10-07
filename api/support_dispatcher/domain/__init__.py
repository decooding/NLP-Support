"""Domain package exports."""

from support_dispatcher.domain.models import (
    CATEGORY_DESCRIPTIONS,
    ClassificationResult,
    ProcessingSource,
    Ticket,
    TicketCategory,
    TicketStatus,
)

__all__ = [
    "CATEGORY_DESCRIPTIONS",
    "ClassificationResult",
    "ProcessingSource",
    "Ticket",
    "TicketCategory",
    "TicketStatus",
]
