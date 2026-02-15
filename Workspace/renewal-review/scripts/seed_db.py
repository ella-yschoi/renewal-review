"""Seed PostgreSQL with renewal pairs from data/renewals.json."""

import asyncio
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.infra.db import Base, get_engine, get_session_factory  # noqa: E402
from app.infra.db_models import RenewalPairRow  # noqa: E402


async def seed():
    if not settings.db_url:
        print("ERROR: RR_DB_URL not set. Add it to .env or export it.")
        sys.exit(1)

    data_path = Path(__file__).resolve().parent.parent / "data" / "renewals.json"
    if not data_path.exists():
        print(f"ERROR: {data_path} not found. Run data/generate.py first.")
        sys.exit(1)

    raw = json.loads(data_path.read_text())
    print(f"Loaded {len(raw)} pairs from {data_path}")

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

    factory = get_session_factory()
    batch_size = 500
    inserted = 0

    for i in range(0, len(raw), batch_size):
        chunk = raw[i : i + batch_size]
        async with factory() as session:
            for pair in chunk:
                prior = pair["prior"]
                renewal = pair["renewal"]
                row = RenewalPairRow(
                    policy_number=prior["policy_number"],
                    policy_type=prior["policy_type"],
                    carrier_prior=prior["carrier"],
                    carrier_renewal=renewal["carrier"],
                    premium_prior=float(prior["premium"]),
                    premium_renewal=float(renewal["premium"]),
                    effective_date_prior=date.fromisoformat(prior["effective_date"]),
                    effective_date_renewal=date.fromisoformat(renewal["effective_date"]),
                    state=prior.get("state", "CA"),
                    prior_json=prior,
                    renewal_json=renewal,
                )
                session.add(row)
            await session.commit()
            inserted += len(chunk)
            print(f"  Inserted {inserted}/{len(raw)}")

    print(f"Done. {inserted} rows in renewal_pairs table.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
