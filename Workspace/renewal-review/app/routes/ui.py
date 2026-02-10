from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates

from app.routes.reviews import get_results_store

router = APIRouter(tags=["ui"])

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

PAGE_SIZE = 50


@router.get("/")
def dashboard(request: Request, page: int = Query(1, ge=1)):
    store = get_results_store()
    all_results = sorted(store.values(), key=lambda r: r.risk_level.value, reverse=True)

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


@router.get("/ui/migration")
def migration_page(request: Request):
    return templates.TemplateResponse(
        "migration.html",
        {"request": request, "active": "migration"},
    )
