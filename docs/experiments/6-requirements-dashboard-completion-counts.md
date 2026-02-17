# Requirements: Dashboard Completion Counts

## Goal
Add review completion count to the dashboard summary section. Display the number of policies that have been contacted and quoted alongside existing metrics.

## Context
- Dashboard route: `app/api/ui.py` → `dashboard()`
- Broker metrics: `app/domain/services/analytics.py` → `compute_broker_metrics()`
- Template: `app/templates/dashboard.html`
- The broker metrics object already contains `contacted` and `quotes_generated` counts
- The dashboard already displays a "Broker Workflow" card with these metrics

## Acceptance Criteria
1. Dashboard summary shows "Contacted: X / Total" count
2. Dashboard summary shows "Quoted: X / Total" count
3. All existing tests pass (`make test`)
4. Linter passes (`make lint`)

## Implementation Notes
- The `broker` object passed to the template already contains:
  - `broker.contacted` - number of policies contacted
  - `broker.quotes_generated` - number of policies with quotes
  - `broker.total` - total number of policies
- Add a new card/section to display completion summary with percentages
- Use safe division to handle edge case where `broker.total` is 0
- Follow existing styling patterns in dashboard.html
