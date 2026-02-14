import time
from collections.abc import Callable

from app.aggregator import aggregate
from app.config import settings
from app.engine.differ import compute_diff
from app.engine.rules import flag_diff
from app.llm.analyzer import analyze_pair, should_analyze
from app.llm.client import LLMClient, LLMClientProtocol
from app.models.diff import DiffFlag
from app.models.policy import RenewalPair
from app.models.review import BatchSummary, ReviewResult, RiskLevel

URGENT_REVIEW_FLAGS = {DiffFlag.PREMIUM_INCREASE_CRITICAL, DiffFlag.LIABILITY_LIMIT_DECREASE}
ACTION_REQUIRED_FLAGS = {DiffFlag.PREMIUM_INCREASE_HIGH, DiffFlag.COVERAGE_DROPPED}


def assign_risk_level(flags: list[DiffFlag]) -> RiskLevel:
    flag_set = set(flags)
    if flag_set & URGENT_REVIEW_FLAGS:
        return RiskLevel.URGENT_REVIEW
    if flag_set & ACTION_REQUIRED_FLAGS:
        return RiskLevel.ACTION_REQUIRED
    if flags:
        return RiskLevel.REVIEW_RECOMMENDED
    return RiskLevel.NO_ACTION_NEEDED


def process_pair(pair: RenewalPair, llm_client: LLMClientProtocol | None = None) -> ReviewResult:
    diff = compute_diff(pair)
    diff = flag_diff(diff, pair)
    rule_risk = assign_risk_level(diff.flags)

    if llm_client and diff.flags and should_analyze(diff, pair):
        insights = analyze_pair(llm_client, diff, pair)
        result = aggregate(pair.prior.policy_number, rule_risk, diff, insights)
        result.pair = pair
        return result

    summary_parts = []
    if diff.flags:
        summary_parts.append(f"Flags: {', '.join(f.value for f in diff.flags)}")
    summary_parts.append(f"Risk: {rule_risk.value}")

    return ReviewResult(
        policy_number=pair.prior.policy_number,
        risk_level=rule_risk,
        diff=diff,
        summary=" | ".join(summary_parts),
        pair=pair,
    )


def process_batch(
    pairs: list[RenewalPair],
    llm_client: LLMClientProtocol | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[list[ReviewResult], BatchSummary]:
    start = time.perf_counter()

    if settings.llm_enabled and llm_client is None:
        llm_client = LLMClient()

    client = llm_client if settings.llm_enabled else None
    total = len(pairs)
    results = []
    for i, p in enumerate(pairs):
        results.append(process_pair(p, client))
        if on_progress:
            on_progress(i + 1, total)
    elapsed_ms = (time.perf_counter() - start) * 1000

    summary = BatchSummary(
        total=len(results),
        no_action_needed=sum(1 for r in results if r.risk_level == RiskLevel.NO_ACTION_NEEDED),
        review_recommended=sum(1 for r in results if r.risk_level == RiskLevel.REVIEW_RECOMMENDED),
        action_required=sum(1 for r in results if r.risk_level == RiskLevel.ACTION_REQUIRED),
        urgent_review=sum(1 for r in results if r.risk_level == RiskLevel.URGENT_REVIEW),
        llm_analyzed=sum(1 for r in results if r.llm_insights),
        processing_time_ms=round(elapsed_ms, 1),
    )
    return results, summary
