import random

from app.config import settings
from app.domain.models.policy import RenewalPair
from app.domain.services.parser import parse_pair


class DbDataSource:
    def __init__(self):
        self._cached_pairs: list[RenewalPair] | None = None

    def load_pairs(self, sample: int | None = None) -> list[RenewalPair]:
        if self._cached_pairs is None:
            self._cached_pairs = self._load()

        if sample and sample < len(self._cached_pairs):
            return random.sample(self._cached_pairs, sample)
        return list(self._cached_pairs)

    def _load(self) -> list[RenewalPair]:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        from app.adaptor.persistence.json_loader import JsonDataSource
        from app.infra.db_models import RenewalPairRow

        sync_url = settings.db_url.replace("+asyncpg", "+psycopg")
        engine = create_engine(sync_url)

        try:
            with Session(engine) as session:
                rows = session.execute(select(RenewalPairRow)).scalars().all()
        except Exception:
            engine.dispose()
            return JsonDataSource()._load()

        engine.dispose()
        return [parse_pair({"prior": row.prior_json, "renewal": row.renewal_json}) for row in rows]

    def invalidate_cache(self) -> None:
        self._cached_pairs = None
