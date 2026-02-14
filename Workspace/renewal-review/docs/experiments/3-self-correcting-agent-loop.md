# Self-Correcting Agent Loop — 자가 수정 에이전트 루프 실험 계획서

## Context

**가설:** Ralph Wiggum 반복 루프 + 삼각 검증을 결합하면, 기능 구현부터 의도 검증까지 **사람 개입 없이** 자동으로 완료할 수 있다.

**핵심 메시지:** AI 파이프라인 아키텍트 — "기능을 큐에 넣으면 코드 작성 → 품질 검증 → 의도 검증 → 자가 수정까지 자동으로 돌아가는 파이프라인을 만들었다"

**실험 1-2 결론의 연장선:**

| 실험 | 증명한 것 | 남은 한계 |
|------|-----------|----------|
| 실험 1 (Agent Teams) | agent 병렬 협업으로 동일 품질, 비슷한 시간 | 수동 orchestration 필요 |
| 실험 2 (삼각검증) | intent mismatch 78% 정밀도 탐지 | 수동 실행, 19분 오버헤드 |
| **실험 3 (본 실험)** | **전체 사이클 자동화 + 자가 수정** | — |

**Ralph Wiggum 패턴이란:**
- `while :; do cat PROMPT.md | claude ; done` — 반복 루프로 AI가 작업을 정제
- 완벽한 첫 시도 대신 **반복을 통한 수렴**
- `--max-iterations` 안전장치, `completion-promise` 완료 신호
- 출처: https://awesomeclaude.ai/ralph-wiggum

**기존 접근의 한계:**
- 실험 2의 삼각 검증은 이슈를 **발견**하지만 **수정하지 않는다**
- 개발자가 직접 Agent A → B → C를 순차 실행해야 한다
- 이슈 발견 후 수정 → 재검증 사이클이 수동

**본 실험의 차별점:**
- 삼각 검증을 **루프 안에 내장** → 이슈 발견 즉시 자동 수정
- 기존 품질 게이트(ruff + pytest + semgrep) + 의도 검증(삼각)을 **단일 파이프라인**으로 통합
- `PROMPT.md` 하나로 기능 정의 → 완성된 코드 산출

---

## 파이프라인 구조

```
PROMPT.md (요구사항 + 완료 기준)
    │
    ▼
┌─────────────────────────────────────────┐
│  Loop (max N iterations)                │
│                                         │
│  Phase 1: 구현                          │
│    Agent A: 코드 작성 (또는 수정)       │
│                                         │
│  Phase 2: 기존 품질 게이트              │
│    ruff check → pytest → semgrep        │
│    ❌ 실패 → Phase 1로 (자동 수정)     │
│                                         │
│  Phase 3: 삼각 검증                     │
│    Agent B: blind review (코드만 읽음)  │
│    Agent C: discrepancy report          │
│    ❌ 이슈 발견 → Phase 1로 (피드백 전달) │
│                                         │
│  Phase 4: 완료                          │
│    모든 게이트 통과 → COMPLETE 출력     │
└─────────────────────────────────────────┘
```

### 핵심 설계 원칙

1. **실패 = 데이터**: 각 반복의 실패 메시지가 다음 반복의 입력이 됨
2. **안전장치 필수**: `max-iterations`로 무한 루프 방지
3. **점진적 수렴**: 첫 반복에서 대부분 완성, 이후 반복에서 edge case 해소
4. **완료 신호**: 모든 게이트 통과 시 정확한 문구(`COMPLETE`)를 출력해야 루프 종료

---

## 실험 과제

renewal-review에 **새 기능 추가** — 자가 수정 루프가 처리할 구현 과제.

과제 선정 기준:
- 실험 1-2와 다른 모듈 (analytics 외)
- 삼각 검증이 의미 있는 수준의 비즈니스 로직 포함
- ~200-400줄 규모 (루프 1회당 5-10분 내 완료 가능)

**구체적 과제는 실험 시작 전 확정** (별도 requirements.md 작성)

---

## 사전 준비

### Step 1: PROMPT.md 작성

루프에 주입할 단일 프롬프트 파일. 아래 구조를 따른다:

```markdown
# Feature: [기능명]

## Requirements
[구체적 요구사항 목록 — 수락 기준 포함]

## Completion Criteria
- [ ] 모든 요구사항 구현
- [ ] ruff check 통과 (0 errors)
- [ ] pytest 전체 통과 (기존 + 신규)
- [ ] semgrep 통과
- [ ] convention.md 준수

## On Failure
- ruff/pytest/semgrep 실패: 오류 메시지를 읽고 코드 수정
- 삼각 검증 이슈: discrepancy-report.md를 읽고 해당 이슈 수정

## Completion Signal
모든 기준 충족 시 반드시 아래 문구를 출력:
<promise>LOOP_COMPLETE</promise>
```

### Step 2: 삼각 검증 스크립트 작성

수동 3단계를 자동화하는 셸 스크립트:

```bash
#!/bin/bash
# scripts/triangular-verify.sh
# 삼각 검증 자동화 — Agent B + Agent C를 순차 실행

set -euo pipefail

REVIEW_DIR="docs/experiments"
CODE_FILES=$(git diff --name-only main..HEAD -- app/ tests/)

# Agent B: blind review
claude --print -p "
Read convention.md and docs/design-doc.md.
Do NOT read docs/experiments/requirements.md.

The following files were recently changed:
$CODE_FILES

For each file:
1. Describe what this code does (behavior, not structure)
2. List any convention violations
3. List potential issues or edge cases

Output your analysis as markdown.
" > "$REVIEW_DIR/blind-review.md"

# Agent C: discrepancy report
claude --print -p "
Read these two documents:
1. docs/experiments/requirements.md (original requirements)
2. $REVIEW_DIR/blind-review.md (blind code analysis)

Do NOT read any code files.

Compare them and produce a discrepancy report:
- Requirements met: list with evidence
- Requirements missed: present in requirements but not in review
- Extra behavior: in review but not in requirements
- Potential bugs: where review contradicts requirements

If ALL requirements are met and no issues found, output exactly:
TRIANGULAR_PASS

Otherwise list each issue.
" > "$REVIEW_DIR/discrepancy-report.md"

# 결과 판정
if grep -q "TRIANGULAR_PASS" "$REVIEW_DIR/discrepancy-report.md"; then
  echo "TRIANGULAR: PASS"
  exit 0
else
  echo "TRIANGULAR: FAIL — issues found in discrepancy-report.md"
  exit 1
fi
```

### Step 3: 메인 루프 스크립트 작성

```bash
#!/bin/bash
# scripts/self-correcting-loop.sh
# Ralph-style 자가 수정 루프 + 삼각 검증

set -euo pipefail

MAX_ITERATIONS=${1:-5}
PROMPT_FILE="PROMPT.md"
PROJECT_DIR="$(pwd)"
ITERATION=0

echo "=== Self-Correcting Agent Loop ==="
echo "Max iterations: $MAX_ITERATIONS"
echo "Prompt: $PROMPT_FILE"
echo "Started: $(date)"

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
  ITERATION=$((ITERATION + 1))
  echo ""
  echo "--- Iteration $ITERATION / $MAX_ITERATIONS ---"

  # Phase 1: 구현 (또는 수정)
  echo "[Phase 1] Agent A: 구현/수정"
  if [ $ITERATION -eq 1 ]; then
    cat "$PROMPT_FILE" | claude --print -p
  else
    # 이전 반복의 실패 피드백을 포함
    FEEDBACK=$(cat /tmp/loop_feedback.txt 2>/dev/null || echo "No feedback")
    claude --print -p "
Read $PROMPT_FILE for requirements.
Previous iteration failed with this feedback:
---
$FEEDBACK
---
Fix the issues described above. Do NOT start from scratch.
Read the existing code first, then make targeted fixes.
"
  fi

  # Phase 2: 기존 품질 게이트
  echo "[Phase 2] Quality gates: ruff + pytest + semgrep"

  GATE_PASS=true

  if ! ruff check app/ tests/ 2>&1; then
    echo "ruff FAILED" | tee /tmp/loop_feedback.txt
    GATE_PASS=false
  fi

  if [ "$GATE_PASS" = true ] && ! uv run pytest -q 2>&1; then
    echo "pytest FAILED" | tee /tmp/loop_feedback.txt
    GATE_PASS=false
  fi

  if [ "$GATE_PASS" = true ] && ! semgrep scan --config auto app/ 2>&1; then
    echo "semgrep FAILED" | tee /tmp/loop_feedback.txt
    GATE_PASS=false
  fi

  if [ "$GATE_PASS" = false ]; then
    echo "[Phase 2] FAILED — looping back"
    continue
  fi
  echo "[Phase 2] PASSED"

  # Phase 3: 삼각 검증
  echo "[Phase 3] Triangular verification"
  if ! bash scripts/triangular-verify.sh 2>&1; then
    cat docs/experiments/discrepancy-report.md > /tmp/loop_feedback.txt
    echo "[Phase 3] FAILED — issues found, looping back"
    continue
  fi
  echo "[Phase 3] PASSED"

  # Phase 4: 완료
  echo ""
  echo "=== LOOP_COMPLETE ==="
  echo "Finished in $ITERATION iteration(s)"
  echo "Ended: $(date)"
  exit 0
done

echo ""
echo "=== MAX ITERATIONS REACHED ==="
echo "Completed $MAX_ITERATIONS iterations without full convergence."
echo "Review remaining issues in /tmp/loop_feedback.txt"
exit 1
```

### Step 4: 브랜치 세팅

```bash
cd ~/Workspace/renewal-review
BASELINE=$(git rev-parse HEAD)
echo "Baseline: $BASELINE"

# wt-experiment에 실험 브랜치
cd ~/Workspace/.worktrees/wt-experiment
git checkout -b experiment/self-correcting-loop $BASELINE
```

---

## 실행

### 자동 루프 실행

```bash
cd ~/Workspace/.worktrees/wt-experiment/Workspace/renewal-review
date +%s > /tmp/exp_loop_start.txt

bash scripts/self-correcting-loop.sh 5

date +%s > /tmp/exp_loop_end.txt
```

### 대조군: 수동 실행 (동일 과제)

비교를 위해 동일 과제를 수동 방식(실험 2와 같은 방식)으로도 실행:

```bash
cd ~/Workspace/.worktrees/wt-feat-1/Workspace/renewal-review
git checkout -b experiment/manual-baseline $BASELINE
date +%s > /tmp/exp_manual_start.txt

# 수동으로 Agent A → ruff/pytest → Agent B → Agent C 순차 실행
# (실험 2와 동일한 절차)

date +%s > /tmp/exp_manual_end.txt
```

---

## 측정 지표

| 지표 | 설명 |
|------|------|
| total_iterations | 완료까지 걸린 루프 반복 횟수 |
| total_time | 전체 소요 시간 (루프 시작 → COMPLETE) |
| phase2_failures | 품질 게이트(ruff/pytest/semgrep) 실패 횟수 |
| phase3_failures | 삼각 검증 실패 횟수 |
| issues_auto_fixed | 루프가 자동으로 수정한 이슈 수 |
| issues_remaining | max iteration 도달 시 남은 이슈 수 |
| human_intervention | 사람이 개입한 횟수 (목표: 0) |
| manual_time | 대조군(수동) 소요 시간 |
| code_quality | 최종 코드 품질 비교 (자동 vs 수동) |

### 판정 기준

- `total_iterations ≤ 3` → 루프가 효율적으로 수렴
- `human_intervention = 0` → 완전 자동화 달성
- `total_time < manual_time` → 수동 대비 시간 절약
- 삼각 검증 precision ≥ 70% 유지 (실험 2 기준)

---

## 실험 결과

| 지표 | 자동 루프 | 수동 (대조군) | Delta |
|------|-----------|-------------|-------|
| 소요 시간 | 641초 (~10m 41s) | 549초 (~9m 9s) | 수동 -92초 |
| 반복 횟수 | 1 | 1 (+삼각 재실행 1회) | 동일 |
| Phase 2 실패 | 0 | 0 | 동일 |
| Phase 3 실패 | 0 | 1 (Agent B 잘못된 모듈 리뷰) | 자동 우위 |
| 자동 수정 이슈 | 0 (첫 시도 통과) | N/A | — |
| 사람 개입 횟수 | 0 | 1 (Agent B 프롬프트 수정) | 자동 우위 |
| 최종 테스트 통과 | 81/81 | 82/82 | 동일 |
| 코드 품질 (1-5) | 4 | 4 | 동일 |
| 삼각 검증 precision | PASS (잠재 이슈 3건, 현재 위반 0) | PASS (잠재 이슈 3건) | 동일 |

### 판정 기준 대비

| 기준 | 결과 | 판정 |
|------|------|------|
| `total_iterations ≤ 3` | 1회 | 충족 |
| `human_intervention = 0` | 0 (자동), 1 (수동) | 자동 충족 |
| `total_time < manual_time` | 641 > 549 | **미충족** |
| 삼각 검증 precision ≥ 70% | PASS (현재 위반 0건) | 충족 |

---

## 도출한 결론

> "자가 수정 루프는 1회 반복 만에 기능 구현 + 품질 검증 + 의도 검증을 완료했다.
> 사람 개입 0회. 수동 방식은 92초 빨랐지만, Agent B 프롬프트 실수로 삼각 검증을 재실행해야 했다.
> **자동화의 가치는 속도가 아니라 신뢰성 — 잠들어도 돌아가는 파이프라인.**"

### 한계와 솔직한 평가

1. **자가 수정 사이클 미작동**: 첫 시도에 모든 게이트를 통과하여 루프의 핵심 가치인 "실패 → 피드백 → 자동 수정"이 한 번도 실행되지 않음. 더 복잡한 과제(portfolio 프로젝트)에서 재검증 필요.
2. **시간 역전**: 자동 루프(641초)가 수동(549초)보다 느림. `claude --print` 버퍼링 오버헤드와 삼각 검증의 전체 코드 스캔이 원인. 자가 수정이 필요한 과제에서는 수동의 반복 비용이 누적되어 역전될 것으로 예상.
3. **삼각 검증 프롬프트 민감도**: 수동 실행에서 Agent B가 잘못된 모듈을 리뷰한 사례 — 자동 스크립트에서는 파일 목록을 `git diff`로 자동 추출하여 이 문제를 회피.

---

## 발표 앵글

### VP에게 전달할 메시지

1. **자동화 수준**: "밤에 기능 3개를 큐에 넣고, 아침에 검증된 코드를 리뷰한다"
2. **품질 보장**: 기존 도구(syntax) + 삼각 검증(intent) 이중 검증
3. **정량적 증거**: 반복 횟수, 시간, 자동 수정률 — 모두 데이터로 제시
4. **실무 적용성**: 어떤 기능이든 PROMPT.md만 바꾸면 동일 파이프라인 재사용

### 실험 1→2→3 스토리라인

```
실험 1: "agent를 여러 명 굴릴 수 있다" (병렬 협업)
    ↓
실험 2: "agent가 서로 검증할 수 있다" (삼각 검증)
    ↓
실험 3: "검증 → 수정까지 자동이다" (자가 수정 루프)
    ↓
결론: "AI agent 파이프라인을 설계하고 운영하는 개발자"
```

---

## 배포 전략: Skill 단일 레이어

실험 완료 후, 파이프라인을 **Claude Code Skill**로 패키징하여 재사용 가능하게 만든다.

### 구조

```
.claude/skills/self-correcting-loop/
├── SKILL.md              ← Claude가 읽는 오케스트레이션 가이드
└── reference/
    └── loop-design.md    ← 상세 설계 (파이프라인 구조, 프롬프트 템플릿)
```

### SKILL.md 프론트매터

```yaml
---
name: self-correcting-loop
description: Use when implementing a feature with automated quality + intent verification loop. Combines Ralph-style iteration with triangular verification.
---
```

### 왜 Skill 단일 레이어인가

| 고려한 방식 | 판단 |
|-------------|------|
| Skill + Shell scripts (2-layer) | 과도 — Skill 안에서 Claude가 직접 실행하면 충분 |
| Private pip 패키지 | 과도 — 팀 규모가 작고, repo 내 배포로 충분 |
| Claude Marketplace | 공개용 — 내부 파이프라인에 부적합 |
| CLAUDE.local.md | 개인용 — 팀 공유 불가 (gitignored) |
| **Skill (단일)** | **적합 — 네이티브 연동, private repo 폐쇄성, git pull만으로 배포** |

### 사용 방법

```
# Claude Code에서 호출
/self-correcting-loop

# 또는 프롬프트에서 참조
"self-correcting-loop Skill을 사용해서 export-csv 기능을 구현해줘"
```

### 배포

- repo의 `.claude/skills/`에 포함 → `git pull`만 하면 팀원 자동 사용
- private repo 안에만 존재 → 폐쇄적
- Skill 내용이 곧 문서 → 별도 README 불필요

### 성장 경로

```
지금: Skill (repo 내 마크다운)
  → 팀 확장 시: private pip 패키지로 승격
  → 엔터프라이즈: Agent SDK 기반 라이브러리
```

---

## 검증 체크리스트

- [x] PROMPT.md 작성 (과제 + 완료 기준)
- [x] requirements.md 작성 (삼각 검증용)
- [x] scripts/triangular-verify.sh 작성 + 테스트
- [x] scripts/self-correcting-loop.sh 작성 + 테스트
- [x] 자동 루프 실행 — 1회 반복, 641초, LOOP_COMPLETE
- [x] 대조군(수동) 실행 — 549초, 삼각 재실행 1회
- [x] 기록 템플릿 채우기
- [x] 기존 테스트 regression 없음 (81/81, 82/82)
- [x] .claude/skills/self-correcting-loop/ 패키징
- [x] 실험 로그 + 프레젠테이션 로그 작성
