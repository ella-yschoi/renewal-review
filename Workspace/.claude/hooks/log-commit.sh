#!/bin/bash
# PostToolUse hook: no-op placeholder
# Rich experiment logging is handled by Claude via CLAUDE.md convention,
# not by this hook. Kept registered for potential future use.
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
if [[ "$COMMAND" != *"git commit"* ]]; then
  exit 0
fi
exit 0
