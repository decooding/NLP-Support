"""Unit tests for the TicketStorage infrastructure component."""

from datetime import datetime, timezone

from support_dispatcher.domain.models import (
    ProcessingSource,
    TicketCategory,
    TicketRecord,
    TicketStatus,
    TicketUpdate,
)
from support_dispatcher.infrastructure.storage import TicketStorage


def test_ticket_storage_crud() -> None:
    storage = TicketStorage()
    now = datetime.now(timezone.utc).isoformat()

    record = TicketRecord(
        ticket_id="TICK-001",
        text="Проблема с входящим письмом в канцелярии",
        metadata={"priority": "high"},
        category=TicketCategory.SED,
        confidence=0.95,
        source=ProcessingSource.SYSTEM1,
        status=TicketStatus.ROUTED,
        trace_id="tr-001",
        model_version="laya-v1",
        created_at=now,
        updated_at=now,
    )

    # Save & Get
    storage.save(record)
    fetched = storage.get("TICK-001")
    assert fetched is not None
    assert fetched.ticket_id == "TICK-001"
    assert fetched.category == TicketCategory.SED

    # List & Filter
    all_tickets = storage.list()
    assert len(all_tickets) == 1

    sed_tickets = storage.list(category=TicketCategory.SED)
    assert len(sed_tickets) == 1

    dka_tickets = storage.list(category=TicketCategory.DKA)
    assert len(dka_tickets) == 0

    # Update
    updated = storage.update(
        "TICK-001",
        TicketUpdate(status=TicketStatus.RESOLVED, operator_notes="Обработано оператором"),
    )
    assert updated is not None
    assert updated.status == TicketStatus.RESOLVED
    assert updated.operator_notes == "Обработано оператором"

    # Stats
    stats = storage.get_stats()
    assert stats.total_tickets == 1
    assert stats.by_status.get(TicketStatus.RESOLVED.value) == 1
    assert stats.by_category.get(TicketCategory.SED.value) == 1

    # Delete
    assert storage.delete("TICK-001") is True
    assert storage.get("TICK-001") is None
    assert storage.delete("TICK-001") is False
