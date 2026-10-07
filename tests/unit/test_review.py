from support_dispatcher.domain.models import (
    ClassificationResult,
    ProcessingSource,
    Ticket,
    TicketCategory,
    TicketStatus,
)
from support_dispatcher.review.queue import ReviewQueue


def test_review_queue_enqueue_and_resolve():
    rq = ReviewQueue()
    ticket = Ticket(ticket_id="T-REV-1", text="Странное неясное обращение")
    provisional = ClassificationResult(
        ticket_id="T-REV-1",
        category=TicketCategory.OTHER,
        confidence=0.3,
        source=ProcessingSource.MANUAL,
        status=TicketStatus.PENDING_MANUAL_REVIEW,
        trace_id="trc-test",
        model_version="test",
    )

    rq.enqueue(ticket, provisional)
    assert rq.size() == 1

    rq.resolve(ticket_id="T-REV-1", resolved_category="SED", operator_id="user_admin")
    assert rq.size() == 0
    assert len(rq._dataset_collector) == 1
    assert rq._dataset_collector[0]["category"] == "SED"
