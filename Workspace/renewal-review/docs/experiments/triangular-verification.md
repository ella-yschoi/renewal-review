# Triangular Verification — 삼각 검증 실험 계획서

## Context

**가설:** 3-에이전트 삼각 검증이 기존 테스트(unit test + lint)가 놓치는 "의도 불일치" 버그를 잡을 수 있다.

**핵심 메시지:** AI 파이프라인 설계자 — "AI 코드의 신뢰성을 자동으로 검증하는 시스템을 데이터로 증명했다"

**기존 검증의 한계:**
- ruff, pytest, semgrep은 구문/보안/로직 오류만 잡음
- "요구사항대로 만들었는가?"는 사람이 직접 확인해야 함
- 교차 모델 검증(GPT vs Claude)은 같은 편향을 공유할 수 있음

**삼각 검증의 차별점:**
- 교차 **에이전트** 검증 — 동일 모델이어도 컨텍스트 격리로 독립성 확보
- 코드 → 설명 → 요구사항 역추적으로 "의도 불일치" 자동 탐지
- 아무도 전체 그림을 못 봄 → 편향 제거

---

## 실험 과제

renewal-review에 Analytics 모듈 추가 (7개 파일, ~300줄)

### 구현 요구사항

1. Batch history 저장 (batch route 수정)
2. Analytics 모델 (BatchRunRecord, TrendPoint, AnalyticsSummary)
3. Analytics 서비스 (compute_trends 함수)
4. Analytics 라우트 (GET /analytics/trends, /analytics/history)
5. 테스트 (0건, 1건, 3건+ 케이스)
6. 기존 68개 테스트 통과 유지

---

## 사전 조건 3종

삼각 검증이 작동하려면 아래 3가지가 사전에 정의되어야 함:

| 문서 | 역할 | 제공 대상 |
|------|------|----------|
| requirements.md | 뭘 만들어야 하는지 (기능 요구사항 + 수락 기준) | Agent A, Agent C |
| architecture.md | 어떻게 만들어야 하는지 (설계 패턴 + 구조) | Agent A, Agent B |
| convention.md | 어떤 규칙을 따라야 하는지 (PEP 8 + 프로젝트 규칙) | Agent A, Agent B |

**핵심: Agent B는 requirements.md를 받지 않는다. Agent C는 코드를 받지 않는다.**

---

## 3단계 Flow

| 단계 | 에이전트 | 입력 | 출력 | 격리 |
|------|---------|------|------|------|
| 1. 구현 | Agent A (wt-feat-1) | 요구사항 + 아키텍처 + 컨벤션 | 코드 | — |
| 2. 해석 | Agent B (wt-feat-2) | 코드 + 컨벤션 + 아키텍처 (요구사항 X) | 블라인드 리뷰 설명문 | 별도 세션 |
| 3. 비교 | Agent C (새 세션) | 요구사항 + Agent B 설명문 (코드 X) | 불일치 리포트 | 별도 세션 |

```
Agent A (요구사항 O, 코드 O)
  → 코드 작성

Agent B (요구사항 X, 코드 O)
  → "이 코드는 X를 한다" 설명 생성

Agent C (요구사항 O, 코드 X)
  → 요구사항 vs 설명 비교
  → 불일치 리포트 출력
```

---

## 이슈 분류 체계

| 유형 | 설명 | 예시 |
|------|------|------|
| Intent Mismatch | 요구사항과 코드 동작이 다름 | "20% 이상"인데 코드는 15% 초과 |
| Missing Feature | 요구사항에 있는데 코드에 없음 | "3건+ 케이스 테스트" 누락 |
| Extra Feature | 요구사항에 없는데 코드에 있음 | 불필요한 캐싱 로직 추가 |
| Convention Violation | 아키텍처/컨벤션 위반 | docstring 추가 (convention.md 위반) |

---

## 측정 지표

| 지표 | 설명 |
|------|------|
| issues_standard | ruff + pytest + semgrep이 잡은 이슈 수 |
| issues_triangular | 삼각 검증이 추가로 잡은 이슈 수 |
| false_positives | Agent C가 보고했지만 실제론 문제 없는 것 |
| precision | 진짜 이슈 / (진짜 이슈 + false positive) |
| time_overhead | 삼각 검증 추가 소요 시간 |
| intent_match_rate | Agent B 설명 vs 요구사항 일치율 (%) |

### 판정 기준

- `issues_triangular > 0` → 삼각 검증이 기존 도구가 못 잡는 이슈를 발견
- `precision > 70%` → 실용적 가치 있음
- `time_overhead < 10분` → 생산성 대비 합리적

---

## 실행 명령어

### Step 1: 사전 문서 작성 (Claude Code에 시킬 것)

```text
Analytics 모듈에 대한 requirements.md와 architecture.md를 작성해줘
```

산출물:
- `docs/experiments/requirements.md` — 기능 요구사항 6개 + 수락 기준
- `docs/experiments/architecture.md` — 파일 구조, 디자인 패턴, 의존성 규칙

### Step 2: Agent A — 구현 (wt-feat-1)

```bash
cd ~/Workspace/.worktrees/wt-feat-1/Workspace/renewal-review
date +%s > /tmp/exp_triangular_start.txt
claude
```

프롬프트:

```text
Read convention.md, docs/experiments/requirements.md,
docs/experiments/architecture.md.

Then implement ALL requirements. Run tests and commit when done.
Do NOT add anything beyond what requirements.md specifies.
```

완료 후 코드를 wt-feat-2에 복사:

```bash
cd ~/Workspace/.worktrees/wt-feat-1/Workspace/renewal-review
git diff --name-only main..HEAD | while read f; do
  cp "$f" ~/Workspace/.worktrees/wt-feat-2/Workspace/renewal-review/"$f"
done
```

### Step 3: Agent B — 블라인드 해석 (wt-feat-2, 별도 세션)

```bash
cd ~/Workspace/.worktrees/wt-feat-2/Workspace/renewal-review
claude
```

프롬프트:

```text
Read convention.md and docs/experiments/architecture.md.
Do NOT read docs/experiments/requirements.md.

The following files were recently added/modified:
- app/models/analytics.py
- app/engine/analytics.py
- app/routes/analytics.py
- app/routes/batch.py (modified)
- app/main.py (modified)
- tests/test_analytics.py

For each file:
1. Describe what this code does (behavior, not structure)
2. List any convention violations
3. List potential issues or edge cases

Save your analysis to docs/experiments/blind-review.md
```

### Step 4: Agent C — 불일치 비교 (새 세션)

```bash
cd ~/Workspace/renewal-review
claude
```

프롬프트:

```text
Read these two documents:
1. docs/experiments/requirements.md (original requirements)
2. docs/experiments/blind-review.md (blind code analysis)

Do NOT read any code files.

Compare them and produce a discrepancy report:
- Requirements met: list with evidence from blind review
- Requirements missed: present in requirements but not in review
- Extra behavior: in review but not in requirements
- Potential bugs: where review description contradicts requirements

Save to docs/experiments/discrepancy-report.md
```

### Step 5: 결과 수집

```bash
date +%s > /tmp/exp_triangular_end.txt

# 소요 시간
echo "Total: $(( $(cat /tmp/exp_triangular_end.txt) - $(cat /tmp/exp_triangular_start.txt) ))초"

# 산출물 확인
cat docs/experiments/discrepancy-report.md
```

---

## Baseline 비교

동일 코드에 대해 기존 도구만 실행한 결과와 비교:

```bash
cd ~/Workspace/.worktrees/wt-feat-1/Workspace/renewal-review
ruff check app/ tests/ > /tmp/exp_ruff_result.txt
uv run pytest -q > /tmp/exp_pytest_result.txt
semgrep scan --config auto app/ > /tmp/exp_semgrep_result.txt
```

### 기록 템플릿

| 지표 | Standard (ruff+pytest+semgrep) | Triangular | Delta |
|------|-------------------------------|------------|-------|
| 발견 이슈 수 |  |  |  |
| Intent Mismatch |  |  |  |
| Missing Feature |  |  |  |
| Extra Feature |  |  |  |
| Convention Violation |  |  |  |
| False Positive |  |  |  |
| Precision |  |  |  |
| 소요 시간 |  |  |  |

---

## 도출할 결론 (예시)

> "기존 테스트 도구(ruff + pytest + semgrep)는 구문/보안 오류를 잡지만,
> '요구사항대로 만들었는가'는 검증하지 못한다.
> 삼각 검증은 추가 8분 투자로 Intent Mismatch 2건, Missing Feature 1건을 발견했다.
> Precision 85% — 실무에서 코드 리뷰 전 자동 프리체크로 충분히 활용 가능."

---

## 검증 체크리스트

- [ ] requirements.md, architecture.md 작성 완료
- [ ] Agent A: 코드 작성 + 테스트 통과
- [ ] Agent B: 블라인드 리뷰 설명문 생성
- [ ] Agent C: 불일치 리포트 생성
- [ ] Baseline 비교 (ruff + pytest + semgrep)
- [ ] 기록 템플릿 채우기
- [ ] 기존 68개 테스트 regression 없음
