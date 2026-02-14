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

# Check experiment log
if ! echo "$STAGED" | grep -q 'experiments/log.md'; then
  MISSING="docs/experiments/log.md"
fi

# Check presentation log
if ! echo "$STAGED" | grep -q 'presentation-log.md'; then
  if [ -n "$MISSING" ]; then
    MISSING="${MISSING}, docs/presentation-log.md"
  else
    MISSING="docs/presentation-log.md"
  fi
fi

if [ -n "$MISSING" ]; then
  cat <<BLOCK
{"decision": "block", "reason": "커밋 전에 로그를 작성하세요.\n\n누락: ${MISSING}\n\n실험 로그 (docs/experiments/log.md):\n## YYYY-MM-DD HH:MM | 브랜치명\n### 무엇을 했는가\n### 왜 했는가\n### 어떻게 했는가\n\n프레젠테이션 로그 (docs/presentation-log.md):\n> Context: / Result: / Insight:\n\n작성 후 git add 하고 다시 커밋하세요."}
BLOCK
  exit 0
fi

exit 0
