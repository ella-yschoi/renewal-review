from app.config import QuoteConfig
from app.domain.models.diff import DiffResult
from app.domain.models.enums import QuoteStrategy
from app.domain.models.policy import PolicyType, RenewalPair
from app.domain.models.quote import CoverageAdjustment, QuoteRecommendation

PROTECTED_FIELDS = {
    "bodily_injury_limit",
    "property_damage_limit",
    "coverage_e_liability",
    "uninsured_motorist",
    "coverage_a_dwelling",
}


def _build_recommendation(
    pair: RenewalPair,
    adjustments: list[CoverageAdjustment],
    savings_pct: float,
    trade_off: str,
) -> QuoteRecommendation | None:
    if not adjustments:
        return None
    return QuoteRecommendation(
        quote_id="",
        adjustments=adjustments,
        estimated_savings_pct=savings_pct,
        estimated_savings_dollar=round(pair.renewal.premium * savings_pct / 100, 2),
        trade_off=trade_off,
    )


def _auto_raise_deductible(pair: RenewalPair, cfg: QuoteConfig) -> QuoteRecommendation | None:
    cov = pair.renewal.auto_coverages
    if cov is None:
        return None

    adjustments: list[CoverageAdjustment] = []
    if cov.collision_deductible < cfg.auto_collision_deductible:
        adjustments.append(
            CoverageAdjustment(
                field="collision_deductible",
                original_value=str(cov.collision_deductible),
                proposed_value=str(cfg.auto_collision_deductible),
                strategy=QuoteStrategy.RAISE_DEDUCTIBLE,
            )
        )
    if cov.comprehensive_deductible < cfg.auto_comprehensive_deductible:
        adjustments.append(
            CoverageAdjustment(
                field="comprehensive_deductible",
                original_value=str(cov.comprehensive_deductible),
                proposed_value=str(cfg.auto_comprehensive_deductible),
                strategy=QuoteStrategy.RAISE_DEDUCTIBLE,
            )
        )

    return _build_recommendation(
        pair,
        adjustments,
        cfg.savings_raise_deductible_auto,
        (
            f"Raising deductibles increases out-of-pocket costs per claim. "
            f"For example, a collision with ${cfg.auto_collision_deductible:,.0f} deductible "
            f"means paying that amount before insurance covers the rest. "
            f"Best for drivers with clean records and emergency savings."
        ),
    )


def _auto_drop_optional(pair: RenewalPair, cfg: QuoteConfig) -> QuoteRecommendation | None:
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
                strategy=QuoteStrategy.DROP_OPTIONAL,
            )
        )
    if cov.roadside_assistance:
        adjustments.append(
            CoverageAdjustment(
                field="roadside_assistance",
                original_value="True",
                proposed_value="False",
                strategy=QuoteStrategy.DROP_OPTIONAL,
            )
        )

    return _build_recommendation(
        pair,
        adjustments,
        cfg.savings_drop_optional,
        (
            "Removing rental reimbursement means no covered rental car while your vehicle "
            "is being repaired (typical rental cost: $30–50/day). Removing roadside assistance "
            "means no covered towing, jump-starts, or lockout service. "
            "Consider whether the client has AAA or another roadside plan as an alternative."
        ),
    )


def _auto_reduce_medical(pair: RenewalPair, cfg: QuoteConfig) -> QuoteRecommendation | None:
    cov = pair.renewal.auto_coverages
    if cov is None:
        return None

    if cov.medical_payments <= cfg.auto_medical_min:
        return None

    adjustments = [
        CoverageAdjustment(
            field="medical_payments",
            original_value=str(cov.medical_payments),
            proposed_value=str(cfg.auto_medical_min),
            strategy=QuoteStrategy.REDUCE_MEDICAL,
        )
    ]
    return _build_recommendation(
        pair,
        adjustments,
        cfg.savings_reduce_medical,
        (
            f"Reducing medical payments from ${cov.medical_payments:,.0f} to "
            f"${cfg.auto_medical_min:,.0f} lowers the per-person injury coverage. "
            f"If a passenger is injured, the policy pays up to ${cfg.auto_medical_min:,.0f} "
            f"regardless of fault. Average ER visit costs $2,000–$3,000. "
            f"This option works if drivers/passengers have good personal health insurance."
        ),
    )


def _home_raise_deductible(pair: RenewalPair, cfg: QuoteConfig) -> QuoteRecommendation | None:
    cov = pair.renewal.home_coverages
    if cov is None:
        return None

    if cov.deductible >= cfg.home_deductible:
        return None

    adjustments = [
        CoverageAdjustment(
            field="deductible",
            original_value=str(cov.deductible),
            proposed_value=str(cfg.home_deductible),
            strategy=QuoteStrategy.RAISE_DEDUCTIBLE,
        )
    ]
    return _build_recommendation(
        pair,
        adjustments,
        cfg.savings_raise_deductible_home,
        (
            f"Raising the home deductible from ${cov.deductible:,.0f} to "
            f"${cfg.home_deductible:,.0f} saves on premium but increases out-of-pocket "
            f"cost per claim. For example, if a tree falls on the roof, the client pays "
            f"the first ${cfg.home_deductible:,.0f} before coverage kicks in. "
            f"Best for homeowners with emergency funds who file claims infrequently."
        ),
    )


def _home_drop_water_backup(pair: RenewalPair, cfg: QuoteConfig) -> QuoteRecommendation | None:
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
            strategy=QuoteStrategy.DROP_WATER_BACKUP,
        )
    ]
    return _build_recommendation(
        pair,
        adjustments,
        cfg.savings_drop_water_backup,
        (
            "Removing water backup coverage (HO 04 95) eliminates protection for sewer "
            "backup, sump pump failure, and foundation seepage. Average water backup claims "
            "cost $7,000–$10,000 in cleanup and restoration. This is one of the most common "
            "homeowner claims. Not recommended for properties with older plumbing, basements, "
            "or prior water-related claims."
        ),
    )


def _home_reduce_personal_property(
    pair: RenewalPair, cfg: QuoteConfig
) -> QuoteRecommendation | None:
    cov = pair.renewal.home_coverages
    if cov is None:
        return None

    target = round(cov.coverage_a_dwelling * cfg.home_personal_property_ratio)
    if cov.coverage_c_personal_property <= target + 100:
        return None

    adjustments = [
        CoverageAdjustment(
            field="coverage_c_personal_property",
            original_value=str(int(cov.coverage_c_personal_property)),
            proposed_value=str(int(target)),
            strategy=QuoteStrategy.REDUCE_PERSONAL_PROPERTY,
        )
    ]
    return _build_recommendation(
        pair,
        adjustments,
        cfg.savings_reduce_personal_property,
        (
            f"Reducing personal property coverage (Coverage C) from "
            f"${cov.coverage_c_personal_property:,.0f} to ${int(target):,} means lower "
            f"reimbursement if belongings are damaged, destroyed, or stolen. "
            f"To check if this is appropriate, the client should do a home inventory — "
            f"total value of furniture, electronics, clothing, and valuables. If it exceeds "
            f"${int(target):,}, this reduction could leave a gap."
        ),
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


def generate_quotes(
    pair: RenewalPair, diff: DiffResult, cfg: QuoteConfig | None = None
) -> list[QuoteRecommendation]:
    if not diff.flags:
        return []

    if cfg is None:
        from app.config import settings

        cfg = settings.quotes

    strategies = (
        _AUTO_STRATEGIES if pair.prior.policy_type == PolicyType.AUTO else _HOME_STRATEGIES
    )

    quotes: list[QuoteRecommendation] = []
    for strategy_fn in strategies:
        quote = strategy_fn(pair, cfg)
        if quote is not None:
            quotes.append(quote)

    # assign sequential IDs
    quotes = [q.model_copy(update={"quote_id": f"Quote {i + 1}"}) for i, q in enumerate(quotes)]

    return quotes[:3]


def explain_no_quotes(pair: RenewalPair, cfg: QuoteConfig | None = None) -> list[str]:
    if cfg is None:
        from app.config import settings

        cfg = settings.quotes

    reasons: list[str] = []
    if pair.prior.policy_type == PolicyType.AUTO:
        cov = pair.renewal.auto_coverages
        if cov:
            if cov.collision_deductible >= cfg.auto_collision_deductible:
                reasons.append(
                    f"Collision deductible already "
                    f"${cov.collision_deductible:,.0f} "
                    f"(threshold: ${cfg.auto_collision_deductible:,.0f})"
                )
            if cov.comprehensive_deductible >= cfg.auto_comprehensive_deductible:
                reasons.append(
                    f"Comprehensive deductible already "
                    f"${cov.comprehensive_deductible:,.0f} "
                    f"(threshold: ${cfg.auto_comprehensive_deductible:,.0f})"
                )
            if not cov.rental_reimbursement:
                reasons.append("Rental reimbursement already removed")
            if not cov.roadside_assistance:
                reasons.append("Roadside assistance already removed")
            if cov.medical_payments <= cfg.auto_medical_min:
                reasons.append(f"Medical payments already at minimum ${cov.medical_payments:,.0f}")
    else:
        cov = pair.renewal.home_coverages
        if cov:
            if cov.deductible >= cfg.home_deductible:
                reasons.append(
                    f"Home deductible already ${cov.deductible:,.0f} "
                    f"(threshold: ${cfg.home_deductible:,.0f})"
                )
            if not cov.water_backup:
                reasons.append("Water backup coverage already removed")
            target = round(cov.coverage_a_dwelling * cfg.home_personal_property_ratio)
            if cov.coverage_c_personal_property <= target + 100:
                reasons.append(
                    f"Personal property (Coverage C) already at "
                    f"${cov.coverage_c_personal_property:,.0f} "
                    f"— near or below recommended ${target:,}"
                )

    return reasons
