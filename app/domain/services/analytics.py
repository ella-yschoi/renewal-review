from collections import defaultdict

from app.domain.models.analytics import AnalyticsSummary, BatchRunRecord, TrendPoint


def compute_trends(records: list[BatchRunRecord]) -> AnalyticsSummary:
    if not records:
        return AnalyticsSummary(
            total_runs=0,
            total_policies_reviewed=0,
            avg_processing_time_ms=0.0,
            risk_distribution={
                "no_action_needed": 0,
                "review_recommended": 0,
                "action_required": 0,
                "urgent_review": 0,
            },
            trends=[],
        )

    total_policies = sum(r.total for r in records)
    avg_time = sum(r.processing_time_ms for r in records) / len(records)

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
                avg_processing_time_ms=round(
                    sum(r.processing_time_ms for r in day_records) / len(day_records), 1
                ),
                urgent_review_ratio=round(day_urgent_review / day_total, 4) if day_total else 0.0,
            )
        )

    return AnalyticsSummary(
        total_runs=len(records),
        total_policies_reviewed=total_policies,
        avg_processing_time_ms=round(avg_time, 1),
        risk_distribution=risk_distribution,
        trends=trends,
    )
