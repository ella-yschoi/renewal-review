# Feature: Smart Quote Generator

## Context

You are working on the renewal-review project — an insurance renewal review pipeline.
Read `convention.md` for coding rules before making any changes.

## Requirements

Read `docs/experiments/3-requirements-quote-generator.md` for full requirements.

Summary:
1. New models in `app/models/quote.py`: CoverageAdjustment, QuoteRecommendation
2. New engine in `app/engine/quote_generator.py`: `generate_quotes(pair, diff) -> list[QuoteRecommendation]`
3. New route in `app/routes/quotes.py`: `POST /quotes/generate`
4. Register router in `app/main.py`
5. Tests in `tests/test_quote_generator.py`: 6 test cases
6. Auto strategies: raise_deductible (10%), drop_optional (4%), reduce_medical (2.5%)
7. Home strategies: raise_deductible (12.5%), drop_water_backup (3%), reduce_personal_property (4%)
8. Hard constraints: NEVER adjust liability fields (bodily_injury_limit, property_damage_limit, coverage_e_liability, uninsured_motorist, coverage_a_dwelling)
9. Skip strategies where adjustment is already in place

## Completion Criteria

- [ ] All 9 functional requirements (FR-1 through FR-9) implemented
- [ ] ruff check app/ tests/ passes with 0 errors
- [ ] uv run pytest -q passes ALL tests (existing + new)
- [ ] semgrep scan --config auto app/ passes
- [ ] convention.md compliance: no docstrings, type hints on all functions, files < 300 lines
- [ ] All quotes preserve liability fields (hard constraint verified in tests)

## On Failure

- If ruff check fails: read the error output, fix the specific lint issues
- If pytest fails: read the failing test output, fix the code to pass
- If semgrep fails: read the security findings, fix the flagged code
- If triangular verification finds issues: read docs/experiments/discrepancy-report.md and fix each listed discrepancy

## Completion Signal

When ALL criteria above are met, output exactly:

<promise>LOOP_COMPLETE</promise>
