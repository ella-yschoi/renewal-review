import json
import random
from pathlib import Path

from app.config import settings
from app.domain.models.policy import RenewalPair
from app.domain.services.parser import parse_pair


class JsonDataSource:
    def __init__(self):
        self._cached_pairs: list[RenewalPair] | None = None

    def load_pairs(self, sample: int | None = None) -> list[RenewalPair]:
        if self._cached_pairs is None:
            self._cached_pairs = self._load()

        if sample and sample < len(self._cached_pairs):
            return random.sample(self._cached_pairs, sample)
        return list(self._cached_pairs)

    def _load(self) -> list[RenewalPair]:
        data_path = Path(settings.data_path)
        if not data_path.exists():
            return []
        raw = json.loads(data_path.read_text())
        return [parse_pair(rp) for rp in raw]

    def total_count(self) -> int:
        if self._cached_pairs is None:
            self._cached_pairs = self._load()
        return len(self._cached_pairs)

    def invalidate_cache(self) -> None:
        self._cached_pairs = None
