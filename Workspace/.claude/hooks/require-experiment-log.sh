#!/bin/bash
# PreToolUse hook: block git commit unless experiment-log.md is staged
# Acts as a gate — Claude must write the log BEFORE committing.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only check git commit commands
if [[ "$COMMAND" != *"git commit"* ]]; then
  exit 0
fi

# Check if experiment-log.md is in the staging area
STAGED=$(git diff --cached --name-only 2>/dev/null | grep 'experiment-log.md')
if [ -z "$STAGED" ]; then
  cat <<'BLOCK'
{"decision": "block", "reason": "docs/experiment-log.md가 staging에 없습니다. 커밋 전에 작업 내역을 작성하세요.\n\n형식:\n## YYYY-MM-DD HH:MM | `브랜치명`\n### 무엇을 했는가\n### 왜 했는가\n### 어떻게 했는가\n\n작성 후 git add docs/experiment-log.md 하고 다시 커밋하세요."}
BLOCK
  exit 0
fi

exit 0
