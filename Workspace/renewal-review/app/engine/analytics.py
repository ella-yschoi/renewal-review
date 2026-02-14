from collections import defaultdict

from app.models.analytics import AnalyticsSummary, BatchRunRecord, TrendPoint


def compute_trends(records: list[BatchRunRecord]) -> AnalyticsSummary:
    if not records:
        return AnalyticsSummary(
            total_runs=0,
            total_policies_reviewed=0,
            avg_processing_time_ms=0.0,
            risk_distribution={"low": 0, "medium": 0, "high": 0, "critical": 0},
            trends=[],
        )

    total_policies = sum(r.total for r in records)
    avg_time = sum(r.processing_time_ms for r in records) / len(records)

    risk_distribution = {
        "low": sum(r.low for r in records),
        "medium": sum(r.medium for r in records),
        "high": sum(r.high for r in records),
        "critical": sum(r.critical for r in records),
    }

    by_date: dict[str, list[BatchRunRecord]] = defaultdict(list)
    for r in records:
        day = r.created_at.strftime("%Y-%m-%d")
        by_date[day].append(r)

    trends = []
    for day in sorted(by_date):
        day_records = by_date[day]
        day_total = sum(r.total for r in day_records)
        day_critical = sum(r.critical for r in day_records)
        trends.append(
            TrendPoint(
                date=day,
                total_runs=len(day_records),
                avg_processing_time_ms=round(
                    sum(r.processing_time_ms for r in day_records) / len(day_records), 1
                ),
                critical_ratio=round(day_critical / day_total, 4) if day_total else 0.0,
            )
        )

    return AnalyticsSummary(
        total_runs=len(records),
        total_policies_reviewed=total_policies,
        avg_processing_time_ms=round(avg_time, 1),
        risk_distribution=risk_distribution,
        trends=trends,
    )
