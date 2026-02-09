import time

from app.aggregator import aggregate
from app.config import settings
from app.engine.differ import compute_diff
from app.engine.rules import flag_diff
from app.llm.analyzer import analyze_pair, should_analyze
from app.llm.client import LLMClient, LLMClientProtocol
from app.models.diff import DiffFlag
from app.models.policy import RenewalPair
from app.models.review import BatchSummary, ReviewResult, RiskLevel

CRITICAL_FLAGS = {DiffFlag.PREMIUM_INCREASE_CRITICAL, DiffFlag.LIABILITY_LIMIT_DECREASE}
HIGH_FLAGS = {DiffFlag.PREMIUM_INCREASE_HIGH, DiffFlag.COVERAGE_DROPPED}


def assign_risk_level(flags: list[DiffFlag]) -> RiskLevel:
    flag_set = set(flags)
    if flag_set & CRITICAL_FLAGS:
        return RiskLevel.CRITICAL
    if flag_set & HIGH_FLAGS:
        return RiskLevel.HIGH
    if flags:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def process_pair(pair: RenewalPair, llm_client: LLMClientProtocol | None = None) -> ReviewResult:
    diff = compute_diff(pair)
    diff = flag_diff(diff, pair)
    rule_risk = assign_risk_level(diff.flags)

    if llm_client and diff.flags and should_analyze(diff, pair):
        insights = analyze_pair(llm_client, diff, pair)
        return aggregate(pair.prior.policy_number, rule_risk, diff, insights)

    summary_parts = []
    if diff.flags:
        summary_parts.append(f"Flags: {', '.join(f.value for f in diff.flags)}")
    summary_parts.append(f"Risk: {rule_risk.value}")

    return ReviewResult(
        policy_number=pair.prior.policy_number,
        risk_level=rule_risk,
        diff=diff,
        summary=" | ".join(summary_parts),
    )


def process_batch(
    pairs: list[RenewalPair], llm_client: LLMClientProtocol | None = None
) -> tuple[list[ReviewResult], BatchSummary]:
    start = time.perf_counter()

    if settings.llm_enabled and llm_client is None:
        llm_client = LLMClient()

    client = llm_client if settings.llm_enabled else None
    results = [process_pair(p, client) for p in pairs]
    elapsed_ms = (time.perf_counter() - start) * 1000

    summary = BatchSummary(
        total=len(results),
        low=sum(1 for r in results if r.risk_level == RiskLevel.LOW),
        medium=sum(1 for r in results if r.risk_level == RiskLevel.MEDIUM),
        high=sum(1 for r in results if r.risk_level == RiskLevel.HIGH),
        critical=sum(1 for r in results if r.risk_level == RiskLevel.CRITICAL),
        llm_analyzed=sum(1 for r in results if r.llm_insights),
        processing_time_ms=round(elapsed_ms, 1),
    )
    return results, summary
