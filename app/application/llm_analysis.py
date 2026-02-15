from pydantic import ValidationError

from app.adaptor.llm.prompts import (
    ENDORSEMENT_COMPARISON,
    REVIEW_SUMMARY,
    RISK_SIGNAL_EXTRACTOR,
)
from app.adaptor.llm.schemas import (
    EndorsementComparisonResponse,
    ReviewSummaryResponse,
    RiskSignalExtractorResponse,
)
from app.domain.models.diff import DiffResult
from app.domain.models.enums import AnalysisType
from app.domain.models.policy import RenewalPair
from app.domain.models.review import LLMInsight, ReviewResult
from app.domain.ports.llm import LLMPort


def should_analyze(diff: DiffResult, pair: RenewalPair) -> bool:
    if pair.prior.notes != pair.renewal.notes and pair.renewal.notes:
        return True

    endorsement_desc_changes = [
        c for c in diff.changes if c.field.startswith("endorsement_description_")
    ]
    return bool(endorsement_desc_changes)


def _analyze_notes(client: LLMPort, notes: str) -> list[LLMInsight]:
    prompt = RISK_SIGNAL_EXTRACTOR.format(notes=notes)
    result = client.complete(prompt, trace_name="risk_signal_extractor")

    if "error" in result:
        return [
            LLMInsight(
                analysis_type=AnalysisType.RISK_SIGNAL_EXTRACTOR,
                finding=f"Analysis failed: {result['error']}",
                confidence=0.0,
            )
        ]

    try:
        parsed = RiskSignalExtractorResponse.model_validate(result)
    except ValidationError:
        return [
            LLMInsight(
                analysis_type=AnalysisType.RISK_SIGNAL_EXTRACTOR,
                finding="Malformed LLM response",
                confidence=0.0,
            )
        ]

    insights = []
    for signal in parsed.signals:
        insights.append(
            LLMInsight(
                analysis_type=AnalysisType.RISK_SIGNAL_EXTRACTOR,
                finding=signal.description,
                confidence=parsed.confidence,
                reasoning=parsed.summary,
            )
        )
    return insights


def _analyze_endorsement(client: LLMPort, prior_desc: str, renewal_desc: str) -> LLMInsight:
    prompt = ENDORSEMENT_COMPARISON.format(
        prior_endorsement=prior_desc, renewal_endorsement=renewal_desc
    )
    result = client.complete(prompt, trace_name="endorsement_comparison")

    if "error" in result:
        return LLMInsight(
            analysis_type=AnalysisType.ENDORSEMENT_COMPARISON,
            finding=f"Analysis failed: {result['error']}",
            confidence=0.0,
        )

    try:
        parsed = EndorsementComparisonResponse.model_validate(result)
    except ValidationError:
        return LLMInsight(
            analysis_type=AnalysisType.ENDORSEMENT_COMPARISON,
            finding="Malformed LLM response",
            confidence=0.0,
        )

    return LLMInsight(
        analysis_type=AnalysisType.ENDORSEMENT_COMPARISON,
        finding=f"Change type: {parsed.change_type}",
        confidence=parsed.confidence,
        reasoning=parsed.reasoning,
    )


def generate_summary(client: LLMPort, result: ReviewResult) -> str | None:
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
        parsed = ReviewSummaryResponse.model_validate(response)
        return parsed.summary
    except (ValidationError, Exception):
        return None


def analyze_pair(client: LLMPort, diff: DiffResult, pair: RenewalPair) -> list[LLMInsight]:
    insights: list[LLMInsight] = []

    # notes analysis
    if pair.renewal.notes and pair.prior.notes != pair.renewal.notes:
        insights.extend(_analyze_notes(client, pair.renewal.notes))

    # endorsement description changes
    for change in diff.changes:
        if change.field.startswith("endorsement_description_"):
            insights.append(_analyze_endorsement(client, change.prior_value, change.renewal_value))

    return insights
