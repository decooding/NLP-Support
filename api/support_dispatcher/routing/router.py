"""Routing adapters: forwarding classified tickets to Service Desk and webhooks."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from support_dispatcher.domain.models import ClassificationResult, Ticket

logger = logging.getLogger(__name__)


@dataclass
class RoutedMessage:
    """Dispatched payload record."""

    target_queue: str
    ticket_id: str
    category: str
    confidence: float
    source: str


class DispatchRouter:
    """Routes successfully classified tickets to corresponding queues."""

    CATEGORY_QUEUE_MAP: dict[str, str] = {
        "SED": "queue.service_desk.sed",
        "DKA": "queue.service_desk.hr",
        "TECHNICAL_BUG": "queue.engineering.bugs",
        "FEATURE_REQUEST": "queue.product.features",
        "GENERAL_INQUIRY": "queue.support.first_line",
        "OTHER": "queue.support.manual_triage",
    }

    def __init__(self) -> None:
        self.dispatched_history: list[RoutedMessage] = []

    async def route(self, ticket: Ticket, result: ClassificationResult) -> RoutedMessage:
        """Determines the destination queue and sends the ticket."""
        queue_name = self.CATEGORY_QUEUE_MAP.get(
            result.category.value, "queue.support.manual_triage"
        )
        message = RoutedMessage(
            target_queue=queue_name,
            ticket_id=ticket.ticket_id,
            category=result.category.value,
            confidence=result.confidence,
            source=result.source.value,
        )
        self.dispatched_history.append(message)
        logger.info(
            "Ticket %s routed to %s (category: %s, confidence: %.2f, source: %s)",
            ticket.ticket_id,
            queue_name,
            result.category.value,
            result.confidence,
            result.source.value,
        )
        return message
