from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from app.adaptor.storage.memory import InMemoryReviewStore
from app.application.batch import enrich_with_llm, process_pair
from app.application.llm_analysis import generate_summary
from app.domain.models.review import ReviewResult, RiskLevel
from app.domain.ports.result_writer import ResultWriter
from app.domain.services.parser import parse_pair
from app.infra.deps import get_llm_client, get_result_writer, get_review_store

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _lazy_enrich(result: ReviewResult) -> None:
    if result.llm_summary_generated:
        return
    if not result.diff.flags:
        return
    client = get_llm_client()
    if client is None:
        return
    if result.risk_level == RiskLevel.REVIEW_RECOMMENDED:
        enrich_with_llm(result, client)
    else:
        llm_summary = generate_summary(client, result)
        if llm_summary:
            result.summary = llm_summary
            result.llm_summary_generated = True
    if result.llm_summary_generated:
        writer = get_result_writer()
        writer.save_llm_result("enrich", result)


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


@router.patch("/{policy_number}/broker-contacted")
def toggle_broker_contacted(
    policy_number: str,
    store: InMemoryReviewStore = Depends(get_review_store),
    writer: ResultWriter = Depends(get_result_writer),
) -> dict:
    result = store.get(policy_number)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No review found for {policy_number}")
    result.broker_contacted = not result.broker_contacted
    writer.update_broker_contacted(policy_number, result.broker_contacted)
    return {"broker_contacted": result.broker_contacted}


@router.patch("/{policy_number}/quote-generated")
def toggle_quote_generated(
    policy_number: str,
    store: InMemoryReviewStore = Depends(get_review_store),
    writer: ResultWriter = Depends(get_result_writer),
) -> dict:
    result = store.get(policy_number)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No review found for {policy_number}")
    result.quote_generated = not result.quote_generated
    writer.update_quote_generated(policy_number, result.quote_generated)
    return {"quote_generated": result.quote_generated}


@router.patch("/{policy_number}/reviewed-at")
def mark_reviewed(
    policy_number: str,
    store: InMemoryReviewStore = Depends(get_review_store),
    writer: ResultWriter = Depends(get_result_writer),
) -> dict:
    result = store.get(policy_number)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No review found for {policy_number}")
    now = datetime.now(ZoneInfo("America/Vancouver"))
    result.reviewed_at = now
    writer.update_reviewed_at(policy_number, now)
    return {"reviewed_at": now.isoformat()}
