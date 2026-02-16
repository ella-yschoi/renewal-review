import copy

from hypothesis import given, settings
from hypothesis import strategies as st

from app.domain.models.policy import (
    AutoCoverages,
    Endorsement,
    HomeCoverages,
    PolicySnapshot,
    RenewalPair,
    Vehicle,
)
from app.domain.services.differ import (
    compute_diff,
    diff_auto_coverages,
    diff_endorsements,
    diff_home_coverages,
    diff_vehicles,
)
from app.domain.services.parser import parse_pair


def test_identical_auto_pair_no_changes(auto_pair_raw: dict):
    raw = copy.deepcopy(auto_pair_raw)
    raw["renewal"] = copy.deepcopy(raw["prior"])
    pair = parse_pair(raw)
    diff = compute_diff(pair)
    assert len(diff.changes) == 0


def test_identical_home_pair_no_changes(home_pair_raw: dict):
    raw = copy.deepcopy(home_pair_raw)
    raw["renewal"] = copy.deepcopy(raw["prior"])
    pair = parse_pair(raw)
    diff = compute_diff(pair)
    assert len(diff.changes) == 0


def test_premium_change_detected(auto_pair: RenewalPair):
    diff = compute_diff(auto_pair)
    premium_changes = [c for c in diff.changes if c.field == "premium"]
    assert len(premium_changes) == 1
    assert premium_changes[0].change_pct == 13.0


def test_vehicle_added(auto_pair: RenewalPair):
    diff = compute_diff(auto_pair)
    added = [c for c in diff.changes if c.field == "vehicle_added"]
    assert len(added) == 1
    assert "Tesla" in added[0].renewal_value


def test_endorsement_added_and_description_changed(auto_pair: RenewalPair):
    diff = compute_diff(auto_pair)
    endorse_changes = [c for c in diff.changes if "endorsement" in c.field]
    assert len(endorse_changes) >= 1


def test_home_coverage_changes(home_pair: RenewalPair):
    diff = compute_diff(home_pair)
    dwelling = [c for c in diff.changes if c.field == "coverage_a_dwelling"]
    assert len(dwelling) == 1
    assert float(dwelling[0].renewal_value) == 371000.0


def test_home_endorsement_removed(home_pair: RenewalPair):
    diff = compute_diff(home_pair)
    removed = [c for c in diff.changes if c.field == "endorsement_removed"]
    assert len(removed) == 1
    assert "HO 04 95" in removed[0].prior_value


def test_water_backup_dropped(home_pair: RenewalPair):
    diff = compute_diff(home_pair)
    wb = [c for c in diff.changes if c.field == "water_backup"]
    assert len(wb) == 1
    assert wb[0].prior_value == "True"
    assert wb[0].renewal_value == "False"


def test_diff_auto_coverages_none():
    assert diff_auto_coverages(None, None) == []
    assert diff_auto_coverages(AutoCoverages(), None) == []


def test_diff_home_coverages_none():
    assert diff_home_coverages(None, None) == []
    assert diff_home_coverages(HomeCoverages(), None) == []


def test_diff_vehicles_empty():
    prior = PolicySnapshot(
        policy_number="T",
        policy_type="auto",
        carrier="X",
        effective_date="2024-01-01",
        expiration_date="2025-01-01",
        premium=100,
    )
    renewal = copy.deepcopy(prior)
    assert diff_vehicles(prior, renewal) == []


def test_diff_endorsements_premium_change():
    prior = PolicySnapshot(
        policy_number="T",
        policy_type="auto",
        carrier="X",
        effective_date="2024-01-01",
        expiration_date="2025-01-01",
        premium=100,
        endorsements=[Endorsement(code="E1", description="Test", premium=50)],
    )
    renewal = prior.model_copy(deep=True)
    renewal.endorsements[0].premium = 75
    changes = diff_endorsements(prior, renewal)
    assert any("endorsement_premium" in c.field for c in changes)


# --- Hypothesis property-based tests ---


@given(
    prior_premium=st.floats(min_value=100, max_value=100000, allow_nan=False),
    renewal_premium=st.floats(min_value=100, max_value=100000, allow_nan=False),
)
@settings(max_examples=200)
def test_premium_pct_calculation(prior_premium: float, renewal_premium: float):
    prior = PolicySnapshot(
        policy_number="HYP-001",
        policy_type="auto",
        carrier="X",
        effective_date="2024-01-01",
        expiration_date="2025-01-01",
        premium=prior_premium,
    )
    renewal = prior.model_copy(deep=True)
    renewal.premium = renewal_premium
    pair = RenewalPair(prior=prior, renewal=renewal)
    diff = compute_diff(pair)

    if prior_premium == renewal_premium:
        assert len(diff.changes) == 0
    else:
        premium_changes = [c for c in diff.changes if c.field == "premium"]
        assert len(premium_changes) == 1
        expected_pct = round((renewal_premium - prior_premium) / prior_premium * 100, 2)
        assert premium_changes[0].change_pct == expected_pct


@given(n_vehicles=st.integers(min_value=0, max_value=5))
@settings(max_examples=50)
def test_identical_vehicles_no_diff(n_vehicles: int):
    vehicles = [
        Vehicle(vin=f"VIN{i:017d}", year=2020, make="Make", model="Model")
        for i in range(n_vehicles)
    ]
    prior = PolicySnapshot(
        policy_number="HYP-V",
        policy_type="auto",
        carrier="X",
        effective_date="2024-01-01",
        expiration_date="2025-01-01",
        premium=1000,
        vehicles=vehicles,
    )
    renewal = prior.model_copy(deep=True)
    pair = RenewalPair(prior=prior, renewal=renewal)
    diff = compute_diff(pair)
    vehicle_changes = [c for c in diff.changes if "vehicle" in c.field]
    assert len(vehicle_changes) == 0
