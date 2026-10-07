"""Prometheus metrics, structured logging and request tracing."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from prometheus_client import Counter, Histogram

logger = logging.getLogger("support_dispatcher")

# Prometheus Metrics
TICKET_REQUESTS_TOTAL = Counter(
    "support_dispatcher_tickets_total",
    "Total tickets processed by status and source",
    ["status", "source", "category"],
)

FALLBACK_REQUESTS_TOTAL = Counter(
    "support_dispatcher_fallback_total",
    "Total tickets diverted from System 1 to System 2 or HITL",
    ["reason"],
)

SYSTEM1_LATENCY_SECONDS = Histogram(
    "support_dispatcher_system1_latency_seconds",
    "Inference latency for System 1 fast-path",
    buckets=[0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0],
)

SYSTEM2_LATENCY_SECONDS = Histogram(
    "support_dispatcher_system2_latency_seconds",
    "Inference latency for System 2 deep-path",
    buckets=[0.5, 1.0, 2.0, 3.5, 5.0, 10.0],
)


def generate_trace_id() -> str:
    """Generates a UUID-based correlation ID."""
    return f"trc-{uuid.uuid4().hex[:12]}"


def log_audit_event(
    trace_id: str,
    ticket_id: str,
    action: str,
    source: str,
    status: str,
    **kwargs: Any,
) -> None:
    """Logs structured telemetry metadata (ticket_id, category, status)."""
    extra_details = " ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(
        "AUDIT trace_id=%s ticket_id=%s action=%s source=%s status=%s %s",
        trace_id,
        ticket_id,
        action,
        source,
        status,
        extra_details,
    )
