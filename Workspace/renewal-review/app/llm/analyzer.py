from app.llm.client import LLMClientProtocol
from app.llm.prompts import (
    COVERAGE_SIMILARITY,
    ENDORSEMENT_COMPARISON,
    REVIEW_SUMMARY,
    RISK_SIGNAL_EXTRACTOR,
)
from app.models.diff import DiffResult
from app.models.policy import RenewalPair
from app.models.review import LLMInsight, ReviewResult


def should_analyze(diff: DiffResult, pair: RenewalPair) -> bool:
    if pair.prior.notes != pair.renewal.notes and pair.renewal.notes:
        return True

    endorsement_desc_changes = [
        c for c in diff.changes if c.field.startswith("endorsement_description_")
    ]
    if endorsement_desc_changes:
        return True

    return bool(
        pair.prior.home_coverages
        and pair.renewal.home_coverages
        and pair.prior.home_coverages.water_backup != pair.renewal.home_coverages.water_backup
    )


def _analyze_notes(client: LLMClientProtocol, notes: str) -> list[LLMInsight]:
    prompt = RISK_SIGNAL_EXTRACTOR.format(notes=notes)
    result = client.complete(prompt, trace_name="risk_signal_extractor")

    if "error" in result:
        return [
            LLMInsight(
                analysis_type="risk_signal_extractor",
                finding=f"Analysis failed: {result['error']}",
                confidence=0.0,
            )
        ]

    insights = []
    for signal in result.get("signals", []):
        insights.append(
            LLMInsight(
                analysis_type="risk_signal_extractor",
                finding=signal.get("description", ""),
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("summary", ""),
            )
        )
    return insights


def _analyze_endorsement(
    client: LLMClientProtocol, prior_desc: str, renewal_desc: str
) -> LLMInsight:
    prompt = ENDORSEMENT_COMPARISON.format(
        prior_endorsement=prior_desc, renewal_endorsement=renewal_desc
    )
    result = client.complete(prompt, trace_name="endorsement_comparison")

    if "error" in result:
        return LLMInsight(
            analysis_type="endorsement_comparison",
            finding=f"Analysis failed: {result['error']}",
            confidence=0.0,
        )

    change_type = result.get("change_type", "unknown")
    return LLMInsight(
        analysis_type="endorsement_comparison",
        finding=f"Change type: {change_type}",
        confidence=result.get("confidence", 0.5),
        reasoning=result.get("reasoning", ""),
    )


def _analyze_coverage(client: LLMClientProtocol, prior_cov: str, renewal_cov: str) -> LLMInsight:
    prompt = COVERAGE_SIMILARITY.format(prior_coverage=prior_cov, renewal_coverage=renewal_cov)
    result = client.complete(prompt, trace_name="coverage_similarity")

    if "error" in result:
        return LLMInsight(
            analysis_type="coverage_similarity",
            finding=f"Analysis failed: {result['error']}",
            confidence=0.0,
        )

    equivalent = result.get("equivalent", True)
    return LLMInsight(
        analysis_type="coverage_similarity",
        finding=f"Coverages {'equivalent' if equivalent else 'NOT equivalent'}",
        confidence=result.get("confidence", 0.5),
        reasoning=result.get("reasoning", ""),
    )


def generate_summary(client: LLMClientProtocol, result: ReviewResult) -> str | None:
    if result.pair is None:
        return None

    pair = result.pair
    diff = result.diff
    prior_premium = pair.prior.premium
    renewal_premium = pair.renewal.premium
    if prior_premium > 0:
        pct = ((renewal_premium - prior_premium) / prior_premium) * 100
        premium_change = f"{pct:+.1f}%"
    else:
        premium_change = "N/A"

    flagged_changes = [c for c in diff.changes if c.flag]
    other_changes = [c for c in diff.changes if not c.flag]
    key_changes_list = (flagged_changes + other_changes)[:5]
    key_changes = "\n".join(
        f"- {c.field}: {c.prior_value} → {c.renewal_value}"
        + (f" [{c.flag.value}]" if c.flag else "")
        for c in key_changes_list
    )

    llm_insights_section = ""
    if result.llm_insights:
        findings = "\n".join(f"- {i.finding}" for i in result.llm_insights)
        llm_insights_section = f"LLM insights:\n{findings}"

    prompt = REVIEW_SUMMARY.format(
        policy_number=pair.prior.policy_number,
        policy_type=pair.prior.policy_type.value,
        prior_premium=f"{prior_premium:.2f}",
        renewal_premium=f"{renewal_premium:.2f}",
        premium_change=premium_change,
        risk_level=result.risk_level.value,
        flags=", ".join(f.value for f in diff.flags),
        key_changes=key_changes or "None",
        llm_insights_section=llm_insights_section,
    )

    try:
        response = client.complete(prompt, trace_name="review_summary")
        if "error" in response:
            return None
        return response.get("summary")
    except Exception:
        return None


def analyze_pair(
    client: LLMClientProtocol, diff: DiffResult, pair: RenewalPair
) -> list[LLMInsight]:
    insights: list[LLMInsight] = []

    # notes analysis
    if pair.renewal.notes and pair.prior.notes != pair.renewal.notes:
        insights.extend(_analyze_notes(client, pair.renewal.notes))

    # endorsement description changes
    for change in diff.changes:
        if change.field.startswith("endorsement_description_"):
            insights.append(_analyze_endorsement(client, change.prior_value, change.renewal_value))

    # coverage text comparison for boolean drops
    coverage_drops = [
        c
        for c in diff.changes
        if c.field in {"water_backup", "replacement_cost"}
        and c.prior_value == "True"
        and c.renewal_value == "False"
    ]
    for drop in coverage_drops:
        insights.append(
            _analyze_coverage(client, f"{drop.field}: active", f"{drop.field}: removed")
        )

    return insights
