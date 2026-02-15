from fastapi.testclient import TestClient

from app.domain.models.diff import DiffResult
from app.domain.models.policy import (
    AutoCoverages,
    Endorsement,
    HomeCoverages,
    PolicySnapshot,
    PolicyType,
    RenewalPair,
)
from app.domain.models.review import ReviewResult, RiskLevel
from app.domain.services.portfolio_analyzer import analyze_portfolio
from app.main import app

client = TestClient(app)


def _make_review(
    policy_number: str,
    policy_type: PolicyType,
    premium: float,
    prior_premium: float,
    carrier: str = "TestCarrier",
    risk_level: RiskLevel = RiskLevel.REVIEW_RECOMMENDED,
    auto_coverages: AutoCoverages | None = None,
    home_coverages: HomeCoverages | None = None,
    endorsements: list[Endorsement] | None = None,
) -> ReviewResult:
    prior = PolicySnapshot(
        policy_number=policy_number,
        policy_type=policy_type,
        carrier=carrier,
        effective_date="2024-01-01",
        expiration_date="2025-01-01",
        premium=prior_premium,
        auto_coverages=auto_coverages if policy_type == PolicyType.AUTO else None,
        home_coverages=home_coverages if policy_type == PolicyType.HOME else None,
    )
    renewal = PolicySnapshot(
        policy_number=policy_number,
        policy_type=policy_type,
        carrier=carrier,
        effective_date="2025-01-01",
        expiration_date="2026-01-01",
        premium=premium,
        auto_coverages=auto_coverages if policy_type == PolicyType.AUTO else None,
        home_coverages=home_coverages if policy_type == PolicyType.HOME else None,
        endorsements=endorsements or [],
    )
    return ReviewResult(
        policy_number=policy_number,
        risk_level=risk_level,
        diff=DiffResult(policy_number=policy_number, changes=[], flags=[]),
        pair=RenewalPair(prior=prior, renewal=renewal),
    )


def _build_store(reviews: list[ReviewResult]) -> dict[str, ReviewResult]:
    return {r.policy_number: r for r in reviews}


def test_bundle_auto_home():
    auto = _make_review(
        "AUTO-001",
        PolicyType.AUTO,
        1200.0,
        1100.0,
        auto_coverages=AutoCoverages(),
    )
    home = _make_review(
        "HOME-001",
        PolicyType.HOME,
        2000.0,
        1900.0,
        home_coverages=HomeCoverages(),
    )
    store = _build_store([auto, home])
    result = analyze_portfolio(["AUTO-001", "HOME-001"], store)

    assert result.bundle_analysis.is_bundle is True
    assert result.bundle_analysis.has_auto is True
    assert result.bundle_analysis.has_home is True
    assert result.bundle_analysis.bundle_discount_eligible is True
    assert result.bundle_analysis.carrier_mismatch is False
    assert result.total_premium == 3200.0
    assert result.total_prior_premium == 3000.0
    assert len(result.client_policies) == 2


def test_auto_only_no_bundle():
    auto1 = _make_review(
        "AUTO-001",
        PolicyType.AUTO,
        1200.0,
        1100.0,
        auto_coverages=AutoCoverages(),
    )
    auto2 = _make_review(
        "AUTO-002",
        PolicyType.AUTO,
        800.0,
        750.0,
        auto_coverages=AutoCoverages(),
    )
    store = _build_store([auto1, auto2])
    result = analyze_portfolio(["AUTO-001", "AUTO-002"], store)

    assert result.bundle_analysis.is_bundle is False
    assert result.bundle_analysis.has_auto is True
    assert result.bundle_analysis.has_home is False


def test_duplicate_medical_detection():
    auto = _make_review(
        "AUTO-001",
        PolicyType.AUTO,
        1200.0,
        1100.0,
        auto_coverages=AutoCoverages(medical_payments=5000.0),
    )
    home = _make_review(
        "HOME-001",
        PolicyType.HOME,
        2000.0,
        1900.0,
        home_coverages=HomeCoverages(coverage_f_medical=5000.0),
    )
    store = _build_store([auto, home])
    result = analyze_portfolio(["AUTO-001", "HOME-001"], store)

    medical_flags = [f for f in result.cross_policy_flags if f.flag_type == "duplicate_medical"]
    assert len(medical_flags) == 1
    assert medical_flags[0].severity == "warning"


def test_unbundle_risk_high():
    auto = _make_review(
        "AUTO-001",
        PolicyType.AUTO,
        1200.0,
        1100.0,
        risk_level=RiskLevel.ACTION_REQUIRED,
        auto_coverages=AutoCoverages(),
    )
    home = _make_review(
        "HOME-001",
        PolicyType.HOME,
        2000.0,
        1900.0,
        risk_level=RiskLevel.NO_ACTION_NEEDED,
        home_coverages=HomeCoverages(),
    )
    store = _build_store([auto, home])
    result = analyze_portfolio(["AUTO-001", "HOME-001"], store)

    assert result.bundle_analysis.unbundle_risk == "high"


def test_premium_concentration():
    auto = _make_review(
        "AUTO-001",
        PolicyType.AUTO,
        500.0,
        480.0,
        auto_coverages=AutoCoverages(),
    )
    home = _make_review(
        "HOME-001",
        PolicyType.HOME,
        4500.0,
        4300.0,
        home_coverages=HomeCoverages(),
    )
    store = _build_store([auto, home])
    result = analyze_portfolio(["AUTO-001", "HOME-001"], store)

    concentration_flags = [
        f for f in result.cross_policy_flags if f.flag_type == "premium_concentration"
    ]
    assert len(concentration_flags) == 1
    assert concentration_flags[0].severity == "warning"
    assert "HOME-001" in concentration_flags[0].affected_policies


def test_high_portfolio_increase():
    auto = _make_review(
        "AUTO-001",
        PolicyType.AUTO,
        1500.0,
        1000.0,
        auto_coverages=AutoCoverages(),
    )
    home = _make_review(
        "HOME-001",
        PolicyType.HOME,
        2500.0,
        2000.0,
        home_coverages=HomeCoverages(),
    )
    store = _build_store([auto, home])
    # total: 4000, prior: 3000, change: +33.3%
    result = analyze_portfolio(["AUTO-001", "HOME-001"], store)

    increase_flags = [
        f for f in result.cross_policy_flags if f.flag_type == "high_portfolio_increase"
    ]
    assert len(increase_flags) == 1
    assert increase_flags[0].severity == "critical"


def test_single_policy_error():
    response = client.post(
        "/portfolio/analyze",
        json={"policy_numbers": ["AUTO-001"]},
    )
    assert response.status_code == 422


def test_missing_policy_error():
    from app.infra.deps import get_review_store as get_results_store

    store = get_results_store()
    store.clear()

    response = client.post(
        "/portfolio/analyze",
        json={"policy_numbers": ["FAKE-001", "FAKE-002"]},
    )
    assert response.status_code == 422
    assert "No review found" in response.json()["detail"]
