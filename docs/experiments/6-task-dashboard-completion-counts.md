# Task: Dashboard Completion Counts

## Implementation Plan

### Files to Modify
- `app/templates/dashboard.html` - Add completion summary card

### Steps

1. **Add Completion Summary Card**
   - Location: After line 62 (after Broker Workflow card, before stats grid)
   - Add a new card with heading "Review Completion Summary"
   - Display "Contacted: X / Total (Y%)" using `broker.contacted` and `broker.total`
   - Display "Quoted: X / Total (Y%)" using `broker.quotes_generated` and `broker.total`
   - Calculate percentages safely: `(count / total * 100) if total else 0`
   - Use consistent styling with existing cards (card class, h2 heading, grid layout)

2. **Style Considerations**
   - Follow existing card styling patterns
   - Use grid layout for horizontal display of two metrics
   - Use existing color scheme (blue for contacted, purple for quotes)
   - Font sizes consistent with other stat displays

### No Backend Changes Required
- The `broker` object already contains all needed data
- No changes to `app/api/ui.py` or `app/domain/services/analytics.py`
- This is a template-only change

### Testing
- Run `make lint` to verify code style
- Run `make test` to ensure no regressions
- Manual verification: check dashboard displays counts correctly
