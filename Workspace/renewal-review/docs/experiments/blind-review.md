# Blind Review -- Quote Generator Module

> **Agent B** | 2026-02-14
> This review is written without reading any requirements document. All observations are derived solely from reading the source code.

---

## 1. File-by-File Analysis

### 1.1 `app/models/quote.py`

**What this code does:**

Defines two Pydantic data models that represent the output of the quote generation pipeline.

- `CoverageAdjustment` represents a single proposed change to a coverage field. It carries the field name (`field`), its current value as a string (`original_value`), the suggested replacement as a string (`proposed_value`), and the name of the strategy that produced it (`strategy`). This is the atomic unit of a cost-saving recommendation.
- `QuoteRecommendation` bundles one or more `CoverageAdjustment` items into a single recommendation. It assigns a `quote_id` string, an `estimated_savings_pct` (percentage), an `estimated_savings_dollar` (absolute dollar amount), and a human-readable `trade_off` string explaining what the customer gives up.

Together, these models form the API contract for the `/quotes/generate` endpoint's response.

**Convention violations:**

None. No docstrings are present (correct per convention). Type hints are used throughout. The file is 17 lines -- well under the 300-line limit.

**Potential issues / edge cases:**

1. **String-typed values lose type safety.** Both `original_value` and `proposed_value` are `str`. The generator stores floats as `"1000.0"` and booleans as `"True"/"False"`. Consumers must know how to parse these back. This is a deliberate trade-off to keep a single model for heterogeneous field types, but it means there is no schema-level validation that a proposed deductible is actually numeric.
2. **No validation constraints on savings fields.** `estimated_savings_pct` has no `ge=0, le=100` bounds. `estimated_savings_dollar` has no `ge=0` bound. Negative or impossibly large values would pass Pydantic validation.
3. **`quote_id` has no format constraint.** Any arbitrary string is accepted. The generator produces sequential IDs like `"Q1"`, `"Q2"`, but the model does not enforce this pattern.

---

### 1.2 `app/engine/quote_generator.py`

**What this code does:**

This is the core business logic. It takes a `RenewalPair` and a `DiffResult` and produces up to 3 `QuoteRecommendation` objects, each representing a different strategy for reducing the renewal premium.

**Protected fields:** A `frozenset` of 5 field names (`bodily_injury_limit`, `property_damage_limit`, `coverage_e_liability`, `uninsured_motorist`, `coverage_a_dwelling`) that must never appear in any adjustment. These are presumably legally mandated or critical coverage limits. The guard on line 144 skips any strategy whose adjustments touch a protected field.

**Auto insurance strategies (3):**

| Strategy | Function | Logic | Hardcoded savings rate |
|---|---|---|---|
| `raise_deductible` | `_auto_raise_deductible` | Proposes raising collision deductible to 1000 if < 1000, and comprehensive deductible to 500 if < 500. Can produce 1 or 2 adjustments. | 10% |
| `drop_optional` | `_auto_drop_optional` | Proposes dropping rental reimbursement and/or roadside assistance if currently enabled. | 4% |
| `reduce_medical` | `_auto_reduce_medical` | Proposes reducing medical payments to 2000 if currently above 2000. | 2.5% |

**Home insurance strategies (3):**

| Strategy | Function | Logic | Hardcoded savings rate |
|---|---|---|---|
| `raise_deductible` | `_home_raise_deductible` | Proposes raising deductible to 2500 if < 2500. | 12.5% |
| `drop_water_backup` | `_home_drop_water_backup` | Proposes dropping water backup coverage if enabled. | 3% |
| `reduce_personal_property` | `_home_reduce_personal_property` | Proposes reducing coverage_c_personal_property to 50% of coverage_a_dwelling if currently above that ratio. | 4% |

**`generate_quotes(pair, diff)` main function:**

1. Returns `[]` immediately if `diff.flags` is empty (no noteworthy changes detected).
2. Selects the strategy list based on `renewal.policy_type` (AUTO or HOME) and whether the corresponding coverages object exists. Returns `[]` if neither matches.
3. Iterates through strategies in definition order. For each: calls the strategy function, skips if it returns `None`, skips if any adjustment touches a protected field, otherwise computes `savings_dollar = round(renewal.premium * savings_rate, 2)` and appends a `QuoteRecommendation`.
4. `quote_id` is assigned as `"Q{len(quotes) + 1}"` -- sequential starting from Q1.
5. Returns at most 3 quotes (`quotes[:3]`).

**Convention violations:**

- **Imprecise type hint on lines 101 and 107:** The strategy lists are typed as `list[tuple[str, float, callable]]`. Lowercase `callable` is a builtin function, not a proper type annotation. Convention says "Use type hints -- let the type system document intent." A more precise type would be `Callable[[AutoCoverages], list[CoverageAdjustment] | None]` (or the Home equivalent). The current annotation does not communicate the expected signature at all.

**Potential issues / edge cases:**

1. **Savings rates are hardcoded constants.** The 10%, 4%, 2.5% (auto) and 12.5%, 3%, 4% (home) rates are fixed. They do not vary by state, carrier, or policy specifics. The field names say "estimated" which acknowledges this, but the estimates are static.
2. **`pair.prior` is never read.** The function accepts the full `RenewalPair` but only ever accesses `pair.renewal`. The prior-period snapshot is ignored entirely. This means the generator does not use how much the premium increased, what changed between periods, or any prior coverage values to inform its recommendations.
3. **`diff` is used only as a gate, not as input.** The `DiffResult` is checked for non-empty `flags` and then discarded. The specific flags (e.g., `PREMIUM_INCREASE_CRITICAL` vs `DEDUCTIBLE_INCREASE`) do not influence which strategies run or their parameters. Every strategy runs regardless of which flags are present.
4. **Premium edge cases:** If `renewal.premium` is 0, savings dollars will be 0 while savings percentage is positive -- a confusing but not crashing result. If premium is negative (no model-level guard), savings dollars will be negative.
5. **Strategy interaction not modeled.** Each quote is independent. If a user applied multiple recommendations, the combined savings would not equal the sum of individual percentages, but nothing in the model or API communicates this.
6. **`_TRADE_OFF_MESSAGES.get(name, "")` fails silently.** If a new strategy name is added to the strategy list but not to `_TRADE_OFF_MESSAGES`, the trade-off will be an empty string with no error. A `KeyError` (via `[]` access) or an assertion would be safer for catching developer mistakes.
7. **`quotes[:3]` cap is invisible to callers.** There is no indication in the API response that recommendations were truncated. Currently both Auto and Home have exactly 3 strategies, so the cap never activates, but it would silently drop strategies if more are added.
8. **Boundary condition on deductible comparisons:** `_auto_raise_deductible` uses `<` (strict less than), so `collision_deductible == 1000` does NOT trigger. `_home_raise_deductible` uses `>=` to bail out, so `deductible == 2500` also does NOT trigger. `_auto_reduce_medical` uses `<=` to bail out, so `medical_payments == 2000` does NOT trigger. These boundaries are consistent and correct, but they are not documented.
9. **`_home_reduce_personal_property` target is a float computation.** `target = cov.coverage_a_dwelling * 0.5` may introduce floating-point imprecision for certain dwelling values. The result is converted to string via `str(target)`, which could produce values like `"150000.00000000003"`.
10. **No logging or observability.** No strategy application is logged. In production, diagnosing why a particular policy did or did not receive a recommendation would require re-running the logic.

---

### 1.3 `app/routes/quotes.py`

**What this code does:**

Defines a FastAPI `APIRouter` with prefix `/quotes` and a single endpoint:

- **POST `/quotes/generate`**: Accepts a `RenewalPair` in the request body. Internally: (1) computes the diff between prior and renewal via `compute_diff`, (2) applies flag rules via `flag_diff`, (3) short-circuits with `[]` if no flags exist, (4) calls `generate_quotes` and returns the result as `list[QuoteRecommendation]`.

The route is self-contained: it performs the full diff + flag + quote pipeline from scratch, without depending on any prior `/reviews/compare` call.

**Convention violations:**

None. No docstrings. Type hints present. File is 18 lines.

**Potential issues / edge cases:**

1. **Redundant diff computation.** The same `compute_diff` + `flag_diff` pipeline also runs in `/reviews/compare`. If a client calls both endpoints with the same input, the diff is computed twice. This is not a performance issue (the computation is lightweight), but it creates a subtle consistency risk: if `compute_diff` or `flag_diff` behavior changes, the two endpoints could diverge.
2. **Duplicate `diff.flags` guard.** The route checks `if not diff.flags: return []` on line 16-17, and `generate_quotes` internally performs the same check on line 123. The route-level check is an optimization (avoids a function call), but the logic would be correct without it. This is minor redundancy, not a bug.
3. **No authentication or authorization.** Anyone who can reach the endpoint can generate quotes for any policy. Convention says "Validate all external input at system boundaries" -- Pydantic handles structural validation, but there is no business-level access control.
4. **No rate limiting.** The endpoint could be called at high volume. Given that the computation is purely in-memory and stateless, this is low risk, but worth noting for production readiness.

---

### 1.4 `app/main.py` (quotes router registration only)

**What this code does:**

The `quotes_router` is imported from `app.routes.quotes` on line 6 and registered with `app.include_router(quotes_router)` on line 20. This exposes the `/quotes/generate` endpoint on the FastAPI app instance.

The router is the 5th of 6 routers registered (after ui, reviews, batch, eval; before analytics). Each router has a unique prefix, so there are no URL collisions.

**Convention violations:**

None. The file is 27 lines. Import style and structure are consistent with the rest of the file.

**Potential issues / edge cases:**

- Router registration order does not matter for FastAPI in this case since all prefixes are unique. No issues here.
- The import is clean and follows the established pattern of other routers.

---

### 1.5 `tests/test_quote_generator.py`

**What this code does:**

Contains 8 tests and 2 helper functions, covering the quote generation pipeline from unit-level strategy testing to integration-level route testing.

**Helpers:**

- `_make_pair(policy_type, premium, auto_cov, home_cov, renewal_premium)`: Constructs a `RenewalPair` with synthetic data. Both prior and renewal get the same coverages object. Renewal premium defaults to `premium * 1.15` (15% increase), which reliably triggers the `PREMIUM_INCREASE_HIGH` flag and ensures `diff.flags` is non-empty.
- `_get_flagged_diff(pair)`: Convenience wrapper that runs `compute_diff` then `flag_diff`.

**Individual tests:**

| Test | What it verifies |
|---|---|
| `test_auto_all_strategies_applicable` | Auto policy with all 3 strategies triggering. Asserts 3 quotes with savings percentages 10.0, 4.0, 2.5 in order. |
| `test_home_all_strategies_applicable` | Home policy with all 3 strategies triggering. Asserts 3 quotes with savings percentages 12.5, 3.0, 4.0 in order. |
| `test_auto_already_optimized` | Auto policy where all coverages are already at or beyond threshold values. Asserts empty result. |
| `test_liability_fields_never_adjusted` | Asserts no quote's adjustments reference any field in `PROTECTED_FIELDS`. This is a property-style assertion over all generated quotes. |
| `test_no_flags_returns_empty` | Prior and renewal have identical premiums (no flag triggers). Asserts `diff.flags == []` and quotes are empty. Tests the flag-gate behavior. |
| `test_existing_tests_regression` | Posts to `/reviews/compare` with sample data. Asserts 200 status. Ensures the new quote feature does not break the existing review endpoint. |
| `test_route_auto_quote` | Posts auto sample data to `/quotes/generate`. Asserts 200 and response is a list. |
| `test_route_home_quote` | Posts home sample data to `/quotes/generate`. Asserts 200 and response is a list. |

**Convention violations:**

None. File follows `test_*.py` naming. Tests focus on business logic. No trivial getter/setter tests.

**Potential issues / edge cases:**

1. **`estimated_savings_dollar` is never asserted.** All strategy tests verify only `estimated_savings_pct`. For example, with premium=2000 and rate=0.10, savings_dollar should be 200.0, but no test checks this. A bug in the dollar calculation (e.g., using `prior.premium` instead of `renewal.premium`) would go undetected.
2. **`trade_off` text is never asserted.** No test verifies that trade-off messages are correct or even non-empty.
3. **Adjustment content is never inspected.** Tests verify the number of quotes and their savings percentages, but not what fields are actually proposed to change or what values are proposed. A bug that swaps `collision_deductible` and `comprehensive_deductible` proposed values would pass all current tests.
4. **No partial-application tests for Home.** There are tests for "all strategies apply" and "all strategies already optimized" (auto only), but no test where only 1 or 2 home strategies trigger. For example: deductible already at 2500 but water_backup is True.
5. **No partial-application tests for Auto.** Similarly, there is no auto test where exactly 1 or 2 (but not all 3) strategies fire.
6. **Boundary values are tested only implicitly.** `test_auto_already_optimized` uses `collision_deductible=1000`, `comprehensive_deductible=500`, `medical_payments=2000` -- which are exactly at the boundary. This confirms the boundary behavior but bundles all boundaries into one test, making it harder to diagnose a failure if one boundary condition regresses.
7. **Route tests are shallow.** `test_route_auto_quote` and `test_route_home_quote` only check `status_code == 200` and `isinstance(data, list)`. They do not verify the list length, the structure of individual items, or any field values. A regression that returns an empty list instead of 3 quotes would pass.
8. **Prior and renewal share the same coverages object in `_make_pair`.** Since Pydantic models are effectively immutable (frozen or copied on validation), this is not a mutation bug, but it means no test exercises the scenario where prior and renewal have different coverage values. The generator ignores `pair.prior`, so this is technically fine, but it also means the tests would not catch a future change that starts reading `pair.prior` incorrectly.
9. **`test_no_flags_returns_empty` depends on `AutoCoverages()` defaults.** The default `AutoCoverages()` has `collision_deductible=500`, `comprehensive_deductible=250`, etc., which ARE eligible for optimization. The test passes because the flag gate blocks quote generation, not because no strategies apply. The test name does not make this distinction clear, though the assertion `assert diff.flags == []` does.
10. **No negative/error-path tests.** There is no test for invalid input (e.g., missing required fields, wrong policy type), malformed JSON, or premium=0/negative values.

---

## 2. Module Behavior Summary

### What this module does

The Quote Generator automatically produces up to 3 cost-saving recommendations for an insurance renewal policy. It analyzes the renewal's coverage details and identifies where the customer could reduce their premium by raising deductibles, dropping optional coverages, or reducing non-essential coverage limits.

### Data flow

```
Client -> POST /quotes/generate (RenewalPair)
  -> compute_diff(pair) -> DiffResult
  -> flag_diff(diff, pair) -> DiffResult with flags
  -> [gate: if no flags, return []]
  -> generate_quotes(pair, diff) -> list[QuoteRecommendation]
  -> Response: JSON array of up to 3 recommendations
```

### Key design decisions

1. **Strategy pattern via tuple lists.** Each policy type (Auto/Home) has a list of `(name, savings_rate, function)` tuples. This makes adding new strategies easy: add a function and append a tuple.
2. **Protected fields as a safety net.** A `frozenset` of 5 critical fields prevents any strategy from touching legally or contractually important coverage limits. The check is centralized in `generate_quotes`, not in individual strategies.
3. **Flag gate.** Quote generation is gated on `diff.flags` being non-empty. This couples quote generation to the diff/flag pipeline, meaning quotes are only offered when something noteworthy changed in the renewal.
4. **Stateless computation.** No database, no caching, no side effects. The entire pipeline is a pure function from `RenewalPair` to `list[QuoteRecommendation]`.
5. **Fixed savings rates.** Each strategy has a single hardcoded savings rate regardless of policy details. The output explicitly labels these as "estimated."

### Architecture

Three-layer structure following the project's existing pattern:

- **Models** (`app/models/quote.py`): Data contracts (`CoverageAdjustment`, `QuoteRecommendation`)
- **Engine** (`app/engine/quote_generator.py`): Business logic (strategy functions + orchestrator)
- **Routes** (`app/routes/quotes.py`): HTTP interface (single POST endpoint)
- **Registration** (`app/main.py`): Router wired into the FastAPI app

Dependencies on existing modules: `engine/differ.py`, `engine/rules.py`, `models/policy.py`, `models/diff.py`.

---

## 3. Key Observations for Cross-Comparison

The following table enumerates specific behavioral facts that can be compared against requirements or another reviewer's observations.

| # | Observed Behavior | Notes |
|---|---|---|
| 1 | Auto strategies: raise_deductible (10%), drop_optional (4%), reduce_medical (2.5%) | Fixed rates, definition order |
| 2 | Home strategies: raise_deductible (12.5%), drop_water_backup (3%), reduce_personal_property (4%) | Fixed rates, definition order |
| 3 | Maximum 3 quotes returned | `quotes[:3]` hardcoded |
| 4 | Protected fields: bodily_injury_limit, property_damage_limit, coverage_e_liability, uninsured_motorist, coverage_a_dwelling | frozenset, never adjustable |
| 5 | Empty `diff.flags` -> empty quotes | Gate in both route and engine |
| 6 | `pair.prior` is never accessed | Only `pair.renewal` is used |
| 7 | `diff` content (specific flags, changes) is not used | Only `diff.flags` emptiness matters |
| 8 | Savings dollar = `renewal.premium * savings_rate` | Based on renewal premium, not prior or delta |
| 9 | `quote_id` format: "Q1", "Q2", "Q3" | Sequential, not unique/persistent |
| 10 | Auto collision deductible threshold: 1000 (strict `<`) | At 1000, strategy does NOT trigger |
| 11 | Auto comprehensive deductible threshold: 500 (strict `<`) | At 500, strategy does NOT trigger |
| 12 | Auto medical payments threshold: 2000 (`<=` to bail) | At 2000, strategy does NOT trigger |
| 13 | Home deductible threshold: 2500 (`>=` to bail) | At 2500, strategy does NOT trigger |
| 14 | Home personal property target: `coverage_a_dwelling * 0.5` | Ratio-based reduction |
| 15 | Strategies run in definition order, not sorted by savings | Order happens to be savings-descending for Auto; not for Home (12.5, 3, 4) |
| 16 | Each quote is independent; no combined/bundled recommendations | No interaction modeling |
| 17 | Single POST endpoint at `/quotes/generate` | No GET, no persistence, no listing |
| 18 | Diff is recomputed inside the route | Not reused from a prior `/reviews/compare` call |
| 19 | Unsupported policy type returns `[]`, not an error | Silent no-op |
| 20 | `proposed_value` for floats uses `str()` conversion | May produce values like `"150000.00000000003"` for some inputs |
| 21 | Tests verify savings percentages but not dollar amounts, trade-off text, or adjustment field values | Gaps in assertion coverage |
