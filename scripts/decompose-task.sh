#!/bin/bash
# decompose-task.sh — Generate requirements + task files, optionally run agentic dev pipeline
#
# Usage:
#   bash scripts/decompose-task.sh "Add CSV export to analytics"
#   bash scripts/decompose-task.sh --run "Add CSV export to analytics"
#
# The --run flag executes the agentic dev pipeline after generating files.

set -euo pipefail

# --- Parse arguments ---
RUN_PIPELINE=false
DESCRIPTION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run)
      RUN_PIPELINE=true
      shift
      ;;
    *)
      DESCRIPTION="$1"
      shift
      ;;
  esac
done

if [ -z "$DESCRIPTION" ]; then
  echo "Usage: bash scripts/decompose-task.sh [--run] \"feature description\""
  echo ""
  echo "Options:"
  echo "  --run    After generating files, execute the agentic dev pipeline"
  echo ""
  echo "Examples:"
  echo "  bash scripts/decompose-task.sh \"Add health check endpoint\""
  echo "  bash scripts/decompose-task.sh --run \"Add CSV export to analytics\""
  exit 1
fi

# --- Determine project root ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXPERIMENTS_DIR="$PROJECT_ROOT/docs/experiments"
PIPELINE_SCRIPT="$HOME/.agents/skills/agentic-dev-pipeline/agentic-dev-pipeline.sh"

# --- Determine next experiment number ---
mkdir -p "$EXPERIMENTS_DIR"
LAST_NUM=$(ls "$EXPERIMENTS_DIR"/ 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -1)
NEXT_NUM=$(( ${LAST_NUM:-0} + 1 ))

# --- Derive slug from description ---
SLUG=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')

REQUIREMENTS_FILE="$EXPERIMENTS_DIR/${NEXT_NUM}-requirements-${SLUG}.md"
TASK_FILE="$EXPERIMENTS_DIR/${NEXT_NUM}-task-${SLUG}.md"

# --- Pre-flight: check claude CLI ---
if ! command -v claude &>/dev/null; then
  echo "ERROR: 'claude' CLI not found in PATH. Install Claude Code first."
  exit 1
fi

# Claude Code nested call unblock
unset CLAUDECODE 2>/dev/null || true

echo "=== Task Decomposition ==="
echo "Description: $DESCRIPTION"
echo "Requirements: $REQUIREMENTS_FILE"
echo "Task file:    $TASK_FILE"
echo ""

# --- Generate requirements file ---
echo "[1/2] Generating requirements file..."
claude --print -p "
You are a requirements analyst for the renewal-review project (insurance renewal review pipeline).

Read CLAUDE.md and .claude/rules/conventions.md for project context.
Read docs/design-doc.md for the current architecture.

Look at existing requirements files in docs/experiments/ for format reference:
- docs/experiments/3-requirements-quote-generator.md
- docs/experiments/4-requirements-portfolio-aggregator.md

Generate a requirements document for this feature:
\"$DESCRIPTION\"

The requirements file must include:
1. Overview — what this feature does and why
2. Functional Requirements — FR-1, FR-2, etc. with specific, testable criteria
3. Data Models — if new Pydantic models are needed
4. API Endpoints — if new routes are needed
5. Acceptance Criteria — checkbox list of verifiable conditions

Write the output as a standalone markdown file. Do NOT include code fences around the entire document.
Output ONLY the markdown content, nothing else.
" > "$REQUIREMENTS_FILE"

echo "  Created: $REQUIREMENTS_FILE"

# --- Generate task file ---
echo "[2/2] Generating task file..."
claude --print -p "
You are a task decomposer for the renewal-review project (insurance renewal review pipeline).

Read CLAUDE.md and .claude/rules/conventions.md for project context.
Read docs/design-doc.md for the current architecture.
Read the requirements file at: $REQUIREMENTS_FILE

Look at existing task files in docs/experiments/ for format reference:
- docs/experiments/3-PROMPT-quote-generator.md
- docs/experiments/4-PROMPT-portfolio-aggregator.md

Generate an implementation task file for this feature:
\"$DESCRIPTION\"

The task file must include:
1. Context — project description, files to read first
2. Requirements — reference the requirements file, provide a summary
3. Existing Patterns to Follow — point to similar existing files
4. Completion Criteria — checklist (lint, test, security, conventions)
5. On Failure — what to do when each gate fails
6. Completion Signal — <promise>LOOP_COMPLETE</promise>

Write the output as a standalone markdown file. Do NOT include code fences around the entire document.
Output ONLY the markdown content, nothing else.
" > "$TASK_FILE"

echo "  Created: $TASK_FILE"

echo ""
echo "=== Decomposition Complete ==="
echo "Requirements: $REQUIREMENTS_FILE"
echo "Task file:    $TASK_FILE"

# --- Optionally run the pipeline ---
if [ "$RUN_PIPELINE" = true ]; then
  echo ""
  echo "=== Running Agentic Dev Pipeline ==="

  if [ ! -f "$PIPELINE_SCRIPT" ]; then
    echo "ERROR: Pipeline script not found: $PIPELINE_SCRIPT"
    echo "Install the agentic-dev-pipeline skill first."
    exit 1
  fi

  cd "$PROJECT_ROOT"
  PROMPT_FILE="$TASK_FILE" \
  REQUIREMENTS_FILE="$REQUIREMENTS_FILE" \
  bash "$PIPELINE_SCRIPT" 5
fi
