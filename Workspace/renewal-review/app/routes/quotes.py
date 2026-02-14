from fastapi import APIRouter

from app.engine.differ import compute_diff
from app.engine.quote_generator import generate_quotes
from app.engine.rules import flag_diff
from app.models.policy import RenewalPair
from app.models.quote import QuoteRecommendation

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.post("/generate", response_model=list[QuoteRecommendation])
def generate(pair: RenewalPair) -> list[QuoteRecommendation]:
    diff = compute_diff(pair)
    diff = flag_diff(diff, pair)
    if not diff.flags:
        return []
    return generate_quotes(pair, diff)
