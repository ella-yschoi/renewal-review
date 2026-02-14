# Agent-Native Project Delivery: Renewal Review

## Overview

Insurance renewal review pipeline — 8,000건 보험 갱신 정책을 rule-based + LLM hybrid로 심사하는 시스템.
Agent-native 워크플로우로 **일주일 분량 작업을 하루에 완료**한 경험을 보여준다.

---

## 1. Setup — Agent가 잘 일할 수 있는 환경 만들기

Agent-native의 핵심은 agent에게 코드를 맡기는 것이 아니라, **agent가 잘 일할 수 있는 환경을 먼저 만드는 것**.

### Rulesets

| 파일 | 역할 |
|------|------|
| `CLAUDE.md` | Agent 행동 규칙 — no docstrings, minimal diffs, read before write |
| `convention.md` | 코드 스타일 + 프로세스 규칙 — 300줄 제한, 브랜치 네이밍, 커밋 컨벤션 |

Agent는 매 작업 전 이 파일을 읽고 규칙을 따름. 아티클에서 말하는 "agents are good at reading rules" 그대로.

### Quality Gates (Tests + Linters + Hooks)

| 도구 | 역할 |
|------|------|
| **pytest** (68 tests) | Agent의 reward signal — 통과할 때까지 반복 |
| **Hypothesis** | Property-based testing — 엣지 케이스 자동 탐색 |
| **Ruff** | Lint + format — code slop 방지 |
| **Gitleaks** | Secret detection — API 키 커밋 차단 |
| **Semgrep** | SAST 보안 스캐닝 — 보안 취약점 자동 탐지 |

Pre-commit hook으로 묶어서, **커밋 시점에 자동으로 전부 실행**. Agent가 이 게이트를 통과하지 못하면 커밋 자체가 불가.

### Parallel Workspace

Git worktrees로 병렬 작업 공간 준비:
- `wt-feat-1` — Frontend 작업
- `wt-feat-2` — Backend 개선
- `wt-research` — 리서치 전용

한 브랜치에서 작업하면서 다른 브랜치 작업을 동시에 진행할 수 있는 구조.

### Reusable Skills

26개 agent skill 셋업 (brainstorming, test-driven-development, systematic-debugging, verification-before-completion 등). Agent가 상황에 맞는 워크플로우를 자동으로 선택.

---

## 2. Plan — 명확한 계획이 agent 성능을 결정한다

아티클: *"People spend time thinking about what to do and less time thinking about how to do it."*

### Implementation Plan 구조

코드를 쓰기 전에 상세 plan을 먼저 작성:

- **Phase 0**: Scaffolding (프로젝트 구조, 의존성)
- **Phase 1A**: Models + Parser (ACORD 보험 표준 기반)
- **Phase 1B**: Diff Engine + Rules (15종 규칙)
- **Phase 1C**: Mock Data Generator (8,000건)
- **Phase 1D**: Batch Processor + API
- **Phase 2A**: LLM Client + Prompts (3종)
- **Phase 2B**: LLM Analyzer + Aggregator
- **Phase 2C**: Eval + Migration Demo

각 Phase별로 파일 목록, 예상 라인 수, 커밋 메시지, 검증 기준까지 정의. Agent에게 "뭘 만들어"가 아니라 **"이 순서로, 이 구조로, 이 기준을 통과하게"** 지시.

### V1 → V2 점진적 마이그레이션 설계

한번에 복잡한 시스템을 만들지 않음:
1. V1 (규칙 기반)을 먼저 완성 + 테스트 통과 확인
2. V2 (LLM 추가)를 V1 위에 얹음 — 동일 API 계약 유지
3. Feature flag (`RR_LLM_ENABLED`)로 토글 전환

---

## 3. Execute — 실행 과정

### V1: Rule-Based Pipeline

```
8,000건 정책 (mock JSON)
  → Parser (ACORD 필드 정규화)
  → Diff Engine (전년 vs 갱신 필드별 비교)
  → Rule Flagger (15종 임계값 규칙 → DiffFlag)
  → Risk Level (flags 조합 → low/medium/high/critical)
  → Batch Processor (일괄 처리 + 통계)
  → FastAPI API (결과 조회 + 배치 실행)
```

**성능**: 8,000건 < 1초, 테스트 65개 통과

### V2: LLM Hybrid Migration

V1 파이프라인은 그대로 두고, LLM 레이어만 추가:

```
동일 파이프라인
  → LLM Analyzer (비정형 텍스트만 선별 투입, 5-15%)
       ├ coverage_similarity — 커버리지 동등성 판단
       ├ endorsement_comparison — 자연어 배서 비교
       └ risk_signal_extractor — 메모에서 위험 시그널 추출
  → Risk Aggregator (규칙 + LLM 종합)
  → Langfuse trace (비용/지연시간 추적)
```

**마이그레이션 원칙**:
- 동일 API 계약 유지 (`llm_insights` 필드만 추가)
- `RR_LLM_ENABLED=false` 시 V1과 동일 동작
- LLM은 flag 건만 선별 투입 (비용 최적화)
- Provider 전환 가능 (OpenAI / Anthropic config)

### 프롬프트 엔지니어링

3종 structured output 프롬프트:
- **COVERAGE_SIMILARITY** — "Water damage" vs "Water backup" 동등성 판단 → JSON `{equivalent, confidence, reasoning}`
- **ENDORSEMENT_COMPARISON** — 자연어 배서 텍스트 비교 → JSON `{material_change, change_type, confidence}`
- **RISK_SIGNAL_EXTRACTOR** — 메모에서 위험 시그널 추출 → JSON `{signals[], confidence, summary}`

Confidence score 기반으로 aggregator가 risk level 상향 여부 결정 (threshold: 0.7~0.8).

### Frontend UI

Jinja2 기반 3개 페이지:
- **Dashboard** — 배치 실행, 리스크 분포, 정책 목록 (pagination)
- **Review Detail** — Prior vs Renewal 나란히 비교, flags, field changes, LLM insights
- **Migration Comparison** — V1 vs V2 동일 정책 비교, 리스크 변경 케이스

### 병렬 작업

Git worktrees로 frontend(wt-feat-1)과 backend(wt-feat-2) 동시 진행 후 main에 머지.

---

## 4. Result — 달성한 것

### 정량 지표

| 지표 | 결과 |
|------|------|
| 총 작업 시간 | ~1일 |
| 코드 라인 | ~2,500줄 (app + tests + generator) |
| 테스트 | 68개 (unit + property-based + integration) |
| 처리 성능 | 8,000건 < 1초 |
| Eval 정확도 | 100% (5/5 golden set) |
| LLM 선별 투입율 | 5-15% (비용 최적화) |
| 리스크 분포 | Low 15% / Med 45% / High 29% / Crit 11% |

### 아키텍처

```
renewal-review/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py             # pydantic-settings
│   ├── aggregator.py         # 규칙 + LLM 종합
│   ├── data_loader.py        # 데이터 캐싱
│   ├── models/               # Pydantic 모델 (policy, diff, review)
│   ├── engine/               # V1 파이프라인 (parser, differ, rules, batch)
│   ├── llm/                  # V2 LLM (client, prompts, analyzer, mock)
│   ├── routes/               # API (reviews, batch, eval, ui)
│   └── templates/            # Jinja2 UI (dashboard, review, migration)
├── data/
│   ├── generate.py           # 8,000건 mock 생성기
│   └── samples/              # 테스트 fixture + golden eval
└── tests/                    # 68 tests
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard UI |
| GET | `/ui/review/{policy_number}` | Review detail UI |
| GET | `/ui/migration` | Migration comparison UI |
| GET | `/health` | Health check |
| POST | `/reviews/compare` | 단일 정책 비교 |
| GET | `/reviews/{policy_number}` | 결과 조회 |
| POST | `/batch/run?sample=N` | 배치 처리 (async) |
| GET | `/batch/status/{job_id}` | Job 상태 조회 |
| GET | `/batch/summary` | 배치 통계 |
| POST | `/eval/run` | Golden set eval |
| POST | `/migration/comparison?sample=N` | V1 vs V2 비교 |

### Tech Stack

- Python 3.13 + FastAPI + Pydantic v2 + Jinja2
- uv (프로젝트 관리)
- pytest + Hypothesis (property-based testing)
- OpenAI / Anthropic (LLM, config 전환)
- Langfuse (LLM observability)
- Pre-commit: Ruff + Gitleaks + Semgrep

---

## 5. Agent-Native 아티클 매핑

### 직접 반영된 개념

| 아티클 | 이 프로젝트 |
|--------|------------|
| "Rulesets prevent code slop" | `CLAUDE.md` + `convention.md` — agent 행동 규칙 |
| "Tests are the reward signal" | 68 tests — agent가 통과할 때까지 반복 |
| "Linters for consistent styling" | Ruff lint + format, pre-commit hooks |
| "A week of work in a day or two" | 전체 파이프라인 + UI + 테스트를 ~1일에 완료 |
| "Everyone's a PM and team lead" | 나는 아키텍처/요구사항만 정의, agent가 구현 |
| "Plan mode UIs, akin to PRDs" | 상세 implementation plan 작성 후 단계별 실행 |
| "Simple / Manageable / Complex" | Phase별 태스크 분류 + 순차 실행 |

### 핵심 메시지

> Agent-native는 agent에게 코드를 맡기는 게 아니라, **agent가 잘 일할 수 있는 환경을 만드는 것**이다.
> Rulesets, tests, hooks를 먼저 셋업하고, 명확한 plan을 주면, 일주일 걸릴 프로젝트가 하루에 나온다.

---

## Demo Flow

1. **Dashboard** → Run Sample (100) → 통계/분포 확인
2. Critical/High 정책 클릭 → Prior vs Renewal 비교 + Flags + LLM Insights
3. **Run Eval** → 정확도 100% 확인
4. **Migration** → Compare (50) → V1 vs V2 delta 확인
5. Risk 변경된 정책 클릭 → "규칙만으로는 medium이었는데, LLM이 notes에서 위험 신호를 찾아서 high로 올렸다"
6. Langfuse 대시보드 → LLM trace 확인
