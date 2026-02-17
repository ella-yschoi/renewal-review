# Renewal Review — Presentation Log

> 커밋마다 자동 기록. 각 엔트리의 Context / Result / Insight를 채워서 프레젠테이션 소스로 활용한다.
> **최신순 정렬** — 새 엔트리는 항상 맨 위에 추가한다.
>
> - **Context**: 이 커밋의 맥락과 의도 (왜 이 작업이 필요했는지)
> - **Result**: 결과 또는 변경 효과 (무엇이 달라졌는지)
> - **Insight**: 프레젠테이션에서 강조할 포인트 (청중이 기억할 한 문장)

---

### 2026-02-16 19:40 | `main` | `aea6692`

**fix: enable tag mode with track_progress and grant Bash access**

_1 file changed, 3 insertions(+), 4 deletions(-)_

> **Context**: Agent Dispatch 2차 실행(Issue #4)이 88턴, $3.33을 소비하고 성공적으로 완료되었지만 PR/브랜치/코멘트가 하나도 생성되지 않았다. 원인: `claude-code-action`의 `prompt:` 입력이 Agent Mode로 라우팅되면 branch/commit/PR/comment 인프라가 전부 비활성화된다. Agent가 만든 모든 결과물은 러너 종료 시 사라진다.
> **Result**: `track_progress: true` 추가로 Tag Mode를 강제하여 자동 브랜치 생성 → 커밋 → push → PR 링크 → 이슈 코멘트 체인이 활성화됨. 프롬프트 step 6도 "leave all files in the working tree"로 변경하여 action이 커밋을 담당하도록 수정.
> **Insight**: `claude-code-action`의 내부 모드 분기(Agent vs Tag)는 문서화되어 있지 않다 — 소스코드 `detector.ts`를 직접 분석해야 발견할 수 있었다. "행동은 성공했지만 결과가 없다"는 증상에서 인프라 레이어 문제를 의심하는 것이 핵심이었다.

---

### 2026-02-16 19:40 | `main` | `f0875a6`

**fix: grant Bash tool access and test health endpoint version**

_3 files changed, 6 insertions(+), 5 deletions(-)_

> **Context**: Agent Dispatch 1차 실행(Issue #3)에서 agent가 디렉토리 생성을 15회+ 시도(mkdir, touch, python os.makedirs, install -d 등)하며 전부 실패. `claude-code-action`은 Bash를 기본 차단하므로 파일 I/O(Read/Write/Edit)만 가능하고 쉘 명령은 불가능했다. Code Review Bot 테스트를 위해 health endpoint에 version 필드를 추가하여 PR #2 생성.
> **Result**: `claude_args: '--allowedTools "Bash,Edit,Read,Write,Glob,Grep" --disallowedTools "Bash(rm -rf:*),Bash(sudo:*)"'` 추가로 Bash 허용 (파괴적 명령은 차단). Code Review Bot이 PR #2에 자동 리뷰 코멘트 작성 — 첫 번째 완전 동작 확인.
> **Insight**: Agent에게 도구를 줄 때 "모두 허용 후 위험한 것 차단"이 "기본 차단 후 하나씩 허용"보다 실용적이다 — 예측 못한 도구 필요(mkdir, make, git)가 agent를 무한 루프에 빠뜨린다.

---

### 2026-02-16 19:40 | `main` | `41ec67a`

**feat: add agent-native CI/CD pipeline**

_9 files changed, 726 insertions(+), 235 deletions(-)_

> **Context**: Agent-Native Engineering 아티클의 3가지 핵심 패턴(Issue Dispatch, Code Review Bot, Task Decomposition)을 프로젝트에 적용. `.github/` 디렉토리가 없는 상태에서 처음부터 구축. 3-Tier Issue Templates(`one-shot`/`manageable`/`complex`), 2개의 GitHub Actions 워크플로우, 로컬 Task Decomposition 스크립트를 한 번에 생성.
> **Result**: `agent-dispatch.yml`(Issue → 자동 구현 → PR), `code-review.yml`(PR → 자동 리뷰), `decompose-task.sh`(로컬 진입점), Issue Templates 3종 생성. Self-Correcting Loop → Agentic Dev Pipeline으로 이름 변경. 가이드 문서 전면 개편.
> **Insight**: CI/CD 파이프라인의 핵심은 "자동화"가 아니라 "진입점의 다양화"다 — GitHub Issue, 로컬 스크립트(`--run`), 로컬 스크립트(`--dispatch`) 3가지 경로로 동일한 파이프라인에 진입할 수 있어야 팀 전체가 채택한다.

---

### 2026-02-16 19:36 | `main` | `154e4d7`

**chore: move hooks into project and register agentic-dev-pipeline skill**

_9 files changed, 339 insertions(+), 3 deletions(-)_

> **Context**: 에이전트 인프라(훅 6개, 스킬)가 로컬 머신의 홈 디렉토리에 흩어져 있어 repo 클론 시 재현 불가능했고, agentic-dev-pipeline 스킬은 공유할 방법이 없었다. 프레젠테이션에서 `.claude/` 디렉토리 구조를 한눈에 보여주려면 프로젝트 안에 통합 필요.
> **Result**: 6개 훅 → `.claude/hooks/`로 이동 + `settings.json` 등록, agentic-dev-pipeline → 별도 GitHub repo(`ella-yschoi/agentic-dev-pipeline`)로 분리 + 프로젝트 스킬 등록(`.claude/skills/agentic-dev-pipeline/SKILL.md`). `git clone` 한 번으로 훅 자동 적용, 스킬 설치 가능.
> **Insight**: Agent 인프라의 가치는 "만드는 것"이 아니라 "다른 사람이 클론 한 번으로 동일 환경을 재현할 수 있는 것"이다 — 훅은 프로젝트 안에, 범용 스킬은 별도 repo에 분리하면 이식성과 재사용성을 동시에 확보한다.

---

### 2026-02-16 14:15 | `main` | uncommitted

**feat: dashboard progress bar, account column split, account sorting, portfolio info banner**

_7 files changed, 185 insertions(+), 27 deletions(-)_

> **Context**: Dashboard에서 배치 리뷰 실행 시 스피너만 표시되어 브로커가 진행 상황을 알 수 없었고, 8,000건 정책 탐색에 Account 기준 정렬이 없었으며, Portfolio 페이지에 역할 설명이 부재. DB에도 `insured_name`/`account_id`가 JSON blob 안에만 있어 쿼리 불가.
> **Result**: Dashboard에 파란색 프로그레스 바(진행률 %/정책 수/ETA) 추가, Policy #와 Account 컬럼 분리, Dashboard·Portfolio 양쪽에 Account 정렬(▲/▼ 클릭), Portfolio에 보라색 안내 배너 추가. DB `raw_renewals`에 `insured_name`/`account_id` 탑레벨 컬럼 추가 및 re-seed.
> **Insight**: 프로그레스 바의 가치는 "완료까지 기다리게 하는 것"이 아니라 "기다릴 수 있다는 확신을 주는 것"이다 — ETA와 정책 수를 보여주면 브로커가 다른 작업과 멀티태스킹할 수 있다.

---

### 2026-02-16 13:11 | `main` | uncommitted

**refactor: generalize self-correcting-loop skill to be project-agnostic**

_5 files created at ~/.agents/skills/, 3 files deleted from project, 1 guide rewritten_

> **Context**: Self-correcting loop 스킬이 renewal-review 전용으로 하드코딩(ruff/pytest/semgrep, `app/`, `docs/experiments/`)되어 있어 다른 프로젝트에서 사용 불가능. 실험 4에서 "PROMPT.md만 바꾸면 어떤 기능이든"을 증명했지만, 스킬 자체가 특정 프로젝트에 종속되어 있었다. 이를 Python/Node/Rust/Go 어떤 프로젝트에서든 자동 감지 기반으로 동작하도록 범용화.
> **Result**: `detect-project.sh`(9개 감지 함수)를 공유 라이브러리로 추출, 양 스크립트가 source하여 lint/test/security 명령을 자동 결정. ENV var 오버라이드 우선, Makefile/package.json/도구 존재 순서로 fallback. 출력 경로를 `$OUTPUT_DIR`로 통일하여 프로젝트 디렉토리 구조에 무의존. renewal-review에서 자동 감지 검증 완료(Python, make lint, make test, semgrep).
> **Insight**: 도구의 범용성은 "하드코딩을 추상화하는 것"이 아니라 "감지 우선순위를 설계하는 것"이다 — ENV → Makefile → package.json → 도구 존재 확인 순서가 사용자의 명시적 의도를 존중하면서 자동화를 제공한다.

---

### 2026-02-16 03:34 | `main` | uncommitted

**refactor: major 8-phase overhaul — DB persistence, rule expansion, broker workflow, analytics**

_30+ files changed_

> **Context**: DB에 아무것도 저장되지 않아 앱 재시작 시 모든 결과 소실되는 핵심 문제를 해결하면서, 브로커 관점의 워크플로우 추적, 규칙 기반 리스크 판별 확장, UI 개편을 동시에 진행. 8개 Phase를 의존성 그래프에 따라 순차 실행하여 100→117 테스트 유지하면서 완료.
> **Result**: Write-through DB 전략(메모리 + DB 동시 저장), 23개 DiffFlag(+8 신규: violations, SR-22, 25세 미만, coverage gap, notes 키워드 4종), 브로커 워크플로우(contacted/quote/reviewed 체크박스), Analytics 브로커 지표 카드, Quote Generator 페이지 제거 → Review Detail 인라인 통합. DB 실패 시 graceful degradation(log warning, 정상 동작).
> **Insight**: 대규모 리팩토링에서 핵심은 Phase 간 의존성을 명확히 하고 각 Phase 완료 후 테스트 검증을 반복하는 것 — 117개 테스트가 매 단계 안전망 역할을 하여 8개 Phase를 연속으로 실행할 수 있었다.

---

### 2026-02-15 18:06 | `main` | uncommitted

**feat: implement per-task LLM model routing based on Langfuse benchmark**

_5 files changed (config, openai client, anthropic client, routing client, design-doc)_

> **Context**: 실험 5에서 3개 모델을 정량 비교했지만, 프로덕션 코드는 여전히 단일 모델만 사용 중이었다. 벤치마크 결과("작업 복잡도에 따라 모델 격차가 달라진다")를 코드에 반영하여 task별 최적 모델을 자동 선택하도록 구현.
> **Result**: `risk_signal_extractor` → Sonnet (복합 추론, 정확도 0.90), 나머지 3개 → Haiku (동급 정확도, 2배 빠르고 10배 저렴). `LLMClient`가 `trace_name`으로 라우팅. `LLMPort` 인터페이스 변경 없음 (adaptor에서 흡수). `RR_LLM_PROVIDER` 환경변수 제거.
> **Insight**: 벤치마크의 가치는 숫자 자체가 아니라 "숫자를 코드에 반영하는 것"이다. 실험 → 결론 → 구현까지 이어져야 데이터 기반 의사결정이 완성된다.

---

### 2026-02-15 17:03 | `main` | uncommitted

**feat: add regulatory signal (SR-22) to risk_signal_extractor mock**

_1 file changed_

> **Context**: 프롬프트에 `regulatory`가 signal type으로 정의되어 있지만 mock에서 테스트되지 않는 갭이 있었다. `adaptor/llm/` 파일 수정이므로 CLAUDE.md의 트리거 조건에 따라 `/insurance-domain` 스킬을 참조하여, ACORD 표준 기반의 도메인 지식으로 signal 내용을 작성.
> **Result**: SR-22 filing(주 정부 요구 고위험 증명서) signal 추가. 스킬의 Core Terminology와 prompts.py의 regulatory 정의를 교차 참조하여, generic하지 않은 도메인 특화 내용으로 작성됨. 100/100 테스트 유지.
> **Insight**: Custom Skill이 "문서에만 있는 지식"이 아니라 "코드 변경 시 자동으로 참조되는 지식"으로 작동하려면, CLAUDE.md의 트리거 조건(L1)과 스킬 내용(L2)이 파이프라인으로 연결되어야 한다 — 이번 작업에서 그 L1→L2 흐름이 설계 의도대로 작동함을 확인.

---

### 2026-02-15 14:51 | `main` | uncommitted

**refactor: align LLM prompts, mock responses, and sample data with ACORD standards**

_10 files changed_

> **Context**: ACORD 표준 갭 분석 결과를 CLAUDE.md + Custom Skill 인프라로 구축한 뒤, 실제 코드에 도메인 지식을 반영하는 작업. LLM 프롬프트 4개가 보험 업계 표준 용어를 사용하도록 정렬하고, mock 응답의 버그(`property_condition`이 프롬프트 enum에 없는 값)를 수정하고, 샘플 데이터의 endorsement code를 ACORD 표준 form number(`HO 04 61`, `HO 04 95`)로 교체.
> **Result**: 프롬프트가 ACORD 커버리지 코드(BI, PD, UM, HO 04 xx, PP 03 xx)를 직접 참조하고, 보호 필드 목록이 명시되어 LLM이 liability 감소를 추천하는 것을 구조적으로 방지. mock의 잠재 validation 버그 해결. 샘플 데이터가 데모에서 업계 표준 form number로 표시됨. 100/100 테스트 유지.
> **Insight**: 도메인 지식의 가치는 문서에 정리하는 것이 아니라 코드가 실행하는 결정에 스며드는 것 — ACORD form number가 프롬프트에 있으면 LLM이 "HO 04 95 제거"라고 구체적으로 설명하고, 보호 필드 목록이 프롬프트에 있으면 LLM이 liability 감소를 추천하지 않는다.

---

### 2026-02-15 12:39 | `experiment/portfolio-aggregator` | uncommitted

**refactor: hexagonal architecture + design patterns (Enum, Config, Immutability, DI)**

_45 files changed, 765 insertions(+), 578 deletions(-)_

> **Context**: BMS 교체 가능성을 대비하여 도메인 로직이 외부 시스템(BMS 데이터 포맷, LLM 프로바이더, DB)에 의존하지 않도록 헥사고날 아키텍처를 적용. 동시에 코드베이스 전반의 일관성을 높이기 위해 4가지 디자인 패턴(Enum 중앙화, Config 중앙화, Immutability, DI)을 함께 적용. 기존 `engine/`, `models/`, `routes/`, `llm/` 플랫 구조에서 `domain/`, `application/`, `api/`, `adaptor/`, `infra/` 5-레이어 구조로 전환. 추가로, LLM 응답을 `dict[str, Any]`에서 `.get()`으로 수동 파싱하던 패턴을 Pydantic 스키마 검증(`adaptor/llm/schemas.py`)으로 전환하여 타입 안전성과 에러 핸들링 일관성을 확보.
> **Result**: 의존성 방향 `api/ → application/ → domain/ ← adaptor/` 확립. domain/에서 외부 레이어 import 0건 달성. LLM 응답 4종(risk_signal, endorsement, review_summary, quote_personalization)에 대한 Pydantic 검증 스키마 도입 — `model_validate()` + `ValidationError` fallback으로 기존 `.get()` 방어 코드 제거. malformed 응답 테스트 4건 추가. 8단계 리팩토링 전 과정에서 100/100 테스트 유지. ruff 0, semgrep 0, 경계 위반 0건.
> **Insight**: 헥사고날 아키텍처의 가치는 "현재 코드가 예뻐지는 것"이 아니라 "미래의 변경이 한 레이어에서 끝나는 것" — BMS가 바뀌면 `adaptor/persistence/`에 새 loader 하나, LLM 프로바이더가 바뀌면 `adaptor/llm/`에 새 클라이언트 하나 추가하면 끝. Pydantic 스키마는 LLM 응답의 "계약"을 명시하여, 프롬프트를 바꿔도 응답 형식이 맞는지 자동 검증한다.

---

### 2026-02-15 12:03 | `main` | `9d71b37`

**refactor: rollback coverage similarity and portfolio LLM points**

> **Context**: LLM 적용 포인트 6개를 "왜 여기에 LLM을 썼는가" 관점에서 재평가. 4가지 기준(입력 형태, 의미 해석 필요성, Rule 대안 한계, 출력 품질 차이)으로 각 포인트를 분석한 결과, Coverage Similarity(boolean 비교)와 Portfolio Analysis(100% 구조화된 입력 + 이미 잘 작동하는 JS rule-based fallback)는 LLM이 실질적 가치를 더하지 않음을 확인.
> **Result**: LLM 포인트 6개 → 4개. 432줄 삭제하면서 기능 손실 0 — 기존 rule-based 로직이 이미 해당 케이스를 커버. Portfolio 페이지는 rule-based verdict/action items만 표시 (sparkle 제거). User-facing 출력 기준 LLM 비중 58% → 33%로 정리.
> **Insight**: LLM 적용의 핵심은 "어디에 쓸 수 있는가"가 아니라 "어디에 안 쓸 것인가" — 구조화된 입력의 결정적 판단에 LLM을 넣는 건 비용만 추가하고 정확도는 같거나 떨어진다. "이것도 LLM으로"의 유혹을 이겨내는 것이 좋은 하이브리드 설계.

---

### 2026-02-15 03:45 | `experiment/portfolio-aggregator` | `1cb5e26`

**improve: unify button layouts and fix portfolio selection reset**

> **Context**: 데모 리허설 중 발견된 UX 문제들 — insight 페이지 200건 비교는 LLM 비용 과다, portfolio 테이블 공간 낭비 + 새로고침 시 이전 선택이 남아있음, Quality Check 결과가 제목과 분리.
> **Result**: 3개 페이지 레이아웃 통일. Compare Sample (100) 단일 버튼, 테이블 full-width, 새로고침 시 선택 초기화 (페이지네이션은 유지), Quality Check 제목-정확도 한 줄 배치.
> **Insight**: "사용자가 예상하는 상태"와 "실제 상태"의 불일치는 기능 버그보다 더 큰 혼란을 준다 — 새로고침했는데 이전 선택이 남아있는 건 기능이 아니라 버그.

---

### 2026-02-15 03:15 | `experiment/portfolio-aggregator` | `b22a258`

**fix: broker-friendly terminology audit and analytics key mismatch**

> **Context**: 데모 UI에 "Batch Run", "Job ID", "Eval", "LLM", "Delta", "Latency" 같은 개발자 용어가 산재. analytics 페이지는 risk_distribution 키 불일치로 500 에러. 브로커 데모 전에 전체 용어 정리 필요.
> **Result**: 6개 템플릿 전체 감사 완료. 모든 라벨이 브로커가 즉시 이해할 수 있는 단어로 변환되고, 시간 표시가 ms에서 초 단위로 통일됨. analytics 500 에러 해결.
> **Insight**: UI 용어 하나가 "이건 내가 쓰는 도구" vs "이건 개발자의 도구"를 결정한다 — 기술적 정확성보다 사용자 인지 비용이 데모 성패를 가른다.

---

### 2026-02-15 02:30 | `experiment/portfolio-aggregator` | `1e02a34`

**feat: broker-friendly portfolio modal, nav UX improvements, and bug fixes**

> **Context**: 자가 수정 루프가 만든 Portfolio Aggregator 백엔드는 정확하지만, UI가 raw JSON 수준이라 브로커가 "이게 문제인가? 뭘 해야 하나?"를 바로 판단할 수 없었음. AI가 코드를 생성하는 것과 그 결과물이 실제 사용자에게 가치 있는 것 사이의 간극을 메우는 작업.
> **Result**: 모달이 한눈에 건강 상태(verdict), 권고 사항(bundle/flag 액션), 우선순위별 체크리스트(action items)를 보여줌. 페이지 간 선택 유지, 네비게이션 워크플로우 정렬까지 완료하여 데모 가능 수준 도달.
> **Insight**: AI가 생성한 코드의 진짜 완성은 "돌아간다"가 아니라 "사용자가 바로 행동할 수 있다" — 백엔드 자동 생성 후에도 UX 레이어는 사람의 판단이 필요하다.

---

### 2026-02-15 01:32 | `experiment/portfolio-aggregator` | uncommitted

**feat: Langfuse LLM provider benchmark — OpenAI vs Anthropic (v1 + v2)**

> **Context**: 프로젝트에서 LLM provider를 선정해야 하는데, "어떤 모델이 좋은지"를 감이 아닌 데이터로 판단하고 싶었다. Langfuse Datasets + Experiments SDK를 활용해 같은 테스트 데이터를 gpt-4o-mini, claude-sonnet, claude-haiku 세 모델에 동일하게 돌리고, 정확도(key_match), 속도(latency), 토큰 효율성을 자동 스코어링하는 파이프라인을 구축했다. 3개 보험 분석 작업(리스크 시그널 추출, 보증 조항 비교, 보장 동등성 판단) x 5개 테스트 케이스 x 3개 모델 = 총 45회 호출. v1 실험 후 프롬프트를 개선(signal 그룹핑 규칙, 빈 입력 처리, JSON 순수성)하여 v2까지 실행.
> **Result**: (1) Sonnet이 정확도 1위(0.97)지만 Haiku가 90% 수준(0.93)을 1/10 가격 + 동일 속도로 달성 — 가성비 최적은 Haiku. (2) 프롬프트 v2에서 예상치 못한 발견: signal 그룹핑 규칙을 추가했더니 Sonnet 0.90→0.80, Haiku 0.80→0.70으로 하락. 모델이 규칙을 잘 따랐지만 expected_output이 새 규칙을 반영하지 않아서 "정답지가 틀린" 상황이 발생. (3) gpt-4o-mini는 명시적 규칙("빈 입력 = 삭제")에 가장 잘 반응(0.70→0.80), Anthropic 모델은 암묵적 추론으로 이미 처리하고 있었음.
> **Insight**: LLM 평가에서 가장 어려운 건 프롬프트 엔지니어링이 아니라 "정답을 정의하는 것"이다 — 프롬프트를 개선했더니 점수가 떨어졌고, 원인은 모델이 아니라 정답지에 있었다.

---

### 2026-02-15 00:45 | `experiment/portfolio-aggregator` | `de21fc1`

**feat: add Portfolio Risk Aggregator — cross-policy analysis via self-correcting loop**

> **Context**: 실험 3에서 검증한 자가 수정 루프를 "한 번 쓰고 버리는 도구"가 아닌 "재사용 가능한 파이프라인"으로 증명하기 위해, 완전히 다른 도메인의 기능(교차 정책 분석)을 동일 파이프라인으로 구현. PROMPT.md와 requirements.md만 교체하고 Skill 오케스트레이션(방법 B)으로 실행.
> **Result**: 1회 반복, 사람 개입 0회, 89/89 테스트 통과, TRIANGULAR_PASS. 번들 분석, 중복 보장 탐지, 총 노출 계산, 보험료 집중도 위험 — 4가지 교차 분석 기능이 자동 구현됨.
> **Insight**: 파이프라인의 진짜 가치는 두 번째 실행에서 나온다 — "이 파이프라인을 만들었습니다"가 아니라 "이 파이프라인에 기능을 넣으면 나옵니다"가 설득력.

---

### 2026-02-14 22:30 | `experiment/portfolio-aggregator` | `41c0e85`

**chore: set up experiment 4 — portfolio aggregator requirements, prompt, and team guide**

> **Context**: 실험 3에서 만든 자가 수정 루프가 "한 번 쓰고 버리는 도구"가 아니라 "팀이 반복 사용하는 파이프라인"임을 증명하기 위해, 완전히 다른 도메인(교차 정책 위험 분석)의 기능을 준비. 스크립트를 파라미터화하고 팀 가이드를 작성하여 개인 실험에서 팀 도구로 전환.
> **Result**: PROMPT.md + requirements.md 두 파일만 작성하면 누구나 자가 수정 루프를 돌릴 수 있는 환경 완성. 스크립트는 환경변수로 경로를 주입받아 실험 번호에 독립적.
> **Insight**: 파이프라인의 가치는 첫 번째 실행이 아니라 두 번째 실행에서 증명된다 — 설정 변경 없이 새 기능을 투입할 수 있으면 그것이 진짜 자동화.

---

### 2026-02-14 14:45 | 실험 3 최종 비교 — 자동 루프 vs 수동 대조군

**Self-Correcting Loop: 641초 자동 vs 549초 수동, 사람 개입 0 vs 1**

> **Context**: 동일한 Smart Quote Generator 과제를 자동 루프(`self-correcting-loop.sh`)와 수동 오케스트레이션(Claude Code 세션)으로 각각 실행. 자동은 PROMPT.md → claude --print → ruff/pytest/semgrep → triangular-verify.sh 전체 파이프라인을 사람 없이 실행. 수동은 개발자가 코드 작성, 품질 게이트, 삼각 검증을 순차적으로 직접 오케스트레이션.
> **Result**: 자동 641초(1회 반복, 사람 개입 0), 수동 549초(삼각 검증 재실행 1회, 사람 개입 1). 자동이 92초 느렸지만 완전 자율 완료. 수동은 Agent B가 잘못된 모듈을 리뷰하여 프롬프트 수정 후 재실행 필요.
> **Insight**: 자동화의 가치는 속도가 아니라 **신뢰성** — 밤에 기능 3개를 큐에 넣고, 아침에 검증된 코드를 리뷰한다. 사람이 실수를 감지하고 수정하는 비용은 과제가 복잡해질수록 기하급수적으로 증가한다.

---

### 2026-02-14 15:30 | `experiment/self-correcting-loop` | `pending`

**feat: implement Smart Quote Generator — auto/home alternative quotes**

> **Context**: Self-Correcting Loop 실험의 Phase 1 (구현 단계). 요구사항 문서(3-requirements-quote-generator.md)의 FR-1~FR-9를 하나의 반복에서 완전 구현. 기존 renewal-review 파이프라인이 "위험 탐지"까지만 했다면, Quote Generator는 "탐지된 위험에 대한 대안 제시"를 자동화하는 다음 단계.
> **Result**: Auto 3전략(raise_deductible 10%, drop_optional 4%, reduce_medical 2.5%) + Home 3전략(raise_deductible 12.5%, drop_water_backup 3%, reduce_personal_property 4%) 구현. 보호 제약(liability 필드 5개 불변) 적용. ruff 0 errors, 81/81 tests passed, semgrep 0 findings. 모든 파일 300줄 미만.
> **Insight**: 전략 패턴으로 전략별 독립 함수를 리스트에 등록하면, 새 전략 추가가 함수 하나 + 리스트 등록 한 줄로 끝남. 확장성과 테스트 용이성 모두 확보.

---

### 2026-02-14 14:30 | `experiment/self-correcting-loop` | (initial setup)

**chore: add self-correcting loop scripts and experiment docs**

> **Context**: 실험 1(병렬 협업)과 실험 2(삼각 검증)를 하나의 자동화 파이프라인으로 통합하는 실험 3의 준비 단계. Ralph Wiggum 반복 루프 패턴에 삼각 검증을 내장하여, PROMPT.md 하나로 기능 정의 → 구현 → 품질 검증 → 의도 검증 → 자가 수정까지 사람 개입 없이 완료하는 파이프라인을 설계.
> **Result**: `triangular-verify.sh`(Agent B+C 순차 실행, PASS/FAIL 판정)과 `self-correcting-loop.sh`(4-phase while 루프, max-iterations 안전장치, 피드백 전달) 작성 완료. 실험 과제는 Smart Quote Generator — 보험 대안 견적 자동 생성.
> **Insight**: 실험 2에서 삼각 검증이 "이슈를 발견"했다면, 실험 3은 "발견 즉시 자동 수정"까지 닫는다. 핵심은 실패 메시지를 다음 반복의 입력으로 전달하는 피드백 루프 — 완벽한 첫 시도 대신 반복을 통한 수렴.

---

### 2026-02-14 00:47 | `main` | 삼각 검증 실험

**실험 C: 삼각 검증(Triangular Verification)으로 코드 품질 검증**

> **Context**: 실험 A/B는 "얼마나 빠르게 만드는가"를 비교했다. 실험 C는 "만든 코드가 요구사항대로인가"를 검증한다. 3개 에이전트를 컨텍스트 격리하여 코드→설명→요구사항 역추적 방식으로 "의도 불일치"를 자동 탐지.
> **Result**: ruff+pytest+semgrep이 0개 잡은 상태에서, 삼각 검증은 Intent Mismatch 2건(FIFO 100건 미구현, 타임존 불일치), Missing Feature 2건, Extra Feature 3건을 추가 발견. Precision 78%. 소요 시간 ~19분.
> **Insight**: 기존 도구는 "코드가 깨졌는가"만 체크한다. 삼각 검증은 "코드가 의도대로인가"를 체크한다. FIFO 100건 제한이 빠진 건 테스트에도, 린터에도, 보안 스캐너에도 안 잡히지만 — 요구사항 문서와 코드 설명을 삼각 비교하면 바로 드러난다.

---

### 2026-02-14 00:20 | 실험 비교 분석

**SubAgent vs Agent Teams — 최종 비교**

> **Context**: 동일 과제를 두 가지 오케스트레이션 모델로 수행한 결과 비교. SubAgent는 Task tool 기반 fire-and-forget, Teams는 TeamCreate/TaskCreate 기반 구조적 협업.
> **Result**: 시간(354 vs 318초), 코드량(334 vs 335줄), 테스트(73/73) 모두 거의 동일. 차이는 병렬화 전략과 오케스트레이션 오버헤드.
> **Insight**: 두 방식 모두 6분 안에 production-ready 모듈을 생성했다. **차이는 "만드는 속도"가 아니라 "조율하는 방식"에 있다.** 소규모는 SubAgent(오버헤드 적음, 병렬화 자유), 대규모는 Teams(태스크 추적, 의존성 관리, 확장성)가 유리.

---

### 2026-02-14 00:10 | `experiment/teams-analytics` | `15f7545`

**feat: add analytics module via agent teams experiment**

> **Context**: SubAgent vs Agent Teams 비교 실험의 두 번째 실행. 동일 과제를 TeamCreate + TaskCreate/TaskUpdate + SendMessage 기반 Agent Teams 방식으로 구현. 3인 팀(modeler, router, tester)을 순차 스폰하여 의존성 기반으로 작업 진행.
> **Result**: 318초(~5분)에 동일한 모듈 완성. 73/73 테스트 통과. ruff 수정 0건 — 첫 시도에 클린. 태스크 자동 완료 마킹도 정상 동작.
> **Insight**: Agent Teams는 태스크 의존성(blockedBy)이 명시적이라 "누가 뭘 기다리는지"가 투명하다. 하지만 이 실험 규모(~300줄)에서는 순차 스폰 오버헤드가 병렬화 이점을 상쇄. 대규모 프로젝트에서 팀원 수를 늘릴 때 진가가 나올 구조.

---

### 2026-02-14 00:00 | `experiment/subagent-analytics` | `17b2756`

**feat: add analytics module via subagent experiment**

> **Context**: SubAgent vs Agent Teams 비교 실험의 첫 번째 실행. 동일 과제(Batch Monitoring 모듈 추가)를 SubAgent 4단계 파이프라인(리서치→모델+서비스→라우트+main→테스트)으로 구현. 2단계와 3단계를 병렬 디스패치하여 시간 단축.
> **Result**: 354초(~6분)에 모델 3종 + 서비스 + API 2개 + 테스트 5개 완성. 73/73 테스트 통과. ruff 수정 8건 포함. 기존 코드 패턴을 정확히 따르는 코드 생성.
> **Insight**: SubAgent 방식의 강점은 오케스트레이터가 "무엇을 만들지"를 구체적으로 지시할 수 있다는 점 — 인터페이스 스펙(필드명, 시그니처)을 프롬프트에 명시하면 의존성 없이 병렬 작업이 가능하다. 6분 만에 production-ready 모듈이 나온 것은 리서치→구현 파이프라인이 잘 동작한 결과.
