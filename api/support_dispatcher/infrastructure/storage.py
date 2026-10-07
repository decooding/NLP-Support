"""In-memory and persistent storage adapters for the support ticketing system."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from threading import RLock

from support_dispatcher.domain.models import (
    TicketCategory,
    TicketRecord,
    TicketStatsResponse,
    TicketStatus,
    TicketUpdate,
)

logger = logging.getLogger(__name__)


class TicketStorage:
    """Thread-safe storage for support tickets with querying and aggregation."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._tickets: dict[str, TicketRecord] = {}

    def save(self, record: TicketRecord) -> TicketRecord:
        """Saves or updates a ticket record."""
        with self._lock:
            self._tickets[record.ticket_id] = record
            logger.debug("Stored ticket %s with status %s", record.ticket_id, record.status)
            return record

    def get(self, ticket_id: str) -> TicketRecord | None:
        """Retrieves a ticket by its ID."""
        with self._lock:
            return self._tickets.get(ticket_id)

    def list(
        self,
        status: TicketStatus | None = None,
        category: TicketCategory | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TicketRecord]:
        """Lists tickets with optional status and category filtering."""
        with self._lock:
            results = list(self._tickets.values())
            if status is not None:
                results = [t for t in results if t.status == status]
            if category is not None:
                results = [t for t in results if t.category == category]

            # Sort by creation time descending
            results.sort(key=lambda t: t.created_at, reverse=True)
            return results[offset : offset + limit]

    def update(self, ticket_id: str, update: TicketUpdate) -> TicketRecord | None:
        """Updates ticket lifecycle status, category, or notes."""
        with self._lock:
            record = self._tickets.get(ticket_id)
            if record is None:
                return None

            now_iso = datetime.now(timezone.utc).isoformat()
            updated_data = record.model_dump()
            updated_data["updated_at"] = now_iso

            if update.status is not None:
                updated_data["status"] = update.status
            if update.category is not None:
                updated_data["category"] = update.category
            if update.operator_notes is not None:
                updated_data["operator_notes"] = update.operator_notes

            new_record = TicketRecord(**updated_data)
            self._tickets[ticket_id] = new_record
            return new_record

    def delete(self, ticket_id: str) -> bool:
        """Removes a ticket from storage."""
        with self._lock:
            if ticket_id in self._tickets:
                del self._tickets[ticket_id]
                return True
            return False

    def count(self) -> int:
        """Returns total number of stored tickets."""
        with self._lock:
            return len(self._tickets)

    def get_stats(self) -> TicketStatsResponse:
        """Computes aggregate distribution statistics for tickets."""
        with self._lock:
            total = len(self._tickets)
            status_counts = Counter(t.status.value for t in self._tickets.values())
            category_counts = Counter(t.category.value for t in self._tickets.values())
            source_counts = Counter(t.source.value for t in self._tickets.values())

            return TicketStatsResponse(
                total_tickets=total,
                by_status=dict(status_counts),
                by_category=dict(category_counts),
                by_source=dict(source_counts),
            )

    def clear(self) -> None:
        """Clears all records in storage."""
        with self._lock:
            self._tickets.clear()
