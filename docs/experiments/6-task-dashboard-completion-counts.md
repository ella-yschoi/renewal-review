# Task: Implement Dashboard Review Completion Counts

## Overview

Add a summary card to the dashboard showing contacted and quoted policy counts with percentages.

## Implementation Steps

### 1. Modify Template: `app/templates/dashboard.html`

**Location**: After the existing "Broker Workflow" card (after line 62) or within the stats grid.

**Add a new card section**:

```html
<div class="card" style="margin-bottom:16px;">
  <h2 style="margin-bottom:12px;">Review Completion Summary</h2>
  <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:12px;">
    <div style="text-align:center;">
      <div style="font-size:24px; font-weight:700; color:#3182ce;">{{ broker.contacted }} / {{ broker.total }}</div>
      <div style="font-size:11px; color:#718096; margin-top:2px;">Contacted</div>
      {% set contacted_pct = (broker.contacted / broker.total * 100) if broker.total else 0 %}
      <div style="font-size:12px; color:#4a5568; margin-top:4px;">{{ "%.1f"|format(contacted_pct) }}%</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:24px; font-weight:700; color:#805ad5;">{{ broker.quotes_generated }} / {{ broker.total }}</div>
      <div style="font-size:11px; color:#718096; margin-top:2px;">Quoted</div>
      {% set quoted_pct = (broker.quotes_generated / broker.total * 100) if broker.total else 0 %}
      <div style="font-size:12px; color:#4a5568; margin-top:4px;">{{ "%.1f"|format(quoted_pct) }}%</div>
    </div>
  </div>
</div>
```

**Key details**:
- Use existing `broker.contacted`, `broker.quotes_generated`, `broker.total` values
- Safe division: `if broker.total else 0` handles zero division
- Format percentages to 1 decimal place using Jinja2 `format` filter
- Colors match existing dashboard: blue (#3182ce) for contacted, purple (#805ad5) for quoted
- Grid layout with 2 columns for side-by-side display

### 2. No Backend Changes Required

The `broker` object already contains all needed data:
- `broker.contacted` (line 122 in ui.py)
- `broker.quotes_generated` (line 122 in ui.py)
- `broker.total` (line 122 in ui.py)

### 3. Quality Gates

Run both gates to ensure no regressions:
```bash
make lint
make test
```

### 4. Files to Modify

- `app/templates/dashboard.html` - Add completion summary card

### 5. Testing Approach

Manual verification:
1. Start the server
2. Navigate to dashboard
3. Verify the new card displays correctly
4. Verify counts match the "Broker Workflow" card values
5. Verify percentage calculations are correct

Automated:
- Existing tests should continue to pass
- No new test file needed (template-only change)

## Edge Cases

1. **Zero total**: Division by zero handled with `if broker.total else 0`
2. **Empty data**: Display shows "0 / 0 (0.0%)"
3. **Large numbers**: Display format accommodates any count size

## Rollback Plan

If issues arise:
1. Remove the new card section from dashboard.html
2. Commit and push revert
