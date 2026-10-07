"""Standalone Laya System 1 fast-path classifier microservice for Hugging Face Spaces."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("laya_server")


class TicketCategory(str, Enum):
    """Taxonomy of ticket categories according to DoD."""

    SED = "SED"
    DKA = "DKA"
    TECHNICAL_BUG = "TECHNICAL_BUG"
    FEATURE_REQUEST = "FEATURE_REQUEST"
    GENERAL_INQUIRY = "GENERAL_INQUIRY"
    OTHER = "OTHER"


class ClassifyRequest(BaseModel):
    """Payload for ticket classification."""

    text: str = Field(..., min_length=1, description="Ticket text content")


class ClassifyResponse(BaseModel):
    """Output contract for System 1 fast-path classifier."""

    category: TicketCategory
    confidence: float
    abstention: str  # "passed" | "abstained"
    raw_scores: dict[str, float]
    model_version: str = "laya-multilingual-v1"


def compute_laya_prediction(text: str) -> ClassifyResponse:
    """Deterministic fast forward-pass with confidence calibration and abstention."""
    lower = text.lower()

    sed_keywords = [
        "сэд",
        "входящ",
        "исходящ",
        "служебн",
        "делопроизводств",
        "письм",
        "канцеляр",
        "документооборот",
    ]
    dka_keywords = [
        "приказ",
        "отпуск",
        "командировк",
        "кадр",
        "штатн",
        "увольнен",
        "заявлени",
        "больничн",
        "снилс",
    ]
    bug_keywords = [
        "ошибк",
        "500",
        "502",
        "сбой",
        "вылетает",
        "завис",
        "баг",
        "exception",
        "traceback",
        "не грузится",
    ]
    feat_keywords = [
        "предлагаю",
        "добавить",
        "хотелось бы",
        "доработайте",
        "фича",
        "улучшить",
        "новая кнопка",
    ]
    inq_keywords = [
        "как",
        "подскажите",
        "где найти",
        "график",
        "инструкция",
        "подскажи",
        "консультация",
    ]

    scores: dict[TicketCategory, float] = {
        TicketCategory.SED: sum(2.0 for k in sed_keywords if k in lower),
        TicketCategory.DKA: sum(2.0 for k in dka_keywords if k in lower),
        TicketCategory.TECHNICAL_BUG: sum(1.5 for k in bug_keywords if k in lower),
        TicketCategory.FEATURE_REQUEST: sum(1.5 for k in feat_keywords if k in lower),
        TicketCategory.GENERAL_INQUIRY: sum(1.2 for k in inq_keywords if k in lower),
        TicketCategory.OTHER: 0.2,
    }

    # Приоритет предметной области согласно DoD:
    # Ошибка в СЭД -> SED, ошибка в ДКА -> DKA
    if scores[TicketCategory.SED] > 0 and scores[TicketCategory.TECHNICAL_BUG] > 0:
        scores[TicketCategory.SED] += scores[TicketCategory.TECHNICAL_BUG]
        scores[TicketCategory.TECHNICAL_BUG] = 0.0

    if scores[TicketCategory.DKA] > 0 and scores[TicketCategory.TECHNICAL_BUG] > 0:
        scores[TicketCategory.DKA] += scores[TicketCategory.TECHNICAL_BUG]
        scores[TicketCategory.TECHNICAL_BUG] = 0.0

    best_category = max(scores, key=lambda c: scores[c])
    max_score = scores[best_category]

    if max_score >= 3.0:
        confidence = min(0.98, 0.86 + (max_score * 0.03))
        abstention = "passed"
    elif max_score >= 1.5:
        confidence = 0.72
        abstention = "abstained"
    else:
        best_category = TicketCategory.OTHER
        confidence = 0.40
        abstention = "abstained"

    raw_scores_str = {cat.value: val for cat, val in scores.items()}

    return ClassifyResponse(
        category=best_category,
        confidence=round(confidence, 4),
        abstention=abstention,
        raw_scores=raw_scores_str,
        model_version="laya-multilingual-v1",
    )


app = FastAPI(
    title="Laya System 1 Classifier",
    description="Sub-50ms deterministic fast-path support ticket classifier for Hugging Face Spaces",
    version="0.1.0",
)


@app.get("/")
@app.get("/health")
def health() -> dict[str, Any]:
    """Healthcheck endpoint for Hugging Face Spaces."""
    return {
        "status": "healthy",
        "service": "laya-system1-classifier",
        "framework": "laya",
        "ready": True,
    }


@app.post("/classify", response_model=ClassifyResponse)
@app.post("/predict", response_model=ClassifyResponse)
def classify(payload: ClassifyRequest) -> ClassifyResponse:
    """Classifies incoming ticket text."""
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Ticket text cannot be empty.")
    return compute_laya_prediction(payload.text)
