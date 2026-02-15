from app.adaptor.storage.memory import (
    InMemoryHistoryStore,
    InMemoryJobStore,
    InMemoryReviewStore,
)
from app.domain.models.review import BatchSummary

_review_store = InMemoryReviewStore()
_history_store = InMemoryHistoryStore()
_job_store = InMemoryJobStore()


def get_review_store() -> InMemoryReviewStore:
    return _review_store


def get_history_store() -> InMemoryHistoryStore:
    return _history_store


def get_job_store() -> InMemoryJobStore:
    return _job_store


def get_last_summary() -> BatchSummary | None:
    return _job_store.last_summary
