import pytest

from support_dispatcher.domain.models import TicketCategory
from support_dispatcher.system2.client import GeminiClassificationResponse, GeminiClient


@pytest.mark.asyncio
async def test_system2_mock_client_schema():
    client = GeminiClient(api_key="mock_key")
    resp = await client.classify("Прошу разъяснить приказ об отпуске сотрудника.")
    assert isinstance(resp, GeminiClassificationResponse)
    assert resp.category == TicketCategory.DKA
    assert resp.confidence >= 0.70
    assert resp.reasoning != ""
    assert resp.draft_reply is not None
