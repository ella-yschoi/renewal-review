from app.config import settings
from app.domain.models.enums import FlagType, Severity, UnbundleRisk
from app.domain.models.policy import PolicyType
from app.domain.models.portfolio import BundleAnalysis, CrossPolicyFlag, PortfolioSummary
from app.domain.models.review import ReviewResult, RiskLevel


def _build_bundle_analysis(
    results: list[ReviewResult],
) -> BundleAnalysis:
    auto_results = [r for r in results if r.pair and r.pair.renewal.policy_type == PolicyType.AUTO]
    home_results = [r for r in results if r.pair and r.pair.renewal.policy_type == PolicyType.HOME]

    has_auto = len(auto_results) > 0
    has_home = len(home_results) > 0
    is_bundle = has_auto and has_home

    carriers: set[str] = set()
    for r in results:
        if r.pair:
            carriers.add(r.pair.renewal.carrier)
    carrier_mismatch = len(carriers) > 1
    bundle_discount_eligible = is_bundle and not carrier_mismatch

    unbundle_risk = UnbundleRisk.LOW
    if is_bundle:
        risk_levels = [r.risk_level for r in results]
        if RiskLevel.ACTION_REQUIRED in risk_levels or RiskLevel.URGENT_REVIEW in risk_levels:
            unbundle_risk = UnbundleRisk.HIGH
        elif RiskLevel.REVIEW_RECOMMENDED in risk_levels:
            unbundle_risk = UnbundleRisk.MEDIUM

    return BundleAnalysis(
        has_auto=has_auto,
        has_home=has_home,
        is_bundle=is_bundle,
        bundle_discount_eligible=bundle_discount_eligible,
        carrier_mismatch=carrier_mismatch,
        unbundle_risk=unbundle_risk,
    )


def _detect_duplicate_coverage(results: list[ReviewResult]) -> list[CrossPolicyFlag]:
    flags: list[CrossPolicyFlag] = []

    auto_with_medical: list[str] = []
    home_with_medical: list[str] = []
    auto_with_roadside: list[str] = []
    home_with_roadside: list[str] = []

    for r in results:
        if not r.pair:
            continue
        snap = r.pair.renewal
        if snap.policy_type == PolicyType.AUTO and snap.auto_coverages:
            if snap.auto_coverages.medical_payments > 0:
                auto_with_medical.append(r.policy_number)
            if snap.auto_coverages.roadside_assistance:
                auto_with_roadside.append(r.policy_number)
        elif snap.policy_type == PolicyType.HOME and snap.home_coverages:
            if snap.home_coverages.coverage_f_medical > 0:
                home_with_medical.append(r.policy_number)
            for endo in snap.endorsements:
                desc_lower = endo.description.lower()
                if "roadside" in desc_lower or "towing" in desc_lower:
                    home_with_roadside.append(r.policy_number)
                    break

    if auto_with_medical and home_with_medical:
        flags.append(
            CrossPolicyFlag(
                flag_type=FlagType.DUPLICATE_MEDICAL,
                severity=Severity.WARNING,
                description=(
                    "Both auto medical payments and home medical coverage "
                    "(Coverage F) are active. Review for potential overlap."
                ),
                affected_policies=auto_with_medical + home_with_medical,
            )
        )

    if auto_with_roadside and home_with_roadside:
        flags.append(
            CrossPolicyFlag(
                flag_type=FlagType.DUPLICATE_ROADSIDE,
                severity=Severity.INFO,
                description=(
                    "Roadside assistance is present on both auto policy "
                    "and home endorsements. Consider consolidating."
                ),
                affected_policies=auto_with_roadside + home_with_roadside,
            )
        )

    return flags


def _calculate_exposure_flags(results: list[ReviewResult]) -> list[CrossPolicyFlag]:
    cfg = settings.portfolio
    flags: list[CrossPolicyFlag] = []
    total_liability = 0.0
    affected: list[str] = []

    for r in results:
        if not r.pair:
            continue
        snap = r.pair.renewal
        if snap.policy_type == PolicyType.HOME and snap.home_coverages:
            total_liability += snap.home_coverages.coverage_e_liability
            affected.append(r.policy_number)
        elif snap.policy_type == PolicyType.AUTO and snap.auto_coverages:
            bi_str = snap.auto_coverages.bodily_injury_limit.split("/")[0]
            total_liability += float(bi_str) * 1000
            affected.append(r.policy_number)

    if not affected:
        return flags

    if total_liability > cfg.high_liability:
        flags.append(
            CrossPolicyFlag(
                flag_type=FlagType.HIGH_LIABILITY_EXPOSURE,
                severity=Severity.INFO,
                description=(
                    f"Total liability exposure is ${total_liability:,.0f}, "
                    f"exceeding ${cfg.high_liability:,.0f}. Consider umbrella policy review."
                ),
                affected_policies=affected,
            )
        )
    elif total_liability < cfg.low_liability:
        flags.append(
            CrossPolicyFlag(
                flag_type=FlagType.LOW_LIABILITY_EXPOSURE,
                severity=Severity.WARNING,
                description=(
                    f"Total liability exposure is ${total_liability:,.0f}, "
                    f"below ${cfg.low_liability:,.0f}. Client may be underinsured."
                ),
                affected_policies=affected,
            )
        )

    return flags


def _detect_premium_concentration(
    results: list[ReviewResult], total_premium: float, premium_change_pct: float
) -> list[CrossPolicyFlag]:
    cfg = settings.portfolio
    flags: list[CrossPolicyFlag] = []

    if total_premium > 0:
        for r in results:
            if not r.pair:
                continue
            pct = r.pair.renewal.premium / total_premium
            if pct >= cfg.concentration_pct:
                flags.append(
                    CrossPolicyFlag(
                        flag_type=FlagType.PREMIUM_CONCENTRATION,
                        severity=Severity.WARNING,
                        description=(
                            f"Policy {r.policy_number} represents "
                            f"{pct:.0%} of total portfolio premium. "
                            "Loss of this policy significantly impacts revenue."
                        ),
                        affected_policies=[r.policy_number],
                    )
                )

    if abs(premium_change_pct) >= cfg.portfolio_change_pct:
        all_policies = [r.policy_number for r in results]
        flags.append(
            CrossPolicyFlag(
                flag_type=FlagType.HIGH_PORTFOLIO_INCREASE,
                severity=Severity.CRITICAL,
                description=f"Total portfolio premium changed by {premium_change_pct:+.1f}%. "
                "Review all policies for retention risk.",
                affected_policies=all_policies,
            )
        )

    return flags


def analyze_portfolio(
    policy_numbers: list[str],
    results_store: dict[str, ReviewResult],
) -> PortfolioSummary:
    unique_numbers = list(dict.fromkeys(policy_numbers))

    results: list[ReviewResult] = []
    for pn in unique_numbers:
        result = results_store.get(pn)
        if result is None:
            raise ValueError(f"No review found for policy: {pn}")
        results.append(result)

    total_premium = sum(r.pair.renewal.premium for r in results if r.pair)
    total_prior_premium = sum(r.pair.prior.premium for r in results if r.pair)
    premium_change_pct = (
        ((total_premium - total_prior_premium) / total_prior_premium * 100)
        if total_prior_premium > 0
        else 0.0
    )

    risk_breakdown: dict[str, int] = {}
    for r in results:
        level = r.risk_level.value
        risk_breakdown[level] = risk_breakdown.get(level, 0) + 1

    bundle_analysis = _build_bundle_analysis(results)
    cross_policy_flags: list[CrossPolicyFlag] = []
    cross_policy_flags.extend(_detect_duplicate_coverage(results))
    cross_policy_flags.extend(_calculate_exposure_flags(results))
    cross_policy_flags.extend(
        _detect_premium_concentration(results, total_premium, premium_change_pct)
    )

    return PortfolioSummary(
        client_policies=unique_numbers,
        total_premium=total_premium,
        total_prior_premium=total_prior_premium,
        premium_change_pct=round(premium_change_pct, 2),
        risk_breakdown=risk_breakdown,
        bundle_analysis=bundle_analysis,
        cross_policy_flags=cross_policy_flags,
    )
