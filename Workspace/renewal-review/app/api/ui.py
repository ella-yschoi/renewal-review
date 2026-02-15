from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates

from app.adaptor.storage.memory import InMemoryHistoryStore, InMemoryReviewStore
from app.domain.models.review import BatchSummary, ReviewResult, RiskLevel
from app.domain.services.analytics import compute_trends
from app.infra.deps import get_history_store, get_last_summary, get_review_store

router = APIRouter(tags=["ui"])

_RISK_SEVERITY = {
    RiskLevel.NO_ACTION_NEEDED: 0,
    RiskLevel.REVIEW_RECOMMENDED: 1,
    RiskLevel.ACTION_REQUIRED: 2,
    RiskLevel.URGENT_REVIEW: 3,
}

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

PAGE_SIZE = 50


@router.get("/")
def dashboard(
    request: Request,
    page: int = Query(1, ge=1),
    store: InMemoryReviewStore = Depends(get_review_store),
    last_summary: BatchSummary | None = Depends(get_last_summary),
):
    all_results = sorted(store.values(), key=lambda r: _RISK_SEVERITY[r.risk_level], reverse=True)

    total = len(all_results)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    start = (page - 1) * PAGE_SIZE
    results = all_results[start : start + PAGE_SIZE]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active": "dashboard",
            "summary": last_summary,
            "results": results,
            "page": page,
            "total_pages": total_pages,
            "total_results": total,
        },
    )


_BACK_LINKS = {
    "quotes": ("/ui/quotes", "Back to Quote Generator"),
    "portfolio": ("/ui/portfolio", "Back to Portfolio"),
}
_DEFAULT_BACK = ("/", "Back to Dashboard")


@router.get("/ui/review/{policy_number}")
def review_detail(
    request: Request,
    policy_number: str,
    ref: str = Query(""),
    store: InMemoryReviewStore = Depends(get_review_store),
):
    result = store.get(policy_number)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No review found for {policy_number}")
    back_url, back_label = _BACK_LINKS.get(ref, _DEFAULT_BACK)
    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "active": ref or "dashboard",
            "result": result,
            "back_url": back_url,
            "back_label": back_label,
        },
    )


@router.get("/ui/analytics")
def analytics_page(
    request: Request,
    history: InMemoryHistoryStore = Depends(get_history_store),
):
    records = history.list()
    summary = compute_trends(records)
    return templates.TemplateResponse(
        "analytics.html",
        {"request": request, "active": "analytics", "history": records, "summary": summary},
    )


@router.get("/ui/quotes")
def quotes_page(
    request: Request,
    page: int = Query(1, ge=1),
    store: InMemoryReviewStore = Depends(get_review_store),
):
    flagged: list[ReviewResult] = [
        r for r in store.values() if r.diff.flags and r.pair is not None
    ]
    flagged.sort(key=lambda r: _RISK_SEVERITY[r.risk_level], reverse=True)

    total = len(flagged)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    start = (page - 1) * PAGE_SIZE
    results = flagged[start : start + PAGE_SIZE]

    return templates.TemplateResponse(
        "quotes.html",
        {
            "request": request,
            "active": "quotes",
            "flagged_results": results,
            "page": page,
            "total_pages": total_pages,
            "total_flagged": total,
        },
    )


@router.get("/ui/portfolio")
def portfolio_page(
    request: Request,
    page: int = Query(1, ge=1),
    store: InMemoryReviewStore = Depends(get_review_store),
):
    all_results = sorted(store.values(), key=lambda r: _RISK_SEVERITY[r.risk_level], reverse=True)
    total = len(all_results)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    start = (page - 1) * PAGE_SIZE
    results = all_results[start : start + PAGE_SIZE]
    return templates.TemplateResponse(
        "portfolio.html",
        {
            "request": request,
            "active": "portfolio",
            "results": results,
            "page": page,
            "total_pages": total_pages,
            "total_results": total,
        },
    )


@router.get("/ui/insight")
def insight_page(request: Request):
    return templates.TemplateResponse(
        "migration.html",
        {"request": request, "active": "insight"},
    )
