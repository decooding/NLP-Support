"""Unit tests for the Hugging Face Spaces Laya classifier standalone application."""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Import the hf_space app directly
HF_SPACE_DIR = Path(__file__).resolve().parents[2] / "hf_space"
if str(HF_SPACE_DIR) not in sys.path:
    sys.path.insert(0, str(HF_SPACE_DIR))

import app as hf_app  # noqa: E402


def test_hf_space_health() -> None:
    client = TestClient(hf_app.app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "laya-system1-classifier"


def test_hf_space_classify_sed() -> None:
    client = TestClient(hf_app.app)
    response = client.post(
        "/classify",
        json={"text": "Входящее письмо не проходит регистрацию в канцелярии СЭД"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "SED"
    assert data["confidence"] >= 0.85
    assert data["abstention"] == "passed"


def test_hf_space_classify_empty() -> None:
    client = TestClient(hf_app.app)
    response = client.post("/classify", json={"text": "   "})
    assert response.status_code == 400
