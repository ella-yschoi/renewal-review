#!/bin/bash
# scripts/triangular-verify.sh
# 삼각 검증 자동화 — Agent B (blind review) + Agent C (discrepancy report)
# 사용법: bash scripts/triangular-verify.sh
#   환경변수: REQUIREMENTS_FILE (기본값: experiment 3 파일)
# 실행 위치: renewal-review/ 프로젝트 루트에서 실행

set -euo pipefail

# Claude Code 세션 안에서 nested 호출 차단 해제
unset CLAUDECODE 2>/dev/null || true

REVIEW_DIR="docs/experiments"
LOG_DIR="docs/logs"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-$REVIEW_DIR/3-requirements-quote-generator.md}"
BLIND_REVIEW_FILE="$REVIEW_DIR/blind-review.md"
DISCREPANCY_FILE="$REVIEW_DIR/discrepancy-report.md"

mkdir -p "$LOG_DIR"

# 변경된 코드 파일 목록 (main 대비)
CODE_FILES=$(git diff --name-only main..HEAD -- app/ tests/ 2>/dev/null || echo "No diff available")

if [ -z "$CODE_FILES" ] || [ "$CODE_FILES" = "No diff available" ]; then
  echo "[triangular-verify] WARNING: No code changes detected vs main."
  echo "Falling back to listing all app/ and tests/ files."
  CODE_FILES=$(find app/ tests/ -name '*.py' -type f 2>/dev/null | sort)
fi

echo "[triangular-verify] Started: $(date)"
echo "[triangular-verify] Files to review:"
echo "$CODE_FILES"
echo ""

# --- Agent B: Blind Review ---
echo "[triangular-verify] Phase B: Blind review (코드만 읽고 행동 설명)"

claude --print -p "
You are Agent B in a triangular verification process.

Read convention.md and docs/design-doc.md for project context.
Do NOT read any requirements document ($REQUIREMENTS_FILE).

The following files were recently changed or created:
$CODE_FILES

For each file:
1. Describe what this code does (behavior and intent, not just structure)
2. List any convention.md violations
3. List potential issues, edge cases, or bugs

Output your analysis as structured markdown.
" > "$BLIND_REVIEW_FILE" 2>&1

echo "[triangular-verify] Blind review saved to $BLIND_REVIEW_FILE"

# --- Agent C: Discrepancy Report ---
echo "[triangular-verify] Phase C: Discrepancy report (requirements vs blind review)"

claude --print -p "
You are Agent C in a triangular verification process.

Read these two documents carefully:
1. $REQUIREMENTS_FILE (original requirements — the source of truth)
2. $BLIND_REVIEW_FILE (blind code analysis by another agent)

Do NOT read any code files directly.

Compare them and produce a discrepancy report with these sections:

## Requirements Met
List each requirement from the requirements doc that is confirmed by the blind review, with evidence.

## Requirements Missed
Requirements present in the requirements doc but NOT reflected in the blind review.

## Extra Behavior
Behavior described in the blind review but NOT in the requirements.

## Potential Bugs
Where the blind review contradicts or conflicts with requirements.

## Verdict
If ALL requirements are met and no critical issues found, output exactly on its own line:
TRIANGULAR_PASS

Otherwise, list each issue that must be fixed.
" > "$DISCREPANCY_FILE" 2>&1

echo "[triangular-verify] Discrepancy report saved to $DISCREPANCY_FILE"

# --- 결과 판정 ---
echo ""
if grep -q "TRIANGULAR_PASS" "$DISCREPANCY_FILE"; then
  echo "[triangular-verify] RESULT: PASS"
  echo "[triangular-verify] Ended: $(date)"
  exit 0
else
  echo "[triangular-verify] RESULT: FAIL — issues found in $DISCREPANCY_FILE"
  echo "[triangular-verify] Ended: $(date)"
  exit 1
fi
