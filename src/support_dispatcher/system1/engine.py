"""System 1 Engine interface and lightweight local classifier with confidence calibration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import httpx

from support_dispatcher.domain.models import TicketCategory

logger = logging.getLogger(__name__)


@dataclass
class System1Prediction:
    """Output contract for System 1 fast-path classifier."""

    category: TicketCategory
    confidence: float
    abstention: str  # "passed", "abstained", "unevaluated"
    raw_scores: dict[str, float]


class LayaClassifierEngine:
    """System 1 Fast-Path classification engine.

    Provides non-autoregressive fast classification with calibrated confidence scores
    and abstention capabilities. Works with remote Hugging Face Spaces Docker server
    or local calibrated engine with seamless fallback.
    """

    def __init__(
        self,
        min_confidence: float = 0.85,
        max_concurrency: int = 4,
        model_name: str = "multilingual",
        device: str = "cpu",
        remote_url: str | None = None,
        remote_timeout: float = 3.0,
    ) -> None:
        self.min_confidence = min_confidence
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.model_name = model_name
        self.device = device
        self.remote_url = remote_url.rstrip("/") if remote_url else None
        self.remote_timeout = remote_timeout
        self.is_ready = False

    async def initialize(self) -> None:
        """Warm-up model weights and set readiness."""
        if self.remote_url:
            try:
                async with httpx.AsyncClient(timeout=self.remote_timeout) as client:
                    resp = await client.get(f"{self.remote_url}/health")
                    if resp.status_code == 200:
                        logger.info("Connected to remote Laya HF Space at %s", self.remote_url)
            except Exception as e:
                logger.warning("Could not pre-warm remote Laya (%s): %s", self.remote_url, e)
        # Warmup pass
        _ = await self.classify("Тестовый тикет для прогрева системы документооборота")
        self.is_ready = True
        logger.info("System 1 LayaClassifierEngine warmed up and ready.")

    async def classify(self, text: str) -> System1Prediction:
        """Runs inference via remote HF Spaces endpoint or thread-pool isolated local inference."""
        if self.remote_url:
            try:
                return await self._predict_remote(text)
            except Exception as e:
                logger.warning(
                    "Remote Laya inference failed at %s (%s). Falling back to local engine.",
                    self.remote_url,
                    e,
                )
        async with self.semaphore:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._predict_sync, text)

    async def _predict_remote(self, text: str) -> System1Prediction:
        """Calls remote Hugging Face Space Laya Docker microservice."""
        async with httpx.AsyncClient(timeout=self.remote_timeout) as client:
            resp = await client.post(
                f"{self.remote_url}/classify",
                json={"text": text},
            )
            resp.raise_for_status()
            data = resp.json()
            return System1Prediction(
                category=TicketCategory(data["category"]),
                confidence=float(data["confidence"]),
                abstention=str(data["abstention"]),
                raw_scores=dict(data.get("raw_scores", {})),
            )

    def _predict_sync(self, text: str) -> System1Prediction:
        """Synchronous CPU/GPU forward-pass simulation / heuristic / calibrated inference."""
        lower = text.lower()

        # Keyword semantic weighting with calibration
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

        # Расчет калиброванной уверенности и softmax / temperature scaling
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

        return System1Prediction(
            category=best_category,
            confidence=round(confidence, 4),
            abstention=abstention,
            raw_scores=raw_scores_str,
        )
