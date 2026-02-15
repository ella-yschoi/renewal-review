from fastapi import APIRouter, Depends

from app.adaptor.storage.memory import InMemoryHistoryStore
from app.domain.models.analytics import AnalyticsSummary, BatchRunRecord
from app.domain.services.analytics import compute_trends
from app.infra.deps import get_history_store

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/history", response_model=list[BatchRunRecord])
def get_history(
    history: InMemoryHistoryStore = Depends(get_history_store),
) -> list[BatchRunRecord]:
    return history.list()


@router.get("/trends", response_model=AnalyticsSummary)
def get_trends(
    history: InMemoryHistoryStore = Depends(get_history_store),
) -> AnalyticsSummary:
    return compute_trends(history.list())
