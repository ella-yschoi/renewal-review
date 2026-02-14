import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.engine.differ import compute_diff
from app.engine.quote_generator import PROTECTED_FIELDS, generate_quotes
from app.engine.rules import flag_diff
from app.main import app
from app.models.policy import (
    AutoCoverages,
    HomeCoverages,
    PolicySnapshot,
    PolicyType,
    RenewalPair,
)

client = TestClient(app)
SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"


def _make_pair(
    policy_type: PolicyType,
    premium: float = 2000.0,
    auto_cov: AutoCoverages | None = None,
    home_cov: HomeCoverages | None = None,
    renewal_premium: float | None = None,
) -> RenewalPair:
    prior = PolicySnapshot(
        policy_number=f"TEST-{policy_type.value.upper()}-001",
        policy_type=policy_type,
        carrier="TestCarrier",
        effective_date="2024-01-01",
        expiration_date="2025-01-01",
        premium=premium,
        auto_coverages=auto_cov if policy_type == PolicyType.AUTO else None,
        home_coverages=home_cov if policy_type == PolicyType.HOME else None,
    )
    renewal = PolicySnapshot(
        policy_number=f"TEST-{policy_type.value.upper()}-001",
        policy_type=policy_type,
        carrier="TestCarrier",
        effective_date="2025-01-01",
        expiration_date="2026-01-01",
        premium=renewal_premium or premium * 1.15,
        auto_coverages=auto_cov if policy_type == PolicyType.AUTO else None,
        home_coverages=home_cov if policy_type == PolicyType.HOME else None,
    )
    return RenewalPair(prior=prior, renewal=renewal)


def _get_flagged_diff(pair: RenewalPair):
    diff = compute_diff(pair)
    return flag_diff(diff, pair)


def test_auto_all_strategies_applicable():
    cov = AutoCoverages(
        collision_deductible=500,
        comprehensive_deductible=250,
        medical_payments=5000,
        rental_reimbursement=True,
        roadside_assistance=True,
    )
    pair = _make_pair(PolicyType.AUTO, premium=2000, auto_cov=cov)
    diff = _get_flagged_diff(pair)
    quotes = generate_quotes(pair, diff)

    assert len(quotes) == 3
    assert quotes[0].estimated_savings_pct == 10.0
    assert quotes[1].estimated_savings_pct == 4.0
    assert quotes[2].estimated_savings_pct == 2.5


def test_home_all_strategies_applicable():
    cov = HomeCoverages(
        deductible=1000,
        water_backup=True,
        coverage_a_dwelling=300000,
        coverage_c_personal_property=200000,
    )
    pair = _make_pair(PolicyType.HOME, premium=3000, home_cov=cov)
    diff = _get_flagged_diff(pair)
    quotes = generate_quotes(pair, diff)

    assert len(quotes) == 3
    assert quotes[0].estimated_savings_pct == 12.5
    assert quotes[1].estimated_savings_pct == 3.0
    assert quotes[2].estimated_savings_pct == 4.0


def test_auto_already_optimized():
    cov = AutoCoverages(
        collision_deductible=1000,
        comprehensive_deductible=500,
        medical_payments=2000,
        rental_reimbursement=False,
        roadside_assistance=False,
    )
    pair = _make_pair(PolicyType.AUTO, auto_cov=cov)
    diff = _get_flagged_diff(pair)
    quotes = generate_quotes(pair, diff)

    assert quotes == []


def test_liability_fields_never_adjusted():
    cov = AutoCoverages(
        collision_deductible=500,
        comprehensive_deductible=250,
        medical_payments=5000,
        rental_reimbursement=True,
        roadside_assistance=True,
    )
    pair = _make_pair(PolicyType.AUTO, auto_cov=cov)
    diff = _get_flagged_diff(pair)
    quotes = generate_quotes(pair, diff)

    for quote in quotes:
        for adj in quote.adjustments:
            assert adj.field not in PROTECTED_FIELDS, (
                f"Protected field {adj.field} was adjusted in {quote.quote_id}"
            )


def test_no_flags_returns_empty():
    pair = _make_pair(
        PolicyType.AUTO,
        premium=1000,
        auto_cov=AutoCoverages(),
        renewal_premium=1000,
    )
    diff = _get_flagged_diff(pair)
    assert diff.flags == []
    quotes = generate_quotes(pair, diff)
    assert quotes == []


def test_existing_tests_regression():
    raw = json.loads((SAMPLES_DIR / "auto_pair.json").read_text())
    resp = client.post("/reviews/compare", json=raw)
    assert resp.status_code == 200


def test_route_auto_quote():
    raw = json.loads((SAMPLES_DIR / "auto_pair.json").read_text())
    resp = client.post("/quotes/generate", json=raw)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_route_home_quote():
    raw = json.loads((SAMPLES_DIR / "home_pair.json").read_text())
    resp = client.post("/quotes/generate", json=raw)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
