from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.adaptor.storage.memory import InMemoryReviewStore
from app.domain.models.portfolio import PortfolioSummary
from app.domain.services.portfolio_analyzer import analyze_portfolio
from app.infra.deps import get_review_store

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class PortfolioRequest(BaseModel):
    policy_numbers: list[str]


@router.post("/analyze", response_model=PortfolioSummary)
def analyze(
    request: PortfolioRequest,
    store: InMemoryReviewStore = Depends(get_review_store),
) -> PortfolioSummary:
    if len(request.policy_numbers) < 2:
        raise HTTPException(
            status_code=422,
            detail="Portfolio analysis requires at least 2 policies",
        )

    try:
        summary = analyze_portfolio(request.policy_numbers, store)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return summary
