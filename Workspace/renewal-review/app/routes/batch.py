import json
import random
from pathlib import Path

from fastapi import APIRouter, Query

from app.config import settings
from app.engine.batch import process_batch
from app.engine.parser import parse_pair
from app.models.review import BatchSummary
from app.routes.reviews import get_results_store

router = APIRouter(prefix="/batch", tags=["batch"])

_last_summary: BatchSummary | None = None


def _load_pairs(sample: int | None = None) -> list:
    data_path = Path(settings.data_path)
    if not data_path.exists():
        return []
    raw_pairs = json.loads(data_path.read_text())
    if sample and sample < len(raw_pairs):
        raw_pairs = random.sample(raw_pairs, sample)
    return [parse_pair(rp) for rp in raw_pairs]


@router.post("/run")
def run_batch(sample: int | None = Query(None, ge=1)) -> dict:
    global _last_summary
    pairs = _load_pairs(sample)
    if not pairs:
        return {"error": "No data found. Run data/generate.py first."}

    results, summary = process_batch(pairs)
    _last_summary = summary

    store = get_results_store()
    for r in results:
        store[r.policy_number] = r

    return {
        "processed": summary.total,
        "summary": summary.model_dump(),
    }


@router.get("/summary", response_model=BatchSummary | None)
def get_summary() -> BatchSummary | None:
    return _last_summary
