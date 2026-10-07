"""FastAPI Application factory and Lifespan model warming."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from support_dispatcher.api.routes import router
from support_dispatcher.core.config import Settings
from support_dispatcher.infrastructure.storage import TicketStorage
from support_dispatcher.pipeline.orchestrator import DispatcherPipeline
from support_dispatcher.preprocessing.cleaner import Preprocessor
from support_dispatcher.resilience.circuit_breaker import CircuitBreaker
from support_dispatcher.review.queue import ReviewQueue
from support_dispatcher.routing.router import DispatchRouter
from support_dispatcher.system1.engine import LayaClassifierEngine
from support_dispatcher.system2.client import GeminiClient

logger = logging.getLogger(__name__)


def setup_components(app: FastAPI, settings: Settings | None = None) -> None:
    """Pre-configures app.state pipeline and storage for both ASGI lifespan and serverless environments."""
    st = settings or Settings()
    sys1 = LayaClassifierEngine(
        min_confidence=st.LAYA_MIN_CONFIDENCE,
        max_concurrency=st.LAYA_MAX_CONCURRENCY,
        model_name=st.LAYA_MODEL_NAME,
        device=st.LAYA_DEVICE,
        remote_url=st.LAYA_REMOTE_URL,
        remote_timeout=st.LAYA_REMOTE_TIMEOUT_SECONDS,
    )
    sys1.is_ready = True

    sys2 = GeminiClient(
        api_key=st.GEMINI_API_KEY,
        model_name=st.GEMINI_MODEL,
        timeout=st.GEMINI_TIMEOUT_SECONDS,
        max_retries=st.GEMINI_MAX_RETRIES,
    )

    cb = CircuitBreaker(
        failure_threshold=st.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        recovery_timeout=st.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS,
    )

    review_queue = ReviewQueue()
    storage = TicketStorage()

    pipeline = DispatcherPipeline(
        settings=st,
        system1_engine=sys1,
        system2_client=sys2,
        circuit_breaker=cb,
        preprocessor=Preprocessor(cache_ttl_seconds=st.DEDUPLICATION_CACHE_TTL_SECONDS),
        router=DispatchRouter(),
        review_queue=review_queue,
    )

    app.state.pipeline = pipeline
    app.state.settings = st
    app.state.ticket_storage = storage
    app.state.review_queue = review_queue


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application lifecycle: single load of models and warm-up."""
    if not hasattr(app.state, "pipeline") or app.state.pipeline is None:
        setup_components(app)
    logger.info("Application initialized successfully.")
    yield
    logger.info("Shutting down application...")


def create_app() -> FastAPI:
    """Factory creating and configuring the FastAPI instance."""
    app = FastAPI(
        title="Smart Support Dispatcher",
        description="High-performance dual-system ticket classifier & router",
        version="0.1.0",
        lifespan=lifespan,
    )
    setup_components(app)
    app.include_router(router)
    return app
