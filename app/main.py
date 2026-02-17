import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.analytics import router as analytics_router
from app.api.batch import router as batch_router
from app.api.eval import router as eval_router
from app.api.portfolio import router as portfolio_router
from app.api.quotes import router as quotes_router
from app.api.reviews import router as reviews_router
from app.api.ui import router as ui_router
from app.infra.db import init_db

logger = logging.getLogger(__name__)


def _restore_cache_from_db() -> None:
    from app.data_loader import load_pairs
    from app.domain.models.diff import DiffFlag, DiffResult, FieldChange
    from app.domain.models.review import LLMInsight, ReviewResult, RiskLevel
    from app.infra.deps import get_result_writer, get_review_store

    writer = get_result_writer()
    rows = writer.load_latest_results()
    if not rows:
        return

    pairs_by_pn = {p.prior.policy_number: p for p in load_pairs()}

    llm_by_pn: dict[str, dict] = {}
    for lr in writer.load_latest_llm_results():
        llm_by_pn[lr["policy_number"]] = lr

    store = get_review_store()
    for row in rows:
        pn = row["policy_number"]
        changes = [FieldChange(**c) for c in (row["changes_json"] or [])]
        flags = [DiffFlag(f) for f in (row["flags_json"] or [])]
        diff = DiffResult(policy_number=pn, changes=changes, flags=flags)

        llm_row = llm_by_pn.get(pn)
        llm_insights = []
        llm_summary_generated = False
        risk_level = row["risk_level"]
        summary = row.get("summary_text", "")

        if llm_row:
            llm_insights = [LLMInsight(**i) for i in (llm_row["insights_json"] or [])]
            llm_summary_generated = bool(llm_insights or llm_row.get("summary_text"))
            if llm_row.get("summary_text"):
                summary = llm_row["summary_text"]
            if llm_row.get("risk_level"):
                risk_level = llm_row["risk_level"]

        result = ReviewResult(
            policy_number=pn,
            risk_level=RiskLevel(risk_level),
            diff=diff,
            summary=summary,
            llm_insights=llm_insights,
            llm_summary_generated=llm_summary_generated,
            pair=pairs_by_pn.get(pn),
            broker_contacted=row.get("broker_contacted", False),
            quote_generated=row.get("quote_generated", False),
            reviewed_at=row.get("reviewed_at"),
        )
        store[result.policy_number] = result

    logger.info("Restored %d results from DB cache", len(rows))


def _restore_comparison_from_db() -> None:
    from app.api import eval as eval_module
    from app.infra.deps import get_result_writer

    writer = get_result_writer()
    saved = writer.load_latest_comparison()
    if saved is not None:
        eval_module._last_comparison = saved
        logger.info("Restored latest comparison result from DB")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    try:
        _restore_cache_from_db()
    except Exception:
        logger.warning("Could not restore cache from DB, starting fresh")
    try:
        _restore_comparison_from_db()
    except Exception:
        logger.warning("Could not restore comparison from DB")
    yield


app = FastAPI(
    title="Renewal Review",
    description="Insurance renewal review pipeline — rule-based + LLM hybrid",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(ui_router)
app.include_router(reviews_router)
app.include_router(batch_router)
app.include_router(eval_router)
app.include_router(analytics_router)
app.include_router(quotes_router)
app.include_router(portfolio_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}
