import json

from pydantic import ValidationError

from app.application.prompts import QUOTE_PERSONALIZATION
from app.domain.models.enums import LLMTaskName
from app.domain.models.llm_schemas import QuotePersonalizationResponse
from app.domain.models.policy import RenewalPair
from app.domain.models.quote import QuoteRecommendation
from app.domain.ports.llm import LLMPort


def _build_policy_context(pair: RenewalPair) -> str:
    sections: list[str] = []
    sections.append(f"Policy: {pair.prior.policy_number} ({pair.prior.policy_type.value})")
    sections.append(f"Premium: ${pair.prior.premium:.2f} → ${pair.renewal.premium:.2f}")

    if pair.renewal.auto_coverages:
        cov = pair.renewal.auto_coverages
        sections.append(
            f"Auto coverages: collision_deductible=${cov.collision_deductible:.0f}, "
            f"comprehensive_deductible=${cov.comprehensive_deductible:.0f}, "
            f"medical_payments=${cov.medical_payments:.0f}, "
            f"rental={cov.rental_reimbursement}, roadside={cov.roadside_assistance}"
        )

    if pair.renewal.home_coverages:
        cov = pair.renewal.home_coverages
        sections.append(
            f"Home coverages: deductible=${cov.deductible:.0f}, "
            f"water_backup={cov.water_backup}, "
            f"coverage_c=${cov.coverage_c_personal_property:.0f}"
        )

    if pair.renewal.vehicles:
        for v in pair.renewal.vehicles:
            sections.append(f"Vehicle: {v.year} {v.make} {v.model} ({v.usage})")

    if pair.renewal.drivers:
        for d in pair.renewal.drivers:
            parts = f"Driver: {d.name}, age {d.age}, violations={d.violations}"
            if d.sr22:
                parts += ", SR-22"
            sections.append(parts)

    if pair.renewal.notes:
        sections.append(f"Notes: {pair.renewal.notes}")

    return "\n".join(sections)


def _build_quotes_json(quotes: list[QuoteRecommendation]) -> str:
    return json.dumps(
        [
            {
                "quote_id": q.quote_id,
                "strategy": q.adjustments[0].strategy if q.adjustments else "",
                "trade_off": q.trade_off,
            }
            for q in quotes
        ],
        indent=2,
    )


def personalize_quotes(
    client: LLMPort,
    quotes: list[QuoteRecommendation],
    pair: RenewalPair,
) -> list[QuoteRecommendation]:
    if not quotes:
        return quotes

    prompt = QUOTE_PERSONALIZATION.format(
        policy_context=_build_policy_context(pair),
        quotes_json=_build_quotes_json(quotes),
    )

    try:
        response = client.complete(prompt, trace_name=LLMTaskName.QUOTE_PERSONALIZATION)
        if "error" in response:
            return quotes
    except Exception:
        return quotes

    try:
        parsed = QuotePersonalizationResponse.model_validate(response)
    except ValidationError:
        return quotes

    llm_quotes = {q.quote_id: q for q in parsed.quotes}

    for quote in quotes:
        if quote.quote_id in llm_quotes:
            llm_q = llm_quotes[quote.quote_id]
            quote.trade_off = llm_q.trade_off
            quote.broker_tip = llm_q.broker_tip

    return quotes
