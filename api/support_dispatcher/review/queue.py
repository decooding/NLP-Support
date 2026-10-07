"""Human-in-the-Loop review queue and corrected dataset collector."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from support_dispatcher.domain.models import ClassificationResult, Ticket

logger = logging.getLogger(__name__)


@dataclass
class ReviewItem:
    """Item placed in the HITL queue for manual triage."""

    ticket: Ticket
    provisional_result: ClassificationResult
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_category: str | None = None
    resolved_by: str | None = None


class ReviewQueue:
    """Manages tickets waiting for manual human review and collects corrected annotations."""

    def __init__(self) -> None:
        self._queue: dict[str, ReviewItem] = {}
        self._dataset_collector: list[dict[str, str]] = []

    def enqueue(self, ticket: Ticket, provisional: ClassificationResult) -> None:
        """Puts a low-confidence or failed ticket into the HITL queue."""
        self._queue[ticket.ticket_id] = ReviewItem(ticket=ticket, provisional_result=provisional)
        logger.info("Ticket %s enqueued for Human Review.", ticket.ticket_id)

    def resolve(self, ticket_id: str, resolved_category: str, operator_id: str) -> None:
        """Resolves a review item and records it into retraining dataset."""
        if ticket_id in self._queue:
            item = self._queue.pop(ticket_id)
            item.resolved_category = resolved_category
            item.resolved_by = operator_id
            self._dataset_collector.append(
                {
                    "ticket_id": ticket_id,
                    "text": item.ticket.text,
                    "category": resolved_category,
                    "operator": operator_id,
                }
            )
            logger.info("Ticket %s resolved by %s as %s", ticket_id, operator_id, resolved_category)

    def size(self) -> int:
        """Returns pending review queue length."""
        return len(self._queue)
