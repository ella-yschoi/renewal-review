# Discrepancy Report — Triangular Verification (Round 2: Portfolio Aggregator)

> Agent C comparison of requirements doc vs. blind code review
> Date: 2026-02-14

---

## Requirements Met

### FR-1: Portfolio Analysis Endpoint
**CONFIRMED.** The blind review describes `app/routes/portfolio.py` implementing `POST /portfolio/analyze` that accepts a JSON body with `policy_numbers` (list of strings). It validates at least 2 policies (422 otherwise), looks up results from the shared store, and returns 422 when a policy number is not found. This matches FR-1 exactly.

**Evidence:** Blind review `app/routes/portfolio.py` section -- "Single POST endpoint at `/portfolio/analyze`. Accepts a JSON body with `policy_numbers` (list of strings). Validates that at least 2 policies are provided (422 error otherwise)... Catches `ValueError` from missing policy lookups and converts to 422 HTTP errors."

### FR-2: Portfolio Summary Model
**CONFIRMED.** The blind review describes `PortfolioSummary` as a Pydantic model with: `client_policies` (list of policy numbers), `total_premium`, `total_prior_premium`, `premium_change_pct`, `risk_breakdown` (dict[str, int]), `bundle_analysis` (BundleAnalysis), and `cross_policy_flags` (list[CrossPolicyFlag]). All fields match the requirement.

**Evidence:** Blind review `app/models/portfolio.py` section -- "`PortfolioSummary` is the top-level response model aggregating all policies: total/prior premiums, percentage change, risk breakdown by level, bundle analysis, and cross-policy flags." Issue #3 confirms `risk_breakdown` is typed as `dict[str, int]`.

### FR-3: Bundle Analysis
**CONFIRMED.** The blind review describes `BundleAnalysis` with `has_auto`, `has_home`, `is_bundle`, `bundle_discount_eligible` (True when same carrier), `carrier_mismatch` (True when carriers differ), and `unbundle_risk` with values "low"/"medium"/"high". The unbundle risk logic matches: high when action_required-level risk is present in a bundle, medium when review_recommended, low otherwise.

**Evidence:** Blind review `app/engine/portfolio_analyzer.py` -- "`_build_bundle_analysis`: Determines auto/home bundling status, checks for carrier mismatch across policies, assesses unbundle risk based on the worst risk level among results." Issue #4 in tests confirms unbundle_risk="high" is tested via `ACTION_REQUIRED`, and notes medium path uses `REVIEW_RECOMMENDED`.

### FR-4: Cross-Policy Flags
**CONFIRMED.** `CrossPolicyFlag` model has `flag_type` (str), `severity` (str with values "info"/"warning"/"critical"), `description` (str), and `affected_policies` (list[str]).

**Evidence:** Blind review `app/models/portfolio.py` section -- "`CrossPolicyFlag` represents a cross-policy issue detected during analysis... with a type identifier, severity level, description, and list of affected policy numbers."

### FR-5: Duplicate Coverage Detection
**CONFIRMED.** The blind review describes `_detect_duplicate_coverage` detecting: (1) overlapping medical payments (auto `medical_payments` + home `coverage_f_medical`) producing `duplicate_medical` flag, and (2) roadside assistance overlap (auto `roadside_assistance` + home endorsement containing "roadside"/"towing") producing `duplicate_roadside` flag.

**Evidence:** Blind review `app/engine/portfolio_analyzer.py` -- "`_detect_duplicate_coverage`: Scans for overlapping medical payments (auto medical_payments + home Coverage F) and roadside assistance (auto roadside_assistance + home endorsement with 'roadside'/'towing' in description)."

Note: The requirements specify `duplicate_medical` severity as "warning" and `duplicate_roadside` severity as "info". The blind review lists the engine producing `"warning"`, `"info"`, and `"critical"` as severity values (models section, issue #1), which is consistent.

### FR-6: Total Exposure Calculation
**CONFIRMED.** The blind review describes `_calculate_exposure_flags` summing home `Coverage E` liability + auto bodily injury first number x 1000, then flagging `high_liability_exposure` when >$500K and `low_liability_exposure` when <$200K.

**Evidence:** Blind review `app/engine/portfolio_analyzer.py` -- "`_calculate_exposure_flags`: Sums liability exposure across all policies (home Coverage E + auto bodily injury first number x 1000) and flags if total exceeds $500K (umbrella recommendation) or falls below $200K (underinsurance warning)."

Note: The requirements specify high exposure as severity "info" and low exposure as severity "warning". The blind review's issue #1 in the models section confirms the engine only produces `"warning"`, `"info"`, and `"critical"` -- consistent with requirements.

### FR-7: Premium Concentration Risk
**CONFIRMED.** The blind review describes `_detect_premium_concentration` flagging: (1) any single policy >= 70% of total premium as `premium_concentration`, and (2) overall portfolio premium change exceeding +/-15% as `high_portfolio_increase`.

**Evidence:** Blind review `app/engine/portfolio_analyzer.py` -- "`_detect_premium_concentration`: Flags any single policy that represents >= 70% of total portfolio premium. Also flags if the overall portfolio premium change exceeds +/-15%."

Note on severity: FR-7 specifies `premium_concentration` as "warning" and `high_portfolio_increase` as "critical". The blind review confirms these are among the values the engine produces.

### FR-8: Edge Cases
**CONFIRMED.** The blind review confirms:
- 1 policy or empty list returns 422 error (route validation: "Validates that at least 2 policies are provided (422 error otherwise)")
- Deduplication via `dict.fromkeys` (engine issue #5: "Deduplication via `dict.fromkeys`... Correct and idiomatic")
- Auto-only or home-only analysis works (test `test_auto_only_no_bundle` shows `is_bundle=False` for two auto policies)

**Evidence:** Blind review route section and test section.

### FR-9: Testing (8 required test cases)
**CONFIRMED.** The blind review describes exactly 8 test cases matching all required scenarios:

| Required Test Case | Test Name | Evidence |
|---|---|---|
| 1. auto + home bundle, is_bundle=True | `test_bundle_auto_home` | "Auto + Home from same carrier produces `is_bundle=True`, `bundle_discount_eligible=True`, correct premium totals." |
| 2. auto only, is_bundle=False | `test_auto_only_no_bundle` | "Two auto policies produce `is_bundle=False`." |
| 3. duplicate medical detection | `test_duplicate_medical_detection` | "Auto with medical_payments > 0 + Home with coverage_f_medical > 0 triggers `duplicate_medical` flag." |
| 4. unbundle_risk high case | `test_unbundle_risk_high` | "Bundle where one policy has `ACTION_REQUIRED` risk produces `unbundle_risk=\"high\"`." |
| 5. premium_concentration detection | `test_premium_concentration` | "One policy at 90% of total premium triggers `premium_concentration` flag." |
| 6. high_portfolio_increase detection | `test_high_portfolio_increase` | "33.3% total premium increase triggers `high_portfolio_increase` flag." |
| 7. single policy 422 error | `test_single_policy_error` | "Route rejects single-policy requests with 422." |
| 8. missing policy 422 error | `test_missing_policy_error` | "Route returns 422 with 'No review found' for nonexistent policies." |

### Non-Functional Requirements
**PARTIALLY CONFIRMED.**
- Convention compliance: All files report "Convention violations: None"
- File sizes: `portfolio.py` model 27 lines, `portfolio_analyzer.py` 232 lines, route 27 lines -- all under 300 lines
- No docstrings: Confirmed across all new files

**Not verifiable via blind review:** "existing tests all pass (no regression)", "ruff check 0 errors", "semgrep 0 findings" are runtime checks that require execution, not static review.

---

## Requirements Missed

**None identified.** All functional requirements (FR-1 through FR-9) and all non-functional requirements assessable via code review are reflected in the blind review.

---

## Extra Behavior

### 1. PortfolioRequest inline model
The blind review notes a `PortfolioRequest` Pydantic model defined inline in `app/routes/portfolio.py` (route issue #1). This is not specified in the requirements but is a reasonable implementation detail for request validation. It is a minor pattern difference from other routes in the codebase.

### 2. Absolute-value threshold for portfolio premium change
The blind review notes `_detect_premium_concentration` fires on `abs(premium_change_pct) >= 15.0`, meaning it triggers on both increases AND decreases of 15% or more. FR-7 says "전체 보험료 변동이 15% 이상이면" (premium change >= 15%). The use of `abs()` means a 15% *decrease* would also trigger the flag. The Korean word "변동" (change/fluctuation) can encompass both directions, so this is a reasonable interpretation. However, the flag name `high_portfolio_increase` is directionally specific to increases.

### 3. Division-by-zero handling for prior premiums
The engine returns `premium_change_pct = 0.0` when `total_prior_premium` is zero. This is an implementation decision not specified in the requirements but necessary for correctness.

### 4. Router registration in main.py
The blind review describes modification to `app/main.py` to register the portfolio router. This is an implicit infrastructure requirement (the endpoint must be reachable) but not explicitly stated in the requirements doc.

---

## Potential Bugs

### 1. `bodily_injury_limit` parsing fragility (Medium severity)
**Requirement (FR-6):** auto `bodily_injury_limit` first number x 1000.
**Blind review finding:** `split("/")[0]` on the BI limit string will crash with `IndexError` on empty string or produce incorrect results for non-standard formats. The `AutoCoverages` model defaults to "100/300", but there is no validation enforcing this format.
**Assessment:** If any policy has a non-standard BI limit format (empty string, raw number, unexpected delimiter), the entire portfolio analysis would crash with an unhandled exception. This is an edge case not addressed by the requirements, but it represents a runtime failure risk.

### 2. Pair-less ReviewResult inconsistency (Low severity)
**Blind review finding:** The engine raises `ValueError` for missing reviews but silently skips reviews where `r.pair is None`. A pair-less review would be counted in `risk_breakdown` but excluded from premium calculations, bundle analysis, and cross-policy flags.
**Assessment:** The inconsistency means a pair-less review produces a misleading summary (counted in one metric but not others). This scenario is unlikely in practice but represents a defensive programming gap.

### 3. `high_portfolio_increase` flag name vs. abs() behavior (Low severity)
**Requirement (FR-7):** "전체 보험료 변동이 15% 이상이면 `high_portfolio_increase` 플래그 (severity: 'critical')."
**Blind review finding:** Uses `abs(premium_change_pct) >= 15.0`, so a 15% decrease also triggers the flag.
**Assessment:** The flag name `high_portfolio_increase` implies only increases, but the implementation also flags large decreases. This is a naming/semantic inconsistency. The requirement text is ambiguous enough to allow this interpretation, but the flag name misleads consumers.

---

## Test Coverage Gaps (advisory, not requirement violations)

The blind review identifies untested code paths that exceed FR-9's 8 required cases but represent quality risks:

1. **Carrier mismatch** -- `bundle_discount_eligible=False` when carriers differ (untested branch)
2. **Duplicate roadside detection** -- endorsement text matching for "roadside"/"towing" (untested)
3. **Liability exposure flags** -- neither high (>$500K) nor low (<$200K) threshold tested; BI limit parsing untested
4. **Unbundle risk "medium"** -- only "high" case tested; "medium" (REVIEW_RECOMMENDED) untested
5. **Deduplication** -- passing duplicate policy numbers not tested
6. **Happy-path route integration** -- no HTTP-level test for successful portfolio analysis (only error cases tested via HTTP)

FR-9 requires "최소 8개 테스트 케이스" (at least 8 test cases) with 8 specific scenarios. All 8 are implemented. The gaps above are additional branches beyond the required test cases.

---

## Verdict

All 9 functional requirements (FR-1 through FR-9) are confirmed met by the blind review. All non-functional requirements assessable via code review are satisfied. The 8 required test cases are implemented and match their specifications exactly.

Issues found:
- **No critical bugs** that violate requirements
- **Medium-severity edge case:** BI limit parsing could crash on non-standard formats (FR-6 implementation risk)
- **Low-severity naming inconsistency:** `high_portfolio_increase` flag name vs. `abs()` threshold behavior
- **Low-severity defensive gap:** pair-less ReviewResult handled inconsistently
- **Advisory:** 6 additional code branches not covered by tests (beyond FR-9's required 8 cases)

All issues are edge cases or design quality concerns, not requirement violations.

TRIANGULAR_PASS
