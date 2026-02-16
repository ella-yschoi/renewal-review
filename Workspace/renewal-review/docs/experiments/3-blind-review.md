I've now read every file. Here is my complete analysis:

---

# Agent B — Blind Review Analysis

## app/\_\_init\_\_.py
**Behavior:** Empty init file, makes `app/` a package.  
**Convention violations:** None.  
**Issues:** None.

---

## app/aggregator.py
**Behavior:** Combines rule-based risk assessment with LLM insights. Escalates the risk level based on high-confidence LLM signals: "NOT equivalent" findings → HIGH, ≥2 risk signals → HIGH, restriction changes → HIGH, combined strong signals → CRITICAL. Produces a `ReviewResult` with a summary string.

**Convention violations:** None.

**Issues:**
1. **String matching fragility** (line 21): `"NOT equivalent" in i.finding` — the aggregator is tightly coupled to the exact string produced by `_analyze_coverage` in `analyzer.py`. If the LLM analysis output format changes, this silently stops escalating risk.
2. **String matching fragility** (line 34): `"restriction" in i.finding.lower()` — same issue, depends on exact text produced by the mock client's `change_type: "restriction"` being embedded in the finding string `"Change type: restriction"`. This coupling is implicit and fragile.

---

## app/config.py
**Behavior:** Loads `.env`, defines `Settings` with env prefix `RR_`. Exposes `settings` singleton.

**Convention violations:** None.

**Issues:** None.

---

## app/data\_loader.py
**Behavior:** Loads `RenewalPair` data from DB (async) or JSON fallback. Caches in a module-level global. Falls back to JSON if `asyncio.run()` raises `RuntimeError` (e.g., already-running event loop).

**Convention violations:** None.

**Issues:**
1. **`RuntimeError` catch is overly broad** (line 49): `asyncio.run()` raises `RuntimeError` when called from within an existing async context, but `RuntimeError` can come from other sources. Should catch specifically or log the fallback.
2. **Global mutable state** (`_cached_pairs`): No thread safety. If two requests call `load_pairs` simultaneously, both could trigger `_load_from_db()` before the cache is set.
3. **`sample` falsy check** (line 18): `if sample and sample < len(...)` — `sample=0` would be falsy, but the route has `ge=1`, so this is fine in practice.

---

## app/db.py
**Behavior:** SQLAlchemy async engine/session factory with naming conventions. Lazy singleton pattern for engine and session factory. `init_db()` creates all tables.

**Convention violations:** None.

**Issues:** None.

---

## app/main.py
**Behavior:** Creates a FastAPI app, includes all routers, exposes `/health`.

**Convention violations:** None.

**Issues:** None.

---

## app/engine/\_\_init\_\_.py
**Behavior:** Empty init file.  
**Convention violations:** None.  
**Issues:** None.

---

## app/engine/analytics.py
**Behavior:** `compute_trends` takes a list of `BatchRunRecord`, computes aggregate stats (total runs, policies, average processing time, risk distribution, daily trends). Groups records by date for trend points.

**Convention violations:** None.

**Issues:** None. Clean, well-structured function.

---

## app/engine/batch.py
**Behavior:** Core processing pipeline. `assign_risk_level` maps diff flags to risk levels. `process_pair` diffs a renewal pair, applies rules, optionally runs LLM analysis. `process_batch` processes all pairs with progress callback, returns results + summary.

**Convention violations:** None.

**Issues:**
1. **Direct attribute mutation on Pydantic model** (line 37): `result.pair = pair` — this mutates a `ReviewResult` after construction. Works because Pydantic v2 doesn't freeze by default, but it's a pattern smell. Both code paths set `pair`, so it's functional.

---

## app/engine/differ.py
**Behavior:** Computes field-by-field diffs between prior and renewal policy snapshots. Handles universal fields (premium, carrier, notes), auto/home coverages, vehicles, drivers, and endorsements. Returns a `DiffResult` with all `FieldChange` items.

**Convention violations:** None.

**Issues:**
1. **File is 232 lines** — approaching the 300-line soft limit from convention.md but still within bounds.
2. **`_pct_change` returns `None` when prior is 0** (line 12): This is correct but means `FieldChange.change_pct` will be `None` for zero-prior values. Downstream consumers should handle this.

---

## app/engine/parser.py
**Behavior:** Parses raw dict data into typed Pydantic models. Normalizes dates (strips whitespace, `/` → `-`), uppercases VINs and license numbers, parses coverages based on policy type.

**Convention violations:** None.

**Issues:**
1. **Date normalization is naive** (line 16): `_normalize_date` only handles `/` → `-`. Doesn't handle other formats (e.g., `MM-DD-YYYY` vs `YYYY-MM-DD`). The Pydantic `date` field on `PolicySnapshot` will reject invalid formats, so this is somewhat self-protecting.

---

## app/engine/quote\_generator.py
**Behavior:** Generates up to 3 alternative quote recommendations based on renewal pair data and diff flags. Auto strategies: raise deductible (10% savings), drop optional coverages (4%), reduce medical payments (2.5%). Home strategies: raise deductible (12.5%), drop water backup (3%), reduce personal property (4%). Protected fields are never adjusted. Each strategy returns `None` if already optimized, skipping it.

**Convention violations:** None.

**Issues:**
1. **`PROTECTED_FIELDS` is declared but never actively enforced in the generation logic** (lines 5-11): The constant exists and tests check against it, but the strategies simply never touch those fields by design. The protection is implicit (no strategy function adjusts a protected field) rather than explicit (no guard checks `if field in PROTECTED_FIELDS: skip`). If someone adds a new strategy that touches a protected field, the `PROTECTED_FIELDS` set won't prevent it.
2. **`quote_id=""` is set at construction then mutated** (lines 41, 75, 100, etc. → line 209): Every `QuoteRecommendation` is created with `quote_id=""`, then reassigned in the loop at line 209. This is functional but could be cleaner — the intermediate empty-string state means the model has an invalid ID between creation and the loop.
3. **`quotes[:3]` truncation** (line 211): Since both `_AUTO_STRATEGIES` and `_HOME_STRATEGIES` have exactly 3 entries, this truncation is currently a no-op. But if strategies are added later, the IDs assigned in the loop (line 208-209) would cover all quotes, then some would be sliced off, leaving gaps in Q-numbering. Should assign IDs after truncation. Actually, re-reading: the IDs are assigned first on all quotes, then truncated. If there were 4 strategies yielding 4 quotes, IDs would be Q1-Q4, but only Q1-Q3 would be returned. This is a latent bug that doesn't manifest with current strategy counts.

---

## app/engine/rules.py
**Behavior:** Flag engine. Examines premium changes, carrier changes, and field-level changes to assign `DiffFlag` values. Premium thresholds: HIGH at 10%, CRITICAL at 20%. Detects liability limit decreases, deductible increases, coverage drops/adds, vehicle/driver/endorsement changes, notes changes, and boolean coverage changes.

**Convention violations:** None.

**Issues:**
1. **`flag_diff` mutates the input `DiffResult`** (line 125-145): The function takes `diff` and returns it, but also mutates it in-place (sets `diff.flags` and individual `c.flag`). This is a side-effect pattern. Callers use the return value, so it works, but it's worth noting.
2. **`diff.flags = list(set(flags))`** (line 144): Converting to set deduplicates, which is good. But if the same field type appears multiple times (e.g., two separate COVERAGE_DROPPED flags from different fields), only one flag instance remains in the set. The `flags` list on individual `FieldChange` objects is still correct, but the top-level `flags` list loses count information. This is intentional (flags as "present/absent" markers), but worth documenting.

---

## app/llm/\_\_init\_\_.py
**Behavior:** Empty init file.  
**Convention violations:** None.  
**Issues:** None.

---

## app/llm/analyzer.py
**Behavior:** Determines whether to invoke LLM analysis (`should_analyze`), then runs up to 3 analysis types: risk signal extraction from notes, endorsement comparison, and coverage similarity for boolean drops. Produces `LLMInsight` objects.

**Convention violations:** None.

**Issues:**
1. **`should_analyze` only checks water\_backup changes** (line 22-26): The condition `pair.prior.home_coverages.water_backup != pair.renewal.home_coverages.water_backup` means LLM analysis is triggered for water\_backup changes but not for `replacement_cost` changes. However, `analyze_pair` at line 114-120 checks both `water_backup` and `replacement_cost` in the coverage\_drops filter. So a `replacement_cost` drop won't trigger LLM analysis through the batch pipeline (since `should_analyze` returns False for it), but if called directly, `analyze_pair` would process it. This is an inconsistency — `replacement_cost` drops are handled in `analyze_pair` but never reached via the normal flow because `should_analyze` doesn't gate on them.

---

## app/llm/client.py
**Behavior:** Real LLM client supporting OpenAI and Anthropic providers, with optional Langfuse tracing. Parses JSON responses, returns error dict on failure.

**Convention violations:** None.

**Issues:**
1. **Bare exception handling** (line 57): `except (json.JSONDecodeError, Exception) as e:` — `Exception` already includes `json.JSONDecodeError`, so the tuple is redundant. This catches _all_ exceptions, which is intentional (don't crash on LLM failures), but the syntax is misleading.
2. **`raw` reference before assignment** (line 58): `"raw_response": raw if "raw" in dir() else ""` — uses `dir()` to check if `raw` was assigned. This is a code smell. If `_call_provider` throws before assigning, `raw` won't exist. The `dir()` trick works but is unusual.
3. **Anthropic call doesn't request JSON format** (lines 69-74): OpenAI uses `response_format={"type": "json_object"}` (line 81) to force JSON output, but the Anthropic call doesn't use structured output or equivalent. The prompts request JSON, but the Anthropic model might return non-JSON, leading to `json.JSONDecodeError`.

---

## app/llm/mock.py
**Behavior:** Deterministic mock LLM client for testing and migration comparisons. Records all calls. Returns canned responses based on `trace_name`. Supports optional Langfuse tracing even in mock mode.

**Convention violations:** None.

**Issues:**
1. **Langfuse in mock is surprising**: A mock client initializing Langfuse (lines 9-15) is unexpected. This means test runs with `LANGFUSE_PUBLIC_KEY` set will send trace data, which could pollute production observability.

---

## app/llm/prompts.py
**Behavior:** Three prompt templates for LLM analysis: coverage similarity, endorsement comparison, and risk signal extraction. Each requests JSON output with specific schema.

**Convention violations:** None.

**Issues:**
1. **`PROMPT_MAP` is defined but never used anywhere** (lines 52-56): Dead code.

---

## app/models/\_\_init\_\_.py
**Behavior:** Empty init file.  
**Convention violations:** None.  
**Issues:** None.

---

## app/models/analytics.py
**Behavior:** Three Pydantic models for analytics: `BatchRunRecord` (single batch run), `TrendPoint` (daily aggregate), `AnalyticsSummary` (full summary with trends).

**Convention violations:** None.

**Issues:** None.

---

## app/models/db\_models.py
**Behavior:** SQLAlchemy ORM models for `renewal_pairs` and `batch_results` tables. Uses mapped columns with typed annotations.

**Convention violations:** None.

**Issues:**
1. **`effective_date_prior` / `effective_date_renewal` have no explicit column type** (lines 19-20): `mapped_column()` with no type argument for `date` fields. SQLAlchemy can infer from `Mapped[date]`, but being explicit (like the other columns) would be more consistent.

---

## app/models/diff.py
**Behavior:** Data models for diff results. `DiffFlag` enum has 15 flag types. `FieldChange` holds a single field diff. `DiffResult` holds all changes and flags for a policy.

**Convention violations:** None.

**Issues:** None.

---

## app/models/policy.py
**Behavior:** Core domain models. `PolicyType` (auto/home), `Endorsement`, `Vehicle`, `Driver`, `AutoCoverages`, `HomeCoverages`, `PolicySnapshot`, `RenewalPair`. Uses Pydantic with sensible defaults.

**Convention violations:** None.

**Issues:**
1. **`effective_date`/`expiration_date` typed as `date`** (lines 63-64) but `_normalize_date` in parser returns a string: Pydantic v2 coerces `str` → `date` automatically if the format is correct, so this works. But the type mismatch between the parser's return type (str) and the model's field type (date) is implicit.

---

## app/models/quote.py
**Behavior:** Two Pydantic models: `CoverageAdjustment` (field, original/proposed values, strategy name) and `QuoteRecommendation` (quote ID, adjustments list, savings percentage/dollar, trade-off description).

**Convention violations:** None.

**Issues:** None.

---

## app/models/review.py
**Behavior:** Review-related models. `RiskLevel` enum (4 levels), `LLMInsight` (analysis type, finding, confidence, reasoning), `ReviewResult` (full review output), `BatchSummary` (batch stats).

**Convention violations:** None.

**Issues:** None.

---

## app/routes/\_\_init\_\_.py
**Behavior:** Empty init file.  
**Convention violations:** None.  
**Issues:** None.

---

## app/routes/analytics.py
**Behavior:** Two endpoints: GET `/analytics/history` returns the FIFO history, GET `/analytics/trends` computes and returns analytics summary. Module-level `deque(maxlen=100)` as in-memory store.

**Convention violations:** None.

**Issues:** None.

---

## app/routes/batch.py
**Behavior:** POST `/batch/run` starts an async batch job — loads pairs, processes them in a thread executor, stores results, records analytics history. GET `/batch/status/{job_id}` checks job progress. GET `/batch/summary` returns the last batch summary.

**Convention violations:** None.

**Issues:**
1. **`asyncio.get_event_loop()` is deprecated** (line 49): Should use `asyncio.get_running_loop()` instead. `get_event_loop()` can create a new loop in some contexts and emits a deprecation warning in Python 3.10+.
2. **`_jobs` dict grows unboundedly** (line 23): Completed/failed jobs are never cleaned up. Over time this is a memory leak.
3. **`store.clear()` before adding results** (line 56): This wipes the entire results store on every batch run. Any previously-stored review results from `/reviews/compare` calls are lost. This is a design choice but could surprise users.
4. **Hardcoded timezone** (line 76): `ZoneInfo("America/Vancouver")` — the timezone is hardcoded rather than configurable. Other parts of the codebase use UTC.
5. **Race condition in `_process()`**: The lambda `lambda: process_batch(pairs, on_progress=on_progress)` runs in a thread executor while `_jobs[job_id]` is updated from both the executor thread (via `on_progress`) and the async task. Dict access in CPython is thread-safe due to the GIL, but this pattern is brittle.

---

## app/routes/eval.py
**Behavior:** Two features: (1) `/eval/run` — golden evaluation against a test set, checks risk levels and flags. (2) `/migration/comparison` — runs the same data through basic (rule-only) and LLM (mock) pipelines to compare results. Returns risk distribution diff, examples of changed classifications.

**Convention violations:** None.

**Issues:**
1. **Same `asyncio.get_event_loop()` deprecation** (line 96).
2. **`_migration_jobs` grows unboundedly** (line 17): Same memory leak pattern as batch.py.
3. **File is 189 lines** — reasonable size.
4. **`_risk_dist` has untyped `results` parameter** (line 68): The type hint is `list` without specifying element type. Should be `list[ReviewResult]`.

---

## app/routes/quotes.py
**Behavior:** POST `/quotes/generate` — parses a raw pair, processes it to get diff flags, then generates quote recommendations.

**Convention violations:** None.

**Issues:**
1. **Double flag check** (lines 21 + `generate_quotes` line 194): The route checks `if not result.diff.flags: return []`, and `generate_quotes` internally also checks `if not diff.flags: return []`. The check in the route is redundant. Not a bug, but unnecessary duplication.

---

## app/routes/reviews.py
**Behavior:** POST `/reviews/compare` — parses and processes a pair, stores the result. GET `/reviews/{policy_number}` — retrieves a stored review.

**Convention violations:** None.

**Issues:** None.

---

## app/routes/ui.py
**Behavior:** Three UI routes: dashboard (paginated results list), review detail page, migration comparison page. Uses Jinja2 templates.

**Convention violations:** None.

**Issues:**
1. **Direct import of private variable** (line 28): `from app.routes.batch import _last_summary` — accessing a "private" module variable. Should ideally have a getter function like `get_last_summary()` for consistency with `get_results_store()` and `get_history_store()`.
2. **Sorting by enum string value** (line 19): `key=lambda r: r.risk_level.value` — sorts alphabetically by the string value ("critical", "high", "low", "medium"), not by severity. This means the actual order would be: critical, high, low, medium — with LOW appearing before MEDIUM. This is a **bug**. The intended behavior is likely to sort by risk severity (critical first, then high, medium, low).

---

## tests/\_\_init\_\_.py
**Behavior:** Empty init file.  
**Convention violations:** None.  
**Issues:** None.

---

## tests/conftest.py
**Behavior:** Shared test fixtures. Loads auto and home sample pairs from JSON files in `data/samples/`.

**Convention violations:** None.

**Issues:** None.

---

## tests/test\_analytics.py
**Behavior:** 6 tests covering `compute_trends` (empty, single, multiple records), analytics route endpoints, and FIFO deque limit behavior.

**Convention violations:** None.

**Issues:** None. Solid test coverage.

---

## tests/test\_batch.py
**Behavior:** Tests for `assign_risk_level`, `process_pair`, and `process_batch` covering all risk levels and batch processing.

**Convention violations:** None.

**Issues:** None.

---

## tests/test\_differ.py
**Behavior:** Comprehensive diff tests including identical-pair-no-diff, specific field detection, hypothesis property-based tests for premium percentage calculation and vehicle diffs.

**Convention violations:** None.

**Issues:** None. Good use of hypothesis for property-based testing.

---

## tests/test\_llm\_analyzer.py
**Behavior:** Tests `should_analyze` gating logic, LLM analysis for notes/endorsements/coverage drops, integration with mock client.

**Convention violations:** None.

**Issues:** None.

---

## tests/test\_main.py
**Behavior:** Single health check route test.

**Convention violations:** None.

**Issues:**
1. **Duplicated test**: `test_health()` exists in both `test_main.py` and `test_routes.py`. Minor redundancy.

---

## tests/test\_models.py
**Behavior:** Model structure tests: pair shapes, flag enum count, field change construction, risk level ordering, batch summary defaults.

**Convention violations:** None.

**Issues:** None.

---

## tests/test\_parser.py
**Behavior:** Tests snapshot parsing, vehicle/driver/endorsement parsing, date normalization, notes extraction.

**Convention violations:** None.

**Issues:** None.

---

## tests/test\_quote\_generator.py
**Behavior:** 8 tests: auto all-strategies, home all-strategies, already-optimized auto, protected field check, no-flags-empty, and route integration tests for both auto and home.

**Convention violations:** None.

**Issues:** None. Thorough coverage.

---

## tests/test\_routes.py
**Behavior:** Integration tests for review, batch, and health routes. Tests happy paths, error cases (invalid input, 404), and batch job creation.

**Convention violations:** None.

**Issues:** None.

---

## tests/test\_rules.py
**Behavior:** Tests premium threshold boundaries (below/at high and critical), premium decrease, carrier change, all flag types on real sample data, and flag-change consistency.

**Convention violations:** None.

**Issues:** None.

---

## Summary of Significant Issues

| Severity | File | Issue |
|----------|------|-------|
| **BUG** | `app/routes/ui.py:19` | Risk level sorting by string value produces wrong order (critical, high, **low**, **medium** instead of critical, high, medium, low) |
| **BUG (latent)** | `app/llm/analyzer.py:22-26` | `should_analyze` doesn't trigger for `replacement_cost` drops, but `analyze_pair` handles them — unreachable code path |
| **BUG (latent)** | `app/engine/quote_generator.py:208-211` | Quote IDs assigned before `[:3]` truncation — would produce ID gaps if strategies > 3 |
| Fragility | `app/aggregator.py:21,34` | Risk escalation depends on exact substring matches in LLM findings — tightly coupled to output format |
| Deprecation | `app/routes/batch.py:49`, `eval.py:96` | `asyncio.get_event_loop()` deprecated in Python 3.10+ |
| Memory leak | `app/routes/batch.py:23`, `eval.py:17` | Job dicts grow unboundedly, never cleaned up |
| Code smell | `app/llm/client.py:57-58` | Redundant exception tuple; `dir()` trick for checking `raw` variable |
| Dead code | `app/llm/prompts.py:52-56` | `PROMPT_MAP` defined but never imported or used |
| Inconsistency | `app/routes/batch.py:76` | Hardcoded `America/Vancouver` timezone vs UTC used elsewhere |
| Inconsistency | `app/routes/ui.py:28` | Direct import of `_last_summary` private variable |
