import pytest

from support_dispatcher.domain.models import (
    ClassificationResult,
    ProcessingSource,
    Ticket,
    TicketCategory,
    TicketStatus,
)
from support_dispatcher.routing.router import DispatchRouter


@pytest.mark.asyncio
async def test_dispatch_router():
    router = DispatchRouter()
    ticket = Ticket(ticket_id="T-RT-1", text="Тест маршрутизации")
    result = ClassificationResult(
        ticket_id="T-RT-1",
        category=TicketCategory.SED,
        confidence=0.95,
        source=ProcessingSource.SYSTEM1,
        status=TicketStatus.ROUTED,
        trace_id="trc-test",
        model_version="test",
    )

    routed = await router.route(ticket, result)
    assert routed.target_queue == "queue.service_desk.sed"
    assert routed.ticket_id == "T-RT-1"
    assert len(router.dispatched_history) == 1
