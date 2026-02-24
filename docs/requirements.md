# Renewal Review — Product Requirements

## 1. Problem Statement

Insurance agencies manually compare thousands of policies every renewal season.
The task involves identifying risks such as coverage reductions and premium spikes between Prior (current) and Renewal policies.
The current process has the following problems:

- **Time**: Processing ~8,000 policies one by one manually — takes days
- **Accuracy**: Risk of omissions during manual comparison
- **Text risk blind spot**: Quantitative comparison cannot catch risks hidden in unstructured text such as memos and endorsement descriptions
- **No trend tracking**: Only the last result remains after each batch run, making it impossible to track risk trends over time
- **Cross-risk blind spot**: Single-policy reviews cannot detect overlapping coverage, bundle discount opportunities, or coverage gaps across multiple policies for the same customer

## 2. Proposed Solution

Provide a web tool that automatically compares Prior/Renewal policy pairs, detects changes, and classifies risks.
Value is delivered quickly through a 5-phase incremental expansion:

| Phase | Name | Core Value |
|-------|------|------------|
| 1 | **Basic Analytics** | Rule-based auto comparison + risk classification — days to minutes |
| 2 | **LLM Analytics** | Add LLM analysis — eliminate text-based risk blind spots |
| 3 | **Broker Workflow** | Broker contact/quote tracking + alternative quote recommendations — support real-world workflows |
| 4 | **Portfolio Aggregator** | Account-level cross-risk analysis — discover bundle discounts and coverage gaps |
| 5 | **Batch Monitoring** | Batch history retention + trend analysis — monitor risks over time |

## 3. User Stories

### Underwriter / Reviewer

- Can input a policy pair and immediately see changes and risk level
- Can run thousands of policies in a batch and prioritize review starting from the highest risk
- Can select specific policies for review (selective batch in addition to full batch)
- LLM detects risk signals hidden in memos and endorsement descriptions so nothing is missed
- Can compare with previous batches to see if risk trends are worsening
- LLM recommends alternative quotes with coverage adjustment strategies for high-risk policies

### Broker / Agent

- Can record whether a broker has been contacted for each policy after review
- Can track whether a quote has been generated to manage follow-up status
- Can monitor batch progress in real time via a progress bar

### Agency Manager

- Can view the overall risk distribution at a glance on the Dashboard
- Can monitor team work status through Broker Workflow metrics (contact rate, quote rate)
- Can group multiple policies for the same customer to check cross-risks (coverage gaps, bundle opportunities)
- Can monitor batch history and trends on the Batch Monitoring page
- Can preview how risk assessments change when transitioning from Basic Analytics to LLM Analytics

## 4. Requirements

### 4.1 Functional — Basic Analytics (Rule-based Comparison)

- Compares all fields of a policy pair to derive changes
- Assigns risk flags to changes (premium changes, coverage changes, vehicle/driver changes, endorsement changes, etc.)
- Classifies into 4 risk levels (Critical / High / Medium / Low) based on flag combinations
- Supports single comparison, selective batch, and full batch (all or sample)
- Dashboard displays batch result summary, risk distribution, and individual review details
- Dashboard displays an Account (insured_name) column with sorting capability
- Displays a progress bar with completion percentage and estimated remaining time during batch execution
- Persists review results and batch history in DB (SQLAlchemy + SQLite/PostgreSQL)

### 4.2 Functional — LLM Analytics (Rule + LLM)

- Selectively invokes LLM only for cases that require analysis
- Extracts risk signals from memos, determines the nature of endorsement changes, and assesses coverage equivalence
- Can upgrade risk level based on LLM results (downgrade not allowed)
- Falls back to rule-based results only on LLM failure (no batch interruption)
- Provides accuracy evaluation (Eval) based on a golden set
- Provides Basic to LLM Analytics Migration comparison (identify risk-changed cases, persist in DB)
- Automatically generates LLM-based AI Summary for flagged policies (lazy enrichment)

### 4.3 Functional — Broker Workflow (Broker Workflow Support)

- Can toggle broker contact status (contacted) for each policy
- Can toggle quote generation status (quote_generated) for each policy
- Displays Broker Workflow metrics on the Dashboard (Pending, contact rate, quote rate, etc.)
- Generates LLM-based alternative quotes (Quote Recommendation) for high-risk policies
  - Up to 3 cost-saving quotes per coverage adjustment strategy
  - trade_off: specific scenario/amount descriptions, broker_tip: actionable conversation guide

### 4.4 Functional — Portfolio Risk Aggregator (Cross-risk Analysis)

- Groups policies by account (account_id) and displays the list
- Aggregates type (Auto / Home / Bundle), total premium, and highest risk per account
- Provides cross-risk analysis for multi-policy (2+) accounts (coverage overlap, bundle discount, coverage gap)
- Supports Account sorting (ascending/descending) and pagination
- Displays analysis results in a modal (verdict, recommendations, action items)

### 4.5 Functional — Batch Monitoring (Batch History + Trend Analysis)

- Automatically saves history on batch completion (max 100 entries, oldest removed first)
- Provides trend analysis: total run count, average processing time, cumulative risk distribution, time-series trends
- Batch Monitoring page provides summary cards, risk distribution bar, and history table

### 4.6 Non-Functional

- Rule-based batch of 8,000 policies within 10 seconds
- Persistent DB storage for review results and batch history (SQLAlchemy, JSON/PostgreSQL selectable)
- Data source switching possible with configuration change only (JSON ↔ PostgreSQL)
- LLM provider selectable (OpenAI / Anthropic); Basic Analytics operates normally when disabled
- LLM tracing integration (Langfuse), can be disabled
- Adding each phase has no impact on existing features/tests
- Agent infrastructure (hooks, skills, settings) is included in the project so that the development environment is reproducible with just `git clone`
- agentic-dev-pipeline skill is managed in a separate GitHub repo for project-independent reuse
- GitHub Actions CI/CD: `tier:one-shot` issue → agent-dispatch workflow → automatic implementation + PR creation
- Code Review Bot: automatic review comments on PR creation/sync (conventions, bugs, security)
- 3-Tier Issue Templates: one-shot / manageable / complex classification (GitHub Issue Templates)
- Local Task Decomposition: generate requirements + task files via `scripts/decompose-task.sh`

## 5. Success Criteria

| Metric | Target |
|--------|--------|
| Processing time | Complete 8,000-policy batch within 10 seconds (from days to minutes) |
| Risk detection accuracy | Eval pass rate of 90%+ against golden set |
| Text risk coverage | 10%+ increase in High or above risk detections when switching to LLM Analytics vs. Basic |
| System stability | Basic Analytics functions at 100% even during LLM failures |
| Broker Workflow visibility | Contact rate/quote rate metrics viewable in real time on Dashboard |
| Cross-risk detection | Identify coverage gaps/overlaps in bundle accounts via Portfolio |

## 6. Scope

### In Scope

- Policy comparison for two types: Auto / Home
- Batch processing at ~8,000 policy scale
- Web-based Dashboard, Review Detail, LLM Insights, Portfolio, Batch Monitoring UI
- JSON file and PostgreSQL data sources
- SQLAlchemy-based persistent DB storage for review results and batch history
- Langfuse-based LLM tracing
- Broker Workflow (contact/quote tracking, alternative quote recommendations)
- Portfolio Risk Aggregator (account-level cross-risk analysis)

### Out of Scope

- Authentication/authorization, multi-user, real-time notifications
- External insurance system integrations
- Production deployment (CI/CD, container orchestration)
- Chart/graph visualizations (tables and numbers are sufficient)
- Batch Monitoring history deletion/editing/export

## 7. Go-to-Market

| Phase | Description | Deliverables |
|-------|-------------|--------------|
| Basic Analytics launch | Rule-based comparison + Dashboard | 8,000-policy batch processing, risk classification |
| LLM Analytics launch | LLM analysis integration + Migration comparison | Eval pass rate report, Basic/LLM comparison report |
| Broker Workflow launch | Contact/quote tracking + alternative quote recommendations | Dashboard Broker metrics, Quote Recommendations |
| Portfolio Aggregator launch | Account-level cross-risk analysis | Portfolio page, Bundle analysis |
| Batch Monitoring launch | History storage + trend analysis UI | Batch Monitoring page, trend monitoring |

Each phase incrementally expands while maintaining all functionality from previous phases.
