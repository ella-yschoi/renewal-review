from app.models.diff import DiffResult
from app.models.policy import AutoCoverages, HomeCoverages, PolicyType, RenewalPair
from app.models.quote import CoverageAdjustment, QuoteRecommendation

PROTECTED_FIELDS = frozenset(
    {
        "bodily_injury_limit",
        "property_damage_limit",
        "coverage_e_liability",
        "uninsured_motorist",
        "coverage_a_dwelling",
    }
)


# --- Auto strategies ---


def _auto_raise_deductible(cov: AutoCoverages) -> list[CoverageAdjustment] | None:
    adjustments: list[CoverageAdjustment] = []
    if cov.collision_deductible < 1000:
        adjustments.append(
            CoverageAdjustment(
                field="collision_deductible",
                original_value=str(cov.collision_deductible),
                proposed_value="1000.0",
                strategy="raise_deductible",
            )
        )
    if cov.comprehensive_deductible < 500:
        adjustments.append(
            CoverageAdjustment(
                field="comprehensive_deductible",
                original_value=str(cov.comprehensive_deductible),
                proposed_value="500.0",
                strategy="raise_deductible",
            )
        )
    return adjustments or None


def _auto_drop_optional(cov: AutoCoverages) -> list[CoverageAdjustment] | None:
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
    return adjustments or None


def _auto_reduce_medical(cov: AutoCoverages) -> list[CoverageAdjustment] | None:
    if cov.medical_payments <= 2000:
        return None
    return [
        CoverageAdjustment(
            field="medical_payments",
            original_value=str(cov.medical_payments),
            proposed_value="2000.0",
            strategy="reduce_medical",
        )
    ]


# --- Home strategies ---


def _home_raise_deductible(cov: HomeCoverages) -> list[CoverageAdjustment] | None:
    if cov.deductible >= 2500:
        return None
    return [
        CoverageAdjustment(
            field="deductible",
            original_value=str(cov.deductible),
            proposed_value="2500.0",
            strategy="raise_deductible",
        )
    ]


def _home_drop_water_backup(cov: HomeCoverages) -> list[CoverageAdjustment] | None:
    if not cov.water_backup:
        return None
    return [
        CoverageAdjustment(
            field="water_backup",
            original_value="True",
            proposed_value="False",
            strategy="drop_water_backup",
        )
    ]


def _home_reduce_personal_property(cov: HomeCoverages) -> list[CoverageAdjustment] | None:
    target = cov.coverage_a_dwelling * 0.5
    if cov.coverage_c_personal_property <= target:
        return None
    return [
        CoverageAdjustment(
            field="coverage_c_personal_property",
            original_value=str(cov.coverage_c_personal_property),
            proposed_value=str(target),
            strategy="reduce_personal_property",
        )
    ]


_AUTO_STRATEGIES: list[tuple[str, float, callable]] = [
    ("raise_deductible", 0.10, _auto_raise_deductible),
    ("drop_optional", 0.04, _auto_drop_optional),
    ("reduce_medical", 0.025, _auto_reduce_medical),
]

_HOME_STRATEGIES: list[tuple[str, float, callable]] = [
    ("raise_deductible", 0.125, _home_raise_deductible),
    ("drop_water_backup", 0.03, _home_drop_water_backup),
    ("reduce_personal_property", 0.04, _home_reduce_personal_property),
]

_TRADE_OFF_MESSAGES = {
    "raise_deductible": "Higher out-of-pocket cost per claim in exchange for lower premium",
    "drop_optional": "Lose rental reimbursement and/or roadside assistance coverage",
    "reduce_medical": "Lower medical payments limit from current level to $2,000",
    "drop_water_backup": "No coverage for water backup or sump pump overflow damage",
    "reduce_personal_property": "Personal property coverage reduced to 50% of dwelling value",
}


def generate_quotes(pair: RenewalPair, diff: DiffResult) -> list[QuoteRecommendation]:
    if not diff.flags:
        return []

    renewal = pair.renewal
    premium = renewal.premium
    quotes: list[QuoteRecommendation] = []

    if renewal.policy_type == PolicyType.AUTO and renewal.auto_coverages:
        strategies = _AUTO_STRATEGIES
        coverages = renewal.auto_coverages
    elif renewal.policy_type == PolicyType.HOME and renewal.home_coverages:
        strategies = _HOME_STRATEGIES
        coverages = renewal.home_coverages
    else:
        return []

    for name, savings_rate, strategy_fn in strategies:
        adjustments = strategy_fn(coverages)
        if adjustments is None:
            continue
        # Verify no protected fields are adjusted
        if any(adj.field in PROTECTED_FIELDS for adj in adjustments):
            continue
        savings_dollar = round(premium * savings_rate, 2)
        quotes.append(
            QuoteRecommendation(
                quote_id=f"Q{len(quotes) + 1}",
                adjustments=adjustments,
                estimated_savings_pct=round(savings_rate * 100, 1),
                estimated_savings_dollar=savings_dollar,
                trade_off=_TRADE_OFF_MESSAGES.get(name, ""),
            )
        )

    return quotes[:3]
