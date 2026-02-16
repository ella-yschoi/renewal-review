from datetime import UTC, datetime

import pytest
from starlette.testclient import TestClient

from app.domain.models.analytics import BatchRunRecord
from app.domain.models.diff import DiffFlag, DiffResult, FieldChange
from app.domain.models.review import ReviewResult, RiskLevel
from app.domain.services.analytics import compute_broker_metrics, compute_trends
from app.infra.deps import get_history_store, get_review_store
from app.main import app


def _make_record(
    job_id: str = "test-1",
    total: int = 10,
    no_action_needed: int = 5,
    review_recommended: int = 3,
    action_required: int = 1,
    urgent_review: int = 1,
    processing_time_ms: float = 100.0,
    created_at: datetime | None = None,
) -> BatchRunRecord:
    return BatchRunRecord(
        job_id=job_id,
        total=total,
        no_action_needed=no_action_needed,
        review_recommended=review_recommended,
        action_required=action_required,
        urgent_review=urgent_review,
        processing_time_ms=processing_time_ms,
        created_at=created_at or datetime.now(UTC),
    )


def _make_review(
    policy_number: str = "POL-1",
    risk_level: RiskLevel = RiskLevel.REVIEW_RECOMMENDED,
    flags: list[DiffFlag] | None = None,
    broker_contacted: bool = False,
    quote_generated: bool = False,
    reviewed_at: datetime | None = None,
) -> ReviewResult:
    return ReviewResult(
        policy_number=policy_number,
        risk_level=risk_level,
        diff=DiffResult(
            policy_number=policy_number,
            flags=flags or [],
            changes=[FieldChange(field="test", prior_value="a", renewal_value="b")],
        ),
        broker_contacted=broker_contacted,
        quote_generated=quote_generated,
        reviewed_at=reviewed_at,
    )


def test_compute_trends_empty():
    result = compute_trends([])
    assert result.total_runs == 0
    assert result.total_policies_reviewed == 0
    assert result.risk_distribution == {
        "no_action_needed": 0,
        "review_recommended": 0,
        "action_required": 0,
        "urgent_review": 0,
    }
    assert result.trends == []


def test_compute_trends_single_record():
    record = _make_record()
    result = compute_trends([record])
    assert result.total_runs == 1
    assert result.total_policies_reviewed == 10
    assert result.risk_distribution["urgent_review"] == 1
    assert len(result.trends) == 1


def test_compute_trends_multiple_records():
    records = [
        _make_record(
            job_id="a",
            total=10,
            no_action_needed=5,
            review_recommended=3,
            action_required=1,
            urgent_review=1,
            processing_time_ms=100.0,
        ),
        _make_record(
            job_id="b",
            total=20,
            no_action_needed=10,
            review_recommended=5,
            action_required=3,
            urgent_review=2,
            processing_time_ms=200.0,
        ),
        _make_record(
            job_id="c",
            total=15,
            no_action_needed=8,
            review_recommended=4,
            action_required=2,
            urgent_review=1,
            processing_time_ms=150.0,
        ),
    ]
    result = compute_trends(records)
    assert result.total_runs == 3
    assert result.total_policies_reviewed == 45
    assert result.risk_distribution["no_action_needed"] == 23
    assert result.risk_distribution["urgent_review"] == 4
    assert len(result.trends) == 1


def test_compute_broker_metrics_empty():
    result = compute_broker_metrics([])
    assert result.total == 0
    assert result.pending == 0
    assert result.contact_needed == 0
    assert result.contacted == 0
    assert result.quotes_generated == 0
    assert result.reviewed == 0


def test_compute_broker_metrics_with_total_policies():
    reviews = [
        _make_review("P1", flags=[DiffFlag.PREMIUM_INCREASE_HIGH], reviewed_at=datetime.now(UTC)),
    ]
    result = compute_broker_metrics(reviews, total_policies=100)
    assert result.total == 100
    assert result.pending == 99
    assert result.contact_needed == 1


def test_compute_broker_metrics_mixed():
    now = datetime.now(UTC)
    reviews = [
        _make_review("P1", flags=[DiffFlag.PREMIUM_INCREASE_HIGH], reviewed_at=now),
        _make_review(
            "P2",
            flags=[DiffFlag.COVERAGE_DROPPED],
            broker_contacted=True,
            quote_generated=True,
            reviewed_at=now,
        ),
        _make_review("P3", flags=[], reviewed_at=now),
        _make_review(
            "P4",
            flags=[DiffFlag.SR22_FILING],
            broker_contacted=True,
            reviewed_at=now,
        ),
    ]
    result = compute_broker_metrics(reviews)
    assert result.total == 4
    assert result.pending == 0
    assert result.contact_needed == 1  # P1: has flags, not contacted
    assert result.contacted == 2  # P2, P4
    assert result.quotes_generated == 1  # P2
    assert result.reviewed == 4


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


def test_analytics_broker_route():
    now = datetime.now(UTC)
    client = TestClient(app)
    review_store = get_review_store()
    review_store.clear()
    review_store["P1"] = _make_review(
        "P1",
        flags=[DiffFlag.PREMIUM_INCREASE_HIGH],
        reviewed_at=now,
    )
    review_store["P2"] = _make_review("P2", broker_contacted=True, reviewed_at=now)

    response = client.get("/analytics/broker")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert data["pending"] == data["total"] - 2
    assert data["contact_needed"] == 1
    assert data["contacted"] == 1

    review_store.clear()


def test_history_batch_limit(_clear_history: None):
    store = get_history_store()
    for i in range(105):
        store.append(_make_record(job_id=f"job-{i}"))
    assert len(store) == 100
    assert store[0].job_id == "job-5"
    assert store[-1].job_id == "job-104"
