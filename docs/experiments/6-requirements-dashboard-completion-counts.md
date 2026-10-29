# Requirements: Dashboard Review Completion Counts

## Objective

Add review completion summary to the dashboard showing contacted and quoted policy counts with totals and percentages.

## Acceptance Criteria

1. Dashboard displays "Contacted: X / Total (Y%)" count
2. Dashboard displays "Quoted: X / Total (Y%)" count
3. All existing tests pass (`make test`)
4. Linter passes (`make lint`)

## Technical Context

- Dashboard route: `app/api/ui.py` → `dashboard()` function (line 42)
- Broker metrics: `app/domain/services/analytics.py` → `compute_broker_metrics()` function (line 61)
- Template: `app/templates/dashboard.html`
- Broker metrics object already contains:
  - `broker.contacted`: count of contacted policies
  - `broker.quotes_generated`: count of quoted policies
  - `broker.total`: total policy count

## Design Decisions

1. **Location**: Add a new summary card below or near the existing "Broker Workflow" card
2. **Data source**: Use existing `broker` object passed to template (no backend changes needed)
3. **Display format**: "Contacted: X / Total (Y%)" and "Quoted: X / Total (Y%)"
4. **Styling**: Follow existing dashboard card styling patterns

## Non-Goals

- No backend changes required (data already available)
- No new API endpoints
- No database schema changes
- No changes to analytics logic
