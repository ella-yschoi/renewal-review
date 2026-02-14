import asyncio
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
        _cached_pairs = _load_from_db() if settings.db_url else _load_from_json()

    if sample and sample < len(_cached_pairs):
        return random.sample(_cached_pairs, sample)
    return list(_cached_pairs)


def _load_from_json() -> list[RenewalPair]:
    data_path = Path(settings.data_path)
    if not data_path.exists():
        return []
    raw = json.loads(data_path.read_text())
    return [parse_pair(rp) for rp in raw]


def _load_from_db() -> list[RenewalPair]:
    from app.db import get_session_factory
    from app.models.db_models import RenewalPairRow

    factory = get_session_factory()
    if factory is None:
        return _load_from_json()

    async def _fetch():
        from sqlalchemy import select

        async with factory() as session:
            result = await session.execute(select(RenewalPairRow))
            rows = result.scalars().all()
        return rows

    try:
        rows = asyncio.run(_fetch())
    except RuntimeError:
        return _load_from_json()

    pairs = []
    for row in rows:
        pair = parse_pair({"prior": row.prior_json, "renewal": row.renewal_json})
        pairs.append(pair)
    return pairs


def invalidate_cache():
    global _cached_pairs
    _cached_pairs = None
