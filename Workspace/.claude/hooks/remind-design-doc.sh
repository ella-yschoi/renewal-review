#!/bin/bash
# PostToolUse hook: remind agent to update design-doc.md when code files are edited
# Uses a temp flag to fire only once per batch of changes (not every edit).
# Flag is cleared when design.md is committed (by require-design-doc.sh).

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only check code files under renewal-review/app/ or tests/
if [[ "$FILE_PATH" != *"/renewal-review/app/"* && "$FILE_PATH" != *"/renewal-review/tests/"* ]]; then
  exit 0
fi

FLAG="/tmp/claude-design-doc-reminded"

# Already reminded in this batch — stay silent
if [ -f "$FLAG" ]; then
  exit 0
fi

# First code edit in this batch — remind once
touch "$FLAG"
echo "코드 변경 감지 ($(basename "$FILE_PATH")). 커밋 전에 docs/design-doc.md 관련 섹션을 업데이트하세요."
exit 0
