"""Add quotes_json column to rule_results table."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.config import settings  # noqa: E402
from app.infra.db import get_engine  # noqa: E402


async def migrate():
    if not settings.db_url:
        print("ERROR: RR_DB_URL not set. Add it to .env or export it.")
        sys.exit(1)

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text("ALTER TABLE rule_results ADD COLUMN IF NOT EXISTS quotes_json JSON DEFAULT '[]'")
        )
    await engine.dispose()
    print("OK: quotes_json column added to rule_results")


if __name__ == "__main__":
    asyncio.run(migrate())
