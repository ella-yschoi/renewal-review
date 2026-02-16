from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.application.batch import process_pair
from app.domain.services.parser import parse_pair
from app.domain.services.quote_generator import explain_no_quotes, generate_quotes
from app.infra.deps import get_llm_client

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.post("/generate")
def generate(raw_pair: dict) -> dict:
    try:
        pair = parse_pair(raw_pair)
    except (KeyError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid renewal pair: {e}") from e

    result = process_pair(pair)

    if not result.diff.flags:
        return {"quotes": [], "reasons": []}

    quotes = generate_quotes(pair, result.diff)

    if not quotes:
        return {"quotes": [], "reasons": explain_no_quotes(pair)}

    client = get_llm_client()
    if client and quotes:
        from app.application.quote_advisor import personalize_quotes

        quotes = personalize_quotes(client, quotes, pair)

    return {"quotes": [q.model_dump() for q in quotes], "reasons": []}
