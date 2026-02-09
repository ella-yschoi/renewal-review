from app.llm.client import LLMClientProtocol
from app.llm.prompts import (
    COVERAGE_SIMILARITY,
    ENDORSEMENT_COMPARISON,
    RISK_SIGNAL_EXTRACTOR,
)
from app.models.diff import DiffResult
from app.models.policy import RenewalPair
from app.models.review import LLMInsight


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
