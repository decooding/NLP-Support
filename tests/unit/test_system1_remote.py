"""Unit tests for System 1 Laya remote HF Spaces integration and fallback."""

import pytest
import respx
from httpx import Response

from support_dispatcher.domain.models import TicketCategory
from support_dispatcher.system1.engine import LayaClassifierEngine


@pytest.mark.asyncio
@respx.mock
async def test_laya_remote_prediction_success() -> None:
    remote_url = "https://example-laya.hf.space"
    respx.post(f"{remote_url}/classify").mock(
        return_value=Response(
            200,
            json={
                "category": "SED",
                "confidence": 0.96,
                "abstention": "passed",
                "raw_scores": {"SED": 5.0},
            },
        )
    )

    engine = LayaClassifierEngine(remote_url=remote_url)
    pred = await engine.classify("Тестовый документ")

    assert pred.category == TicketCategory.SED
    assert pred.confidence == 0.96
    assert pred.abstention == "passed"


@pytest.mark.asyncio
@respx.mock
async def test_laya_remote_prediction_fallback_to_local_on_error() -> None:
    remote_url = "https://example-laya.hf.space"
    respx.post(f"{remote_url}/classify").mock(
        return_value=Response(500, text="Internal Server Error")
    )

    engine = LayaClassifierEngine(remote_url=remote_url)
    # On remote failure, it must fall back to local heuristic without throwing
    pred = await engine.classify("Служебная записка канцелярия СЭД")

    assert pred.category == TicketCategory.SED
    assert pred.confidence >= 0.85
    assert pred.abstention == "passed"
