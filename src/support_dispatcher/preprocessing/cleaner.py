"""Ticket preprocessing, text normalization, and deduplication engine."""

from __future__ import annotations

import re
import time

from support_dispatcher.core.config import ValidationError
from support_dispatcher.domain.models import Ticket


class Preprocessor:
    """Cleans incoming ticket texts and manages deduplication cache."""

    def __init__(self, cache_ttl_seconds: int = 3600) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        # In-memory deduplication cache: ticket_id -> timestamp
        self._seen_tickets: dict[str, float] = {}

    def validate_and_clean(self, ticket: Ticket) -> str:
        """Validates ticket length and strips abnormal whitespace and zero-width characters."""
        if not ticket.ticket_id.strip():
            raise ValidationError("Ticket ID cannot be empty.")

        text = ticket.text.strip()
        if not text:
            raise ValidationError("Ticket text cannot be empty.")

        # Убираем невидимые управляющие символы и нормализуем пробелы
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def is_duplicate(self, ticket_id: str) -> bool:
        """Checks if a ticket with this ID was recently processed."""
        now = time.monotonic()
        # Clean expired entries
        expired_keys = [
            k for k, t in self._seen_tickets.items() if now - t > self.cache_ttl_seconds
        ]
        for k in expired_keys:
            del self._seen_tickets[k]

        if ticket_id in self._seen_tickets:
            return True

        self._seen_tickets[ticket_id] = now
        return False
