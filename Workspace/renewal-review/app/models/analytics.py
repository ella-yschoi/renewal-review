from datetime import datetime

from pydantic import BaseModel


class BatchRunRecord(BaseModel):
    job_id: str
    total: int
    low: int
    medium: int
    high: int
    critical: int
    processing_time_ms: float
    created_at: datetime


class TrendPoint(BaseModel):
    date: str
    total_runs: int
    avg_processing_time_ms: float
    critical_ratio: float


class AnalyticsSummary(BaseModel):
    total_runs: int
    total_policies_reviewed: int
    avg_processing_time_ms: float
    risk_distribution: dict[str, int]
    trends: list[TrendPoint]
