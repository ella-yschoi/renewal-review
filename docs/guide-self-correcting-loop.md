# Self-Correcting Agent Loop — 팀 가이드

이 레포에는 **자가 수정 에이전트 루프**가 내장되어 있다.
기능 요구사항을 PROMPT.md 하나로 정의하면, AI가 구현 → 품질 검증 → 의도 검증 → 자가 수정까지 **사람 개입 없이** 반복 실행한다.

---

## 전제 조건

### 도구

| 도구 | 용도 | 설치 확인 |
|------|------|-----------|
| Claude Code | AI 코딩 + Skill 실행 | `claude --version` |
| ruff | 린트 + 포맷 | `ruff --version` |
| pytest | 테스트 | `uv run pytest --version` |
| semgrep | SAST 보안 스캐닝 | `semgrep --version` |
| uv | Python 패키지/실행 | `uv --version` |

### 프로젝트 설정

```bash
cd Workspace/renewal-review
uv sync --extra dev          # 의존성 설치
uv run pytest -q             # 기존 테스트 통과 확인
ruff check app/ tests/       # 린트 클린 확인
```

---

## 파이프라인 구조

```
PROMPT.md + requirements.md
    │
    ▼
┌─────────────────────────────────────────┐
│  Loop (max N iterations)                │
│                                         │
│  Phase 1: 구현                          │
│    Agent A: 코드 작성 (또는 수정)       │
│    - 첫 반복: PROMPT.md 기반 전체 구현  │
│    - 이후 반복: 피드백 기반 수정만      │
│                                         │
│  Phase 2: 품질 게이트                   │
│    ruff → pytest → semgrep (순차)       │
│    ❌ 실패 → 에러 출력을 피드백으로     │
│       → Phase 1로 되돌아감              │
│                                         │
│  Phase 3: 삼각 검증                     │
│    Agent B: blind review (코드만 읽음)  │
│    Agent C: requirements vs B 비교      │
│    ❌ 불일치 → 리포트를 피드백으로      │
│       → Phase 1로 되돌아감              │
│                                         │
│  Phase 4: 완료                          │
│    모든 게이트 통과 → LOOP_COMPLETE     │
└─────────────────────────────────────────┘
```

**핵심 원칙:**
- 실패 = 데이터 — 실패 출력이 다음 반복의 입력이 된다
- 안전장치 — `max-iterations`로 무한 루프 방지 (기본 5회)
- 점진적 수렴 — 대부분 1~2회 반복 내 완료

---

## 사용법

### 1단계: 파일 두 개 작성

**requirements 파일** — 삼각 검증의 기준이 되는 기능 요구사항.

```
docs/experiments/<번호>-requirements-<기능명>.md
```

```markdown
# <기능명> — Requirements

## Functional Requirements

### FR-1: ...
### FR-2: ...

## Non-Functional Requirements
- convention.md 준수
- 기존 테스트 전부 통과
- ruff check 0 errors
- 파일당 300줄 미만
```

**PROMPT 파일** — 에이전트에게 전달하는 구현 지시서.

```
docs/experiments/<번호>-PROMPT-<기능명>.md
```

```markdown
# Feature: <기능명>

## Context
프로젝트 맥락. convention.md, design-doc.md 읽으라는 지시.

## Requirements
Read `docs/experiments/<번호>-requirements-<기능명>.md` for full requirements.

요약:
1. 새 모델 위치, 이름
2. 새 엔진 위치, 함수 시그니처
3. 새 라우트 경로
4. 테스트 수
5. 핵심 비즈니스 규칙

## Existing Patterns to Follow
기존 코드에서 참고할 패턴 (모델, 엔진, 라우트 파일명).

## Completion Criteria
- [ ] 모든 FR 구현
- [ ] ruff check 0 errors
- [ ] pytest 전체 통과 (기존 + 신규)
- [ ] semgrep 통과
- [ ] convention.md 준수

## On Failure
- ruff 실패: 에러 메시지 읽고 수정
- pytest 실패: 실패 테스트 출력 읽고 수정
- 삼각 검증 실패: discrepancy-report.md 읽고 수정

## Completion Signal
When ALL criteria met, output exactly:
<promise>LOOP_COMPLETE</promise>
```

### 2단계: 실행

**방법 A: 셸 스크립트 (터미널에서 직접)**

Claude Code 세션 밖에서 실행한다. 스크립트가 `claude --print`를 nested 호출하므로 터미널에서 직접 실행해야 한다.

```bash
cd Workspace/renewal-review

PROMPT_FILE="docs/experiments/4-PROMPT-portfolio-aggregator.md" \
REQUIREMENTS_FILE="docs/experiments/4-requirements-portfolio-aggregator.md" \
bash scripts/self-correcting-loop.sh 5
```

- 첫 번째 인자: max iterations (기본 5)
- 환경변수 생략 시 experiment 3의 기본값 사용
- 로그: `docs/logs/loop-execution.log`

**방법 B: Skill 호출 (Claude Code 세션 안에서)**

Claude Code 세션 안에서 skill을 호출하면, 에이전트가 직접 루프를 오케스트레이션한다.

```
self-correcting-loop Skill을 사용해서 <기능명>을 구현해줘.
PROMPT: docs/experiments/<번호>-PROMPT-<기능명>.md
Requirements: docs/experiments/<번호>-requirements-<기능명>.md
```

이 방식에서는:
- Phase 1: 에이전트가 직접 코드 작성
- Phase 2: `ruff check`, `uv run pytest`, `semgrep scan` 직접 실행
- Phase 3: Task tool로 Agent B, Agent C를 subagent로 실행
- Phase 4: 모든 게이트 통과 시 완료 보고

### 3단계: 결과 확인

루프 완료 후 생성되는 파일:

| 파일 | 내용 |
|------|------|
| `docs/logs/loop-execution.log` | 전체 실행 로그 (반복 횟수, 시간, 각 phase 결과) |
| `docs/experiments/blind-review.md` | Agent B의 blind code review |
| `docs/experiments/discrepancy-report.md` | Agent C의 requirements vs code 비교 |

확인 사항:
- `LOOP_COMPLETE` 출력 여부
- 총 반복 횟수 (1~2회가 정상)
- Phase 2/3 실패 횟수와 원인
- 새로 생성된 코드 파일의 품질

---

## 삼각 검증이란

일반적인 품질 도구(ruff, pytest, semgrep)는 **구문과 구조**를 검사한다.
삼각 검증은 **의도(intent)**를 검사한다 — "코드가 요구사항과 일치하는가?"

```
Requirements (원본 요구사항)
        ↕ 비교
Code → Agent B (코드만 읽고 행동 기술) → Blind Review
        ↕ 비교
Agent C (Requirements vs Blind Review) → Discrepancy Report
```

- **Agent B**: 코드를 읽되 requirements는 보지 않음 → 편향 없는 행동 기술
- **Agent C**: Requirements와 B의 분석을 비교 → 불일치 발견
- 세 관점(요구사항, 코드, 독립 분석)이 일치하면 `TRIANGULAR_PASS`

---

## 실제 사례

### Experiment 3: Smart Quote Generator

```bash
PROMPT_FILE="docs/experiments/3-PROMPT-quote-generator.md" \
REQUIREMENTS_FILE="docs/experiments/3-requirements-quote-generator.md" \
bash scripts/self-correcting-loop.sh 5
```

결과: 1회 반복, 641초, 사람 개입 0회, 81/81 테스트 통과

### Experiment 4: Portfolio Risk Aggregator

```bash
PROMPT_FILE="docs/experiments/4-PROMPT-portfolio-aggregator.md" \
REQUIREMENTS_FILE="docs/experiments/4-requirements-portfolio-aggregator.md" \
bash scripts/self-correcting-loop.sh 5
```

---

## 트러블슈팅

### `claude` 명령어를 찾을 수 없음

셸 스크립트 방식은 `claude` CLI가 PATH에 있어야 한다.

```bash
which claude    # 경로 확인
claude --version
```

### nested claude 호출 차단

Claude Code 세션 안에서 셸 스크립트를 실행하면 `CLAUDECODE` 환경변수 때문에 nested 호출이 차단된다. 스크립트에 `unset CLAUDECODE`가 이미 포함되어 있지만, 직접 터미널에서 실행하는 것을 권장한다.

### Phase 2에서 pytest 실패가 반복됨

- 기존 테스트가 통과하는 상태에서 시작했는지 확인
- `uv sync --extra dev`로 의존성이 최신인지 확인
- 데이터 파일(`data/renewals.json`)이 존재하는지 확인 (없으면 `python data/generate.py`)

### Phase 3에서 TRIANGULAR_PASS가 안 나옴

- `docs/experiments/discrepancy-report.md`를 직접 읽고 어떤 요구사항이 누락/불일치인지 확인
- requirements 파일이 너무 모호하면 Agent C가 판단을 못 함 → requirements를 더 구체적으로 작성
- 피드백이 다음 반복에 전달되므로, 루프가 자동으로 수정 시도함

### max iterations에 도달했는데 미완료

- `docs/logs/loop-execution.log`에서 마지막 피드백 확인
- max iterations를 늘려서 재실행하거나
- 남은 이슈를 수동으로 수정 후 삼각 검증만 따로 실행:

```bash
REQUIREMENTS_FILE="docs/experiments/<번호>-requirements-<기능명>.md" \
bash scripts/triangular-verify.sh
```

---

## 파일 구조

```
renewal-review/
├── .claude/skills/self-correcting-loop/
│   └── SKILL.md                          ← Skill 정의 (Claude Code가 읽음)
├── scripts/
│   ├── self-correcting-loop.sh           ← 메인 루프 스크립트
│   └── triangular-verify.sh              ← 삼각 검증 스크립트
├── docs/experiments/
│   ├── <번호>-requirements-<기능명>.md   ← 요구사항 (삼각 검증 기준)
│   ├── <번호>-PROMPT-<기능명>.md         ← 에이전트 프롬프트
│   ├── blind-review.md                   ← Agent B 출력 (자동 생성)
│   └── discrepancy-report.md             ← Agent C 출력 (자동 생성)
└── docs/logs/
    └── loop-execution.log                ← 실행 로그 (자동 생성)
```
