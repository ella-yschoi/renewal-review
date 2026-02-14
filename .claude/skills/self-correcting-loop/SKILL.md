---
name: self-correcting-loop
description: "Use when implementing a feature with automated quality + intent verification loop. Combines Ralph-style iteration with triangular verification. Invoke when the user asks to implement a feature end-to-end with verification, or says 'self-correcting loop'."
---

# Self-Correcting Agent Loop

Implement a feature from a single PROMPT.md file through an automated loop: code → quality gates → triangular verification → self-correction, with zero human intervention.

## When to Use

- User asks to implement a feature with full automated verification
- User wants a "PROMPT.md → verified code" pipeline
- User mentions "self-correcting loop", "automated loop", or "Ralph Wiggum pattern"

## Prerequisites

Before starting, ensure:
1. A `PROMPT.md` (or equivalent) exists with: requirements summary, completion criteria, on-failure instructions, and a `<promise>LOOP_COMPLETE</promise>` completion signal
2. A `requirements.md` exists for triangular verification (Agent B/C need it)
3. Quality tools are available: `ruff`, `pytest`, `semgrep`
4. `convention.md` exists in the project root

## Pipeline Structure

```
PROMPT.md
    │
    ▼
┌─────────────────────────────────────────┐
│  Loop (max N iterations)                │
│                                         │
│  Phase 1: Implementation                │
│    Agent A: Write or fix code           │
│    - First iteration: full implementation│
│    - Later iterations: targeted fixes   │
│      using feedback from previous phase │
│                                         │
│  Phase 2: Quality Gates                 │
│    ruff check → pytest → semgrep        │
│    ❌ Fail → save output as feedback    │
│       → back to Phase 1                 │
│                                         │
│  Phase 3: Triangular Verification       │
│    Agent B: blind review (no reqs)      │
│    Agent C: discrepancy report          │
│    ❌ Issues found → save report as     │
│       feedback → back to Phase 1        │
│                                         │
│  Phase 4: Complete                      │
│    All gates passed → LOOP_COMPLETE     │
└─────────────────────────────────────────┘
```

## Execution Steps

### Step 1: Validate Inputs

Check that PROMPT.md, requirements.md, and convention.md exist. Verify ruff/pytest/semgrep are available.

### Step 2: Run the Loop

Use `scripts/self-correcting-loop.sh` if available, or orchestrate manually:

```bash
# Terminal execution (outside Claude Code session)
cd <project-root>
bash scripts/self-correcting-loop.sh 5
```

If orchestrating within a Claude Code session (manual mode):

1. **Phase 1** — Implement the feature per PROMPT.md. On subsequent iterations, read the feedback file and make targeted fixes only.

2. **Phase 2** — Run quality gates sequentially (fast-fail order):
   ```
   ruff check app/ tests/
   uv run pytest -q
   semgrep scan --config auto app/
   ```
   If any fails, capture the error output and loop back to Phase 1.

3. **Phase 3** — Triangular verification using two subagents:
   - **Agent B** (Task tool, general-purpose): Read code files + convention.md + design-doc.md. Do NOT read requirements. Describe what each file does, list violations and potential issues. Write to `docs/experiments/blind-review.md`.
   - **Agent C** (Task tool, general-purpose): Read requirements.md + blind-review.md. Do NOT read code. Compare and produce discrepancy report. Write to `docs/experiments/discrepancy-report.md`.
   - If `TRIANGULAR_PASS` is NOT in the discrepancy report, use the report as feedback and loop back to Phase 1.

4. **Phase 4** — All gates passed. Report LOOP_COMPLETE with iteration count and timing.

### Step 3: Record Results

After completion, record in experiment/presentation logs:
- Total iterations, time, phase failures
- Human interventions (target: 0)
- Triangular verification findings

## Key Design Principles

1. **Failure = Data**: Each iteration's failure output becomes the next iteration's input
2. **Safety first**: `max-iterations` prevents infinite loops (default: 5)
3. **Convergence**: Most work done in iteration 1, subsequent iterations fix edge cases
4. **Completion signal**: Exact `LOOP_COMPLETE` string exits the loop

## Shell Script Notes

When using the shell scripts (`scripts/self-correcting-loop.sh`, `scripts/triangular-verify.sh`):
- Scripts must `unset CLAUDECODE` to enable nested `claude` CLI calls
- Run from the project root directory
- `claude --print -p "..."` for non-interactive execution
- Feedback is passed via `/tmp/self-correcting-loop-feedback.txt`
- Logs are written to `docs/logs/loop-execution.log`

## PROMPT.md Template

```markdown
# Feature: [Feature Name]

## Context
[Project context, what to read before coding]

## Requirements
Read `docs/experiments/<requirements-file>.md` for full requirements.
[Brief summary of key requirements]

## Completion Criteria
- [ ] All functional requirements implemented
- [ ] ruff check passes (0 errors)
- [ ] pytest passes ALL tests (existing + new)
- [ ] semgrep passes
- [ ] convention.md compliance

## On Failure
- ruff/pytest/semgrep: read error output, fix specific issues
- triangular verification: read discrepancy-report.md, fix each issue

## Completion Signal
When ALL criteria met, output exactly:
<promise>LOOP_COMPLETE</promise>
```

## Experimental Evidence

- **Experiment 3 results**: 1 iteration, 641s, 0 human interventions, all gates passed
- **Manual baseline**: 549s, 1 human intervention (Agent B prompt error)
- **Verdict**: Automation value is reliability, not speed — zero human intervention at the cost of ~90s overhead
