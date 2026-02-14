from datetime import datetime

from pydantic import BaseModel


class BatchRunRecord(BaseModel):
    job_id: str
    total: int
    no_action_needed: int
    review_recommended: int
    action_required: int
    urgent_review: int
    processing_time_ms: float
    created_at: datetime


class TrendPoint(BaseModel):
    date: str
    total_runs: int
    avg_processing_time_ms: float
    urgent_review_ratio: float


class AnalyticsSummary(BaseModel):
    total_runs: int
    total_policies_reviewed: int
    avg_processing_time_ms: float
    risk_distribution: dict[str, int]
    trends: list[TrendPoint]
