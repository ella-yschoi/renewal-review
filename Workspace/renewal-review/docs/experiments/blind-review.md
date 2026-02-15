# Agent B — Blind Review Analysis (Round 2: Portfolio Aggregator)

> Reviewed files: `app/models/portfolio.py`, `app/engine/portfolio_analyzer.py`, `app/routes/portfolio.py`, `app/main.py`, `tests/test_portfolio.py`
> Convention reference: `convention.md`, `docs/design-doc.md`
> Date: 2026-02-14

---

## app/models/portfolio.py (NEW)

**Behavior:** Defines three Pydantic models for portfolio-level analysis. `CrossPolicyFlag` represents a cross-policy issue detected during analysis (e.g., duplicate coverage, high exposure), with a type identifier, severity level, description, and list of affected policy numbers. `BundleAnalysis` captures whether a client has auto/home bundling, whether carriers match, and the risk level of unbundling. `PortfolioSummary` is the top-level response model aggregating all policies: total/prior premiums, percentage change, risk breakdown by level, bundle analysis, and cross-policy flags.

**Convention violations:** None. No docstrings, uses type hints, file is well under 300 lines (27 lines).

**Issues:**
1. **`severity` and `unbundle_risk` are untyped strings** (lines 5, 17): `CrossPolicyFlag.severity` accepts any string but the engine only produces `"warning"`, `"info"`, and `"critical"`. `BundleAnalysis.unbundle_risk` only produces `"low"`, `"medium"`, `"high"`. Both should be `Literal` types or `StrEnum` values to enforce valid values at the model level. As-is, a typo like `severity="warn"` would pass validation silently.
2. **`flag_type` is also an untyped string** (line 4): The engine produces specific values (`"duplicate_medical"`, `"duplicate_roadside"`, `"high_liability_exposure"`, `"low_liability_exposure"`, `"premium_concentration"`, `"high_portfolio_increase"`). An enum would make these discoverable and prevent typos.
3. **`risk_breakdown` typed as `dict[str, int]`** (line 25): The keys are `RiskLevel` enum values (strings), but this type doesn't constrain to valid risk levels. A consumer could insert arbitrary keys. Minor — this matches the existing pattern in `AnalyticsSummary.risk_distribution`.

---

## app/engine/portfolio_analyzer.py (NEW)

**Behavior:** Core business logic for cross-policy portfolio analysis. Contains five functions:

- `_build_bundle_analysis`: Determines auto/home bundling status, checks for carrier mismatch across policies, assesses unbundle risk based on the worst risk level among results.
- `_detect_duplicate_coverage`: Scans for overlapping medical payments (auto medical_payments + home Coverage F) and roadside assistance (auto roadside_assistance + home endorsement containing "roadside" or "towing").
- `_calculate_exposure_flags`: Sums liability exposure across all policies (home Coverage E + auto bodily injury first number x 1000) and flags if total exceeds $500K (umbrella recommendation) or falls below $200K (underinsurance warning).
- `_detect_premium_concentration`: Flags any single policy that represents >= 70% of total portfolio premium. Also flags if the overall portfolio premium change exceeds +/-15%.
- `analyze_portfolio`: Orchestrator. Deduplicates policy numbers, looks up results from the store, calculates premium totals, builds risk breakdown, runs all analyses, and returns `PortfolioSummary`.

**Convention violations:** None. No docstrings, type hints throughout, functions are single-responsibility, file is 232 lines (within 300-line limit).

**Issues:**
1. **`bodily_injury_limit` parsing assumes format "X/Y"** (line 110): `snap.auto_coverages.bodily_injury_limit.split("/")[0]` will crash with `IndexError` if the value is an empty string, or produce wrong results for non-standard formats. The `AutoCoverages` model defaults to `"100/300"`, but there's no validation at the model level that enforces this format. If external data contains `"100000"` (a raw number) or `""`, the parsing fails.
2. **`float(bi_str) * 1000` assumes the value is in thousands** (line 111): This is a domain assumption (bodily injury limits are typically expressed as "100/300" meaning $100K/$300K). The assumption is correct for standard insurance data, but there's no inline comment explaining this conversion despite the convention saying to comment non-obvious logic. The `# bodily_injury_limit format: "100/300" -- first number x 1000` comment on line 109 does explain it — so this is adequately documented.
3. **`total_prior_premium` division-by-zero is handled but produces `0.0`** (lines 202-206): If all prior premiums are zero (new policies), the percentage change is `0.0`. This is mathematically questionable — going from $0 to any amount is an infinite increase, not 0%. However, returning 0.0 is a pragmatic choice that avoids breaking downstream logic. Worth noting that this means `_detect_premium_concentration`'s `abs(premium_change_pct) >= 15.0` check would never fire for new-policy portfolios, even if the total premium is very large.
4. **`results` list skips entries with `r.pair is None`** in premium calculation (line 200-201): The `if r.pair` guard is correct defensively, but `analyze_portfolio` at line 196 raises `ValueError` if a policy number has no review. The only way `r.pair` could be `None` is if a `ReviewResult` exists in the store without a pair attached. The code handles this inconsistently — it raises on missing reviews but silently skips pair-less reviews. A pair-less review would contribute to `risk_breakdown` (line 211-212) but not to premiums (line 200-201), bundle analysis, or cross-policy flags. This could produce misleading summaries (e.g., a policy counted in risk breakdown but its premium excluded from totals).
5. **Deduplication via `dict.fromkeys`** (line 189): Correct and idiomatic. Preserves insertion order in Python 3.7+. No issue.
6. **`_detect_premium_concentration` receives `premium_change_pct` but also receives `total_premium`** (line 146): The function could compute `premium_change_pct` internally if it also received `total_prior_premium`, but the caller pre-computes it. This is fine — avoids recalculation.
7. **No upper bound on policy count**: `analyze_portfolio` will process any number of policies. For very large portfolios (hundreds of policies), the nested iteration in `_detect_premium_concentration` (iterating all results inside a loop that's already O(n)) is still O(n) per call since the inner loop is just one pass. No performance concern for reasonable portfolio sizes.

---

## app/routes/portfolio.py (NEW)

**Behavior:** Single POST endpoint at `/portfolio/analyze`. Accepts a JSON body with `policy_numbers` (list of strings). Validates that at least 2 policies are provided (422 error otherwise). Looks up the shared results store from `app.routes.reviews.get_results_store()`, calls `analyze_portfolio`, and returns a `PortfolioSummary`. Catches `ValueError` from missing policy lookups and converts to 422 HTTP errors.

**Convention violations:** None. No docstrings, uses type hints, file is 27 lines.

**Issues:**
1. **`PortfolioRequest` model defined inline** (lines 11-12): This is a route-local request model, not a domain model. Defining it here (rather than in `app/models/portfolio.py`) is a judgment call. The existing `app/routes/quotes.py` does not define inline models — it accepts a raw dict. This is actually better than the quotes route pattern (typed vs untyped input), but it's a different pattern from other routes in the codebase.
2. **No upper bound on `policy_numbers`** (line 12): A client could submit thousands of policy numbers. While `analyze_portfolio` is O(n), there's no max length validation. For a production API, this could be a denial-of-service vector if the store is large.
3. **Sync endpoint** (line 16): `def analyze(...)` is synchronous. This matches the existing route patterns (`app/routes/reviews.py`, `app/routes/quotes.py`). For CPU-bound analysis with many policies, this blocks the event loop, but the existing codebase uses sync endpoints for similar workloads, so this is consistent.
4. **Status code 422 for both validation error and missing policy** (lines 19, 27): Using 422 (Unprocessable Entity) is semantically correct for validation failures. For missing policies, 404 could also be argued, but 422 is reasonable since the request body is the problem. Consistent choice.
5. **Shared mutable state via `get_results_store()`** (line 23): The portfolio route reads from the same in-memory dict that `app/routes/reviews.py` and `app/routes/batch.py` write to. The batch route clears this store on every run (`store.clear()` in `batch.py` line 56). This means portfolio analysis results depend on timing — if a batch run starts between individual review submissions and the portfolio analyze call, all previously-stored reviews are wiped. This is a pre-existing architectural issue (noted in the previous blind review), but the portfolio feature amplifies its impact since it requires multiple policies to be present simultaneously.

---

## app/main.py (MODIFIED)

**Behavior:** Added `from app.routes.portfolio import router as portfolio_router` and `app.include_router(portfolio_router)`. The portfolio router is registered after the quotes router.

**Convention violations:** None.

**Issues:**
1. **Router registration order**: The portfolio router is added last (line 23). Router order matters for route matching in FastAPI only when paths could collide. `/portfolio/analyze` does not collide with any existing prefix (`/reviews`, `/batch`, `/eval`, `/analytics`, `/quotes`, `/ui`). No issue.

---

## tests/test_portfolio.py (NEW)

**Behavior:** 8 tests covering the portfolio analysis feature:

- `test_bundle_auto_home`: Auto + Home from same carrier produces `is_bundle=True`, `bundle_discount_eligible=True`, correct premium totals.
- `test_auto_only_no_bundle`: Two auto policies produce `is_bundle=False`.
- `test_duplicate_medical_detection`: Auto with medical_payments > 0 + Home with coverage_f_medical > 0 triggers `duplicate_medical` flag.
- `test_unbundle_risk_high`: Bundle where one policy has `ACTION_REQUIRED` risk produces `unbundle_risk="high"`.
- `test_premium_concentration`: One policy at 90% of total premium triggers `premium_concentration` flag.
- `test_high_portfolio_increase`: 33.3% total premium increase triggers `high_portfolio_increase` flag.
- `test_single_policy_error`: Route rejects single-policy requests with 422.
- `test_missing_policy_error`: Route returns 422 with "No review found" for nonexistent policies.

Uses a `_make_review` helper to construct `ReviewResult` objects with full `RenewalPair` data, and a `_build_store` helper to create the lookup dict.

**Convention violations:** None. File naming follows `test_*.py` convention. Tests cover business logic, not trivial getters.

**Issues:**
1. **No test for carrier mismatch** (missing): `_build_bundle_analysis` has a `carrier_mismatch` code path that sets `bundle_discount_eligible=False` when carriers differ. No test exercises this. This is a significant untested branch.
2. **No test for duplicate roadside detection** (missing): `_detect_duplicate_coverage` checks for roadside assistance overlap (auto `roadside_assistance=True` + home endorsement with "roadside"/"towing" in description). No test covers this path.
3. **No test for exposure flags** (missing): `_calculate_exposure_flags` has two branches — high liability (>$500K) and low liability (<$200K). Neither is tested. The bodily injury limit parsing logic (`split("/")[0]`, `float(...) * 1000`) is also untested.
4. **No test for `unbundle_risk="medium"`** (missing): Only "high" is tested (via `ACTION_REQUIRED`). The "medium" path (via `REVIEW_RECOMMENDED` without `ACTION_REQUIRED`/`URGENT_REVIEW`) is not covered. Note: `test_bundle_auto_home` does use `REVIEW_RECOMMENDED` as the default, but it asserts on `is_bundle` and premiums, not on `unbundle_risk`.
5. **No test for deduplication** (missing): `analyze_portfolio` deduplicates via `dict.fromkeys`. No test passes duplicate policy numbers to verify the behavior.
6. **`_make_review` uses same coverages for prior and renewal** (lines 37-38, 48): The helper assigns the same `auto_coverages`/`home_coverages` to both prior and renewal snapshots. This means the `DiffResult` will always have empty changes/flags. This is intentional for portfolio tests (which don't exercise diff logic), but it means the portfolio tests never interact with flagged policies. The `_detect_premium_concentration`'s `abs(premium_change_pct) >= 15.0` path is tested via premium differences, but cross-policy flags that might depend on flag state are not tested.
7. **`test_missing_policy_error` mutates shared state** (lines 189-190): `store = get_results_store(); store.clear()` clears the global results store. If tests run in parallel or in a specific order, this could cause other tests to fail. In practice, pytest runs tests sequentially by default, and the other tests in this file use local stores (not the global one), so this is safe. But it's a fragile pattern — any future test that populates the global store before this test would be affected.
8. **No test for `premium_change_pct` rounding** (missing): `analyze_portfolio` rounds to 2 decimal places (`round(premium_change_pct, 2)`). No test verifies this precision. Minor.
9. **No route integration test for happy path** (missing): `test_single_policy_error` and `test_missing_policy_error` test error cases via the HTTP client. There is no route-level test that populates the global store with reviews and then calls `POST /portfolio/analyze` successfully. All happy-path tests call `analyze_portfolio` directly, bypassing the route layer.

---

## Summary of Significant Issues

| Severity | File | Issue |
|----------|------|-------|
| **Missing test** | `tests/test_portfolio.py` | Carrier mismatch branch is untested — `bundle_discount_eligible=False` when carriers differ |
| **Missing test** | `tests/test_portfolio.py` | Duplicate roadside detection is untested — endorsement text matching logic not exercised |
| **Missing test** | `tests/test_portfolio.py` | Liability exposure flags (high >$500K, low <$200K) and BI limit parsing completely untested |
| **Missing test** | `tests/test_portfolio.py` | No happy-path route integration test — only error cases tested via HTTP client |
| **Edge case** | `app/engine/portfolio_analyzer.py:110` | `bodily_injury_limit.split("/")` assumes "X/Y" format — crashes on empty string or non-standard formats |
| **Edge case** | `app/engine/portfolio_analyzer.py:200-206` | Pair-less `ReviewResult` contributes to risk breakdown but excluded from premium calculations — inconsistent treatment |
| **Design** | `app/models/portfolio.py:5,17` | `severity`, `unbundle_risk`, and `flag_type` are untyped strings — should be `Literal` or `StrEnum` for safety |
| **Design** | `app/routes/portfolio.py:12` | No upper bound on `policy_numbers` list length — potential DoS vector |
| **Fragility** | `tests/test_portfolio.py:189-190` | `store.clear()` mutates global state — could break tests if execution order changes |
| **Architectural** | `app/routes/portfolio.py:23` | Depends on shared mutable `_results_store` that is cleared by batch runs — portfolio analysis results are timing-dependent |
