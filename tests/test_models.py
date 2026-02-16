from app.domain.models.diff import DiffFlag, DiffResult, FieldChange
from app.domain.models.policy import PolicyType, RenewalPair
from app.domain.models.review import BatchSummary, RiskLevel


def test_auto_pair_structure(auto_pair: RenewalPair):
    assert auto_pair.prior.policy_type == PolicyType.AUTO
    assert auto_pair.prior.auto_coverages is not None
    assert len(auto_pair.prior.vehicles) == 1
    assert len(auto_pair.renewal.vehicles) == 2


def test_home_pair_structure(home_pair: RenewalPair):
    assert home_pair.prior.policy_type == PolicyType.HOME
    assert home_pair.prior.home_coverages is not None
    assert home_pair.prior.home_coverages.coverage_a_dwelling == 350000


def test_diff_flag_values():
    assert len(DiffFlag) == 23


def test_diff_result_with_flags():
    change = FieldChange(
        field="premium",
        prior_value="1200",
        renewal_value="1356",
        change_pct=13.0,
        flag=DiffFlag.PREMIUM_INCREASE_HIGH,
    )
    result = DiffResult(
        policy_number="TEST-001",
        changes=[change],
        flags=[DiffFlag.PREMIUM_INCREASE_HIGH],
    )
    assert result.flags[0] == DiffFlag.PREMIUM_INCREASE_HIGH
    assert result.changes[0].change_pct == 13.0


def test_risk_level_ordering():
    levels = [
        RiskLevel.NO_ACTION_NEEDED,
        RiskLevel.REVIEW_RECOMMENDED,
        RiskLevel.ACTION_REQUIRED,
        RiskLevel.URGENT_REVIEW,
    ]
    assert len(levels) == 4


def test_batch_summary_defaults():
    summary = BatchSummary(total=100)
    assert summary.no_action_needed == 0
    assert summary.llm_analyzed == 0
