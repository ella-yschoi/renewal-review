from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
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
        summary = analyze_portfolio(request.policy_numbers, store)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    if settings.llm_enabled:
        from app.llm.client import LLMClient
        from app.llm.portfolio_advisor import enrich_portfolio

        results = [store[pn] for pn in request.policy_numbers if pn in store]
        summary = enrich_portfolio(LLMClient(), summary, results)

    return summary
