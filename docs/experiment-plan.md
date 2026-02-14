# SubAgent vs Agent Teams — 실험 계획서

## Context

Quandri Software Engineer 인터뷰(2/17) 발표를 위한 실험.

**핵심 질문:** 동일한 구현 작업을 SubAgent 방식과 Agent Teams 방식으로 수행할 때, 생산성(시간/토큰/품질)은 어떻게 달라지는가?

---

## 과제 정의

"Analytics 모듈 추가" — 7개 파일, ~300줄 신규 코드. 연구 + 구현 + 테스트 필요.

### 구현 요구사항

1. Batch history 저장 (batch route 수정)
2. Analytics 모델 (BatchRunRecord, TrendPoint, AnalyticsSummary)
3. Analytics 서비스 (compute_trends 함수)
4. Analytics 라우트 (GET /analytics/trends, /analytics/history)
5. 테스트 (0건, 1건, 3건+ 케이스)
6. 기존 68개 테스트 통과 유지

---

## 사전 준비

### Step 1: 브랜치 세팅

```bash
cd ~/Workspace/renewal-review
BASELINE=$(git rev-parse HEAD)
echo "Baseline: $BASELINE"

# wt-feat-1에 SubAgent 실험 브랜치
cd ~/Workspace/.worktrees/wt-feat-1
git checkout -b experiment/subagent-analytics $BASELINE

# wt-feat-2에 Agent Teams 실험 브랜치
cd ~/Workspace/.worktrees/wt-feat-2
git checkout -b experiment/teams-analytics $BASELINE
```

### Step 2: 양쪽 테스트 통과 확인

```bash
cd ~/Workspace/.worktrees/wt-feat-1/Workspace/renewal-review
uv run pytest -q

cd ~/Workspace/.worktrees/wt-feat-2/Workspace/renewal-review
uv run pytest -q
```

---

## 실험 A: SubAgent 방식

### 명령어 Flow

```bash
cd ~/Workspace/.worktrees/wt-feat-1/Workspace/renewal-review
date +%s > /tmp/exp_subagent_start.txt
claude
```

Claude Code에 아래 프롬프트 붙여넣기:

```text
Read convention.md first. Then implement the following in THIS worktree:

Add an analytics module to the renewal-review pipeline.

Requirements:
1. Batch history 저장 (batch route 수정)
2. Analytics 모델 (BatchRunRecord, TrendPoint, AnalyticsSummary)
3. Analytics 서비스 (compute_trends 함수)
4. Analytics 라우트 (GET /analytics/trends, /analytics/history)
5. 테스트 (0건, 1건, 3건+ 케이스)
6. 기존 68개 테스트 통과 유지

Use subagents (Task tool) to parallelize where possible:
- One subagent for research (read existing code patterns)
- One subagent for models + service implementation
- One subagent for route + main.py registration
- One subagent for tests
Then verify everything works, run tests, and commit.
```

완료 후:

```bash
date +%s > /tmp/exp_subagent_end.txt
cd ~/Workspace/.worktrees/wt-feat-1/Workspace/renewal-review
git log --oneline main..HEAD > /tmp/exp_subagent_commits.txt
git diff --stat main..HEAD > /tmp/exp_subagent_diffstat.txt
uv run pytest -q 2>&1 > /tmp/exp_subagent_tests.txt
```

---

## 실험 B: Agent Teams 방식

### 명령어 Flow

```bash
cd ~/Workspace/.worktrees/wt-feat-2/Workspace/renewal-review
date +%s > /tmp/exp_teams_start.txt
claude
```

Claude Code에 아래 프롬프트 붙여넣기:

```text
Read convention.md first. Then implement the following in THIS worktree:

Add an analytics module to the renewal-review pipeline.

Requirements:
1. Batch history 저장 (batch route 수정)
2. Analytics 모델 (BatchRunRecord, TrendPoint, AnalyticsSummary)
3. Analytics 서비스 (compute_trends 함수)
4. Analytics 라우트 (GET /analytics/trends, /analytics/history)
5. 테스트 (0건, 1건, 3건+ 케이스)
6. 기존 68개 테스트 통과 유지

Use Agent Teams to parallelize this work:
- Create a team called "analytics-feature"
- Spawn a "modeler" teammate for models + service (requirements 2, 3)
- Spawn a "router" teammate for routes + main.py changes (requirements 1, 4)
- Spawn a "tester" teammate for writing tests (requirement 5)
- Coordinate via task list and messages.
Then verify everything works, run tests, and commit.
```

완료 후:

```bash
date +%s > /tmp/exp_teams_end.txt
cd ~/Workspace/.worktrees/wt-feat-2/Workspace/renewal-review
git log --oneline main..HEAD > /tmp/exp_teams_commits.txt
git diff --stat main..HEAD > /tmp/exp_teams_diffstat.txt
uv run pytest -q 2>&1 > /tmp/exp_teams_tests.txt
```

---

## 결과 비교

```bash
# 소요 시간
echo "SubAgent: $(( $(cat /tmp/exp_subagent_end.txt) - $(cat /tmp/exp_subagent_start.txt) ))초"
echo "Teams: $(( $(cat /tmp/exp_teams_end.txt) - $(cat /tmp/exp_teams_start.txt) ))초"

# 코드 비교
echo "=== SubAgent ===" && cat /tmp/exp_subagent_diffstat.txt
echo "=== Teams ===" && cat /tmp/exp_teams_diffstat.txt

# 테스트 결과
cat /tmp/exp_subagent_tests.txt
cat /tmp/exp_teams_tests.txt
```

### 기록 템플릿

| 지표 | SubAgent | Agent Teams | Winner |
|------|----------|-------------|--------|
| 소요 시간 (초) |  |  |  |
| 토큰 사용량 |  |  |  |
| 커밋 수 |  |  |  |
| 생성/수정 파일 수 |  |  |  |
| 추가된 줄 수 |  |  |  |
| 테스트 수 |  |  |  |
| 전체 테스트 통과? |  |  |  |
| 수정 횟수 |  |  |  |
| 완성도 (1-5) |  |  |  |
| 코드 품질 (1-5) |  |  |  |

---

## Claude Code가 자동 생성하는 파일

wt-feat-1, wt-feat-2 각각에서:

| 파일 | 설명 |
|------|------|
| app/models/analytics.py | BatchRunRecord, TrendPoint, AnalyticsSummary |
| app/engine/analytics.py | compute_trends 서비스 |
| app/routes/analytics.py | GET /analytics/trends, /analytics/history |
| app/routes/batch.py | batch history 저장 로직 추가 |
| app/main.py | analytics 라우터 등록 |
| tests/test_analytics.py | 분석 테스트 |

---

## 검증 체크리스트

- [ ] 양쪽 워크트리에서 `uv run pytest -q` 전체 통과
- [ ] 비교 테이블 완성
- [ ] 기존 68개 테스트 regression 없음
