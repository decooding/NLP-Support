"""End-to-end pipeline orchestrator for Smart Support Dispatcher."""

from __future__ import annotations

import logging
import time

from support_dispatcher.core.config import Settings
from support_dispatcher.domain.models import (
    ClassificationResult,
    ProcessingSource,
    Ticket,
    TicketCategory,
    TicketStatus,
)
from support_dispatcher.observability.metrics import (
    FALLBACK_REQUESTS_TOTAL,
    SYSTEM1_LATENCY_SECONDS,
    SYSTEM2_LATENCY_SECONDS,
    TICKET_REQUESTS_TOTAL,
    generate_trace_id,
    log_audit_event,
)
from support_dispatcher.preprocessing.cleaner import Preprocessor
from support_dispatcher.resilience.circuit_breaker import CircuitBreaker
from support_dispatcher.review.queue import ReviewQueue
from support_dispatcher.routing.router import DispatchRouter
from support_dispatcher.system1.engine import LayaClassifierEngine
from support_dispatcher.system2.client import GeminiClient

logger = logging.getLogger(__name__)


class DispatcherPipeline:
    """Orchestrates System 1 -> System 2 -> HITL / Routing flow."""

    def __init__(
        self,
        settings: Settings,
        system1_engine: LayaClassifierEngine,
        system2_client: GeminiClient,
        circuit_breaker: CircuitBreaker,
        preprocessor: Preprocessor,
        router: DispatchRouter,
        review_queue: ReviewQueue,
    ) -> None:
        self.settings = settings
        self.system1 = system1_engine
        self.system2 = system2_client
        self.circuit_breaker = circuit_breaker
        self.preprocessor = preprocessor
        self.router = router
        self.review_queue = review_queue

    async def process_ticket(
        self, ticket: Ticket, trace_id: str | None = None
    ) -> ClassificationResult:
        """Processes an incoming ticket following the strict DoD execution protocol."""
        tid = trace_id or generate_trace_id()

        # 1. Validation & Deduplication
        cleaned_text = self.preprocessor.validate_and_clean(ticket)
        if self.preprocessor.is_duplicate(ticket.ticket_id):
            logger.info(
                "Ticket %s is duplicate, returning deduplicated acknowledgement.", ticket.ticket_id
            )
            # При повторном запросе возвращаем уже зафиксированный статус без повторного инференса
            return ClassificationResult(
                ticket_id=ticket.ticket_id,
                category=TicketCategory.GENERAL_INQUIRY,
                confidence=1.0,
                source=ProcessingSource.SYSTEM1,
                status=TicketStatus.ROUTED,
                trace_id=tid,
                model_version="deduplicated",
            )

        # 2. System 1 Fast-Path
        t0 = time.monotonic()
        sys1_pred = await self.system1.classify(cleaned_text)
        sys1_dur = time.monotonic() - t0
        SYSTEM1_LATENCY_SECONDS.observe(sys1_dur)

        # Проверка порога уверенности System 1 и воздержания
        if (
            sys1_pred.confidence >= self.settings.LAYA_MIN_CONFIDENCE
            and sys1_pred.abstention == "passed"
            and sys1_pred.category != TicketCategory.OTHER
        ):
            result = ClassificationResult(
                ticket_id=ticket.ticket_id,
                category=sys1_pred.category,
                confidence=sys1_pred.confidence,
                source=ProcessingSource.SYSTEM1,
                status=TicketStatus.ROUTED,
                trace_id=tid,
                model_version=f"laya-{self.settings.LAYA_MODEL_NAME}",
            )
            await self.router.route(ticket, result)
            TICKET_REQUESTS_TOTAL.labels(
                status=result.status.value,
                source=result.source.value,
                category=result.category.value,
            ).inc()
            log_audit_event(
                trace_id=tid,
                ticket_id=ticket.ticket_id,
                action="CLASSIFIED",
                source=result.source.value,
                status=result.status.value,
                category=result.category.value,
            )
            return result

        # 3. Fallback to System 2: Deep-Path Invocation through Circuit Breaker
        FALLBACK_REQUESTS_TOTAL.labels(reason="system1_low_confidence_or_abstained").inc()

        try:
            t1 = time.monotonic()
            sys2_resp = await self.circuit_breaker.call(lambda: self.system2.classify(cleaned_text))
            sys2_dur = time.monotonic() - t1
            SYSTEM2_LATENCY_SECONDS.observe(sys2_dur)

            # Проверка уверенности System 2
            if (
                sys2_resp.confidence >= self.settings.GEMINI_MIN_CONFIDENCE
                and sys2_resp.category != TicketCategory.OTHER
            ):
                result = ClassificationResult(
                    ticket_id=ticket.ticket_id,
                    category=sys2_resp.category,
                    confidence=sys2_resp.confidence,
                    source=ProcessingSource.SYSTEM2,
                    status=TicketStatus.ROUTED,
                    trace_id=tid,
                    model_version=self.settings.GEMINI_MODEL,
                    reasoning=sys2_resp.reasoning,
                    draft_reply=sys2_resp.draft_reply,
                )
                await self.router.route(ticket, result)
                TICKET_REQUESTS_TOTAL.labels(
                    status=result.status.value,
                    source=result.source.value,
                    category=result.category.value,
                ).inc()
                log_audit_event(
                    trace_id=tid,
                    ticket_id=ticket.ticket_id,
                    action="CLASSIFIED",
                    source=result.source.value,
                    status=result.status.value,
                    category=result.category.value,
                )
                return result

        except Exception as exc:
            logger.warning(
                "System 2 invocation failed or circuit breaker open for ticket %s: %s",
                ticket.ticket_id,
                exc,
            )

        # 5. Fallback to Human-in-the-Loop (HITL)
        fallback_cat = (
            sys1_pred.category
            if sys1_pred.category != TicketCategory.OTHER
            else TicketCategory.OTHER
        )
        result = ClassificationResult(
            ticket_id=ticket.ticket_id,
            category=fallback_cat,
            confidence=sys1_pred.confidence,
            source=ProcessingSource.MANUAL,
            status=TicketStatus.PENDING_MANUAL_REVIEW,
            trace_id=tid,
            model_version="hitl-fallback",
            reasoning="Uncertain prediction or System 2 unavailable, queued for human verification",
        )
        self.review_queue.enqueue(ticket, result)
        TICKET_REQUESTS_TOTAL.labels(
            status=result.status.value,
            source=result.source.value,
            category=result.category.value,
        ).inc()
        log_audit_event(
            trace_id=tid,
            ticket_id=ticket.ticket_id,
            action="HITL_ENQUEUED",
            source=result.source.value,
            status=result.status.value,
            category=result.category.value,
        )
        return result
