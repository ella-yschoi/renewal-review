# Self-Correcting Agent Loop — 팀 가이드

이 프로젝트는 **글로벌 self-correcting-loop 스킬**을 사용한다.
스킬은 `~/.agents/skills/self-correcting-loop/`에 설치되어 있으며, **Python/Node/Rust/Go 어떤 프로젝트에서든** 사용 가능하다.

기능 요구사항을 PROMPT.md 하나로 정의하면, AI가 구현 → 품질 검증 → 의도 검증 → 자가 수정까지 **사람 개입 없이** 반복 실행한다.

---

## 스킬 위치

```
~/.agents/skills/self-correcting-loop/
├── SKILL.md                ← Skill 정의 (Claude Code가 읽음)
├── detect-project.sh       ← 프로젝트 자동 감지 라이브러리
├── self-correcting-loop.sh ← 메인 루프 스크립트
├── triangular-verify.sh    ← 삼각 검증 스크립트
└── PROMPT-TEMPLATE.md      ← 범용 PROMPT 템플릿
```

## 이 프로젝트에서 자동 감지되는 설정

`detect-project.sh`가 프로젝트 루트의 파일 구조를 분석하여 린트/테스트/보안 명령을 자동 결정한다. 환경변수로 오버라이드 가능.

| 항목 | 감지 결과 |
|------|----------|
| Project Type | Python (`pyproject.toml`) |
| Lint | `make lint` (Makefile target) |
| Test | `make test` (Makefile target) |
| Security | `semgrep scan --config auto --quiet app/` |
| Source dirs | `app/` |
| Instruction files | `CLAUDE.md`, `.claude/rules/conventions.md` |
| Design docs | `docs/design-doc.md` |

---

## 전제 조건

### 도구

| 도구 | 용도 | 설치 확인 |
|------|------|-----------|
| Claude Code | AI 코딩 + Skill 실행 | `claude --version` |
| 린트 도구 | 코드 품질 (자동 감지) | `ruff --version` / `eslint --version` 등 |
| 테스트 도구 | 테스트 (자동 감지) | `pytest --version` / `npm test` 등 |
| 보안 스캐너 | SAST (optional, 자동 감지) | `semgrep --version` (없으면 skip) |

### 프로젝트 설정 (이 프로젝트)

```bash
cd ~/Workspace/renewal-review
uv sync --extra dev          # 의존성 설치
uv run pytest -q             # 기존 테스트 통과 확인
ruff check app/ tests/       # 린트 클린 확인
```

### `.gitignore` 설정

루프 아티팩트가 실수로 커밋되지 않도록 `.gitignore`에 추가한다:

```
.self-correcting-loop/
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
│  Phase 2: 품질 게이트 (자동 감지)       │
│    lint → test → security (순차)        │
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
- 안전장치 — `MAX_ITERATIONS`로 무한 루프 방지 (기본 5회)
- 점진적 수렴 — 대부분 1~2회 반복 내 완료

---

## 환경변수 레퍼런스

| Variable | Default | 설명 |
|----------|---------|------|
| `PROMPT_FILE` | **(필수)** | PROMPT.md 경로 |
| `REQUIREMENTS_FILE` | **(필수)** | 요구사항 문서 경로 |
| `OUTPUT_DIR` | `.self-correcting-loop/` | 아티팩트 출력 디렉토리 |
| `LINT_CMD` | (auto-detect) | 린트 명령 (`"true"`로 설정하면 skip) |
| `TEST_CMD` | (auto-detect) | 테스트 명령 (`"true"`로 설정하면 skip) |
| `SECURITY_CMD` | (auto-detect) | 보안 스캔 명령 (`""`로 설정하면 skip) |
| `SRC_DIRS` | (auto-detect) | 소스 디렉토리 |
| `BASE_BRANCH` | `main` | git diff 기준 브랜치 |
| `MAX_ITERATIONS` | `5` | 최대 반복 횟수 |

---

## 사용법

### 1단계: 파일 두 개 작성

**requirements 파일** — 삼각 검증의 기준이 되는 기능 요구사항.

```markdown
# <기능명> — Requirements

## Functional Requirements

### FR-1: ...
### FR-2: ...

## Non-Functional Requirements
- 프로젝트 컨벤션 준수
- 기존 테스트 전부 통과
- 린트 0 errors
- 파일당 300줄 미만
```

**PROMPT 파일** — 에이전트에게 전달하는 구현 지시서. `~/.agents/skills/self-correcting-loop/PROMPT-TEMPLATE.md`를 복사하여 작성.

### 2단계: 실행

**방법 A: 셸 스크립트 (터미널에서 직접)**

Claude Code 세션 밖에서 실행한다. 스크립트가 `claude --print`를 nested 호출하므로 터미널에서 직접 실행해야 한다.

```bash
cd ~/Workspace/renewal-review

PROMPT_FILE="docs/experiments/4-PROMPT-portfolio-aggregator.md" \
REQUIREMENTS_FILE="docs/experiments/4-requirements-portfolio-aggregator.md" \
bash ~/.agents/skills/self-correcting-loop/self-correcting-loop.sh 5
```

- 첫 번째 인자: max iterations (기본 5)
- `PROMPT_FILE`, `REQUIREMENTS_FILE`은 필수
- 로그: `.self-correcting-loop/loop-execution.log`

환경변수 오버라이드 예시:

```bash
PROMPT_FILE="PROMPT.md" \
REQUIREMENTS_FILE="requirements.md" \
LINT_CMD="ruff check app/ tests/" \
TEST_CMD="uv run pytest -q" \
OUTPUT_DIR="docs/experiments" \
bash ~/.agents/skills/self-correcting-loop/self-correcting-loop.sh
```

**방법 B: Skill 호출 (Claude Code 세션 안에서)**

Claude Code 세션 안에서 skill을 호출하면, 에이전트가 직접 루프를 오케스트레이션한다.

```
self-correcting-loop Skill을 사용해서 <기능명>을 구현해줘.
PROMPT: docs/experiments/<번호>-PROMPT-<기능명>.md
Requirements: docs/experiments/<번호>-requirements-<기능명>.md
```

이 방식에서는:
- Phase 1: 에이전트가 직접 코드 작성
- Phase 2: 자동 감지된 lint/test/security 명령 직접 실행
- Phase 3: Task tool로 Agent B, Agent C를 subagent로 실행
- Phase 4: 모든 게이트 통과 시 완료 보고

### 3단계: 결과 확인

루프 완료 후 `$OUTPUT_DIR/` (기본: `.self-correcting-loop/`)에 생성되는 파일:

| 파일 | 내용 |
|------|------|
| `loop-execution.log` | 전체 실행 로그 (반복 횟수, 시간, 각 phase 결과) |
| `feedback.txt` | 마지막 반복의 피드백 (성공 시 삭제됨, 실패 시 디버깅용) |
| `blind-review.md` | Agent B의 blind code review |
| `discrepancy-report.md` | Agent C의 requirements vs code 비교 |

확인 사항:
- `LOOP_COMPLETE` 출력 여부
- 총 반복 횟수 (1~2회가 정상)
- Phase 2/3 실패 횟수와 원인
- 새로 생성된 코드 파일의 품질

---

## 삼각 검증이란

일반적인 품질 도구(lint, test, security)는 **구문과 구조**를 검사한다.
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

삼각 검증만 단독 실행:

```bash
REQUIREMENTS_FILE="docs/experiments/<번호>-requirements-<기능명>.md" \
bash ~/.agents/skills/self-correcting-loop/triangular-verify.sh
```

---

## 실제 사례

### Experiment 3: Smart Quote Generator

```bash
PROMPT_FILE="docs/experiments/3-PROMPT-quote-generator.md" \
REQUIREMENTS_FILE="docs/experiments/3-requirements-quote-generator.md" \
bash ~/.agents/skills/self-correcting-loop/self-correcting-loop.sh 5
```

결과: 1회 반복, 641초, 사람 개입 0회, 81/81 테스트 통과

### Experiment 4: Portfolio Risk Aggregator

```bash
PROMPT_FILE="docs/experiments/4-PROMPT-portfolio-aggregator.md" \
REQUIREMENTS_FILE="docs/experiments/4-requirements-portfolio-aggregator.md" \
bash ~/.agents/skills/self-correcting-loop/self-correcting-loop.sh 5
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

### Phase 2에서 품질 게이트 실패가 반복됨

- 기존 테스트가 통과하는 상태에서 시작했는지 확인
- 감지된 명령이 예상과 맞는지 확인:
  ```bash
  source ~/.agents/skills/self-correcting-loop/detect-project.sh && print_detected_config
  ```
- 환경변수 오버라이드로 명확히 지정: `LINT_CMD="..."`, `TEST_CMD="..."`

### Phase 3에서 TRIANGULAR_PASS가 안 나옴

- `$OUTPUT_DIR/discrepancy-report.md`를 직접 읽고 어떤 요구사항이 누락/불일치인지 확인
- requirements 파일이 너무 모호하면 Agent C가 판단을 못 함 → requirements를 더 구체적으로 작성
- 피드백이 다음 반복에 전달되므로, 루프가 자동으로 수정 시도함

### 잘못된 도구가 감지됨

환경변수로 오버라이드: `LINT_CMD`, `TEST_CMD`, `SECURITY_CMD`

### max iterations에 도달했는데 미완료

- `$OUTPUT_DIR/loop-execution.log`에서 마지막 피드백 확인
- max iterations를 늘려서 재실행하거나
- 남은 이슈를 수동으로 수정 후 삼각 검증만 따로 실행

---

## 상세 문서

스킬의 전체 문서(지원 언어, 감지 우선순위, 트러블슈팅 등)는 다음을 참조:
`~/.agents/skills/self-correcting-loop/SKILL.md`
