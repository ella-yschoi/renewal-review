# Renewal Review — System Design Document

---

## 1. Overview

A pipeline-based dashboard visualization that automatically compares and analyzes insurance renewal policies to determine risk levels.

- **Prior vs Renewal Comparison**: Diffs all fields between the existing and renewal policies, flagging changes that require attention
- **Rule + LLM Hybrid**: After rule-based risk determination, if conditions are met, the LLM performs in-depth analysis of notes and endorsements to escalate risk
- **Alternative Quote Generation**: Proposes up to 3 savings quotes (Quotes) per coverage adjustment strategy for flagged policies
- **Portfolio Risk Aggregator**: Groups a client's multiple policies for cross-analysis — bundle discounts, duplicate coverage, exposure assessment (rule-based)

**Target Users**: Insurance underwriters, renewal review analysts

---

## 2. Architecture

### Hexagonal Architecture (Ports & Adapters)

```
Dependency direction: api/ → application/ → domain/ ← adaptor/

               ┌───────────────────────────────────────────────┐
               │                  FastAPI App                   │
               └───────────────────────┬───────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
┌───────▼────────┐          ┌──────────▼──────────┐        ┌─────────▼──────────┐
│   api/ (Inbound) │──────▶│   application/       │        │  adaptor/ (Outbound) │
│   FastAPI Routes │         │   Use-case Orchestration │◀───────│  LLM / Storage / DB │
└────────────────┘          └──────────┬──────────┘        └─────────┬──────────┘
                                       │                              │
                            ┌──────────▼──────────┐                  │
                            │   domain/ (Inner Hexagon) │◀─────────────────┘
                            │   Pure Business Logic     │    ports/ Protocol impl
                            │   models/ services/   │
                            │   ports/ (Interfaces)   │
                            └───────────────────────┘
                                       │
                            ┌──────────▼──────────┐
                            │   infra/             │
                            │   DI Wiring + DB     │
                            └───────────────────────┘
```

### Core Principles

- `domain/` does not import external modules (only defines `ports/` Protocols)
- `application/` imports only `domain/` + `ports/` (no implementations)
- External system changes are absorbed in `adaptor/` and do not propagate to the domain

### Agent Infrastructure (`git tracked`)

```
.claude/
├── hooks/                              # Claude Code hooks (project scope)
│   ├── require-design-doc.sh           # PreToolUse — blocks commits without design-doc on code changes
│   ├── require-experiment-log.sh       # PreToolUse — blocks commits without logs on experiment branches
│   ├── lint-on-save.sh                 # PostToolUse — auto-lint after file save
│   ├── remind-design-doc.sh            # PostToolUse — design-doc reminder after code edits
│   ├── log-commit.sh                   # PostToolUse — log reminder after commits
│   └── verify-completion.sh            # Stop — completion verification on agent shutdown
├── rules/
│   └── conventions.md                  # Code conventions (hexagonal, StrEnum, <300 lines, etc.)
├── skills/
│   ├── insurance-domain/SKILL.md       # Insurance domain knowledge (ACORD standards)
│   └── agentic-dev-pipeline/SKILL.md   # Automated implementation + verification pipeline skill
├── settings.json                       # Hook settings (git tracked, auto-applied on clone)
└── settings.local.json                 # Local-only settings (gitignored)
```

- `settings.json`: Project-level hook path mappings. Hooks are auto-applied on repo clone
- `agentic-dev-pipeline` skill: Managed in a separate GitHub repo (`ella-yschoi/agentic-dev-pipeline`). Install via `git clone`

### Module Directory

```
app/
├── main.py                    # Composition root — lifespan(init_db) + router registration
├── config.py                  # Settings + nested config (Rules, Quotes, Portfolio, LLM)
├── data_loader.py             # Data source factory (→ delegates to adaptor/)
│
├── domain/                    # Inner hexagon — pure business logic
│   ├── models/                # 8 modules, 27 Pydantic models (enums, policy, diff, review, quote, portfolio, analytics, llm_schemas)
│   ├── services/              # parser, differ, rules, notes_rules, aggregator, quote_generator, portfolio_analyzer, analytics
│   └── ports/                 # LLMPort, ResultWriter, ReviewStore/HistoryStore/JobStore, DataSourcePort Protocol
│
├── application/               # Use cases — domain + port orchestration
│                              # batch, llm_analysis, quote_advisor, prompts
│
├── api/                       # Inbound adapters — FastAPI routes + Depends()
│                              # reviews, batch, analytics, quotes, portfolio, eval, ui
│
├── adaptor/                   # Outbound adapters — external system implementations
│   ├── llm/                   # LLMClient, AnthropicClient, MockLLMClient
│   ├── storage/               # InMemoryReviewStore, InMemoryHistoryStore, InMemoryJobStore
│   └── persistence/           # JsonDataSource, DbDataSource, DbResultWriter, NoopResultWriter
│
├── infra/                     # Infrastructure — DI wiring, DB, ORM
│
└── templates/                 # base, dashboard, review, portfolio, migration, analytics
```

### Data Flow Summary

#### Batch Processing (Main Pipeline)

```
DB → load_pairs() → [RenewalPair]
                              │
            process_pair() ◄──┘ (loop)
                  │
        compute_diff(pair) → DiffResult (changes)
                  │
        flag_diff(diff, pair) → DiffResult (DiffFlag assignment)
            ├─ _flag_premium        → PREMIUM_INCREASE_*
            ├─ _flag_carrier        → CARRIER_CHANGE
            ├─ _flag_changes        → LIABILITY_LIMIT_DECREASE, COVERAGE_DROPPED, ...
            ├─ _flag_drivers        → SR22_FILING, DRIVER_VIOLATIONS, YOUTHFUL_OPERATOR
            ├─ _flag_coverage_gap   → COVERAGE_GAP
            └─ flag_notes_keywords  → CLAIMS_HISTORY, PROPERTY_RISK, REGULATORY, DRIVER_RISK_NOTE
                  │
        assign_risk_level(flags) → RiskLevel (rule-based)
                  │
        ┌─── LLM client AND flags AND should_analyze()? ─┐
        │ Yes                                              │ No
   analyze_pair() → [LLMInsight]                    ReviewResult (rule only)
        │
   aggregate(rule_risk, insights) → risk may be escalated
        │
   generate_summary(result) → AI summary (optional)
        │
        └──────────────────┬───────────────────────┘
                           │
              review_store[pn] = result     (InMemory)
              writer.save_rule_result()     (DB persist)
                           │
              history_store ← BatchRunRecord (for trend analysis)
```

#### Lazy Enrichment (On Individual Retrieval)

```
GET /reviews/{pn} → review_store.get(pn)
                         │
           ┌── no summary and LLM client? ──┐
           │ Yes                           │ No
    analyze_pair() + generate_summary()    return as-is
           │
    writer.save_llm_result()  (DB persist, LLMResultRow)
```

#### Quote Generation

```
POST /quotes/generate → process_pair() → generate_quotes(pair, diff)
                                              │
                                    ┌── LLM client? ──┐
                                    │ Yes              │ No
                             personalize_quotes()    rule-based quotes only
                                    │
                           [QuoteRecommendation]
```

#### Cross-Analysis & Trends

```
POST /portfolio/analyze → analyze_portfolio(policy_numbers, review_store)
    └─ bundle + duplicate coverage + liability exposure + premium concentration
    └─ PortfolioSummary (on-demand, not persisted)

GET /analytics/trends → compute_trends(history_store.list())
GET /analytics/broker → compute_broker_metrics(review_store.values())
```

#### Persistence Layer

```
┌─ InMemory ────────────────────────────────┐
│ review_store   → ReviewResult per policy  │
│ history_store  → BatchRunRecord (max 100) │
│ job_store      → batch job status         │
└────────────────────────────────────────────┘
         ↕ write-through / restore on startup
┌─ DB (SQLAlchemy) ─────────────────────────┐
│ RuleResultRow  → flags, changes, quotes   │
│ LLMResultRow   → insights, summary        │
└────────────────────────────────────────────┘
```

---

## 3. Data Model

### Enum Central Definitions (`app/domain/models/enums.py`)

| Enum | Values | Usage |
|------|---|-------|
| `Severity` | info, warning, critical | CrossPolicyFlag.severity |
| `UnbundleRisk` | low, medium, high | BundleAnalysis.unbundle_risk |
| `QuoteStrategy` | raise_deductible, drop_optional, reduce_medical, drop_water_backup, reduce_personal_property | CoverageAdjustment.strategy |
| `AnalysisType` | risk_signal_extractor, endorsement_comparison | LLMInsight.analysis_type |
| `LLMTaskName` | risk_signal_extractor, endorsement_comparison, review_summary, quote_personalization | LLM call trace_name, config.task_models key |
| `FlagType` | duplicate_medical, duplicate_roadside, high/low_liability_exposure, premium_concentration, high_portfolio_increase | CrossPolicyFlag.flag_type |

### Policy Domain (`app/domain/models/policy.py`)

| Model | Description | Key Fields |
|------|------|-----------|
| `PolicyType` | StrEnum — `auto`, `home` | — |
| `PolicySnapshot` | Snapshot of a single policy | policy_number, policy_type, carrier, effective_date, expiration_date, premium, state, notes, insured_name, account_id, auto_coverages, home_coverages, vehicles, drivers, endorsements |
| `RenewalPair` | A Prior + Renewal pair | prior: PolicySnapshot, renewal: PolicySnapshot |
| `AutoCoverages` | Auto coverage items | bodily_injury_limit, property_damage_limit, collision_deductible, comprehensive_deductible, uninsured_motorist, medical_payments, rental_reimbursement, roadside_assistance |
| `HomeCoverages` | Home coverage items | coverage_a~f, deductible, wind_hail_deductible, water_backup, replacement_cost |
| `Vehicle` | Vehicle info | vin, year, make, model, usage |
| `Driver` | Driver info | license_number, name, age, violations, sr22 |
| `Endorsement` | Endorsement | code, description, premium |

### Diff Domain (`app/domain/models/diff.py`)

| Model | Description | Key Fields |
|------|------|-----------|
| `FieldChange` | Single field change (frozen) | field, prior_value, renewal_value, change_pct, flag |
| `DiffResult` | Full diff of a single policy | policy_number, changes: list[FieldChange], flags: list[DiffFlag] |

**Full DiffFlag List (23)**:

| Flag | Trigger Condition |
|------|------------|
| `premium_increase_high` | Premium +10% or more |
| `premium_increase_critical` | Premium +20% or more |
| `premium_decrease` | Premium decrease |
| `carrier_change` | Carrier change |
| `liability_limit_decrease` | Liability limit decrease |
| `deductible_increase` | Deductible increase |
| `coverage_dropped` | Coverage reduced/removed |
| `coverage_added` | Coverage added |
| `vehicle_added` | Vehicle added |
| `vehicle_removed` | Vehicle removed |
| `driver_added` | Driver added |
| `driver_removed` | Driver removed |
| `endorsement_added` | Endorsement added |
| `endorsement_removed` | Endorsement removed |
| `notes_changed` | Notes changed |
| `driver_violations` | Driver has violation history |
| `sr22_filing` | SR-22 high-risk certification required |
| `youthful_operator` | Driver under age 25 |
| `coverage_gap` | UM/UIM below minimum limit |
| `claims_history` | Accident/claim keywords in notes |
| `property_risk` | Property risk keywords in notes |
| `regulatory` | Regulatory/non-renewal keywords in notes |
| `driver_risk_note` | Driver risk keywords in notes |

### Review Domain (`app/domain/models/review.py`)

| Model | Description | Key Fields |
|------|------|-----------|
| `RiskLevel` | StrEnum — 4 levels | no_action_needed, review_recommended, action_required, urgent_review |
| `LLMInsight` | Single LLM analysis result | analysis_type, finding, confidence, reasoning |
| `ReviewResult` | Final review result | policy_number, risk_level, diff, llm_insights, summary, pair, broker_contacted, quote_generated, quotes, reviewed_at |
| `BatchSummary` | Batch run summary | total, count per risk level, llm_analyzed, processing_time_ms |

### Analytics Domain (`app/domain/models/analytics.py`)

| Model | Description | Key Fields |
|------|------|-----------|
| `BatchRunRecord` | Single batch run record | job_id, total, count per risk level, processing_time_ms, created_at |
| `TrendPoint` | Daily aggregation | date, total_runs, urgent_review_ratio |
| `AnalyticsSummary` | Overall analytics summary | total_runs, total_policies_reviewed, risk_distribution, trends |
| `BrokerMetrics` | Broker workflow metrics | total, pending, contact_needed, contacted, quotes_generated, reviewed |

### Quote Domain (`app/domain/models/quote.py`)

| Model | Description | Key Fields |
|------|------|-----------|
| `CoverageAdjustment` | Individual adjustment item | field, original_value, proposed_value, strategy |
| `QuoteRecommendation` | Single alternative quote | quote_id (Quote 1~3), adjustments, estimated_savings_pct, estimated_savings_dollar, trade_off, broker_tip |

### Portfolio Domain (`app/domain/models/portfolio.py`)

| Model | Description | Key Fields |
|------|------|-----------|
| `CrossPolicyFlag` | Cross-policy issue | flag_type, severity, description, affected_policies |
| `BundleAnalysis` | Bundle analysis result | has_auto, has_home, is_bundle, bundle_discount_eligible, carrier_mismatch, unbundle_risk |
| `PortfolioSummary` | Overall portfolio summary | client_policies, total_premium, total_prior_premium, premium_change_pct, risk_breakdown, bundle_analysis, cross_policy_flags |

### DB Models (`app/infra/db_models.py`)

| Model | Table Name | Description |
|------|---------|------|
| `RenewalPairRow` | `raw_renewals` | Persistent storage for policy pairs. Preserves originals as prior_json, renewal_json. insured_name, account_id as separate top-level indexed columns |
| `RuleResultRow` | `rule_results` | Rule-based review results. policy_number, job_id, risk_level, flags_json, changes_json, summary_text, broker_contacted, quote_generated, quotes_json, reviewed_at |
| `LLMResultRow` | `llm_results` | LLM analysis results. policy_number, job_id, risk_level, insights_json, summary_text |
| `ComparisonRunRow` | `comparison_runs` | LLM comparison aggregated results. job_id (unique), result_json (JSON blob), created_at |

### DB Persistence (Write-Through)

Write-through strategy that maintains an in-memory cache while also persisting to DB. Abstracted via `ResultWriter` Protocol (`domain/ports/result_writer.py`).

- **DbResultWriter**: Used when DB is configured. All methods wrapped in try/except — on DB failure, logs warning, app continues normally
- **NoopResultWriter**: Used when DB is not configured. All methods are pass-through
- **ResultWriter Protocol methods**: save_rule_result, save_llm_result, update_broker_contacted, update_quote_generated, update_quotes, update_reviewed_at, load_latest_results, load_latest_llm_results, save_comparison_result, load_latest_comparison
- On app startup, `_restore_cache_from_db()` restores InMemoryReviewStore from DB. Reconnects `pair` from `raw_renewals`, restores summary from `rule_results.summary_text`, restores quotes from `rule_results.quotes_json`, merges insights/summary/risk_level from `llm_results`
- On app startup, `_restore_comparison_from_db()` restores the latest LLM comparison aggregated results from DB (`comparison_runs` → `_last_comparison`)

---

## 4. Processing Pipeline

### Step-by-Step Flow

```
1. Data Loading     load_pairs()           Load RenewalPair from DB or JSON
       │
2. Diff             compute_diff(pair)     Per-field change detection → DiffResult
       │
3. Flagging         flag_diff(diff, pair)  Rule-based flag assignment
       │
4. Risk Assignment  assign_risk_level()    Determine risk level from flag combination
       │
5. LLM Enrichment   _lazy_enrich()         Generate AI summary for all flagged policies.
   (conditional)     generate_summary()    Add insights (analyze_pair) only for Review Recommended.
                     enrich_with_llm()     Lazy trigger on detail page entry + DB persist
       │
6. Aggregation      aggregate()            rule_risk + LLM insights → final risk
```

### Risk Level Decision Table (Rule-Based)

| Risk Level | Condition | Applicable Flags |
|-----------|------|-----------|
| `urgent_review` | 1 or more URGENT flags | `premium_increase_critical`, `liability_limit_decrease`, `sr22_filing` |
| `action_required` | 1 or more ACTION flags | `premium_increase_high`, `coverage_dropped`, `driver_violations`, `coverage_gap`, `claims_history` |
| `review_recommended` | Flags present but none of the above | All other flags |
| `no_action_needed` | No flags | — |

> Priority order: urgent_review > action_required > review_recommended > no_action_needed
> (`app/application/batch.py:17-25`)

### LLM Risk Upgrade Conditions (`app/domain/services/aggregator.py`)

Risk can be escalated above rule_risk based on LLM analysis results. Downgrade never occurs.

| Condition | Escalation Target |
|------|----------|
| 2+ risk_signals (confidence >= 0.7) | → `action_required` or higher |
| endorsement restriction (confidence >= 0.75) | → `action_required` or higher |
| Combined conditions above (restriction + risk_signal >= 2) | → `urgent_review` |

### Flag Trigger Thresholds (`app/domain/services/rules.py`)

| Rule | Threshold | Resulting Flag |
|------|--------|----------|
| Premium increase | >= 10% | `premium_increase_high` |
| Premium increase | >= 20% | `premium_increase_critical` |
| Premium decrease | < 0% | `premium_decrease` |
| Liability decrease | prior > renewal (aggregate comparison) | `liability_limit_decrease` |
| Deductible increase | prior < renewal | `deductible_increase` |
| Coverage value decrease | prior > renewal | `coverage_dropped` |
| Boolean coverage removed | True → False | `coverage_dropped` |
| Boolean coverage added | False → True | `coverage_added` |
| Driver violations | violations > 0 | `driver_violations` |
| SR-22 certification | sr22 = True | `sr22_filing` |
| Driver under 25 | age < youthful_operator_age (25) | `youthful_operator` |
| UM/UIM below minimum | UM/UIM < um_uim_min_limit (50/100) | `coverage_gap` |
| Notes keyword matching | Keywords present per category | `claims_history`, `property_risk`, `regulatory`, `driver_risk_note` |

### Quote Generator Strategies (`app/domain/services/quote_generator.py`)

Up to 3 strategies are independently applied per policy type to generate alternative quotes.

**Auto Strategies**:

| Strategy | Savings Rate | Skip Condition |
|------|--------|----------------|
| `raise_deductible` | 10% | collision_deductible >= 1000 AND comprehensive_deductible >= 500 |
| `drop_optional` | 4% | rental_reimbursement=False AND roadside_assistance=False |
| `reduce_medical` | 2.5% | medical_payments <= 2000 |

**Home Strategies**:

| Strategy | Savings Rate | Skip Condition |
|------|--------|----------------|
| `raise_deductible` | 12.5% | deductible >= 2500 |
| `drop_water_backup` | 3% | water_backup=False |
| `reduce_personal_property` | 4% | coverage_c <= dwelling × 0.5 + $100 (threshold for near-equal) |

**Protected Fields** — never modified by any strategy:

`bodily_injury_limit`, `property_damage_limit`, `coverage_e_liability`, `uninsured_motorist`, `coverage_a_dwelling`

---

## 5. API Surface

### Core API

| Method | Path | Description | Response | Status Codes |
|--------|------|-------------|----------|-------------|
| GET | `/health` | Health check | `{"status": "ok", "version": "0.1.0"}` | 200 |
| GET | `/reviews/{policy_number}` | Retrieve review result (triggers lazy LLM enrichment) | `ReviewResult` | 200, 404 |
| PATCH | `/reviews/{pn}/broker-contacted` | Toggle contacted status | `{broker_contacted}` | 200, 404 |
| PATCH | `/reviews/{pn}/quote-generated` | Save quotes (if quotes in body) or toggle | `{quote_generated}` | 200, 404 |
| POST | `/quotes/generate` | Generate alternative quotes | `{quotes, reasons}` | 200, 422 |
| POST | `/portfolio/analyze` | Portfolio cross-analysis | `PortfolioSummary` | 200, 422 |

### Batch / Async

| Method | Path | Description | Response | Status Codes |
|--------|------|-------------|----------|-------------|
| POST | `/batch/run` | Batch run (async, reviewed_at auto-set) | `{"job_id", "status", "total"}` | 200, 404 |
| POST | `/batch/review-selected` | Batch run for selected policies only (store preserved) | `{"job_id", "status", "total"}` | 200, 404 |
| GET | `/batch/total-count` | Total policy count in data source | `{"total"}` | 200 |
| GET | `/batch/status/{job_id}` | Batch progress status | job details (status, processed, total) | 200, 404 |
| POST | `/eval/run` | Run golden eval (dev/QA only) | accuracy + per-scenario results | 200, 404 |
| POST | `/migration/comparison` | Basic vs LLM comparison for **reviewed** + Review Recommended policies (async). `reviewed_at is not None` required. Makes actual LLM API calls (when llm_enabled=true). Demo: 100 sample policies (`comparison_sample_size`). Saves LLM results to DB (`llm_results`), aggregated results to DB (`comparison_runs`). Preserves existing metadata | `{"job_id", "status", "total"}` | 200, 404 |
| GET | `/migration/latest` | Retrieve last comparison result. Memory cache → DB fallback (`comparison_runs`) | comparison result dict or `{"status":"none"}` | 200 |
| GET | `/migration/status/{job_id}` | Migration progress status | job details | 200, 404 |

### Analytics

| Method | Path | Description | Response | Status Codes |
|--------|------|-------------|----------|-------------|
| GET | `/analytics/history` | Batch run history (max 100 entries) | `list[BatchRunRecord]` | 200 |
| GET | `/analytics/trends` | Daily trends + summary | `AnalyticsSummary` | 200 |
| GET | `/analytics/broker` | Broker workflow metrics | `BrokerMetrics` | 200 |

### Async Job Lifecycle

```
POST /batch/run  →  {"job_id": "abc12345", "status": "running"}
                            │
         GET /batch/status/abc12345  (polling)
                            │
              status: "running"  →  processed / total updated
              status: "completed" →  includes summary
              status: "failed"   →  includes error message
```

### UI Pages

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard (includes Broker Workflow). Supports Account sorting via `sort`, `order` query parameters |
| GET | `/ui/review/{policy_number}` | Review detail |
| GET | `/ui/insight` | LLM Insights (Basic vs LLM comparison) |
| GET | `/ui/portfolio` | Portfolio Risk Aggregator. Supports Account sorting via `sort`, `order` query parameters |

---

## 6. UI

| # | Page | Route | Key Features |
|---|--------|-------|----------|
| 1 | Dashboard | `GET /` | On initial entry, unreviewed policies shown as "Pending". **Risk Distribution counts only policies where `reviewed_at is not None`** — Pending = `total - actually_reviewed`. 5 Broker Workflow metrics (pending also calculated based on `reviewed_at`). Selection checkboxes persist across pages/filters via sessionStorage + Review(N) button (global selection count), Review All(N). **Batch progress display**: On Review All/Review(N) execution, shows blue progress bar + policy count + estimated time remaining (ETA). **Policy # and Account columns separated**: Policy # column and Account (insured_name) column are independent. **Account sorting**: Click to toggle ascending/descending (▲/▼), sort/order state linked with pagination and filters. 6 filters: review status (Reviewed/Pending), Risk Level, Contacted, Quote, LLM analysis status (filter state saved to sessionStorage, preserved when returning from detail to dashboard). Contacted checkbox (user toggle), Quote checkbox (read-only), Reviewed At display, pagination (50 items/page) |
| 2 | Review Detail | `GET /ui/review/{pn}` | Layout: Summary → Quote Recommendations (trade_off + broker_tip) → LLM Insights → Policy Overview → Flags → Changes. AI summary targets all flagged policies (lazy enrichment), LLM insights only for Review Recommended. Quote trade_off: 3-4 sentences with specific scenarios/amounts, broker_tip: 2-3 sentences as actionable conversation guide. Back button restores Dashboard filter state (sessionStorage). When accessed via `?ref=insight`, shows "Back to LLM Insights" |
| 3 | LLM Insights | `GET /ui/insight` | Targets **reviewed + Review Recommended** policies (`reviewed_at is not None` required). Makes actual LLM API calls (falls back to MockLLMClient when llm_enabled=false). Production: analyzes all eligible policies. Demo: 100 random samples. LLM results saved to DB + existing metadata preserved. Async execution with progress bar polling (phase/processed/total + estimated time remaining). Results: top summary cards + bottom full comparison table (All Compared Policies, Risk Changed filter, pagination 20 items/page). Policy links pass `?ref=insight` |
| 4 | Portfolio | `GET /ui/portfolio` | Top info banner (purple): Account-level risk analysis description. Displays account (account_id) grouped list. **Account column**: insured_name as main text, policy_numbers as subtext. **Account sorting**: Click to toggle ascending/descending (▲/▼), sort/order state linked with pagination. Columns: Account, Policies, Type (Auto/Home/Bundle), Total Premium, Highest Risk, Action. Bundle accounts (2+ policies) have Analyze button → existing modal, single-policy accounts have View link → review detail. Rule-based verdict/recommendations/action items |
| 5 | Base Layout | — | Shared nav (Dashboard, LLM Insights, Portfolio), global `getLabel()` JS function |

### Label Registry (`app/domain/labels.py`)

A central registry that converts all snake_case enum values and field names to broker-friendly labels.

- `LABELS: dict[str, str]` — raw value → human-readable mapping (RiskLevel, DiffFlag, AnalysisType, FlagType, Severity, FieldChange.field)
- `get_label(raw)` — falls back to `raw.replace("_", " ").title()` if not in LABELS
- Registered as Jinja2 `|label` filter (`app/api/ui.py`)
- `base.html` globally injects `LABELS` JSON + `getLabel()` JS function for consistent labels in dynamic rendering
- CSS classes (`badge-no_action_needed`, etc.) and API JSON responses retain raw snake_case

**Navigation order**: Dashboard → LLM Insights → Portfolio

---

## 7. LLM Integration

### Analysis Entry Conditions (`app/application/llm_analysis.py:should_analyze`)

LLM analysis runs if any of the following apply:

1. Notes have changed and renewal has notes
2. Endorsement description has changed

### Analysis Flow

```
should_analyze(diff, pair) ──▶ True?
       │                            │ No → skip
       │ Yes                        │
  analyze_pair(client, diff, pair)
       │
       ├── _analyze_notes()          ← RISK_SIGNAL_EXTRACTOR prompt
       └── _analyze_endorsement()    ← ENDORSEMENT_COMPARISON prompt
       │
  aggregate(policy_number, rule_risk, diff, insights) → ReviewResult
```

### Review Summary LLM Transition (`app/application/llm_analysis.py:generate_summary`)

Regardless of `should_analyze()` result, generates LLM summary for all policies with flags.
Replaces the previous mechanical format (`"Risk: URGENT_REVIEW | Flags: 3"`) with 2-3 sentence natural language summary.

- Input: ReviewResult (policy metadata, diff, flags, LLM insights)
- key_changes: selects up to 5 changes, prioritizing flagged ones
- On failure, retains existing mechanical summary (returns None)

### Quote Personalization (`app/application/quote_advisor.py:personalize_quotes`)

Replaces rule-based trade_off with customer-context-based detailed personalized text and adds broker_tip.
Strategy selection and savings calculation remain rule-based.

- Single LLM call processes up to 3 quotes in batch
- `_build_policy_context(pair)` — includes only non-empty sections
- `_build_quotes_json(quotes)` — includes adjustments (field/from/to), savings_pct, savings_dollar
- trade_off: 3-4 sentences (specific amounts, claim scenarios, customer risk factors, suitable audience)
- broker_tip: 2-3 sentences (conversation starters, verification questions, related policy details)
- Partial match support: if only 2 of 3 quotes are returned, remaining keep originals
- Respects `settings.llm_enabled` toggle (`app/api/quotes.py`)

### Fallback Behavior

| Scenario | Summary | Quote |
|----------|---------|-------|
| `llm_enabled=false` | Existing mechanical format | hardcoded trade_off, broker_tip="" |
| LLM API error | Retains mechanical summary | Retains original trade_off, broker_tip="" |
| LLM partial response | N/A | Only matched quotes personalized, rest keep originals |
| Policy with no flags | Summary generation skipped | Empty quotes list |

### 4 Prompts (`app/application/prompts.py`)

| Prompt | Role | ACORD Alignment | Output (JSON) |
|---------|------|-----------|------------|
| `RISK_SIGNAL_EXTRACTOR` | Extract risk signals from renewal notes | 6 signal types (claims_history, property_risk, driver_risk, coverage_gap, regulatory, other) | signals[], confidence, summary |
| `ENDORSEMENT_COMPARISON` | Determine material changes in endorsement description changes | HO 04 xx / PP 03 xx form reference, ACORD change type (A/C/D) | material_change, change_type, confidence, reasoning |
| `REVIEW_SUMMARY` | Convert review result to natural language summary | Prioritizes liability limit (BI/PD/Coverage E), broker action-oriented | summary |
| `QUOTE_PERSONALIZATION` | Personalize Quote trade_off/broker_tip | Explicitly prohibits reduction of protected fields (BI, PD, UM, Cov A, Cov E) | quotes[{quote_id, trade_off, broker_tip}] |

### LLM Response Validation Schemas (`app/domain/models/llm_schemas.py`)

All LLM responses are validated via Pydantic `model_validate()` for type-safe access. On missing fields, `ValidationError` → routed to existing fallback path.

| Schema | Target Prompt | Key Fields |
|--------|-------------|----------|
| `RiskSignalExtractorResponse` | `RISK_SIGNAL_EXTRACTOR` | signals: list[RiskSignal], confidence, summary |
| `EndorsementComparisonResponse` | `ENDORSEMENT_COMPARISON` | material_change, change_type, confidence, reasoning |
| `ReviewSummaryResponse` | `REVIEW_SUMMARY` | summary |
| `QuotePersonalizationResponse` | `QUOTE_PERSONALIZATION` | quotes: list[PersonalizedQuote] |

### Provider Configuration (`app/adaptor/llm/`)

- **Anthropic** (`anthropic.py`): `AnthropicClient(model=)` — model injectable, auto-strips markdown code blocks before JSON parsing
- **Routing** (`app/adaptor/llm/client.py`): `LLMClient` — per-task model routing based on `trace_name`. Automatic Sonnet/Haiku selection via `ModelKey` StrEnum + `settings.llm.task_models` mapping. Reuses instances for same model
- **MockLLMClient** (`app/adaptor/llm/mock.py`): For testing, fallback for migration comparison when LLM is disabled
- **Langfuse tracing**: Built into each provider. Auto-activates when `LANGFUSE_PUBLIC_KEY` environment variable is present

---

## 8. Error Handling

### HTTP Errors

| Status | Path | Condition |
|--------|------|------|
| 404 | `GET /reviews/{pn}` | No review for that policy_number |
| 404 | `GET /batch/status/{job_id}` | No such job_id |
| 404 | `GET /migration/status/{job_id}` | No such job_id |
| 404 | `GET /ui/review/{pn}` | No review for that policy_number |
| 404 | `POST /batch/run` | No data (JSON file not generated) |
| 404 | `POST /eval/run` | Golden eval file not found |
| 404 | `POST /migration/comparison` | No reviewed + Review Recommended policies (batch not run or reviews not completed) |
| 404 | `POST /batch/review-selected` | No match for selected policy_numbers |
| 422 | `POST /reviews/compare` | Input JSON parse failure (KeyError, ValidationError) |
| 422 | `POST /quotes/generate` | Input JSON parse failure |
| 422 | `POST /portfolio/analyze` | Insufficient policies (< 2) or reviews not found |

### Fallback Patterns

| Scenario | Fallback | Code Location |
|------|----------|----------|
| DB load failure | Falls back to JSON file | `app/data_loader.py:42-44` |
| LLM JSON parse failure | Returns `{"error": ..., "raw_response": ...}` | `app/adaptor/llm/anthropic.py` |
| LLM analysis error / response schema mismatch | Creates error LLMInsight with confidence=0.0 | `app/application/llm_analysis.py` |
| LLM summary failure | Retains existing mechanical summary | `app/application/batch.py` |
| LLM quote personalization failure | Retains original trade_off, broker_tip="" | `app/application/quote_advisor.py` |

### Async Job Failure

For batch (`/batch/run`) and migration (`/migration/comparison`) async operations:
- On Exception within `_process()`, job status is set to `"failed"`
- Error message stored in `error` field
- Client can detect failure state via subsequent status polling

---

## 9. Non-Functional

### Storage

- **Default**: in-memory — `InMemoryReviewStore`, `InMemoryHistoryStore`, `InMemoryJobStore` (`app/adaptor/storage/memory.py`), injected via `Depends()` (`app/infra/deps.py`)
- **Optional**: PostgreSQL — activated when `RR_DB_URL` environment variable is set. SQLAlchemy async engine (asyncpg) + sync fallback (psycopg). `init_db()` called in FastAPI lifespan to auto-create tables on app startup

### Caching

- `app/data_loader.py`: Module-level `_cached_pairs` — cached after first load. Can be reset via `invalidate_cache()`
- Review All batch clears results_store then replaces with new results. Selected review (`review-selected`) preserves existing store and only upserts selected policies

### Concurrency

- `asyncio.create_task()`: Runs batch and migration operations as async tasks
- `loop.run_in_executor(None, ...)`: Runs CPU-bound processing (diff, flag, LLM calls) in thread pool
- Real-time progress updates via progress callback

### Limits

| Item | Limit | Code Location |
|------|------|----------|
| Analytics history | `deque(maxlen=100)` — max 100 entries, oldest auto-removed | `app/api/analytics.py:10-11` |
| Max quotes | 3 (`quotes[:3]`) | `app/domain/services/quote_generator.py` |
| Min quote condition | Generated only when flags exist | `app/domain/services/quote_generator.py` |
| UI pagination | 50 items/page (`PAGE_SIZE = 50`) | `app/api/ui.py:23` |
| Migration comparison target | All Review Recommended (no limit) | `app/api/eval.py` |

### Docker

- `Dockerfile`: python:3.13-slim + uv, dependency layer caching (`pyproject.toml` + `uv.lock` copied first)
- `docker-compose.yml`: `db` (postgres:16-alpine, healthcheck) + `app` (source volume mount, `--reload`)
- `app` service overrides host to `db` (service name) via `environment.RR_DB_URL`
- `depends_on: db: condition: service_healthy` — app starts after DB is ready
- `Makefile`: `compose-up` (build+run), `compose-down` (stop), `dev`/`test`/`lint` (local use)
- `main.py` lifespan calls `init_db()` → auto-creates tables on app startup

### Timezone

- `America/Vancouver` — applied when creating BatchRunRecord.created_at (`app/api/batch.py:64-76`)

---

## 10. Tech Stack

### Runtime

| Item | Version / Value |
|------|-----------|
| Python | >= 3.13 (`requires-python` in pyproject.toml) |
| Package Manager | uv |
| Web Framework | FastAPI >= 0.115 |
| ASGI Server | uvicorn >= 0.34 |
| ORM | SQLAlchemy >= 2.0 (asyncio) |
| Validation | Pydantic >= 2.10 |
| Templating | Jinja2 >= 3.1 |
| LLM (optional) | OpenAI >= 2.18, Anthropic >= 0.43, Langfuse >= 3.14 — `pip install .[llm]` |
| DB Driver | asyncpg >= 0.30, psycopg >= 3.1 |
| Container | Docker (python:3.13-slim + uv), Docker Compose |
| DB | PostgreSQL 16 (alpine) |

### Dev Dependencies

| Package | Version | Purpose |
|--------|------|------|
| pytest | >= 8.3 | Test framework |
| hypothesis | >= 6.120 | Property-based testing |
| httpx | >= 0.28 | TestClient (FastAPI test dependency) |
| ruff | >= 0.9 | Linter + formatter |

### Environment Variables (`RR_` prefix, `env_nested_delimiter="__"`, `app/config.py`)

| Variable | Default | Description |
|------|--------|------|
| `RR_LLM_ENABLED` | `false` | Enable LLM analysis |
| `RR_DATA_PATH` | `"data/renewals.json"` | Data file path |
| `RR_DB_URL` | `""` | PostgreSQL URL (JSON mode when empty) |
| `LANGFUSE_PUBLIC_KEY` | — | Auto-activates Langfuse tracing when set |

### Nested Configuration (`app/config.py`, env var override: `RR_{section}__{field}`)

| Class | Key Fields | Env Var Example | Referenced In |
|--------|----------|-------------|----------|
| `RuleThresholds` | premium_high_pct (10.0), premium_critical_pct (20.0), youthful_operator_age (25), um_uim_min_limit ("50/100") | `RR_RULES__PREMIUM_HIGH_PCT` | `domain/services/rules.py` (parameter injection) |
| `NotesKeywords` | claims_history, property_risk, regulatory, driver_risk (keyword lists per category) | `RR_NOTES_KEYWORDS__CLAIMS_HISTORY` | `domain/services/notes_rules.py` |
| `QuoteConfig` | auto_collision/comprehensive_deductible, savings_* (12 fields) | `RR_QUOTES__SAVINGS_RAISE_DEDUCTIBLE_AUTO` | `domain/services/quote_generator.py` (parameter injection) |
| `PortfolioThresholds` | high/low_liability, concentration_pct, portfolio_change_pct | `RR_PORTFOLIO__HIGH_LIABILITY` | `domain/services/portfolio_analyzer.py` (parameter injection) |
| `LLMConfig` | sonnet_model, haiku_model, max_tokens, task_models (uses ModelKey) | `RR_LLM__SONNET_MODEL` | `adaptor/llm/client.py` (routing), `anthropic.py` |

### Ruff Configuration (`pyproject.toml`)

- target: Python 3.13
- line-length: 99
- lint rules: E, F, I, N, UP, B, SIM

### Data Directory

```
data/
├── renewals.json             # Full policy data (generated by generate.py)
└── samples/
    ├── auto_pair.json        # Auto policy sample (test/demo)
    ├── home_pair.json        # Home policy sample
    └── golden_eval.json      # Golden eval 5 scenarios
```

---

## 11. Testing

### Test Status

13 files, 116 tests. (1 removed from previous 117)

| File | Test Count | Verification Target |
|------|----------|----------|
| `tests/test_rules.py` | 22 | Premium thresholds, flag assignment, liability/deductible/coverage/endorsement, driver violations, SR-22, youthful operator, coverage gap |
| `tests/test_differ.py` | 14 | Per-field diff calculation, identical policy no-change, vehicle/endorsement/coverage changes |
| `tests/test_routes.py` | 9 | health, compare, get_review, batch run/status/summary |
| `tests/test_parser.py` | 11 | Snapshot/pair parsing, vehicle/driver/endorsement, date normalization, notes, insured_name, account_id |
| `tests/test_quote_generator.py` | 12 | Auto/Home strategies, already-optimized cases, liability protection, route integration, LLM personalization, malformed response |
| `tests/test_batch.py` | 7 | process_pair, assign_risk_level 4 levels, process_batch |
| `tests/test_llm_analyzer.py` | 13 | should_analyze conditions, notes/endorsement analysis, MockLLM integration, generate_summary, malformed response fallback |
| `tests/test_analytics.py` | 9 | compute_trends (empty/single/multiple), compute_broker_metrics, routes (history/trends/broker), FIFO limit |
| `tests/test_notes_rules.py` | 9 | Per-category keyword matching, empty notes, case insensitive, custom config |
| `tests/test_models.py` | 6 | Model structure, DiffFlag values (23), risk level ordering |
| `tests/test_portfolio.py` | 8 | Bundle analysis, duplicate coverage, unbundle risk, premium concentration |
| `tests/test_main.py` | 1 | /health endpoint |
| `tests/conftest.py` | — | Shared fixtures (auto_pair, home_pair, etc.) |

### Golden Eval (`data/samples/golden_eval.json`)

5 scenarios:

| # | Description |
|---|------|
| 1 | 10% premium increase with rate adjustment note |
| 2 | 25% premium increase, water backup dropped, deductible raised, claim history note |
| 3 | Carrier switch, liability downgrade, vehicle removed, teen driver added |
| 4 | Clean renewal with minor premium increase (2.2%) |
| 5 | Inflation guard with endorsement description update and 10% premium increase |

Run via `POST /eval/run`. For each case, compares expected_min_risk and expected_flags against actual results to calculate accuracy.
