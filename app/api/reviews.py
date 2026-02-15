from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from app.adaptor.storage.memory import InMemoryReviewStore
from app.application.batch import enrich_with_llm, process_pair
from app.config import settings
from app.domain.models.review import ReviewResult
from app.domain.services.parser import parse_pair
from app.infra.deps import get_review_store

router = APIRouter(prefix="/reviews", tags=["reviews"])


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
def compare(
    raw_pair: dict,
    store: InMemoryReviewStore = Depends(get_review_store),
) -> ReviewResult:
    try:
        pair = parse_pair(raw_pair)
    except (KeyError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid renewal pair: {e}") from e

    result = process_pair(pair)
    store[result.policy_number] = result
    return result


@router.get("/{policy_number}", response_model=ReviewResult)
def get_review(
    policy_number: str,
    store: InMemoryReviewStore = Depends(get_review_store),
) -> ReviewResult:
    result = store.get(policy_number)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No review found for {policy_number}")
    _lazy_enrich(result)
    return result
