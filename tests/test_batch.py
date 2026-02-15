from app.application.batch import assign_risk_level, process_batch, process_pair
from app.domain.models.diff import DiffFlag
from app.domain.models.policy import RenewalPair
from app.domain.models.review import RiskLevel


def test_process_pair_auto(auto_pair: RenewalPair):
    result = process_pair(auto_pair)
    assert result.policy_number == "AUTO-2024-001"
    assert result.risk_level in RiskLevel
    assert len(result.diff.changes) > 0


def test_process_pair_home(home_pair: RenewalPair):
    result = process_pair(home_pair)
    assert result.policy_number == "HOME-2024-001"
    assert result.risk_level != RiskLevel.NO_ACTION_NEEDED


def test_assign_risk_urgent_review():
    assert assign_risk_level([DiffFlag.PREMIUM_INCREASE_CRITICAL]) == RiskLevel.URGENT_REVIEW
    assert assign_risk_level([DiffFlag.LIABILITY_LIMIT_DECREASE]) == RiskLevel.URGENT_REVIEW


def test_assign_risk_action_required():
    assert assign_risk_level([DiffFlag.PREMIUM_INCREASE_HIGH]) == RiskLevel.ACTION_REQUIRED
    assert assign_risk_level([DiffFlag.COVERAGE_DROPPED]) == RiskLevel.ACTION_REQUIRED


def test_assign_risk_review_recommended():
    assert assign_risk_level([DiffFlag.CARRIER_CHANGE]) == RiskLevel.REVIEW_RECOMMENDED
    assert assign_risk_level([DiffFlag.VEHICLE_ADDED]) == RiskLevel.REVIEW_RECOMMENDED


def test_assign_risk_no_action_needed():
    assert assign_risk_level([]) == RiskLevel.NO_ACTION_NEEDED


def test_process_batch(auto_pair: RenewalPair, home_pair: RenewalPair):
    results, summary = process_batch([auto_pair, home_pair])
    assert len(results) == 2
    assert summary.total == 2
    risk_total = (
        summary.no_action_needed
        + summary.review_recommended
        + summary.action_required
        + summary.urgent_review
    )
    assert risk_total == 2
    assert summary.processing_time_ms > 0
