import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200


def test_compare_auto():
    raw = json.loads((SAMPLES_DIR / "auto_pair.json").read_text())
    resp = client.post("/reviews/compare", json=raw)
    assert resp.status_code == 200
    data = resp.json()
    assert data["policy_number"] == "AUTO-2024-001"
    assert "risk_level" in data
    assert len(data["diff"]["changes"]) > 0


def test_compare_home():
    raw = json.loads((SAMPLES_DIR / "home_pair.json").read_text())
    resp = client.post("/reviews/compare", json=raw)
    assert resp.status_code == 200
    data = resp.json()
    assert data["policy_number"] == "HOME-2024-001"


def test_get_review_after_compare():
    raw = json.loads((SAMPLES_DIR / "auto_pair.json").read_text())
    client.post("/reviews/compare", json=raw)
    resp = client.get("/reviews/AUTO-2024-001")
    assert resp.status_code == 200
    assert resp.json()["policy_number"] == "AUTO-2024-001"


def test_get_review_not_found():
    resp = client.get("/reviews/NONEXISTENT-999")
    assert resp.status_code == 404


def test_batch_summary_none_before_run():
    resp = client.get("/batch/summary")
    assert resp.status_code == 200
