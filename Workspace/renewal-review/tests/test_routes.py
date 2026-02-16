from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200


def test_get_review_not_found():
    resp = client.get("/reviews/NONEXISTENT-999")
    assert resp.status_code == 404


def test_batch_run_returns_job_id():
    resp = client.post("/batch/run?sample=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "running"


def test_batch_job_status_not_found():
    resp = client.get("/batch/status/nonexistent")
    assert resp.status_code == 404
