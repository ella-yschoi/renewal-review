#!/bin/bash
# PreToolUse hook: block git commit if app/ code changed but design-doc.md not staged
# Ensures design doc stays in sync with implementation.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only check git commit commands
if [[ "$COMMAND" != *"git commit"* ]]; then
  exit 0
fi

# Check if any app/ or tests/ files are staged
CODE_STAGED=$(git diff --cached --name-only 2>/dev/null | grep -E '^(Workspace/renewal-review/app/|Workspace/renewal-review/tests/)' | head -1)
if [ -z "$CODE_STAGED" ]; then
  exit 0
fi

# Code is staged — check if design-doc.md is also staged
DOC_STAGED=$(git diff --cached --name-only 2>/dev/null | grep 'design-doc.md')
if [ -z "$DOC_STAGED" ]; then
  cat <<'BLOCK'
{"decision": "block", "reason": "app/ or tests/ code was changed but docs/design-doc.md is not staged.\n\nUpdate the relevant section:\n- 1. Architecture — when adding new modules/layers\n- 2. Data Model — when changing models\n- 3. Processing Pipeline — when changing processing flow\n- 4. API Surface — when adding/changing endpoints\n- 5. UI — when changing pages/templates\n- 6. Error Handling — when adding error handling\n- 7. Testing Strategy — when adding tests\n- 8. Tech Stack — when changing dependencies\n\nAfter updating, run git add docs/design-doc.md and commit again."}
BLOCK
  exit 0
fi

# design.md staged — clear the reminder flag for next batch
rm -f /tmp/claude-design-doc-reminded
exit 0
