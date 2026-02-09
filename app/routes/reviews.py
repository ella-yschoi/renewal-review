from fastapi import APIRouter, HTTPException

from app.engine.batch import process_pair
from app.engine.parser import parse_pair
from app.models.review import ReviewResult

router = APIRouter(prefix="/reviews", tags=["reviews"])

_results_store: dict[str, ReviewResult] = {}


def get_results_store() -> dict[str, ReviewResult]:
    return _results_store


@router.post("/compare", response_model=ReviewResult)
def compare(raw_pair: dict) -> ReviewResult:
    pair = parse_pair(raw_pair)
    result = process_pair(pair)
    _results_store[result.policy_number] = result
    return result


@router.get("/{policy_number}", response_model=ReviewResult)
def get_review(policy_number: str) -> ReviewResult:
    result = _results_store.get(policy_number)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No review found for {policy_number}")
    return result
