import pytest

from support_dispatcher.core.config import Settings
from support_dispatcher.domain.models import ProcessingSource, Ticket, TicketStatus
from support_dispatcher.pipeline.orchestrator import DispatcherPipeline
from support_dispatcher.preprocessing.cleaner import Preprocessor
from support_dispatcher.resilience.circuit_breaker import CircuitBreaker
from support_dispatcher.review.queue import ReviewQueue
from support_dispatcher.routing.router import DispatchRouter
from support_dispatcher.system1.engine import LayaClassifierEngine
from support_dispatcher.system2.client import GeminiClient


@pytest.mark.asyncio
async def test_pipeline_fallback_to_hitl_when_system2_fails():
    settings = Settings(LAYA_MIN_CONFIDENCE=0.99)  # Force System 1 abstention
    sys1 = LayaClassifierEngine(min_confidence=0.99)
    await sys1.initialize()

    # Broken System 2 client that always throws
    class FailingGeminiClient(GeminiClient):
        async def classify(self, text: str):
            raise RuntimeError("Gemini Down")

    sys2 = FailingGeminiClient(api_key="mock")
    cb = CircuitBreaker()
    prep = Preprocessor()
    router = DispatchRouter()
    review_q = ReviewQueue()

    pipeline = DispatcherPipeline(
        settings=settings,
        system1_engine=sys1,
        system2_client=sys2,
        circuit_breaker=cb,
        preprocessor=prep,
        router=router,
        review_queue=review_q,
    )

    ticket = Ticket(ticket_id="T-FAIL-1", text="Непонятное обращение требующее System 2")
    res = await pipeline.process_ticket(ticket)

    assert res.status == TicketStatus.PENDING_MANUAL_REVIEW
    assert res.source == ProcessingSource.MANUAL
    assert review_q.size() == 1
