from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.routes.reviews import get_results_store

router = APIRouter(tags=["ui"])

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/")
def dashboard(request: Request):
    store = get_results_store()
    results = sorted(store.values(), key=lambda r: r.risk_level.value, reverse=True)

    # get last batch summary from batch route
    from app.routes.batch import _last_summary

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active": "dashboard",
            "summary": _last_summary,
            "results": results,
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
