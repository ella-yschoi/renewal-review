# Feature: Portfolio Risk Aggregator

## Context

You are working on the renewal-review project — an insurance renewal review pipeline.
Read `convention.md` for coding rules before making any changes.
Read `docs/design-doc.md` for the current architecture.

The system currently analyzes policies individually. This feature adds cross-policy analysis
for clients with multiple policies (e.g., auto + home), detecting bundle risks, duplicate
coverages, and total exposure.

## Requirements

Read `docs/experiments/4-requirements-portfolio-aggregator.md` for full requirements.

Summary:
1. New models in `app/models/portfolio.py`: CrossPolicyFlag, BundleAnalysis, PortfolioSummary
2. New engine in `app/engine/portfolio_analyzer.py`: `analyze_portfolio(policy_numbers, results_store) -> PortfolioSummary`
3. New route in `app/routes/portfolio.py`: `POST /portfolio/analyze`
4. Register router in `app/main.py`
5. Tests in `tests/test_portfolio.py`: 8 test cases

Key business rules:
- Bundle detection: auto + home from same carrier = bundle eligible
- Unbundle risk: high if bundle with one policy action_required, medium if review_recommended
- Duplicate coverage: medical_payments (auto) + coverage_f_medical (home)
- Total liability: coverage_e_liability + bodily_injury_limit (first number x 1000)
- Premium concentration: any single policy > 70% of total = warning
- Portfolio increase: total premium change > 15% = critical

Edge cases:
- Minimum 2 policies required (422 if fewer)
- Deduplicate policy numbers
- Auto-only or home-only still works (not a bundle)
- All policy_numbers must exist in results_store (422 if missing)

## Existing Patterns to Follow

- Models: see `app/models/quote.py` and `app/models/review.py` for Pydantic pattern
- Engine: see `app/engine/quote_generator.py` for business logic pattern
- Routes: see `app/routes/quotes.py` for FastAPI route pattern
- Router registration: see `app/main.py` for `app.include_router` pattern
- Results store: import `get_results_store` from `app.routes.reviews` (dict[str, ReviewResult])
- Policy data: `ReviewResult.pair.renewal` and `ReviewResult.pair.prior` are `PolicySnapshot` with `AutoCoverages` or `HomeCoverages`

## Completion Criteria

- [ ] All 9 functional requirements (FR-1 through FR-9) implemented
- [ ] ruff check app/ tests/ passes with 0 errors
- [ ] uv run pytest -q passes ALL tests (existing + new, 0 failures)
- [ ] semgrep scan --config auto app/ passes
- [ ] convention.md compliance: no docstrings, type hints on all functions, files < 300 lines
- [ ] At least 8 test cases covering: bundle analysis, auto-only, duplicate medical, unbundle risk, premium concentration, high portfolio increase, 1-policy error, missing-policy error

## On Failure

- If ruff check fails: read the error output, fix the specific lint issues
- If pytest fails: read the failing test output, fix the code to pass
- If semgrep fails: read the security findings, fix the flagged code
- If triangular verification finds issues: read docs/experiments/discrepancy-report.md and fix each listed discrepancy

## Completion Signal

When ALL criteria above are met, output exactly:

<promise>LOOP_COMPLETE</promise>
