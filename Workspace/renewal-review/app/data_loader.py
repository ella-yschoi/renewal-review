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
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.models.db_models import RenewalPairRow

    sync_url = settings.db_url.replace("+asyncpg", "+psycopg")
    engine = create_engine(sync_url)

    try:
        with Session(engine) as session:
            rows = session.execute(select(RenewalPairRow)).scalars().all()
    except Exception:
        engine.dispose()
        return _load_from_json()

    engine.dispose()

    pairs = []
    for row in rows:
        pair = parse_pair({"prior": row.prior_json, "renewal": row.renewal_json})
        pairs.append(pair)
    return pairs


def invalidate_cache():
    global _cached_pairs
    _cached_pairs = None
