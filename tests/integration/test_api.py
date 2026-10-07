import pytest
from httpx import ASGITransport, AsyncClient

from support_dispatcher.api.app import create_app, lifespan
from support_dispatcher.domain.models import ProcessingSource, TicketCategory, TicketStatus


@pytest.mark.asyncio
async def test_full_api_integration():
    app = create_app()

    async with lifespan(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Health check
            res_health = await client.get("/health")
            assert res_health.status_code == 200
            assert res_health.json()["status"] == "healthy"

            # 2. Readiness check
            res_ready = await client.get("/ready")
            assert res_ready.status_code == 200
            assert res_ready.json()["status"] == "ready"

            # 3. Classify Fast-Path (SED)
            res_sed = await client.post(
                "/classify",
                json={
                    "ticket_id": "TCK-101",
                    "text": "Ошибка регистрации входящего письма в СЭД канцелярии",
                    "metadata": {},
                },
            )
            assert res_sed.status_code == 200
            data_sed = res_sed.json()
            assert data_sed["category"] == TicketCategory.SED.value
            assert data_sed["source"] == ProcessingSource.SYSTEM1.value
            assert data_sed["status"] == TicketStatus.ROUTED.value
            assert data_sed["confidence"] >= 0.85

            # 4. Fallback to System 2 (Ambiguous text)
            res_fallback = await client.post(
                "/classify",
                json={
                    "ticket_id": "TCK-102",
                    "text": "Сотрудник Сидоров Иван, телефон +7 912 345-67-89, имеет вопрос по расчету отпуска",
                    "metadata": {},
                },
            )
            assert res_fallback.status_code == 200
            data_fallback = res_fallback.json()
            assert data_fallback["category"] == TicketCategory.DKA.value
            assert data_fallback["source"] in (
                ProcessingSource.SYSTEM2.value,
                ProcessingSource.SYSTEM1.value,
            )

            # 5. Deduplication scenario
            res_dedup = await client.post(
                "/classify",
                json={
                    "ticket_id": "TCK-101",
                    "text": "Повторный вебхук с тем же ID",
                    "metadata": {},
                },
            )
            assert res_dedup.status_code == 200
            assert res_dedup.json()["model_version"] == "deduplicated"

            # 6. Metrics endpoint
            res_metrics = await client.get("/metrics")
            assert res_metrics.status_code == 200
            assert "support_dispatcher_tickets_total" in res_metrics.text
