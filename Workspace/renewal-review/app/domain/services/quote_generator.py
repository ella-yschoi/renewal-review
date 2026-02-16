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
        "Higher deductibles mean more out-of-pocket cost per claim",
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
        "No rental car or roadside help if needed after an incident",
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
        "Lower medical payment limit may not cover all injury costs",
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
        "Higher deductible means more out-of-pocket cost per claim",
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
        "No coverage for water backup or sump overflow damage",
    )


def _home_reduce_personal_property(
    pair: RenewalPair, cfg: QuoteConfig
) -> QuoteRecommendation | None:
    cov = pair.renewal.home_coverages
    if cov is None:
        return None

    target = cov.coverage_a_dwelling * cfg.home_personal_property_ratio
    if cov.coverage_c_personal_property <= target:
        return None

    adjustments = [
        CoverageAdjustment(
            field="coverage_c_personal_property",
            original_value=str(cov.coverage_c_personal_property),
            proposed_value=str(target),
            strategy=QuoteStrategy.REDUCE_PERSONAL_PROPERTY,
        )
    ]
    return _build_recommendation(
        pair,
        adjustments,
        cfg.savings_reduce_personal_property,
        "Less coverage for personal belongings in case of loss",
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
    for i, q in enumerate(quotes):
        q.quote_id = f"Q{i + 1}"

    return quotes[:3]
