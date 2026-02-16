from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from app.domain.models.analytics import AnalyticsSummary, BatchRunRecord, BrokerMetrics, TrendPoint

if TYPE_CHECKING:
    from app.domain.models.review import ReviewResult


def compute_trends(records: list[BatchRunRecord]) -> AnalyticsSummary:
    if not records:
        return AnalyticsSummary(
            total_runs=0,
            total_policies_reviewed=0,
            risk_distribution={
                "no_action_needed": 0,
                "review_recommended": 0,
                "action_required": 0,
                "urgent_review": 0,
            },
            trends=[],
        )

    total_policies = sum(r.total for r in records)

    risk_distribution = {
        "no_action_needed": sum(r.no_action_needed for r in records),
        "review_recommended": sum(r.review_recommended for r in records),
        "action_required": sum(r.action_required for r in records),
        "urgent_review": sum(r.urgent_review for r in records),
    }

    by_date: dict[str, list[BatchRunRecord]] = defaultdict(list)
    for r in records:
        day = r.created_at.strftime("%Y-%m-%d")
        by_date[day].append(r)

    trends = []
    for day in sorted(by_date):
        day_records = by_date[day]
        day_total = sum(r.total for r in day_records)
        day_urgent_review = sum(r.urgent_review for r in day_records)
        trends.append(
            TrendPoint(
                date=day,
                total_runs=len(day_records),
                urgent_review_ratio=round(day_urgent_review / day_total, 4) if day_total else 0.0,
            )
        )

    return AnalyticsSummary(
        total_runs=len(records),
        total_policies_reviewed=total_policies,
        risk_distribution=risk_distribution,
        trends=trends,
    )


def compute_broker_metrics(results: list[ReviewResult], total_policies: int = 0) -> BrokerMetrics:
    reviewed_count = sum(1 for r in results if r.reviewed_at is not None)
    total = max(total_policies, reviewed_count)
    pending = total - reviewed_count
    contact_needed = sum(1 for r in results if r.diff.flags and not r.broker_contacted)
    contacted = sum(1 for r in results if r.broker_contacted)
    quotes_generated = sum(1 for r in results if r.quote_generated)
    reviewed = sum(1 for r in results if r.reviewed_at is not None)
    return BrokerMetrics(
        total=total,
        pending=pending,
        contact_needed=contact_needed,
        contacted=contacted,
        quotes_generated=quotes_generated,
        reviewed=reviewed,
    )
