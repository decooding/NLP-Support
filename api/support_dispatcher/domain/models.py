"""Domain models, taxonomy enums, and system constants for Smart Support Dispatcher."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TicketCategory(str, Enum):
    """Taxonomy of ticket categories according to DoD."""

    SED = "SED"
    DKA = "DKA"
    TECHNICAL_BUG = "TECHNICAL_BUG"
    FEATURE_REQUEST = "FEATURE_REQUEST"
    GENERAL_INQUIRY = "GENERAL_INQUIRY"
    OTHER = "OTHER"


CATEGORY_DESCRIPTIONS: dict[TicketCategory, str] = {
    TicketCategory.SED: "Проблемы с системой электронного документооборота (входящие, исходящие, служебные письма).",
    TicketCategory.DKA: "Проблемы с кадровыми процессами (приказы, отпуска, командировки, штатное расписание, личные дела, кадровое делопроизводство).",
    TicketCategory.TECHNICAL_BUG: "Ошибки сервиса, 5xx-ошибки, баги интерфейса, сбои синхронизации, не относящиеся к СЭД или кадровым процессам.",
    TicketCategory.FEATURE_REQUEST: "Предложения по доработке, запросы нового функционала.",
    TicketCategory.GENERAL_INQUIRY: "Общие вопросы, консультации, не требующие инженерного вмешательства.",
    TicketCategory.OTHER: "Обращение не подходит ни под одну категорию (всегда уходит на ручную проверку).",
}


class ProcessingSource(str, Enum):
    """Source that resolved the ticket."""

    SYSTEM1 = "system1"
    SYSTEM2 = "system2"
    MANUAL = "manual"


class TicketStatus(str, Enum):
    """Routing and lifecycle status of the ticket."""

    ROUTED = "ROUTED"
    PENDING_MANUAL_REVIEW = "PENDING_MANUAL_REVIEW"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class Ticket(BaseModel):
    """Incoming support ticket model."""

    ticket_id: str = Field(..., description="Unique ticket identifier")
    text: str = Field(..., min_length=1, description="Raw ticket text")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary ticket metadata")


class ClassificationResult(BaseModel):
    """Classification response contract according to DoD."""

    ticket_id: str = Field(..., description="Unique ticket identifier")
    category: TicketCategory = Field(..., description="Assigned category from taxonomy")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Calibrated confidence score")
    source: ProcessingSource = Field(..., description="Origin of classification decision")
    status: TicketStatus = Field(..., description="Final processing status")
    trace_id: str = Field(..., description="Distributed tracing identifier")
    model_version: str = Field(..., description="Version of the model that classified the ticket")
    reasoning: str | None = Field(
        default=None, description="Optional reasoning chain from System 2 or fallback notes"
    )
    draft_reply: str | None = Field(
        default=None, description="Optional draft response for support operators"
    )


class TicketCreate(BaseModel):
    """Payload to create a new ticket in the ticketing system."""

    text: str = Field(..., min_length=1, description="Ticket issue description")
    ticket_id: str | None = Field(default=None, description="Optional explicit ticket ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata tags")


class TicketRecord(BaseModel):
    """Stored ticket record in the ticketing system."""

    ticket_id: str = Field(..., description="Unique ticket identifier")
    text: str = Field(..., description="Original raw ticket text")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Ticket metadata")
    category: TicketCategory = Field(..., description="Current category assigned to the ticket")
    confidence: float = Field(..., description="Confidence score")
    source: ProcessingSource = Field(..., description="Source of classification")
    status: TicketStatus = Field(..., description="Current ticket lifecycle status")
    trace_id: str = Field(..., description="Distributed tracing identifier")
    model_version: str = Field(..., description="Model version")
    draft_reply: str | None = Field(default=None, description="Draft response")
    operator_notes: str | None = Field(default=None, description="Operator notes")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class TicketUpdate(BaseModel):
    """Payload to update an existing ticket (operator triage/resolution)."""

    status: TicketStatus | None = Field(default=None, description="New status")
    category: TicketCategory | None = Field(default=None, description="Corrected category")
    operator_notes: str | None = Field(default=None, description="Notes or resolution message")
    resolved_by: str | None = Field(default=None, description="Operator identifier")


class TicketStatsResponse(BaseModel):
    """Aggregated metrics for the ticketing system."""

    total_tickets: int = Field(..., description="Total number of registered tickets")
    by_status: dict[str, int] = Field(..., description="Count of tickets per status")
    by_category: dict[str, int] = Field(..., description="Count of tickets per category")
    by_source: dict[str, int] = Field(..., description="Count of tickets per processing source")

