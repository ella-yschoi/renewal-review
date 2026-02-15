from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.config import settings
from app.engine.batch import process_pair
from app.engine.parser import parse_pair
from app.engine.quote_generator import generate_quotes
from app.models.quote import QuoteRecommendation

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
        from app.llm.client import LLMClient
        from app.llm.quote_advisor import personalize_quotes

        client = LLMClient()
        quotes = personalize_quotes(client, quotes, pair)

    return quotes
