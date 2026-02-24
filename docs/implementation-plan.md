# Renewal Review — Implementation Plan

> PM Requirements: See `docs/requirements.md`

Defines the detailed rules, thresholds, data structures, error handling, etc. needed for implementation.

---

## 1. Data Structures

### Policy Fields

Each Policy Snapshot includes the following:

- **Common**: policy_number, policy_type(auto/home), carrier, effective_date, expiration_date, premium, state, notes
- **Auto**: auto_coverages (BI/PD limit, collision/comprehensive deductible, uninsured motorist, medical payments, rental reimbursement, roadside assistance), vehicles, drivers, endorsements
- **Home**: home_coverages (dwelling A~F, deductible, wind/hail deductible, water_backup, replacement_cost), endorsements

### Data Examples

**Auto — Premium Increase + Notes Added:**

```json
{
  "prior": {
    "policy_number": "AUTO-2024-2282",
    "policy_type": "auto",
    "carrier": "Progressive",
    "effective_date": "2024-10-25",
    "expiration_date": "2025-10-25",
    "premium": 3932.46,
    "state": "GA",
    "notes": "",
    "auto_coverages": {
      "bodily_injury_limit": "50/100",
      "property_damage_limit": "25",
      "collision_deductible": 250,
      "comprehensive_deductible": 100,
      "uninsured_motorist": "50/100",
      "medical_payments": 1000,
      "rental_reimbursement": false,
      "roadside_assistance": false
    },
    "vehicles": [
      { "vin": "9SWK6CG7Y8TS31GJS", "year": 2015, "make": "Toyota", "model": "Camry", "usage": "personal" }
    ],
    "drivers": [
      { "license_number": "D7013790", "name": "Driver 2282-0", "age": 49, "violations": 1, "sr22": false }
    ],
    "endorsements": []
  },
  "renewal": {
    "policy_number": "AUTO-2024-2282",
    "premium": 4474.13,
    "notes": "Bundle discount removed — auto policy moved to different carrier",
    "...rest unchanged..."
  }
}
```

Expected result: Premium +13.8% → `PREMIUM_INCREASE_HIGH` + `NOTES_CHANGED` → **Action Required**.

**Home — Endorsement Removed + Premium Decrease:**

```json
{
  "prior": {
    "policy_number": "HOME-2024-0495",
    "policy_type": "home",
    "carrier": "USAA",
    "premium": 3465.22,
    "endorsements": [
      { "code": "HO 04 95", "description": "Water backup and sump overflow coverage", "premium": 71.76 },
      { "code": "FL01", "description": "Flood insurance supplement", "premium": 61.41 }
    ]
  },
  "renewal": {
    "premium": 3308.99,
    "endorsements": [
      { "code": "HO 04 95", "description": "Water backup and sump overflow coverage", "premium": 71.76 }
    ]
  }
}
```

Expected result: Premium -4.5% → `PREMIUM_DECREASE` + `ENDORSEMENT_REMOVED` (FL01) → **Review Recommended**.

---

## 2. Basic Analytics — Comparison Rules

### Fields to Compare

| Category | Comparison Items |
|----------|-----------------|
| Common | premium, carrier, notes |
| Auto Coverage | BI/PD limit, collision/comprehensive deductible, uninsured motorist, medical payments, rental reimbursement, roadside assistance |
| Home Coverage | dwelling A~F, deductible, wind/hail deductible, water_backup, replacement_cost |
| Vehicles | Added/Removed (set comparison by VIN) |
| Drivers | Added/Removed (set comparison by license number) |
| Endorsements | Added/Removed, description/premium changes within the same code |

### Risk Flags

| Flag | Condition |
|------|-----------|
| Premium Increase — High | Premium increase rate ≥ 10% |
| Premium Increase — Critical | Premium increase rate ≥ 20% |
| Premium Decrease | Premium decreased |
| Carrier Change | Carrier changed |
| Liability Limit Decrease | Liability limit decreased (BI, PD, liability, UM) |
| Deductible Increase | Deductible increased |
| Coverage Dropped | Coverage amount decreased or boolean coverage removed (True→False) |
| Coverage Added | Boolean coverage added (False→True) |
| Vehicle Added / Removed | Vehicle added / removed |
| Driver Added / Removed | Driver added / removed |
| Endorsement Added / Removed | Endorsement added / removed |
| Notes Changed | Notes changed |

### Risk Levels

| Level | Condition |
|-------|-----------|
| Urgent Review | Premium Increase Critical or Liability Limit Decrease present |
| Action Required | Premium Increase High or Coverage Dropped present |
| Review Recommended | At least 1 flag, but Urgent Review/Action Required conditions not met |
| No Action Needed | No flags |

### Error Handling

- Prior or Renewal missing → Return which data is missing
- Required fields (policy_number, policy_type, carrier, effective_date, premium) missing → Error + missing fields
- Non-existent policy number lookup → 404

### Batch Concurrency

- New batch request while already running → Runs separately (not rejected)
- Last completed batch is displayed on Dashboard
- Error during processing → Entire batch fails (no partial success)
- Failed batch does not affect previous successful results

---

## 3. LLM Analytics — LLM Analysis Rules

### Analysis Target Selection

LLM is called when at least one condition is met:
- Notes changed + content present
- Endorsement description changed
- Home boolean coverage changed

Expected LLM target ratio: approximately 32% (primarily notes changes ~30%)

### Analysis Types

| Type | Input | Purpose |
|------|-------|---------|
| Risk Signal Extraction | Policy notes text | Extract risk signals from notes |
| Endorsement Comparison | Prior/Renewal endorsement descriptions | Determine nature of endorsement changes (expansion/restriction/neutral) |
| Coverage Similarity | Prior/Renewal coverage states | Determine coverage equivalency |

Each analysis returns a result, confidence (0–100%), and rationale.

### Risk Escalation

| Condition | Escalation |
|-----------|------------|
| High confidence "not equivalent" coverage determination | → Action Required or higher |
| 2 or more risk signals detected | → Action Required or higher |
| Endorsement change is a "restriction" | → Action Required or higher |
| Multiple conditions above met simultaneously | → Urgent Review |

> Confidence thresholds will be defined during the design phase.

### Cost Constraints

- Maximum 3 LLM calls per case
- Full batch of 8,000 cases: maximum ~$25
- Sample of 100 cases: maximum ~$0.30

### LLM Failure Handling

- Timeout/error/parsing failure → The case is decided by rule-based risk only
- LLM failure does not halt the entire batch
- Failed analyses are recorded as "analysis failed" and not reflected in risk escalation

### Eval

- Golden set: Tagged with expected minimum risk + expected flags
- Actual risk ≥ expected risk & all expected flags included → Pass
- Report overall pass rate as a percentage

### Migration Comparison

- Process the same data with Basic/LLM Analytics separately, display differences
- Items to verify: Risk distribution, processing time, number of LLM-analyzed cases, list of risk-changed cases
- Clicking a risk-changed case shows which LLM insight triggered the escalation

---

## 4. Batch Monitoring — History/Trends Implementation

### Existing Code Context

Existing code that this module integrates with:

**BatchSummary Model** (`app/models/review.py`):
```python
class BatchSummary(BaseModel):
    total: int
    no_action_needed: int = 0
    review_recommended: int = 0
    action_required: int = 0
    urgent_review: int = 0
    llm_analyzed: int = 0
    processing_time_ms: float = 0.0
```

**Batch Execution Flow** (`app/routes/batch.py`):
1. `POST /batch/run` → `load_pairs()` → calls `process_batch(pairs)`
2. `process_batch()` returns `(list[ReviewResult], BatchSummary)`
3. Results saved to `_results_store`, latest summary saved to `_last_summary`
4. Batch completes at `_jobs[job_id]["status"] = JobStatus.COMPLETED`

**UI Structure**:
- nav bar (`base.html`): Dashboard | Migration — two tabs
- Dashboard (`dashboard.html`): Batch run button, stats grid (6 cells), risk distribution bar, review list table
- stats grid pattern: `.stat-card > .value + .label` structure

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `app/models/analytics.py` | **Create** | BatchRunRecord, TrendPoint, AnalyticsSummary |
| `app/engine/analytics.py` | **Create** | compute_trends() pure function |
| `app/routes/analytics.py` | **Create** | GET /analytics/trends, /history + _history store |
| `app/routes/batch.py` | **Modify** | Add history append inside _process() |
| `app/routes/ui.py` | **Modify** | Add GET /ui/analytics route |
| `app/main.py` | **Modify** | Register analytics router |
| `app/templates/base.html` | **Modify** | Add Batch Monitoring link to nav bar |
| `app/templates/analytics.html` | **Create** | Batch Monitoring UI page |
| `tests/test_analytics.py` | **Create** | Unit + API integration tests |

### Layer Structure

```
models/analytics.py          ← Data structure definitions (no dependencies)
    ↑
engine/analytics.py          ← Business logic (imports only models)
    ↑
routes/analytics.py          ← HTTP endpoints + history store
    ↑                           (imports engine + models)
routes/batch.py              ← Appends to history on batch completion
    ↑                           (imports add_record from routes/analytics)
routes/ui.py                 ← Renders Batch Monitoring UI page
    ↑                           (imports from engine/analytics + routes/analytics)
main.py                      ← Router registration
```

**Dependency Rules:**
- `models/` → Does not import other layers
- `engine/` → Imports only `models/`
- `routes/` → Can import `engine/` + `models/`. Can only import data stores from other `routes/` modules
- No circular dependencies

### Data Models

**BatchRunRecord** (`app/models/analytics.py`) — Snapshot of a single batch run:

| Field | Type | Value Source |
|-------|------|-------------|
| `id` | `str` | `job_id` from `batch.py` (uuid[:8]) |
| `timestamp` | `datetime` | `datetime.now(UTC)` |
| `sample_size` | `int` | `len(pairs)` |
| `total` | `int` | `BatchSummary.total` |
| `no_action_needed` | `int` | `BatchSummary.no_action_needed` |
| `review_recommended` | `int` | `BatchSummary.review_recommended` |
| `action_required` | `int` | `BatchSummary.action_required` |
| `urgent_review` | `int` | `BatchSummary.urgent_review` |
| `llm_analyzed` | `int` | `BatchSummary.llm_analyzed` |
| `processing_time_ms` | `float` | `BatchSummary.processing_time_ms` |

**TrendPoint** (`app/models/analytics.py`) — A single time-series data point:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `datetime` | Measurement time (= BatchRunRecord.timestamp) |
| `metric_name` | `str` | `"urgent_review_rate"`, `"action_required_rate"`, `"avg_processing_ms"` |
| `value` | `float` | Rates are 0.0–100.0% |

**AnalyticsSummary** (`app/models/analytics.py`) — Aggregated analysis result:

| Field | Type | Description |
|-------|------|-------------|
| `total_runs` | `int` | Total number of batch runs |
| `avg_processing_time_ms` | `float` | Average processing time (rounded to 1 decimal place) |
| `risk_distribution` | `dict[str, float]` | Cumulative risk rates (%) — `{"no_action_needed": 15.2, ...}` |
| `trends` | `list[TrendPoint]` | Time series (ascending by timestamp) |

### Data Flow

```
1. POST /batch/run called
2. process_batch(pairs) executes → returns (results, summary)
3. Results saved to _results_store (existing behavior, no changes)
4. Saved to _last_summary (existing behavior, no changes)
5. [NEW] Create BatchRunRecord (map summary fields + job_id + timestamp)
6. [NEW] Append to _history (auto-remove oldest when exceeding 100 entries)
7. _jobs[job_id]["status"] = COMPLETED

--- On separate request ---

8. GET /analytics/trends → compute_trends(_history) → AnalyticsSummary
9. GET /analytics/history → _history[::-1] (newest first)
10. GET /ui/analytics → Render HTML with trends + history data
```

### History Store

**Location**: `app/routes/analytics.py` module level

```python
_history: list[BatchRunRecord] = []
MAX_HISTORY = 100

def add_record(record: BatchRunRecord) -> None:
    _history.append(record)
    if len(_history) > MAX_HISTORY:
        _history.pop(0)

def get_history() -> list[BatchRunRecord]:
    return _history
```

**Usage in batch.py:**
```python
from app.routes.analytics import add_record
```

### batch.py Modification Details

Add the following inside the `_process()` function, just before setting COMPLETED:

```python
# Existing code
_last_summary = summary
store = get_results_store()
store.clear()
for r in results:
    store[r.policy_number] = r

# [Added] Record history
from app.models.analytics import BatchRunRecord
from app.routes.analytics import add_record
record = BatchRunRecord(
    id=job_id,
    sample_size=len(pairs),
    total=summary.total,
    no_action_needed=summary.no_action_needed,
    review_recommended=summary.review_recommended,
    action_required=summary.action_required,
    urgent_review=summary.urgent_review,
    llm_analyzed=summary.llm_analyzed,
    processing_time_ms=summary.processing_time_ms,
)
add_record(record)

# Existing code
_jobs[job_id]["status"] = JobStatus.COMPLETED
```

### compute_trends Service

**File**: `app/engine/analytics.py`

**Signature**: `compute_trends(history: list[BatchRunRecord]) -> AnalyticsSummary`

| Input | `total_runs` | `avg_processing_time_ms` | `risk_distribution` | `trends` |
|-------|-------------|--------------------------|---------------------|----------|
| Empty list | 0 | 0.0 | All 0 | `[]` |
| 1 entry `[{total:100, no_action:15, review:45, action:29, urgent:11, time:850}]` | 1 | 850.0 | `{"no_action_needed": 15.0, "review_recommended": 45.0, "action_required": 29.0, "urgent_review": 11.0}` | 3 TrendPoints |
| 3+ entries | N | `sum(time) / N` rounded to 1 decimal | Cumulative rate based on total count | 3 metrics × N per time point |

**risk_distribution Calculation:**
- 3 runs: [{total:100, no_action_needed:15}, {total:200, no_action_needed:40}, {total:50, no_action_needed:10}]
- Cumulative: total=350, no_action_needed=65 → no_action_needed_rate = 65/350 * 100 = 18.6%
- All rates: `round(x, 1)`, if total_sum=0 then all 0.0

**trends Generation:**
- 3 TrendPoints per BatchRunRecord:
  - `urgent_review_rate` = `round(urgent_review / total * 100, 1)` (0.0 if total=0)
  - `action_required_rate` = `round(action_required / total * 100, 1)` (0.0 if total=0)
  - `avg_processing_ms` = processing_time_ms
- Sorted in ascending order by timestamp

### API Routes

**File**: `app/routes/analytics.py`, **Router**: `APIRouter(prefix="/analytics", tags=["analytics"])`

| Endpoint | Response | Notes |
|----------|----------|-------|
| `GET /analytics/trends` | `AnalyticsSummary` | Empty history → default values (not an error) |
| `GET /analytics/history` | `list[BatchRunRecord]` | Newest first (descending by timestamp) |

### UI Design

**nav bar Modification** (`base.html`):
```html
<a href="/" ...>Dashboard</a>
<a href="/ui/migration" ...>Migration</a>
<a href="/ui/analytics" ...>Batch Monitoring</a>
```

**analytics.html** — Follows the `dashboard.html` pattern:
1. `{% extends "base.html" %}` inheritance
2. `stats-grid` 4 cells (Total Runs, Avg Time, Urgent Review Rate, Action Required Rate)
3. `.progress-bar` risk distribution (same pattern as dashboard)
4. `<table>` history list (Run ID, Time, Sample, Total, Low, Med, High, Crit, Processing Time)
5. Empty state: "No batch runs yet. Run a batch from Dashboard first."

**UI Route** (`app/routes/ui.py`):
```python
from app.engine.analytics import compute_trends
from app.routes.analytics import get_history

@router.get("/ui/analytics")
def analytics_page(request: Request):
    history = get_history()
    summary = compute_trends(history)
    return templates.TemplateResponse(
        "analytics.html",
        {"request": request, "active": "analytics", "summary": summary, "history": history[::-1]},
    )
```

### Edge Cases

- History is empty → Total runs 0, empty time series list, all distributions 0 (not an error)
- A specific run has total=0 → That run's rates are 0.0%
- History list query → Newest first (descending)
- Batch History Limit: When adding a new entry, if exceeding 100 entries, the oldest are removed immediately

### Tests

**File**: `tests/test_analytics.py`

**Unit Tests — compute_trends:**

| Test | Input | Verification |
|------|-------|--------------|
| `test_empty_history` | `[]` | total_runs=0, trends=[], all distributions 0 |
| `test_single_run` | 1 entry (total=100, no_action=15, review=45, action=29, urgent=11) | total_runs=1, urgent_review_rate=11.0, action_required_rate=29.0 |
| `test_multiple_runs` | 3 entries (each with different distributions) | Cumulative rates correct, 9 trends, ascending by timestamp |
| `test_risk_distribution_percentage` | 2 entries: [{total:100,no_action_needed:20}, {total:200,no_action_needed:60}] | no_action_needed_rate = 26.7 |
| `test_history_fifo_limit` | 101 entries added | Length 100, oldest removed |

**API Integration Tests:**

| Test | Action | Verification |
|------|--------|--------------|
| `test_trends_empty` | GET /analytics/trends (no batch run) | 200, total_runs=0 |
| `test_history_empty` | GET /analytics/history (no batch run) | 200, empty list |
| `test_trends_after_batch` | POST /batch/run → complete → GET /analytics/trends | total_runs=1 |
| `test_history_order` | 2 batch runs → GET /analytics/history | Newest is first |

---

## 5. Coding Rules

| Type | Pattern | Example |
|------|---------|---------|
| Model Class | PascalCase | `BatchRunRecord`, `TrendPoint` |
| Service Function | snake_case | `compute_trends` |
| Route Function | snake_case | `get_trends`, `get_history` |
| Module-level Variable | `_` prefix | `_history`, `MAX_HISTORY` |
| Test Function | `test_` prefix | `test_empty_history` |

- Follow `convention.md` (no docstrings, 300-line limit, type hints required)
- Pass `ruff check`
- Follow existing code patterns: Pydantic BaseModel, APIRouter with prefix, engine/ pure functions, Jinja2 base.html inheritance
