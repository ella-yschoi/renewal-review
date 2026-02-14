from app.models.diff import DiffResult
from app.models.policy import PolicyType, RenewalPair
from app.models.quote import CoverageAdjustment, QuoteRecommendation

PROTECTED_FIELDS = {
    "bodily_injury_limit",
    "property_damage_limit",
    "coverage_e_liability",
    "uninsured_motorist",
    "coverage_a_dwelling",
}


def _auto_raise_deductible(pair: RenewalPair) -> QuoteRecommendation | None:
    cov = pair.renewal.auto_coverages
    if cov is None:
        return None

    adjustments: list[CoverageAdjustment] = []
    if cov.collision_deductible < 1000:
        adjustments.append(
            CoverageAdjustment(
                field="collision_deductible",
                original_value=str(cov.collision_deductible),
                proposed_value="1000",
                strategy="raise_deductible",
            )
        )
    if cov.comprehensive_deductible < 500:
        adjustments.append(
            CoverageAdjustment(
                field="comprehensive_deductible",
                original_value=str(cov.comprehensive_deductible),
                proposed_value="500",
                strategy="raise_deductible",
            )
        )

    if not adjustments:
        return None

    savings_pct = 10.0
    savings_dollar = round(pair.renewal.premium * savings_pct / 100, 2)
    return QuoteRecommendation(
        quote_id="",
        adjustments=adjustments,
        estimated_savings_pct=savings_pct,
        estimated_savings_dollar=savings_dollar,
        trade_off="Higher deductibles mean more out-of-pocket cost per claim",
    )


def _auto_drop_optional(pair: RenewalPair) -> QuoteRecommendation | None:
    cov = pair.renewal.auto_coverages
    if cov is None:
        return None

    adjustments: list[CoverageAdjustment] = []
    if cov.rental_reimbursement:
        adjustments.append(
            CoverageAdjustment(
                field="rental_reimbursement",
                original_value="True",
                proposed_value="False",
                strategy="drop_optional",
            )
        )
    if cov.roadside_assistance:
        adjustments.append(
            CoverageAdjustment(
                field="roadside_assistance",
                original_value="True",
                proposed_value="False",
                strategy="drop_optional",
            )
        )

    if not adjustments:
        return None

    savings_pct = 4.0
    savings_dollar = round(pair.renewal.premium * savings_pct / 100, 2)
    return QuoteRecommendation(
        quote_id="",
        adjustments=adjustments,
        estimated_savings_pct=savings_pct,
        estimated_savings_dollar=savings_dollar,
        trade_off="No rental car or roadside help if needed after an incident",
    )


def _auto_reduce_medical(pair: RenewalPair) -> QuoteRecommendation | None:
    cov = pair.renewal.auto_coverages
    if cov is None:
        return None

    if cov.medical_payments <= 2000:
        return None

    adjustments = [
        CoverageAdjustment(
            field="medical_payments",
            original_value=str(cov.medical_payments),
            proposed_value="2000",
            strategy="reduce_medical",
        )
    ]
    savings_pct = 2.5
    savings_dollar = round(pair.renewal.premium * savings_pct / 100, 2)
    return QuoteRecommendation(
        quote_id="",
        adjustments=adjustments,
        estimated_savings_pct=savings_pct,
        estimated_savings_dollar=savings_dollar,
        trade_off="Lower medical payment limit may not cover all injury costs",
    )


def _home_raise_deductible(pair: RenewalPair) -> QuoteRecommendation | None:
    cov = pair.renewal.home_coverages
    if cov is None:
        return None

    if cov.deductible >= 2500:
        return None

    adjustments = [
        CoverageAdjustment(
            field="deductible",
            original_value=str(cov.deductible),
            proposed_value="2500",
            strategy="raise_deductible",
        )
    ]
    savings_pct = 12.5
    savings_dollar = round(pair.renewal.premium * savings_pct / 100, 2)
    return QuoteRecommendation(
        quote_id="",
        adjustments=adjustments,
        estimated_savings_pct=savings_pct,
        estimated_savings_dollar=savings_dollar,
        trade_off="Higher deductible means more out-of-pocket cost per claim",
    )


def _home_drop_water_backup(pair: RenewalPair) -> QuoteRecommendation | None:
    cov = pair.renewal.home_coverages
    if cov is None:
        return None

    if not cov.water_backup:
        return None

    adjustments = [
        CoverageAdjustment(
            field="water_backup",
            original_value="True",
            proposed_value="False",
            strategy="drop_water_backup",
        )
    ]
    savings_pct = 3.0
    savings_dollar = round(pair.renewal.premium * savings_pct / 100, 2)
    return QuoteRecommendation(
        quote_id="",
        adjustments=adjustments,
        estimated_savings_pct=savings_pct,
        estimated_savings_dollar=savings_dollar,
        trade_off="No coverage for water backup or sump overflow damage",
    )


def _home_reduce_personal_property(pair: RenewalPair) -> QuoteRecommendation | None:
    cov = pair.renewal.home_coverages
    if cov is None:
        return None

    target = cov.coverage_a_dwelling * 0.5
    if cov.coverage_c_personal_property <= target:
        return None

    adjustments = [
        CoverageAdjustment(
            field="coverage_c_personal_property",
            original_value=str(cov.coverage_c_personal_property),
            proposed_value=str(target),
            strategy="reduce_personal_property",
        )
    ]
    savings_pct = 4.0
    savings_dollar = round(pair.renewal.premium * savings_pct / 100, 2)
    return QuoteRecommendation(
        quote_id="",
        adjustments=adjustments,
        estimated_savings_pct=savings_pct,
        estimated_savings_dollar=savings_dollar,
        trade_off="Less coverage for personal belongings in case of loss",
    )


_AUTO_STRATEGIES = [
    _auto_raise_deductible,
    _auto_drop_optional,
    _auto_reduce_medical,
]
_HOME_STRATEGIES = [
    _home_raise_deductible,
    _home_drop_water_backup,
    _home_reduce_personal_property,
]


def generate_quotes(pair: RenewalPair, diff: DiffResult) -> list[QuoteRecommendation]:
    if not diff.flags:
        return []

    strategies = (
        _AUTO_STRATEGIES if pair.prior.policy_type == PolicyType.AUTO else _HOME_STRATEGIES
    )

    quotes: list[QuoteRecommendation] = []
    for strategy_fn in strategies:
        quote = strategy_fn(pair)
        if quote is not None:
            quotes.append(quote)

    # assign sequential IDs
    for i, q in enumerate(quotes):
        q.quote_id = f"Q{i + 1}"

    return quotes[:3]
