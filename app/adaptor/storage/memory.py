from collections import deque

from app.domain.models.analytics import BatchRunRecord
from app.domain.models.review import BatchSummary, ReviewResult


class InMemoryReviewStore:
    def __init__(self):
        self._store: dict[str, ReviewResult] = {}

    def get(self, policy_number: str) -> ReviewResult | None:
        return self._store.get(policy_number)

    def set(self, policy_number: str, result: ReviewResult) -> None:
        self._store[policy_number] = result

    def clear(self) -> None:
        self._store.clear()

    def values(self) -> list[ReviewResult]:
        return list(self._store.values())

    def items(self) -> list[tuple[str, ReviewResult]]:
        return list(self._store.items())

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        return key in self._store

    def __getitem__(self, key: str) -> ReviewResult:
        return self._store[key]

    def __setitem__(self, key: str, value: ReviewResult) -> None:
        self._store[key] = value


class InMemoryHistoryStore:
    def __init__(self, maxlen: int = 100):
        self._store: deque[BatchRunRecord] = deque(maxlen=maxlen)

    def append(self, record: BatchRunRecord) -> None:
        self._store.append(record)

    def list(self) -> list[BatchRunRecord]:
        return list(self._store)

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)

    def __getitem__(self, index: int) -> BatchRunRecord:
        return self._store[index]


class InMemoryJobStore:
    def __init__(self):
        self._store: dict[str, dict] = {}
        self.last_summary: BatchSummary | None = None

    def get(self, job_id: str) -> dict | None:
        return self._store.get(job_id)

    def set(self, job_id: str, data: dict) -> None:
        self._store[job_id] = data
