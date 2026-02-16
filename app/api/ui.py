import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates

from app.adaptor.storage.memory import InMemoryReviewStore
from app.data_loader import invalidate_cache, load_pairs, total_count
from app.domain.labels import LABELS, get_label
from app.domain.models.diff import DiffResult
from app.domain.models.review import ReviewResult, RiskLevel
from app.domain.services.analytics import compute_broker_metrics
from app.infra.deps import get_review_store

router = APIRouter(tags=["ui"])

_RISK_SEVERITY = {
    RiskLevel.NO_ACTION_NEEDED: 0,
    RiskLevel.REVIEW_RECOMMENDED: 1,
    RiskLevel.ACTION_REQUIRED: 2,
    RiskLevel.URGENT_REVIEW: 3,
}

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["label"] = get_label
templates.env.globals["labels_json"] = json.dumps(LABELS)

PAGE_SIZE = 50


def _pending_row(policy_number: str, pair):
    return ReviewResult(
        policy_number=policy_number,
        risk_level=RiskLevel.NO_ACTION_NEEDED,
        diff=DiffResult(policy_number=policy_number, changes=[], flags=[]),
        pair=pair,
    )


@router.get("/")
def dashboard(
    request: Request,
    page: int = Query(1, ge=1),
    risk: str = Query("", description="Filter by risk level"),
    contacted: str = Query("", description="Filter by contacted status"),
    quoted: str = Query("", description="Filter by quote status"),
    reviewed: str = Query("", description="Filter by reviewed status"),
    llm: str = Query("", description="Filter by LLM analysis status"),
    sort: str = Query("", description="Sort column"),
    order: str = Query("asc", description="Sort order"),
    store: InMemoryReviewStore = Depends(get_review_store),
):
    all_pairs = load_pairs()
    data_total = total_count()

    reviewed_pns: set[str] = set()
    reviewed_rows: list[ReviewResult] = []
    for result in store.values():
        reviewed_pns.add(result.policy_number)
        reviewed_rows.append(result)

    unreviewed_rows = [
        _pending_row(p.prior.policy_number, p)
        for p in all_pairs
        if p.prior.policy_number not in reviewed_pns
    ]

    reviewed_rows.sort(key=lambda r: _RISK_SEVERITY[r.risk_level], reverse=True)

    actually_reviewed = [r for r in reviewed_rows if r.reviewed_at is not None]

    def _count(level: RiskLevel) -> int:
        return sum(1 for r in actually_reviewed if r.risk_level == level)

    risk_dist = {
        "pending": data_total - len(actually_reviewed),
        "no_action_needed": _count(RiskLevel.NO_ACTION_NEEDED),
        "review_recommended": _count(RiskLevel.REVIEW_RECOMMENDED),
        "action_required": _count(RiskLevel.ACTION_REQUIRED),
        "urgent_review": _count(RiskLevel.URGENT_REVIEW),
    }
    risk_dist["total"] = sum(risk_dist.values())

    has_filter = bool(risk or contacted or quoted or reviewed or llm)
    if has_filter:
        combined = list(unreviewed_rows) + list(reviewed_rows)
        if reviewed == "yes":
            combined = [r for r in combined if r.reviewed_at is not None]
        elif reviewed == "no":
            combined = [r for r in combined if r.reviewed_at is None]
        if risk:
            combined = [r for r in combined if r.risk_level.value == risk]
        if contacted == "yes":
            combined = [r for r in combined if r.broker_contacted]
        elif contacted == "no":
            combined = [r for r in combined if not r.broker_contacted]
        if quoted == "yes":
            combined = [r for r in combined if r.quote_generated]
        elif quoted == "no":
            combined = [r for r in combined if not r.quote_generated]
        if llm == "yes":
            combined = [r for r in combined if r.llm_insights]
        elif llm == "no":
            combined = [r for r in combined if not r.llm_insights]
        all_results = combined
    else:
        all_results = unreviewed_rows + reviewed_rows

    if sort == "account":
        all_results.sort(
            key=lambda r: (r.pair.renewal.insured_name if r.pair else "").lower(),
            reverse=(order == "desc"),
        )

    total = len(all_results)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    start = (page - 1) * PAGE_SIZE
    results = all_results[start : start + PAGE_SIZE]

    broker = compute_broker_metrics(list(store.values()), data_total)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active": "dashboard",
            "risk_dist": risk_dist,
            "results": results,
            "page": page,
            "total_pages": total_pages,
            "total_results": total,
            "filter_risk": risk,
            "filter_contacted": contacted,
            "filter_quoted": quoted,
            "filter_reviewed": reviewed,
            "filter_llm": llm,
            "sort": sort,
            "order": order,
            "broker": broker,
            "data_total": data_total,
        },
    )


_BACK_LINKS = {
    "portfolio": ("/ui/portfolio", "Back to Portfolio"),
    "insight": ("/ui/insight", "Back to LLM Insights"),
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


def _extract_account_lookup(
    pairs: list,
) -> dict[str, tuple[str, str]]:
    lookup: dict[str, tuple[str, str]] = {}
    for p in pairs:
        if p.renewal.account_id:
            lookup[p.prior.policy_number] = (
                p.renewal.account_id,
                p.renewal.insured_name,
            )
    return lookup


def _build_account_lookup() -> dict[str, tuple[str, str]]:
    pairs = load_pairs()
    lookup = _extract_account_lookup(pairs)
    if not lookup and pairs:
        # Cache may hold stale data from before account_id was added
        invalidate_cache()
        lookup = _extract_account_lookup(load_pairs())
    return lookup


@router.get("/ui/portfolio")
def portfolio_page(
    request: Request,
    page: int = Query(1, ge=1),
    sort: str = Query("", description="Sort column"),
    order: str = Query("asc", description="Sort order"),
    store: InMemoryReviewStore = Depends(get_review_store),
):
    all_results = list(store.values())

    # Build lookup from current data source for account enrichment
    acct_lookup = _build_account_lookup()

    # Group by account_id (prefer stored pair, fallback to data source)
    account_map: dict[str, list] = {}
    account_names: dict[str, str] = {}
    for r in all_results:
        acct = r.pair.renewal.account_id if r.pair else ""
        name = r.pair.renewal.insured_name if r.pair else ""

        # Enrich from data source if stored pair lacks account_id
        if not acct and r.policy_number in acct_lookup:
            acct, name = acct_lookup[r.policy_number]

        if not acct:
            acct = r.policy_number
        account_map.setdefault(acct, []).append(r)
        if name and acct not in account_names:
            account_names[acct] = name

    accounts = []
    for acct_id, results in account_map.items():
        has_auto = any(r.pair and r.pair.renewal.policy_type.value == "auto" for r in results)
        has_home = any(r.pair and r.pair.renewal.policy_type.value == "home" for r in results)
        if has_auto and has_home:
            acct_type = "Bundle"
        elif has_auto:
            acct_type = "Auto"
        else:
            acct_type = "Home"

        total_premium = sum(r.pair.renewal.premium for r in results if r.pair)
        highest_risk = max(results, key=lambda r: _RISK_SEVERITY[r.risk_level])
        insured_name = account_names.get(acct_id, results[0].policy_number)
        policy_numbers = [r.policy_number for r in results]

        accounts.append(
            {
                "account_id": acct_id,
                "insured_name": insured_name,
                "policy_count": len(results),
                "policy_numbers": policy_numbers,
                "type": acct_type,
                "total_premium": total_premium,
                "highest_risk": highest_risk.risk_level,
            }
        )

    if sort == "account":
        accounts.sort(
            key=lambda a: a["insured_name"].lower(),
            reverse=(order == "desc"),
        )
    else:
        accounts.sort(key=lambda a: _RISK_SEVERITY[a["highest_risk"]], reverse=True)

    total = len(accounts)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    start = (page - 1) * PAGE_SIZE
    page_accounts = accounts[start : start + PAGE_SIZE]

    return templates.TemplateResponse(
        "portfolio.html",
        {
            "request": request,
            "active": "portfolio",
            "accounts": page_accounts,
            "page": page,
            "total_pages": total_pages,
            "total_results": total,
            "sort": sort,
            "order": order,
        },
    )


@router.get("/ui/insight")
def insight_page(request: Request):
    return templates.TemplateResponse(
        "migration.html",
        {"request": request, "active": "insight"},
    )
