from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates

from app.engine.analytics import compute_trends
from app.models.review import ReviewResult, RiskLevel
from app.routes.analytics import get_history_store
from app.routes.reviews import get_results_store

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
def dashboard(request: Request, page: int = Query(1, ge=1)):
    store = get_results_store()
    all_results = sorted(store.values(), key=lambda r: _RISK_SEVERITY[r.risk_level], reverse=True)

    total = len(all_results)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    start = (page - 1) * PAGE_SIZE
    results = all_results[start : start + PAGE_SIZE]

    # get last batch summary from batch route
    from app.routes.batch import _last_summary

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active": "dashboard",
            "summary": _last_summary,
            "results": results,
            "page": page,
            "total_pages": total_pages,
            "total_results": total,
        },
    )


@router.get("/ui/review/{policy_number}")
def review_detail(request: Request, policy_number: str):
    store = get_results_store()
    result = store.get(policy_number)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No review found for {policy_number}")
    return templates.TemplateResponse(
        "review.html",
        {"request": request, "active": "dashboard", "result": result},
    )


@router.get("/ui/analytics")
def analytics_page(request: Request):
    history = get_history_store()
    summary = compute_trends(history)
    return templates.TemplateResponse(
        "analytics.html",
        {"request": request, "active": "analytics", "history": history, "summary": summary},
    )


@router.get("/ui/quotes")
def quotes_page(request: Request, page: int = Query(1, ge=1)):
    store = get_results_store()
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


@router.get("/ui/migration")
def migration_page(request: Request):
    return templates.TemplateResponse(
        "migration.html",
        {"request": request, "active": "migration"},
    )
