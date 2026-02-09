import json
import random
from pathlib import Path

from app.config import settings
from app.engine.parser import parse_pair
from app.models.policy import RenewalPair

_cached_pairs: list[RenewalPair] | None = None


def load_pairs(sample: int | None = None) -> list[RenewalPair]:
    global _cached_pairs
    if _cached_pairs is None:
        data_path = Path(settings.data_path)
        if not data_path.exists():
            return []
        raw = json.loads(data_path.read_text())
        _cached_pairs = [parse_pair(rp) for rp in raw]

    if sample and sample < len(_cached_pairs):
        return random.sample(_cached_pairs, sample)
    return list(_cached_pairs)


def invalidate_cache():
    global _cached_pairs
    _cached_pairs = None
