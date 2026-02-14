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
{"decision": "block", "reason": "app/ 또는 tests/ 코드가 변경되었지만 docs/design-doc.md가 staging에 없습니다.\n\n관련 섹션을 업데이트하세요:\n- 1. Architecture — 새 모듈/계층 추가 시\n- 2. Data Model — 모델 변경 시\n- 3. Processing Pipeline — 처리 흐름 변경 시\n- 4. API Surface — 엔드포인트 추가/변경 시\n- 5. UI — 페이지/템플릿 변경 시\n- 6. Error Handling — 에러 처리 추가 시\n- 7. Testing Strategy — 테스트 추가 시\n- 8. Tech Stack — 의존성 변경 시\n\n업데이트 후 git add docs/design-doc.md 하고 다시 커밋하세요."}
BLOCK
  exit 0
fi

# design.md staged — clear the reminder flag for next batch
rm -f /tmp/claude-design-doc-reminded
exit 0
