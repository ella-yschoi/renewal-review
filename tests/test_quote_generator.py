import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.models.policy import (
    AutoCoverages,
    HomeCoverages,
    PolicySnapshot,
    PolicyType,
    RenewalPair,
)
from app.domain.services.differ import compute_diff
from app.domain.services.quote_generator import PROTECTED_FIELDS, generate_quotes
from app.domain.services.rules import flag_diff
from app.main import app

client = TestClient(app)
SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"


def _make_auto_pair(
    premium: float = 1356.0,
    collision_deductible: float = 500.0,
    comprehensive_deductible: float = 250.0,
    medical_payments: float = 5000.0,
    rental_reimbursement: bool = True,
    roadside_assistance: bool = True,
) -> RenewalPair:
    prior = PolicySnapshot(
        policy_number="TEST-AUTO-001",
        policy_type=PolicyType.AUTO,
        carrier="TestCarrier",
        effective_date="2024-01-01",
        expiration_date="2025-01-01",
        premium=1200.0,
        auto_coverages=AutoCoverages(),
    )
    renewal = PolicySnapshot(
        policy_number="TEST-AUTO-001",
        policy_type=PolicyType.AUTO,
        carrier="TestCarrier",
        effective_date="2025-01-01",
        expiration_date="2026-01-01",
        premium=premium,
        auto_coverages=AutoCoverages(
            collision_deductible=collision_deductible,
            comprehensive_deductible=comprehensive_deductible,
            medical_payments=medical_payments,
            rental_reimbursement=rental_reimbursement,
            roadside_assistance=roadside_assistance,
        ),
    )
    return RenewalPair(prior=prior, renewal=renewal)


def _make_home_pair(
    premium: float = 2952.0,
    deductible: float = 1000.0,
    water_backup: bool = True,
    coverage_a: float = 350000.0,
    coverage_c: float = 210000.0,
) -> RenewalPair:
    prior = PolicySnapshot(
        policy_number="TEST-HOME-001",
        policy_type=PolicyType.HOME,
        carrier="TestCarrier",
        effective_date="2024-01-01",
        expiration_date="2025-01-01",
        premium=2400.0,
        home_coverages=HomeCoverages(),
    )
    renewal = PolicySnapshot(
        policy_number="TEST-HOME-001",
        policy_type=PolicyType.HOME,
        carrier="TestCarrier",
        effective_date="2025-01-01",
        expiration_date="2026-01-01",
        premium=premium,
        home_coverages=HomeCoverages(
            deductible=deductible,
            water_backup=water_backup,
            coverage_a_dwelling=coverage_a,
            coverage_c_personal_property=coverage_c,
        ),
    )
    return RenewalPair(prior=prior, renewal=renewal)


def _diff_with_flags(pair: RenewalPair):
    diff = compute_diff(pair)
    return flag_diff(diff, pair)


# --- Test 1: Auto policy — all 3 strategies applicable ---


def test_auto_all_strategies():
    pair = _make_auto_pair()
    diff = _diff_with_flags(pair)

    quotes = generate_quotes(pair, diff)

    assert len(quotes) == 3
    strategies = {q.adjustments[0].strategy for q in quotes}
    assert strategies == {"raise_deductible", "drop_optional", "reduce_medical"}

    for q in quotes:
        assert q.estimated_savings_pct > 0
        assert q.estimated_savings_dollar > 0
        assert q.trade_off


# --- Test 2: Home policy — all 3 strategies applicable ---


def test_home_all_strategies():
    pair = _make_home_pair()
    diff = _diff_with_flags(pair)

    quotes = generate_quotes(pair, diff)

    assert len(quotes) == 3
    strategies = {q.adjustments[0].strategy for q in quotes}
    assert strategies == {"raise_deductible", "drop_water_backup", "reduce_personal_property"}

    for q in quotes:
        assert q.estimated_savings_pct > 0
        assert q.estimated_savings_dollar > 0


# --- Test 3: Already-optimized auto policy ---


def test_auto_already_optimized():
    pair = _make_auto_pair(
        collision_deductible=1000.0,
        comprehensive_deductible=500.0,
        medical_payments=2000.0,
        rental_reimbursement=False,
        roadside_assistance=False,
    )
    diff = _diff_with_flags(pair)

    quotes = generate_quotes(pair, diff)

    # all strategies should be skipped
    assert len(quotes) == 0


# --- Test 4: Protected fields never adjusted ---


def test_liability_fields_never_adjusted():
    pair = _make_auto_pair()
    diff = _diff_with_flags(pair)
    quotes = generate_quotes(pair, diff)

    for q in quotes:
        for adj in q.adjustments:
            assert adj.field not in PROTECTED_FIELDS

    home_pair = _make_home_pair()
    home_diff = _diff_with_flags(home_pair)
    home_quotes = generate_quotes(home_pair, home_diff)

    for q in home_quotes:
        for adj in q.adjustments:
            assert adj.field not in PROTECTED_FIELDS


# --- Test 5: No flags → empty list ---


def test_no_flags_returns_empty():
    # same premium, same everything → no flags → no quotes
    prior = PolicySnapshot(
        policy_number="TEST-AUTO-002",
        policy_type=PolicyType.AUTO,
        carrier="TestCarrier",
        effective_date="2024-01-01",
        expiration_date="2025-01-01",
        premium=1200.0,
        auto_coverages=AutoCoverages(),
    )
    renewal = PolicySnapshot(
        policy_number="TEST-AUTO-002",
        policy_type=PolicyType.AUTO,
        carrier="TestCarrier",
        effective_date="2025-01-01",
        expiration_date="2026-01-01",
        premium=1200.0,
        auto_coverages=AutoCoverages(),
    )
    pair = RenewalPair(prior=prior, renewal=renewal)
    diff = _diff_with_flags(pair)

    assert diff.flags == []
    quotes = generate_quotes(pair, diff)
    assert quotes == []


# --- Test 6: Existing tests regression (route integration) ---


def test_quote_route_auto():
    raw = json.loads((SAMPLES_DIR / "auto_pair.json").read_text())
    resp = client.post("/quotes/generate", json=raw)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for q in data:
        assert "quote_id" in q
        assert "adjustments" in q
        assert "estimated_savings_pct" in q


def test_quote_route_home():
    raw = json.loads((SAMPLES_DIR / "home_pair.json").read_text())
    resp = client.post("/quotes/generate", json=raw)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# --- Quote Personalization Tests ---


def test_personalize_quotes_with_mock():
    from app.adaptor.llm.mock import MockLLMClient
    from app.adaptor.llm.quote_advisor import personalize_quotes

    pair = _make_home_pair()
    diff = _diff_with_flags(pair)
    quotes = generate_quotes(pair, diff)
    assert len(quotes) > 0

    client_mock = MockLLMClient()
    personalized = personalize_quotes(client_mock, quotes, pair)
    matched = [q for q in personalized if q.broker_tip]
    assert len(matched) > 0
    assert any("quote_personalization" in call[1] for call in client_mock.calls)


def test_personalize_quotes_llm_error():
    from app.adaptor.llm.quote_advisor import personalize_quotes

    class ErrorClient:
        def complete(self, prompt: str, trace_name: str) -> dict:
            return {"error": "API unavailable"}

    pair = _make_auto_pair()
    diff = _diff_with_flags(pair)
    quotes = generate_quotes(pair, diff)
    original_tradeoffs = [q.trade_off for q in quotes]

    result = personalize_quotes(ErrorClient(), quotes, pair)
    assert [q.trade_off for q in result] == original_tradeoffs
    assert all(q.broker_tip == "" for q in result)


def test_personalize_quotes_empty_list():
    from app.adaptor.llm.mock import MockLLMClient
    from app.adaptor.llm.quote_advisor import personalize_quotes

    pair = _make_auto_pair()
    client_mock = MockLLMClient()
    result = personalize_quotes(client_mock, [], pair)
    assert result == []
    assert len(client_mock.calls) == 0


def test_broker_tip_default_empty():
    pair = _make_auto_pair()
    diff = _diff_with_flags(pair)
    quotes = generate_quotes(pair, diff)
    for q in quotes:
        assert q.broker_tip == ""


def test_personalize_quotes_malformed_response():
    from app.adaptor.llm.quote_advisor import personalize_quotes

    class MalformedClient:
        def complete(self, prompt: str, trace_name: str) -> dict:
            return {"quotes": [{"bad_field": "no quote_id"}]}

    pair = _make_home_pair()
    diff = _diff_with_flags(pair)
    quotes = generate_quotes(pair, diff)
    original_tradeoffs = [q.trade_off for q in quotes]

    result = personalize_quotes(MalformedClient(), quotes, pair)
    assert [q.trade_off for q in result] == original_tradeoffs
    assert all(q.broker_tip == "" for q in result)
