# Demo Script

---

# renewal-review

## Part 1: GitHub — Agent-Native CI/CD

### Issue → PR → Review → Merge

(Open Issue #3)

This issue has the `tier:one-shot` label. When that label is applied, the agent-dispatch workflow triggers automatically — no human kicks it off.

(Open PR #1)

The agent decomposed the issue, implemented the code, and created this PR. Then the code-review bot automatically ran and left review comments.

(Scroll to review comments)

These are the automated review comments — the bot checks conventions, potential bugs, and security issues. This is the same triangular verification concept from the presentation, running inside CI.

(Show PR merged status)

The PR was reviewed and merged into main. End to end — issue to merged PR — with zero manual intervention.

(If demo is stuck / not completing)

It looks like the Claude API credit ran out during the run — that's why it's still loading. I tested this before the demo and the full pipeline did complete end to end: issue creation through to PR creation and merge. The workflow itself is fully functional — it's just a credit issue right now.

---

# renewal-review

## Part 2: Renewal-Review Repo Walkthrough

I'll now show you the repo for the product I built.

(Open repo root)

This is the renewal-review repo — the insurance renewal review pipeline.

(Open `.claude/rules/`)

These are the rules the agent follows every session — code conventions, hexagonal architecture constraints, file size limits.

(Open `.claude/hooks/`)

Here are the Claude Code Hooks I mentioned. These enforce discipline automatically:
- `require-experiment-log` — blocks commits on experiment branches without a log entry.
- `require-design-doc` — blocks commits that change app code without updating the design doc.
- `remind-design-doc` — reminds the agent to update design doc when editing code files.

(Open `.claude/skills/`)

And the Custom Skills:
- `insurance-domain` — ACORD standard mappings, coverage types, protected fields, gap analysis. This is what eliminated domain research time.
- `agentic-dev-pipeline` — the automated implement → quality gates → triangular verification loop, packaged for reuse.

# agentic-dev-pipeline

(Open https://github.com/ella-yschoi/agentic-dev-pipeline)

I actually published the agentic-dev-pipeline as an open-source package. It's project-agnostic — auto-detects lint, test, and security tools for Python, Node, Rust, and Go. You can install it as a Python dev dependency or a standalone CLI tool.

(Scroll README — show Pipeline Architecture diagram)

The core loop: Agent A implements code, quality gates run lint/test/security, then triangular verification with two independent agents — one reads only code, the other reads only requirements. If they don't match, feedback goes back to Agent A.

(Open `docs/onboarding-guide.md`)

There's an onboarding guide — a new engineer can go from install to first run in 5 minutes. `init` scaffolds the config, you fill in PROMPT.md and requirements.md, then `run`. It detects your project type and quality tools automatically.

Now let me show you the live product.

---

## Part 3: Live Product Demo

### Dashboard

(Open `http://localhost:8000`)

This is the main dashboard. 8,000 policies processed in under 1 second, 100% rule-based.

**Broker Workflow** — five stages from Not Reviewed through to Reviewed. Each shows count and progress so the broker knows exactly where they stand.

**Risk Distribution** — six cards and a stacked bar. The system surfaces only what needs attention. Most policies require no action.

**Filters** — five dropdowns: review status, risk level, contacted, quote, LLM. The table is sorted by severity — Urgent Review first.

(Click a policy row)

---

### Review Detail

This is everything a broker needs for one policy.

**Header** — policy number, risk badge, "Contacted" checkbox, and "Generate Quote" button. Both are tracked and persisted.

**Summary** — a one-paragraph summary. The sparkle icon means it was AI-generated.

**Prior vs Renewal** — side-by-side comparison: carrier, premium with percentage change, coverage limits, deductibles. Everything diff'd field by field.

**Flags** — these are the 22 rules catching what matters: premium spikes, coverage drops, liability changes.

(Click "Generate Quote")

**Quote Recommendations** — the LLM generates up to 3 alternatives. Each card shows savings, coverage adjustments with old-to-new values, trade-off explanation, and a broker tip.

(Refresh the page)

The quotes persist. No LLM re-call needed — they're saved to the database and rendered instantly on reload. The button now says "Regenerate Quote".

(Navigate back, go to LLM Insights page)

---

### LLM Insights

(Open LLM Insights page)

This page compares rule-based vs LLM analysis side by side.

It targets only Review Recommended policies — not all 8,000. In demo mode, we sample up to 100 to manage API costs.

(Click "Compare")

The progress bar shows both phases: rule-based first, then LLM.

**Results** — three cards: Policies Compared, Risk Level Changes, Policies with Insights.

The key insight: the LLM upgrades some policies from Review Recommended to Action Required or Urgent Review — because it found signals in notes and endorsements that rules cannot parse.

**Table** — purple rows mean the LLM changed the risk level. You can filter to "Risk changed only" or "With insights only" to focus on what the AI found.

(Click a policy to show detail with LLM insights)

---

### Portfolio

(Open Portfolio page)

This page groups policies by account — same customer's Auto and Home together.

**Table** — account name, policy count, type badge (Bundle / Auto / Home), total premium, highest risk.

(Click "Analyze" on a Bundle account)

**Modal** — the LLM runs a cross-policy analysis:
- Verdict banner with color-coded assessment.
- Bundle analysis: discount eligibility, carrier mismatch, unbundle risk.
- Cross-policy flags: duplicate coverage, coverage gaps, carrier inconsistencies.
- Prioritized action items: what the broker should do, ranked by severity.
