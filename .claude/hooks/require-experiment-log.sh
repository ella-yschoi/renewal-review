#!/bin/bash
# PreToolUse hook: block git commit unless experiment log AND presentation log are staged
# Acts as a gate — Claude must write both logs BEFORE committing.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only check git commit commands
if [[ "$COMMAND" != *"git commit"* ]]; then
  exit 0
fi

# Only enforce on experiment branches
BRANCH=$(git branch --show-current 2>/dev/null)
if [[ "$BRANCH" != experiment/* ]]; then
  exit 0
fi

STAGED=$(git diff --cached --name-only 2>/dev/null)
MISSING=""

# Check experiment log (docs/logs/experiments-log.md)
if ! echo "$STAGED" | grep -q 'logs/experiments-log.md'; then
  MISSING="docs/logs/experiments-log.md"
fi

# Check presentation log (docs/logs/presentation-log.md)
if ! echo "$STAGED" | grep -q 'logs/presentation-log.md'; then
  if [ -n "$MISSING" ]; then
    MISSING="${MISSING}, docs/logs/presentation-log.md"
  else
    MISSING="docs/logs/presentation-log.md"
  fi
fi

if [ -n "$MISSING" ]; then
  cat <<BLOCK
{"decision": "block", "reason": "Write the logs before committing.\n\nMissing: ${MISSING}\n\nExperiment log (docs/logs/experiments-log.md):\n## YYYY-MM-DD HH:MM | branch-name\n### What was done\n### Why it was done\n### How it was done\n\nPresentation log (docs/logs/presentation-log.md):\n> Context: / Result: / Insight:\n\nAfter writing, run git add and commit again."}
BLOCK
  exit 0
fi

exit 0
