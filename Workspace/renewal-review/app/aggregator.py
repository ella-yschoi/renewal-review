from app.models.diff import DiffResult
from app.models.review import LLMInsight, ReviewResult, RiskLevel

RISK_ORDER = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]


def _max_risk(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    return max(a, b, key=lambda x: RISK_ORDER.index(x))


def aggregate(
    policy_number: str,
    rule_risk: RiskLevel,
    diff: DiffResult,
    llm_insights: list[LLMInsight],
) -> ReviewResult:
    final_risk = rule_risk

    high_confidence_signals = [
        i for i in llm_insights if i.confidence >= 0.8 and "NOT equivalent" in i.finding
    ]
    if high_confidence_signals:
        final_risk = _max_risk(final_risk, RiskLevel.HIGH)

    risk_signals = [
        i
        for i in llm_insights
        if i.analysis_type == "risk_signal_extractor" and i.confidence >= 0.7
    ]
    if len(risk_signals) >= 2:
        final_risk = _max_risk(final_risk, RiskLevel.HIGH)

    restriction_changes = [
        i for i in llm_insights if "restriction" in i.finding.lower() and i.confidence >= 0.75
    ]
    if restriction_changes:
        final_risk = _max_risk(final_risk, RiskLevel.HIGH)

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
