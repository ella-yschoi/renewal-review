from typing import Protocol

from app.domain.models.policy import RenewalPair


class DataSourcePort(Protocol):
    def load_pairs(self, sample: int | None = None) -> list[RenewalPair]: ...
    def invalidate_cache(self) -> None: ...
