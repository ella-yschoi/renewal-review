from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.config import settings
from app.engine.batch import enrich_with_llm, process_pair
from app.engine.parser import parse_pair
from app.models.review import ReviewResult

router = APIRouter(prefix="/reviews", tags=["reviews"])

_results_store: dict[str, ReviewResult] = {}


def get_results_store() -> dict[str, ReviewResult]:
    return _results_store


def _lazy_enrich(result: ReviewResult) -> None:
    if not settings.llm_enabled:
        return
    if result.llm_summary_generated:
        return
    if not result.diff.flags:
        return

    from app.llm.client import LLMClient

    enrich_with_llm(result, LLMClient())


@router.post("/compare", response_model=ReviewResult)
def compare(raw_pair: dict) -> ReviewResult:
    try:
        pair = parse_pair(raw_pair)
    except (KeyError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid renewal pair: {e}") from e

    result = process_pair(pair)
    _results_store[result.policy_number] = result
    return result


@router.get("/{policy_number}", response_model=ReviewResult)
def get_review(policy_number: str) -> ReviewResult:
    result = _results_store.get(policy_number)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No review found for {policy_number}")
    _lazy_enrich(result)
    return result
