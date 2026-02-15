from app.domain.models.diff import DiffResult
from app.domain.models.enums import AnalysisType
from app.domain.models.review import LLMInsight, ReviewResult, RiskLevel

RISK_ORDER = [
    RiskLevel.NO_ACTION_NEEDED,
    RiskLevel.REVIEW_RECOMMENDED,
    RiskLevel.ACTION_REQUIRED,
    RiskLevel.URGENT_REVIEW,
]


def _max_risk(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    return max(a, b, key=lambda x: RISK_ORDER.index(x))


def aggregate(
    policy_number: str,
    rule_risk: RiskLevel,
    diff: DiffResult,
    llm_insights: list[LLMInsight],
) -> ReviewResult:
    final_risk = rule_risk

    risk_signals = [
        i
        for i in llm_insights
        if i.analysis_type == AnalysisType.RISK_SIGNAL_EXTRACTOR and i.confidence >= 0.7
    ]
    if len(risk_signals) >= 2:
        final_risk = _max_risk(final_risk, RiskLevel.ACTION_REQUIRED)

    restriction_changes = [
        i for i in llm_insights if "restriction" in i.finding.lower() and i.confidence >= 0.75
    ]
    if restriction_changes:
        final_risk = _max_risk(final_risk, RiskLevel.ACTION_REQUIRED)

    # combined strong signals → CRITICAL
    if restriction_changes and len(risk_signals) >= 2:
        final_risk = _max_risk(final_risk, RiskLevel.URGENT_REVIEW)

    summary_parts = [f"Risk: {final_risk.value}"]
    if diff.flags:
        summary_parts.append(f"Flags: {len(diff.flags)}")
    if llm_insights:
        summary_parts.append(f"LLM insights: {len(llm_insights)}")
    if final_risk != rule_risk:
        summary_parts.append(f"Upgraded from {rule_risk.value} by LLM analysis")

    return ReviewResult(
        policy_number=policy_number,
        risk_level=final_risk,
        diff=diff,
        llm_insights=llm_insights,
        summary=" | ".join(summary_parts),
    )
