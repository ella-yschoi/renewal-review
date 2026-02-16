from fastapi import APIRouter, Depends

from app.adaptor.storage.memory import InMemoryHistoryStore, InMemoryReviewStore
from app.data_loader import total_count
from app.domain.models.analytics import AnalyticsSummary, BatchRunRecord, BrokerMetrics
from app.domain.services.analytics import compute_broker_metrics, compute_trends
from app.infra.deps import get_history_store, get_review_store

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


@router.get("/broker", response_model=BrokerMetrics)
def get_broker_metrics(
    store: InMemoryReviewStore = Depends(get_review_store),
) -> BrokerMetrics:
    return compute_broker_metrics(list(store.values()), total_count())
