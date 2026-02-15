from app.llm.client import LLMClientProtocol
from app.llm.prompts import PORTFOLIO_ANALYSIS
from app.models.portfolio import PortfolioSummary
from app.models.review import ReviewResult


def _build_portfolio_context(
    summary: PortfolioSummary,
    results: list[ReviewResult],
) -> str:
    overview = (
        f"Policies: {len(summary.client_policies)}, "
        f"Total premium: ${summary.total_premium:,.2f}, "
        f"Prior premium: ${summary.total_prior_premium:,.2f}, "
        f"Change: {summary.premium_change_pct:+.2f}%"
    )

    risk_lines = [f"  {level}: {count}" for level, count in summary.risk_breakdown.items()]
    risk_text = "\n".join(risk_lines) if risk_lines else "  No risk data"

    ba = summary.bundle_analysis
    bundle_text = (
        f"  Auto: {ba.has_auto}, Home: {ba.has_home}, Bundle: {ba.is_bundle}, "
        f"Discount eligible: {ba.bundle_discount_eligible}, "
        f"Carrier mismatch: {ba.carrier_mismatch}, Unbundle risk: {ba.unbundle_risk}"
    )

    if summary.cross_policy_flags:
        flag_lines = []
        for f in summary.cross_policy_flags:
            flag_lines.append(
                f"  [{f.severity}] {f.flag_type}: {f.description} "
                f"(policies: {', '.join(f.affected_policies)})"
            )
        flags_text = "\n".join(flag_lines)
    else:
        flags_text = "  No cross-policy flags detected"

    policy_lines = []
    for r in results:
        if not r.pair:
            continue
        flag_count = len(r.diff.flags) if r.diff else 0
        policy_lines.append(
            f"  {r.policy_number} ({r.pair.renewal.policy_type.value}): "
            f"premium=${r.pair.renewal.premium:,.2f}, "
            f"risk={r.risk_level.value}, flags={flag_count}"
        )
    policies_text = "\n".join(policy_lines) if policy_lines else "  No policy details"

    return PORTFOLIO_ANALYSIS.format(
        portfolio_overview=overview,
        risk_breakdown=risk_text,
        bundle_analysis=bundle_text,
        cross_policy_flags=flags_text,
        individual_policies=policies_text,
    )


def enrich_portfolio(
    client: LLMClientProtocol,
    summary: PortfolioSummary,
    results: list[ReviewResult],
) -> PortfolioSummary:
    prompt = _build_portfolio_context(summary, results)

    try:
        response = client.complete(prompt, trace_name="portfolio_analysis")
        if "error" in response:
            return summary
    except Exception:
        return summary

    if "verdict" in response and response["verdict"]:
        summary.llm_verdict = response["verdict"]
    if "recommendations" in response and isinstance(response["recommendations"], list):
        summary.llm_recommendations = response["recommendations"]
    if "action_items" in response and isinstance(response["action_items"], list):
        summary.llm_action_items = response["action_items"]

    if summary.llm_verdict or summary.llm_recommendations or summary.llm_action_items:
        summary.llm_enriched = True

    return summary
