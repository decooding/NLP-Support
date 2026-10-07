"""Observability package exports."""

from support_dispatcher.observability.metrics import (
    FALLBACK_REQUESTS_TOTAL,
    SYSTEM1_LATENCY_SECONDS,
    SYSTEM2_LATENCY_SECONDS,
    TICKET_REQUESTS_TOTAL,
    generate_trace_id,
    log_audit_event,
)

__all__ = [
    "FALLBACK_REQUESTS_TOTAL",
    "SYSTEM1_LATENCY_SECONDS",
    "SYSTEM2_LATENCY_SECONDS",
    "TICKET_REQUESTS_TOTAL",
    "generate_trace_id",
    "log_audit_event",
]
