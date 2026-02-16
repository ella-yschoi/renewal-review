from app.adaptor.storage.memory import (
    InMemoryHistoryStore,
    InMemoryJobStore,
    InMemoryReviewStore,
)
from app.domain.models.review import BatchSummary
from app.domain.ports.llm import LLMPort
from app.domain.ports.result_writer import ResultWriter

_review_store = InMemoryReviewStore()
_history_store = InMemoryHistoryStore()
_job_store = InMemoryJobStore()

_llm_client: LLMPort | None = None
_result_writer: ResultWriter | None = None


def get_review_store() -> InMemoryReviewStore:
    return _review_store


def get_history_store() -> InMemoryHistoryStore:
    return _history_store


def get_job_store() -> InMemoryJobStore:
    return _job_store


def get_last_summary() -> BatchSummary | None:
    return _job_store.last_summary


def get_result_writer() -> ResultWriter:
    global _result_writer
    if _result_writer is None:
        from app.config import settings

        if settings.db_url:
            from app.adaptor.persistence.db_writer import DbResultWriter

            _result_writer = DbResultWriter()
        else:
            from app.adaptor.persistence.noop_writer import NoopResultWriter

            _result_writer = NoopResultWriter()
    return _result_writer


def get_llm_client() -> LLMPort | None:
    from app.config import settings

    if not settings.llm_enabled:
        return None

    global _llm_client
    if _llm_client is None:
        from app.adaptor.llm.client import LLMClient

        _llm_client = LLMClient()
    return _llm_client
