from app.engine.batch import assign_risk_level, process_batch, process_pair
from app.models.diff import DiffFlag
from app.models.policy import RenewalPair
from app.models.review import RiskLevel


def test_process_pair_auto(auto_pair: RenewalPair):
    result = process_pair(auto_pair)
    assert result.policy_number == "AUTO-2024-001"
    assert result.risk_level in RiskLevel
    assert len(result.diff.changes) > 0


def test_process_pair_home(home_pair: RenewalPair):
    result = process_pair(home_pair)
    assert result.policy_number == "HOME-2024-001"
    assert result.risk_level != RiskLevel.LOW


def test_assign_risk_critical():
    assert assign_risk_level([DiffFlag.PREMIUM_INCREASE_CRITICAL]) == RiskLevel.CRITICAL
    assert assign_risk_level([DiffFlag.LIABILITY_LIMIT_DECREASE]) == RiskLevel.CRITICAL


def test_assign_risk_high():
    assert assign_risk_level([DiffFlag.PREMIUM_INCREASE_HIGH]) == RiskLevel.HIGH
    assert assign_risk_level([DiffFlag.COVERAGE_DROPPED]) == RiskLevel.HIGH


def test_assign_risk_medium():
    assert assign_risk_level([DiffFlag.CARRIER_CHANGE]) == RiskLevel.MEDIUM
    assert assign_risk_level([DiffFlag.VEHICLE_ADDED]) == RiskLevel.MEDIUM


def test_assign_risk_low():
    assert assign_risk_level([]) == RiskLevel.LOW


def test_process_batch(auto_pair: RenewalPair, home_pair: RenewalPair):
    results, summary = process_batch([auto_pair, home_pair])
    assert len(results) == 2
    assert summary.total == 2
    assert summary.low + summary.medium + summary.high + summary.critical == 2
    assert summary.processing_time_ms > 0
