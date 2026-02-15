from app.config import settings
from app.domain.models.diff import DiffFlag
from app.domain.models.policy import (
    HomeCoverages,
    PolicySnapshot,
    RenewalPair,
)
from app.domain.services.differ import compute_diff
from app.domain.services.rules import flag_diff

PREMIUM_THRESHOLD_HIGH = settings.rules.premium_high_pct
PREMIUM_THRESHOLD_CRITICAL = settings.rules.premium_critical_pct


def _make_pair(prior_premium: float, renewal_premium: float, **kwargs) -> RenewalPair:
    prior = PolicySnapshot(
        policy_number="RULE-001",
        policy_type=kwargs.get("policy_type", "auto"),
        carrier=kwargs.get("prior_carrier", "CarrierA"),
        effective_date="2024-01-01",
        expiration_date="2025-01-01",
        premium=prior_premium,
    )
    renewal = prior.model_copy(deep=True)
    renewal.premium = renewal_premium
    renewal.carrier = kwargs.get("renewal_carrier", prior.carrier)
    return RenewalPair(prior=prior, renewal=renewal)


def test_premium_below_high_threshold():
    pair = _make_pair(1000, 1000 * (1 + PREMIUM_THRESHOLD_HIGH / 100) - 0.01)
    diff = compute_diff(pair)
    result = flag_diff(diff, pair)
    assert DiffFlag.PREMIUM_INCREASE_HIGH not in result.flags
    assert DiffFlag.PREMIUM_INCREASE_CRITICAL not in result.flags


def test_premium_at_high_threshold():
    pair = _make_pair(1000, 1000 * (1 + PREMIUM_THRESHOLD_HIGH / 100))
    diff = compute_diff(pair)
    result = flag_diff(diff, pair)
    assert DiffFlag.PREMIUM_INCREASE_HIGH in result.flags
    assert DiffFlag.PREMIUM_INCREASE_CRITICAL not in result.flags


def test_premium_below_critical_threshold():
    pair = _make_pair(1000, 1000 * (1 + PREMIUM_THRESHOLD_CRITICAL / 100) - 0.01)
    diff = compute_diff(pair)
    result = flag_diff(diff, pair)
    assert DiffFlag.PREMIUM_INCREASE_CRITICAL not in result.flags


def test_premium_at_critical_threshold():
    pair = _make_pair(1000, 1000 * (1 + PREMIUM_THRESHOLD_CRITICAL / 100))
    diff = compute_diff(pair)
    result = flag_diff(diff, pair)
    assert DiffFlag.PREMIUM_INCREASE_CRITICAL in result.flags


def test_premium_decrease():
    pair = _make_pair(1000, 900)
    diff = compute_diff(pair)
    result = flag_diff(diff, pair)
    assert DiffFlag.PREMIUM_DECREASE in result.flags


def test_carrier_change():
    pair = _make_pair(1000, 1000, prior_carrier="OldCo", renewal_carrier="NewCo")
    diff = compute_diff(pair)
    result = flag_diff(diff, pair)
    assert DiffFlag.CARRIER_CHANGE in result.flags


def test_no_flags_identical():
    pair = _make_pair(1000, 1000)
    diff = compute_diff(pair)
    result = flag_diff(diff, pair)
    assert len(result.flags) == 0


def test_vehicle_added_flag(auto_pair: RenewalPair):
    diff = compute_diff(auto_pair)
    result = flag_diff(diff, auto_pair)
    assert DiffFlag.VEHICLE_ADDED in result.flags


def test_endorsement_added_flag(auto_pair: RenewalPair):
    diff = compute_diff(auto_pair)
    result = flag_diff(diff, auto_pair)
    assert DiffFlag.ENDORSEMENT_ADDED in result.flags


def test_coverage_added_flag(auto_pair: RenewalPair):
    diff = compute_diff(auto_pair)
    result = flag_diff(diff, auto_pair)
    assert DiffFlag.COVERAGE_ADDED in result.flags


def test_deductible_increase_flag(home_pair: RenewalPair):
    diff = compute_diff(home_pair)
    result = flag_diff(diff, home_pair)
    assert DiffFlag.DEDUCTIBLE_INCREASE in result.flags


def test_endorsement_removed_flag(home_pair: RenewalPair):
    diff = compute_diff(home_pair)
    result = flag_diff(diff, home_pair)
    assert DiffFlag.ENDORSEMENT_REMOVED in result.flags


def test_coverage_dropped_flag(home_pair: RenewalPair):
    diff = compute_diff(home_pair)
    result = flag_diff(diff, home_pair)
    assert DiffFlag.COVERAGE_DROPPED in result.flags


def test_notes_changed_flag(home_pair: RenewalPair):
    diff = compute_diff(home_pair)
    result = flag_diff(diff, home_pair)
    assert DiffFlag.NOTES_CHANGED in result.flags


def test_liability_decrease_flag():
    prior = PolicySnapshot(
        policy_number="LI-001",
        policy_type="home",
        carrier="X",
        effective_date="2024-01-01",
        expiration_date="2025-01-01",
        premium=2000,
        home_coverages=HomeCoverages(coverage_e_liability=300000),
    )
    renewal = prior.model_copy(deep=True)
    renewal.home_coverages.coverage_e_liability = 100000
    pair = RenewalPair(prior=prior, renewal=renewal)
    diff = compute_diff(pair)
    result = flag_diff(diff, pair)
    assert DiffFlag.LIABILITY_LIMIT_DECREASE in result.flags


def test_flags_match_changes(auto_pair: RenewalPair):
    diff = compute_diff(auto_pair)
    result = flag_diff(diff, auto_pair)
    flagged_changes = [c for c in result.changes if c.flag is not None]
    for c in flagged_changes:
        assert c.flag in result.flags
