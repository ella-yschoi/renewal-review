from datetime import UTC, datetime

import pytest
from starlette.testclient import TestClient

from app.engine.analytics import compute_trends
from app.main import app
from app.models.analytics import BatchRunRecord
from app.routes.analytics import get_history_store


def _make_record(
    job_id: str = "test-1",
    total: int = 10,
    low: int = 5,
    medium: int = 3,
    high: int = 1,
    critical: int = 1,
    processing_time_ms: float = 100.0,
    created_at: datetime | None = None,
) -> BatchRunRecord:
    return BatchRunRecord(
        job_id=job_id,
        total=total,
        low=low,
        medium=medium,
        high=high,
        critical=critical,
        processing_time_ms=processing_time_ms,
        created_at=created_at or datetime.now(UTC),
    )


def test_compute_trends_empty():
    result = compute_trends([])
    assert result.total_runs == 0
    assert result.total_policies_reviewed == 0
    assert result.avg_processing_time_ms == 0.0
    assert result.risk_distribution == {"low": 0, "medium": 0, "high": 0, "critical": 0}
    assert result.trends == []


def test_compute_trends_single_record():
    record = _make_record()
    result = compute_trends([record])
    assert result.total_runs == 1
    assert result.total_policies_reviewed == 10
    assert result.avg_processing_time_ms == 100.0
    assert result.risk_distribution["critical"] == 1
    assert len(result.trends) == 1


def test_compute_trends_multiple_records():
    records = [
        _make_record(
            job_id="a",
            total=10,
            low=5,
            medium=3,
            high=1,
            critical=1,
            processing_time_ms=100.0,
        ),
        _make_record(
            job_id="b",
            total=20,
            low=10,
            medium=5,
            high=3,
            critical=2,
            processing_time_ms=200.0,
        ),
        _make_record(
            job_id="c",
            total=15,
            low=8,
            medium=4,
            high=2,
            critical=1,
            processing_time_ms=150.0,
        ),
    ]
    result = compute_trends(records)
    assert result.total_runs == 3
    assert result.total_policies_reviewed == 45
    assert result.avg_processing_time_ms == 150.0
    assert result.risk_distribution["low"] == 23
    assert result.risk_distribution["critical"] == 4
    assert len(result.trends) == 1


@pytest.fixture
def _clear_history():
    store = get_history_store()
    store.clear()
    yield
    store.clear()


def test_analytics_history_route(_clear_history: None):
    client = TestClient(app)
    response = client.get("/analytics/history")
    assert response.status_code == 200
    assert response.json() == []


def test_analytics_trends_route(_clear_history: None):
    client = TestClient(app)
    store = get_history_store()
    store.append(_make_record())

    response = client.get("/analytics/trends")
    assert response.status_code == 200
    data = response.json()
    assert data["total_runs"] == 1
    assert data["total_policies_reviewed"] == 10
