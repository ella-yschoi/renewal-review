from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.engine.portfolio_analyzer import analyze_portfolio
from app.models.portfolio import PortfolioSummary
from app.routes.reviews import get_results_store

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class PortfolioRequest(BaseModel):
    policy_numbers: list[str]


@router.post("/analyze", response_model=PortfolioSummary)
def analyze(request: PortfolioRequest) -> PortfolioSummary:
    if len(request.policy_numbers) < 2:
        raise HTTPException(
            status_code=422,
            detail="Portfolio analysis requires at least 2 policies",
        )

    store = get_results_store()
    try:
        return analyze_portfolio(request.policy_numbers, store)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
