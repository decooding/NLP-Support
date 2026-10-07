"""API endpoints for ticket classification, ticketing system, health check, readiness, and metrics."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from prometheus_client import generate_latest

from support_dispatcher.domain.models import (
    ClassificationResult,
    Ticket,
    TicketCategory,
    TicketCreate,
    TicketRecord,
    TicketStatsResponse,
    TicketStatus,
    TicketUpdate,
)
from support_dispatcher.infrastructure.storage import TicketStorage
from support_dispatcher.pipeline.orchestrator import DispatcherPipeline
from support_dispatcher.review.queue import ReviewQueue

router = APIRouter()


def get_pipeline(request: Request) -> DispatcherPipeline:
    """Dependency injector extracting pipeline from app state."""
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline is not initialized.",
        )
    return pipeline  # type: ignore[no-any-return]


def get_storage(request: Request) -> TicketStorage:
    """Dependency injector extracting ticket storage from app state."""
    storage = getattr(request.app.state, "ticket_storage", None)
    if storage is None:
        # Fallback in-memory storage if initialized outside lifespan
        storage = TicketStorage()
    return storage


def get_review_queue(request: Request) -> ReviewQueue | None:
    """Dependency injector extracting review queue from app state."""
    return getattr(request.app.state, "review_queue", None)


# --- Core Classification ---


@router.post(
    "/classify", response_model=ClassificationResult, summary="Classify and route incoming ticket"
)
async def classify_ticket(
    ticket: Ticket,
    pipeline: DispatcherPipeline = Depends(get_pipeline),
) -> ClassificationResult:
    """Classifies a support ticket via Fast-Path (System 1) or Deep-Path (System 2 / Fallback)."""
    return await pipeline.process_ticket(ticket)


# --- Ticketing System Endpoints ---


@router.post(
    "/tickets",
    response_model=TicketRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Create and automatically classify a new support ticket",
)
async def create_ticket(
    payload: TicketCreate,
    pipeline: DispatcherPipeline = Depends(get_pipeline),
    storage: TicketStorage = Depends(get_storage),
) -> TicketRecord:
    """Accepts ticket text, classifies it via the dual-system pipeline, and registers it in the ticketing system."""
    ticket_id = payload.ticket_id or f"TICK-{uuid.uuid4().hex[:8].upper()}"
    ticket = Ticket(
        ticket_id=ticket_id,
        text=payload.text,
        metadata=payload.metadata,
    )

    result = await pipeline.process_ticket(ticket)
    now_iso = datetime.now(timezone.utc).isoformat()

    record = TicketRecord(
        ticket_id=ticket.ticket_id,
        text=ticket.text,
        metadata=ticket.metadata,
        category=result.category,
        confidence=result.confidence,
        source=result.source,
        status=result.status,
        trace_id=result.trace_id,
        model_version=result.model_version,
        draft_reply=result.draft_reply,
        created_at=now_iso,
        updated_at=now_iso,
    )
    return storage.save(record)


@router.get(
    "/tickets",
    response_model=list[TicketRecord],
    summary="List tickets with optional status and category filters",
)
async def list_tickets(
    status: TicketStatus | None = Query(default=None, description="Filter by status"),
    category: TicketCategory | None = Query(default=None, description="Filter by category"),
    limit: int = Query(default=50, ge=1, le=500, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    storage: TicketStorage = Depends(get_storage),
) -> list[TicketRecord]:
    """Returns a paginated list of tickets."""
    return storage.list(status=status, category=category, limit=limit, offset=offset)


@router.get(
    "/tickets/stats",
    response_model=TicketStatsResponse,
    summary="Get ticketing system aggregate metrics",
)
async def get_ticket_stats(
    storage: TicketStorage = Depends(get_storage),
) -> TicketStatsResponse:
    """Returns distribution of tickets by status, category, and resolution source."""
    return storage.get_stats()


@router.get(
    "/tickets/{ticket_id}",
    response_model=TicketRecord,
    summary="Get single ticket details by ID",
)
async def get_ticket(
    ticket_id: str,
    storage: TicketStorage = Depends(get_storage),
) -> TicketRecord:
    """Fetches a specific ticket record."""
    record = storage.get(ticket_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )
    return record


@router.patch(
    "/tickets/{ticket_id}",
    response_model=TicketRecord,
    summary="Update ticket status, category, or notes (Operator resolution)",
)
async def update_ticket(
    ticket_id: str,
    update: TicketUpdate,
    storage: TicketStorage = Depends(get_storage),
    review_queue: ReviewQueue | None = Depends(get_review_queue),
) -> TicketRecord:
    """Updates ticket status or category, recording operator feedback in HITL queue."""
    updated = storage.update(ticket_id, update)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )

    # If resolved by operator with category, synchronize with HITL review queue
    if update.category and update.resolved_by and review_queue:
        review_queue.resolve(ticket_id, update.category.value, update.resolved_by)

    return updated


@router.delete(
    "/tickets/{ticket_id}",
    summary="Delete a ticket by ID",
)
async def delete_ticket(
    ticket_id: str,
    storage: TicketStorage = Depends(get_storage),
) -> dict[str, str]:
    """Deletes a ticket from the system."""
    if not storage.delete(ticket_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )
    return {"status": "deleted", "ticket_id": ticket_id}


# --- System & Observability ---


@router.get("/health", summary="Liveness probe")
async def health_check() -> dict[str, str]:
    """Returns 200 OK indicating the service process is alive."""
    return {"status": "healthy"}


@router.get("/ready", summary="Readiness probe")
async def readiness_check(request: Request) -> dict[str, str]:
    """Returns 200 only when models are loaded and warmed up."""
    pipeline = getattr(request.app.state, "pipeline", None)
    if not pipeline or not pipeline.system1.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System 1 model not yet loaded or ready.",
        )
    return {"status": "ready"}


@router.get("/metrics", summary="Prometheus metrics")
async def metrics() -> Response:
    """Exposes Prometheus application metrics."""
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4")


__all__ = [
    "classify_ticket",
    "create_ticket",
    "delete_ticket",
    "get_pipeline",
    "get_review_queue",
    "get_storage",
    "get_ticket",
    "get_ticket_stats",
    "health_check",
    "list_tickets",
    "metrics",
    "readiness_check",
    "router",
    "update_ticket",
]
