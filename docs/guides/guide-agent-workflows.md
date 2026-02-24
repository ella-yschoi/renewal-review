# Agent Workflows — Team Guide

This project uses three agent workflows: **Agentic Dev Pipeline**, **Issue Dispatch**, and **Code Review Bot**.

---

## End-to-End Flow

```
GitHub Issue (tier:one-shot label)
  │
  ▼ ① agent-dispatch.yml trigger
  Task Decomposition (claude-code-action)
  → requirements + task file generation
  │
  ▼ ② Agentic Dev Pipeline
  Implementation → Quality Gate → Triangular Verification → Fix Loop
  │
  ▼ ③ PR creation (closes #issue)
  │
  ▼ ④ code-review.yml auto-trigger
  Code Review Bot → comments
```

**Local entry point:**
```bash
# Run directly from local
bash scripts/decompose-task.sh --run "feature description"

# Dispatch via GitHub Issue (CI/CD trigger)
bash scripts/decompose-task.sh --dispatch "feature description"
```

---

## 3-Tier Task Taxonomy

| Tier | Label | Processing Method | Issue Template |
|------|-------|----------|----------------|
| One-Shot | `tier:one-shot` | AI autonomous processing (dispatch → pipeline → PR) | tier-one-shot.yml |
| Manageable | `tier:manageable` | Background agent + engineer supervision | tier-manageable.yml |
| Complex | `tier:complex` | Engineer-led, synchronous work | tier-complex.yml |

---

## Issue Dispatch (GitHub Actions)

When an issue with the `tier:one-shot` label is created, `.github/workflows/agent-dispatch.yml` is automatically triggered.

1. Read the issue content and generate requirements + task files
2. Run the Agentic Dev Pipeline (implementation → quality gate → triangular verification)
3. Create a PR (closes #issue)

**Required Secret**: `ANTHROPIC_API_KEY` (GitHub Settings → Secrets → Actions)

---

## Code Review Bot (GitHub Actions)

When a PR is opened, `.github/workflows/code-review.yml` is automatically triggered.

Review criteria:
- **Conventions**: conventions.md compliance (no docstrings, type hints, < 300 lines, StrEnum, hexagonal)
- **Bugs**: off-by-one, null handling, missing error handling
- **Security**: OWASP Top 10, hardcoded secrets, unvalidated input
- **Improvements**: simpler alternatives, missing test coverage

Read-only — only writes comments, does not modify code.

---

## Task Decomposition (Local Script)

```bash
# Generate requirements + task files only
bash scripts/decompose-task.sh "Add CSV export to analytics"

# Generate then automatically run the pipeline
bash scripts/decompose-task.sh --run "Add CSV export to analytics"

# Generate → commit → push → create GitHub Issue → CI/CD auto-trigger
bash scripts/decompose-task.sh --dispatch "Add CSV export to analytics"
```

Automatically generates `{N}-requirements-{slug}.md` and `{N}-task-{slug}.md` in `docs/experiments/`.

### Three Modes

| Mode | Command | Behavior |
|------|------|------|
| Generate only | `decompose-task.sh "desc"` | Generate requirements + task files |
| Local execution | `--run "desc"` | Generate → run agentic-dev-pipeline |
| Dispatch | `--dispatch "desc"` | Generate → git commit → push → GitHub Issue (`tier:one-shot`) → CI/CD auto-trigger |

`--dispatch` flow:
1. Generate requirements + task files
2. `git add` + `git commit` (plan files only)
3. `git push -u origin <current branch>`
4. `gh issue create --label "tier:one-shot"` — issue body includes requirements
5. `agent-dispatch.yml` workflow auto-triggers

**Required tool**: `--dispatch` requires `gh` CLI (GitHub CLI).

---

## Agentic Dev Pipeline (Skill)

This project uses the **agentic-dev-pipeline skill**.
The skill is managed in a GitHub repo and can be used with **any Python/Node/Rust/Go project**.

Installation:
```bash
git clone https://github.com/ella-yschoi/agentic-dev-pipeline.git ~/.agents/skills/agentic-dev-pipeline
```

Define feature requirements in a single task file, and the AI will iteratively run implementation → quality verification → intent verification → self-correction **without human intervention**.

---

## Skill Location

```
~/.agents/skills/agentic-dev-pipeline/
├── SKILL.md                  ← Skill definition (read by Claude Code)
├── detect-project.sh         ← Project auto-detection library
├── agentic-dev-pipeline.sh   ← Main loop script
├── triangular-verify.sh      ← Triangular verification script
└── PROMPT-TEMPLATE.md        ← General-purpose PROMPT template
```

## Auto-Detected Settings for This Project

`detect-project.sh` analyzes the file structure at the project root to automatically determine lint/test/security commands. Can be overridden with environment variables.

| Item | Detection Result |
|------|----------|
| Project Type | Python (`pyproject.toml`) |
| Lint | `make lint` (Makefile target) |
| Test | `make test` (Makefile target) |
| Security | `semgrep scan --config auto --quiet app/` |
| Source dirs | `app/` |
| Instruction files | `CLAUDE.md`, `.claude/rules/conventions.md` |
| Design docs | `docs/design-doc.md` |

---

## Prerequisites

### Tools

| Tool | Purpose | Installation Check |
|------|------|-----------|
| Claude Code | AI coding + Skill execution | `claude --version` |
| Lint tool | Code quality (auto-detected) | `ruff --version` / `eslint --version` etc. |
| Test tool | Testing (auto-detected) | `pytest --version` / `npm test` etc. |
| Security scanner | SAST (optional, auto-detected) | `semgrep --version` (skipped if not found) |

### Project Setup (This Project)

```bash
cd ~/Workspace/renewal-review
uv sync --extra dev          # Install dependencies
uv run pytest -q             # Verify existing tests pass
ruff check app/ tests/       # Verify lint is clean
```

### `.gitignore` Setup

Add to `.gitignore` to prevent loop artifacts from being accidentally committed:

```
.agentic-dev-pipeline/
```

---

## Pipeline Structure

```
PROMPT.md + requirements.md
    │
    ▼
┌─────────────────────────────────────────┐
│  Loop (max N iterations)                │
│                                         │
│  Phase 1: Implementation                │
│    Agent A: Write code (or fix)         │
│    - First iteration: Full impl from    │
│      PROMPT.md                          │
│    - Subsequent iterations: Fix based   │
│      on feedback only                   │
│                                         │
│  Phase 2: Quality Gate (auto-detected)  │
│    lint → test → security (sequential)  │
│    ❌ Failure → error output as         │
│       feedback → return to Phase 1      │
│                                         │
│  Phase 3: Triangular Verification       │
│    Agent B: blind review (reads code    │
│    only)                                │
│    Agent C: requirements vs B compare   │
│    ❌ Mismatch → report as feedback     │
│       → return to Phase 1              │
│                                         │
│  Phase 4: Complete                      │
│    All gates passed → LOOP_COMPLETE     │
└─────────────────────────────────────────┘
```

**Core Principles:**
- Failure = data — failure output becomes input for the next iteration
- Safety net — `MAX_ITERATIONS` prevents infinite loops (default: 5)
- Incremental convergence — most tasks complete within 1-2 iterations

---

## Environment Variable Reference

| Variable | Default | Description |
|----------|---------|------|
| `PROMPT_FILE` | **(required)** | Path to PROMPT.md |
| `REQUIREMENTS_FILE` | **(required)** | Path to requirements document |
| `OUTPUT_DIR` | `.agentic-dev-pipeline/` | Artifact output directory |
| `LINT_CMD` | (auto-detect) | Lint command (set to `"true"` to skip) |
| `TEST_CMD` | (auto-detect) | Test command (set to `"true"` to skip) |
| `SECURITY_CMD` | (auto-detect) | Security scan command (set to `""` to skip) |
| `SRC_DIRS` | (auto-detect) | Source directories |
| `BASE_BRANCH` | `main` | Base branch for git diff |
| `MAX_ITERATIONS` | `5` | Maximum number of iterations |

---

## Usage

### Step 1: Write Two Files

**Requirements file** — Functional requirements that serve as the basis for triangular verification.

```markdown
# <Feature Name> — Requirements

## Functional Requirements

### FR-1: ...
### FR-2: ...

## Non-Functional Requirements
- Follow project conventions
- All existing tests pass
- Lint 0 errors
- Less than 300 lines per file
```

**Task file** — Implementation instructions delivered to the agent. Copy from `~/.agents/skills/agentic-dev-pipeline/PROMPT-TEMPLATE.md` to create.

### Step 2: Run

**Method A: Shell Script (directly from terminal)**

Run outside of a Claude Code session. Since the script makes nested `claude --print` calls, it must be run directly from the terminal.

```bash
cd ~/Workspace/renewal-review

PROMPT_FILE="docs/experiments/4-PROMPT-portfolio-aggregator.md" \
REQUIREMENTS_FILE="docs/experiments/4-requirements-portfolio-aggregator.md" \
bash ~/.agents/skills/agentic-dev-pipeline/agentic-dev-pipeline.sh 5
```

- First argument: max iterations (default: 5)
- `PROMPT_FILE`, `REQUIREMENTS_FILE` are required
- Logs: `.agentic-dev-pipeline/loop-execution.log`

Environment variable override example:

```bash
PROMPT_FILE="PROMPT.md" \
REQUIREMENTS_FILE="requirements.md" \
LINT_CMD="ruff check app/ tests/" \
TEST_CMD="uv run pytest -q" \
OUTPUT_DIR="docs/experiments" \
bash ~/.agents/skills/agentic-dev-pipeline/agentic-dev-pipeline.sh
```

**Method B: Skill Invocation (inside a Claude Code session)**

When invoking the skill inside a Claude Code session, the agent orchestrates the loop directly.

```
Use the agentic-dev-pipeline Skill to implement <feature name>.
PROMPT: docs/experiments/<number>-PROMPT-<feature name>.md
Requirements: docs/experiments/<number>-requirements-<feature name>.md
```

In this approach:
- Phase 1: Agent writes code directly
- Phase 2: Runs auto-detected lint/test/security commands directly
- Phase 3: Runs Agent B and Agent C as subagents via the Task tool
- Phase 4: Reports completion when all gates pass

### Step 3: Check Results

After loop completion, files generated in `$OUTPUT_DIR/` (default: `.agentic-dev-pipeline/`):

| File | Content |
|------|------|
| `loop-execution.log` | Full execution log (iteration count, time, result of each phase) |
| `feedback.txt` | Feedback from the last iteration (deleted on success, kept for debugging on failure) |
| `blind-review.md` | Agent B's blind code review |
| `discrepancy-report.md` | Agent C's requirements vs code comparison |

Things to check:
- Whether `LOOP_COMPLETE` was output
- Total number of iterations (1-2 is normal)
- Phase 2/3 failure count and causes
- Quality of newly generated code files

---

## What Is Triangular Verification

Typical quality tools (lint, test, security) check **syntax and structure**.
Triangular verification checks **intent** — "Does the code match the requirements?"

```
Requirements (original requirements)
        ↕ compare
Code → Agent B (reads code only, describes behavior) → Blind Review
        ↕ compare
Agent C (Requirements vs Blind Review) → Discrepancy Report
```

- **Agent B**: Reads the code without seeing requirements → unbiased behavior description
- **Agent C**: Compares requirements with B's analysis → finds discrepancies
- When all three perspectives (requirements, code, independent analysis) align → `TRIANGULAR_PASS`

Run triangular verification standalone:

```bash
REQUIREMENTS_FILE="docs/experiments/<number>-requirements-<feature name>.md" \
bash ~/.agents/skills/agentic-dev-pipeline/triangular-verify.sh
```

---

## Real-World Examples

### Experiment 3: Smart Quote Generator

```bash
PROMPT_FILE="docs/experiments/3-PROMPT-quote-generator.md" \
REQUIREMENTS_FILE="docs/experiments/3-requirements-quote-generator.md" \
bash ~/.agents/skills/agentic-dev-pipeline/agentic-dev-pipeline.sh 5
```

Result: 1 iteration, 641 seconds, 0 human interventions, 81/81 tests passed

### Experiment 4: Portfolio Risk Aggregator

```bash
PROMPT_FILE="docs/experiments/4-PROMPT-portfolio-aggregator.md" \
REQUIREMENTS_FILE="docs/experiments/4-requirements-portfolio-aggregator.md" \
bash ~/.agents/skills/agentic-dev-pipeline/agentic-dev-pipeline.sh 5
```

---

## Troubleshooting

### `claude` command not found

The shell script method requires `claude` CLI to be in PATH.

```bash
which claude    # Check path
claude --version
```

### Nested claude call blocked

Running the shell script inside a Claude Code session blocks nested calls due to the `CLAUDECODE` environment variable. The script already includes `unset CLAUDECODE`, but running directly from the terminal is recommended.

### Quality gate failure repeats in Phase 2

- Verify that existing tests pass before starting
- Confirm that the detected commands match expectations:
  ```bash
  source ~/.agents/skills/agentic-dev-pipeline/detect-project.sh && print_detected_config
  ```
- Specify explicitly with environment variable overrides: `LINT_CMD="..."`, `TEST_CMD="..."`

### TRIANGULAR_PASS not returned in Phase 3

- Read `$OUTPUT_DIR/discrepancy-report.md` directly to check which requirements are missing or mismatched
- If the requirements file is too vague, Agent C cannot make a judgment → write more specific requirements
- Feedback is passed to the next iteration, so the loop automatically attempts corrections

### Wrong tool detected

Override with environment variables: `LINT_CMD`, `TEST_CMD`, `SECURITY_CMD`

### Max iterations reached but incomplete

- Check the last feedback in `$OUTPUT_DIR/loop-execution.log`
- Re-run with a higher max iterations, or
- Manually fix the remaining issues and run triangular verification separately

---

## Detailed Documentation

For the skill's full documentation (supported languages, detection priority, troubleshooting, etc.), refer to:
- GitHub: https://github.com/ella-yschoi/agentic-dev-pipeline
- Local (after installation): `~/.agents/skills/agentic-dev-pipeline/SKILL.md`
