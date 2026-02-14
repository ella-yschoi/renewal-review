#!/bin/bash
# scripts/self-correcting-loop.sh
# Ralph-style 자가 수정 루프 + 삼각 검증
# 사용법: bash scripts/self-correcting-loop.sh [max_iterations]
# 실행 위치: renewal-review/ 프로젝트 루트에서 실행

set -euo pipefail

# Claude Code 세션 안에서 nested 호출 차단 해제
unset CLAUDECODE 2>/dev/null || true

MAX_ITERATIONS=${1:-5}
PROMPT_FILE="docs/experiments/3-PROMPT-quote-generator.md"
LOG_DIR="docs/logs"
LOOP_LOG="$LOG_DIR/loop-execution.log"
FEEDBACK_FILE="/tmp/self-correcting-loop-feedback.txt"

mkdir -p "$LOG_DIR"

# 프롬프트 파일 존재 확인
if [ ! -f "$PROMPT_FILE" ]; then
  echo "ERROR: Prompt file not found: $PROMPT_FILE"
  echo "Run this script from the renewal-review/ project root."
  exit 1
fi

ITERATION=0
START_TIME=$(date +%s)

log() {
  local msg="[$(date '+%H:%M:%S')] $1"
  echo "$msg"
  echo "$msg" >> "$LOOP_LOG"
}

log "=== Self-Correcting Agent Loop ==="
log "Max iterations: $MAX_ITERATIONS"
log "Prompt: $PROMPT_FILE"
log "Started: $(date)"
log ""

while [ "$ITERATION" -lt "$MAX_ITERATIONS" ]; do
  ITERATION=$((ITERATION + 1))
  ITER_START=$(date +%s)

  log "--- Iteration $ITERATION / $MAX_ITERATIONS ---"

  # ============================================
  # Phase 1: 구현 (또는 수정)
  # ============================================
  log "[Phase 1] Agent A: 구현/수정"

  if [ "$ITERATION" -eq 1 ]; then
    # 첫 반복: PROMPT.md를 그대로 전달
    claude --print -p "$(cat "$PROMPT_FILE")" >> "$LOOP_LOG" 2>&1
  else
    # 이후 반복: 이전 피드백을 포함하여 수정 요청
    FEEDBACK=$(cat "$FEEDBACK_FILE" 2>/dev/null || echo "No specific feedback available")
    claude --print -p "
Read $PROMPT_FILE for the full requirements.

Previous iteration ($((ITERATION - 1))) failed with this feedback:
---
$FEEDBACK
---

Fix the issues described above. Do NOT start from scratch.
Read the existing code first, then make targeted fixes only.
After fixing, verify your changes match the requirements.
" >> "$LOOP_LOG" 2>&1
  fi

  log "[Phase 1] Agent A completed"

  # ============================================
  # Phase 2: 기존 품질 게이트 (ruff + pytest + semgrep)
  # ============================================
  log "[Phase 2] Quality gates: ruff + pytest + semgrep"

  GATE_PASS=true
  GATE_OUTPUT=""

  # ruff check
  log "[Phase 2] Running ruff check..."
  if RUFF_OUT=$(ruff check app/ tests/ 2>&1); then
    log "[Phase 2] ruff: PASS"
  else
    log "[Phase 2] ruff: FAIL"
    GATE_OUTPUT="ruff check FAILED:\n$RUFF_OUT"
    GATE_PASS=false
  fi

  # pytest (only if ruff passed)
  if [ "$GATE_PASS" = true ]; then
    log "[Phase 2] Running pytest..."
    if PYTEST_OUT=$(uv run pytest -q 2>&1); then
      log "[Phase 2] pytest: PASS"
    else
      log "[Phase 2] pytest: FAIL"
      GATE_OUTPUT="pytest FAILED:\n$PYTEST_OUT"
      GATE_PASS=false
    fi
  fi

  # semgrep (only if ruff + pytest passed)
  if [ "$GATE_PASS" = true ]; then
    log "[Phase 2] Running semgrep..."
    if SEMGREP_OUT=$(semgrep scan --config auto --quiet app/ 2>&1); then
      log "[Phase 2] semgrep: PASS"
    else
      log "[Phase 2] semgrep: FAIL"
      GATE_OUTPUT="semgrep FAILED:\n$SEMGREP_OUT"
      GATE_PASS=false
    fi
  fi

  if [ "$GATE_PASS" = false ]; then
    printf "%b" "$GATE_OUTPUT" > "$FEEDBACK_FILE"
    ITER_END=$(date +%s)
    log "[Phase 2] FAILED — looping back (iteration took $((ITER_END - ITER_START))s)"
    log ""
    continue
  fi
  log "[Phase 2] ALL PASSED"

  # ============================================
  # Phase 3: 삼각 검증
  # ============================================
  log "[Phase 3] Triangular verification"

  if bash scripts/triangular-verify.sh >> "$LOOP_LOG" 2>&1; then
    log "[Phase 3] PASSED"
  else
    # discrepancy report를 피드백으로 전달
    if [ -f "docs/experiments/discrepancy-report.md" ]; then
      cp docs/experiments/discrepancy-report.md "$FEEDBACK_FILE"
    else
      echo "Triangular verification failed but no discrepancy report found." > "$FEEDBACK_FILE"
    fi
    ITER_END=$(date +%s)
    log "[Phase 3] FAILED — issues found, looping back (iteration took $((ITER_END - ITER_START))s)"
    log ""
    continue
  fi

  # ============================================
  # Phase 4: 완료
  # ============================================
  END_TIME=$(date +%s)
  TOTAL_TIME=$((END_TIME - START_TIME))

  log ""
  log "=== LOOP_COMPLETE ==="
  log "Finished in $ITERATION iteration(s), total ${TOTAL_TIME}s"
  log "Ended: $(date)"

  # 임시 파일 정리
  rm -f "$FEEDBACK_FILE"
  exit 0
done

# max iterations 도달
END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

log ""
log "=== MAX ITERATIONS REACHED ==="
log "Completed $MAX_ITERATIONS iterations without full convergence."
log "Total time: ${TOTAL_TIME}s"
log "Review remaining issues in: $FEEDBACK_FILE"
log "Review full log in: $LOOP_LOG"
exit 1
