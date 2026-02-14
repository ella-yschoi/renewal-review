#!/bin/bash
# PostToolUse hook: remind to update presentation log after commit
# Does NOT modify files — just prints a reminder if presentation-log.md
# was not included in the commit.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only process git commit commands
if [[ "$COMMAND" != *"git commit"* ]]; then
  exit 0
fi

# Check if commit actually succeeded
RESULT=$(echo "$INPUT" | jq -r '.tool_result // empty')
if echo "$RESULT" | grep -qiE '(nothing to commit|no changes added|error:|abort)'; then
  exit 0
fi

# Check if presentation-log.md was part of this commit
COMMITTED=$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null)
if ! echo "$COMMITTED" | grep -q 'presentation-log.md'; then
  echo "주의: 이 커밋에 docs/presentation-log.md가 포함되지 않았습니다. 프레젠테이션 로그 업데이트가 필요하면 별도 커밋으로 추가하세요."
fi

exit 0
