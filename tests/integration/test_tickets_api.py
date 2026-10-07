"""Integration tests for the ticketing system API endpoints and Vercel entrypoint."""

import pytest
from fastapi.testclient import TestClient

from api.index import app as vercel_app
from support_dispatcher.api.app import create_app
from support_dispatcher.domain.models import TicketStatus


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_tickets_crud_flow(client: TestClient) -> None:
    # 1. Create a ticket (SED)
    resp_create = client.post(
        "/tickets",
        json={
            "text": "Входящее письмо не открывается в канцелярии СЭД",
            "metadata": {"source": "portal"},
        },
    )
    assert resp_create.status_code == 201
    ticket_data = resp_create.json()
    ticket_id = ticket_data["ticket_id"]
    assert ticket_id.startswith("TICK-")
    assert ticket_data["category"] == "SED"
    assert ticket_data["status"] == TicketStatus.ROUTED.value
    assert ticket_data["confidence"] >= 0.85

    # 2. Get ticket by ID
    resp_get = client.get(f"/tickets/{ticket_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["ticket_id"] == ticket_id

    # 3. List tickets
    resp_list = client.get("/tickets")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) >= 1

    # 4. Update ticket status (e.g. resolve by operator)
    resp_patch = client.patch(
        f"/tickets/{ticket_id}",
        json={
            "status": "RESOLVED",
            "operator_notes": "Инструкция отправлена заявителю",
            "resolved_by": "operator_42",
        },
    )
    assert resp_patch.status_code == 200
    updated = resp_patch.json()
    assert updated["status"] == "RESOLVED"
    assert updated["operator_notes"] == "Инструкция отправлена заявителю"

    # 5. Check stats
    resp_stats = client.get("/tickets/stats")
    assert resp_stats.status_code == 200
    stats = resp_stats.json()
    assert stats["total_tickets"] >= 1
    assert stats["by_status"].get("RESOLVED", 0) >= 1

    # 6. Delete ticket
    resp_del = client.delete(f"/tickets/{ticket_id}")
    assert resp_del.status_code == 200
    assert resp_del.json()["status"] == "deleted"

    # Verify 404 after deletion
    resp_not_found = client.get(f"/tickets/{ticket_id}")
    assert resp_not_found.status_code == 404


def test_vercel_app_instance() -> None:
    """Verifies that api/index.py creates a valid FastAPI app for Vercel Serverless."""
    assert vercel_app.title == "Smart Support Dispatcher"
    with TestClient(vercel_app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}
