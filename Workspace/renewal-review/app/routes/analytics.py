from fastapi import APIRouter

from app.engine.analytics import compute_trends
from app.models.analytics import AnalyticsSummary, BatchRunRecord

router = APIRouter(prefix="/analytics", tags=["analytics"])

_history: list[BatchRunRecord] = []


def get_history_store() -> list[BatchRunRecord]:
    return _history


@router.get("/history", response_model=list[BatchRunRecord])
def get_history() -> list[BatchRunRecord]:
    return _history


@router.get("/trends", response_model=AnalyticsSummary)
def get_trends() -> AnalyticsSummary:
    return compute_trends(_history)
