from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.application.batch import process_pair
from app.config import settings
from app.domain.models.quote import QuoteRecommendation
from app.domain.services.parser import parse_pair
from app.domain.services.quote_generator import generate_quotes

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.post("/generate", response_model=list[QuoteRecommendation])
def generate(raw_pair: dict) -> list[QuoteRecommendation]:
    try:
        pair = parse_pair(raw_pair)
    except (KeyError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid renewal pair: {e}") from e

    result = process_pair(pair)

    if not result.diff.flags:
        return []

    quotes = generate_quotes(pair, result.diff)

    if settings.llm_enabled and quotes:
        from app.adaptor.llm.client import LLMClient
        from app.adaptor.llm.quote_advisor import personalize_quotes

        client = LLMClient()
        quotes = personalize_quotes(client, quotes, pair)

    return quotes
