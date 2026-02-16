# Agent-Native Project Delivery: Renewal Review

## Overview

Insurance renewal review pipeline — 8,000건 보험 갱신 정책을 rule-based + LLM hybrid로 심사하는 시스템.
Agent-native 워크플로우로 **5일 분량 작업을 반나절에 완료 (10x)**, 그 위에 5가지 실험을 추가하여 총 ~2일 완료.

---

## 1. Setup — Agent가 잘 일할 수 있는 환경 만들기

Agent-native의 핵심은 agent에게 코드를 맡기는 것이 아니라, **agent가 잘 일할 수 있는 환경을 먼저 만드는 것**.

### Rulesets

| 파일 | 역할 |
|------|------|
| `CLAUDE.md` | Agent 행동 규칙 — no docstrings, minimal diffs, read before write |
| `convention.md` | 코드 스타일 + 프로세스 규칙 — 300줄 제한, 헥사고날 레이어 규칙, StrEnum/Config/Immutability/DI 패턴 |

Agent는 매 작업 전 이 파일을 읽고 규칙을 따름.

### Quality Gates (Tests + Linters + Hooks)

| 도구 | 역할 |
|------|------|
| **pytest** (100 tests) | Agent의 reward signal — 통과할 때까지 반복 |
| **Hypothesis** | Property-based testing — 엣지 케이스 자동 탐색 |
| **Ruff** | Lint + format — code slop 방지 |
| **Gitleaks** | Secret detection — API 키 커밋 차단 |
| **Semgrep** | SAST 보안 스캐닝 — 보안 취약점 자동 탐지 |

Pre-commit hook으로 묶어서, **커밋 시점에 자동으로 전부 실행**. Agent가 이 게이트를 통과하지 못하면 커밋 자체가 불가.

### Claude Code Hooks

| Hook | Type | Action |
|------|------|--------|
| `require-experiment-log` | PreToolUse | experiment/ 브랜치 커밋 시 실험 로그 없으면 차단 |
| `require-design-doc` | PreToolUse | app/ 또는 tests/ 변경 시 design-doc.md 없이 커밋 차단 |
| `remind-design-doc` | PostToolUse | 코드 파일 편집 시 1회 리마인더 |

### Parallel Workspace

Git worktrees로 병렬 작업 공간 준비:
- `wt-feat-1`, `wt-feat-2`, `wt-feat-3` — 기능 개발
- `wt-research` — 리서치 전용
- `wt-experiment` — 실험 전용

### Custom Skills

| Skill | 역할 |
|-------|------|
| `insurance-domain` | ACORD 표준 매핑, 필드 갭 분석, 도메인 용어 |
| `self-correcting-loop` | 자동 구현+검증 파이프라인 (실험 3에서 개발) |

---

## 2. Plan — 명확한 계획이 agent 성능을 결정한다

### 문서 기반 계획

| 문서 | 내용 |
|------|------|
| `requirements.md` | FR-1~FR-9, 성공 기준 (수치 포함), golden eval 5 케이스, NFR |
| `design-doc.md` | 5-layer 헥사고날 아키텍처, 데이터 모델 (8 Pydantic), 15 DiffFlags, 4 risk levels, 14+ API endpoints |
| `implementation-plan.md` | Phase 0-2C, 파일명·예상 라인·커밋 메시지·검증 기준 |

Agent에게 "뭘 만들어"가 아니라 **"이 순서로, 이 구조로, 이 기준을 통과하게"** 지시.

### V1 → V2 점진적 마이그레이션

1. V1 (규칙 기반)을 먼저 완성 + 테스트 통과 확인
2. V2 (LLM 추가)를 V1 위에 얹음 — 동일 API 계약 유지
3. Feature flag (`RR_LLM_ENABLED`)로 토글 전환

---

## 3. Execute — 실행 과정

### 파이프라인

```
8,000건 정책 (JSON / PostgreSQL)
  → Parser (ACORD 필드 정규화)
  → Diff Engine (전년 vs 갱신 필드별 비교)
  → Rule Flagger (15종 임계값 규칙 → DiffFlag)
  → Risk Level (flags 조합 → low/medium/high/critical)
  → LLM Analyzer (비정형 텍스트만 선별 투입, 5-15%)
       ├ risk_signal_extractor — 메모에서 위험 시그널 추출
       ├ endorsement_comparison — 자연어 배서 비교
       ├ review_summary — 리뷰 맥락 기반 요약
       └ quote_personalization — 견적 맞춤 조언
  → Risk Aggregator (규칙 + LLM 종합)
  → Langfuse trace (비용/지연시간 추적)
```

### LLM 4개 적용 포인트

| LLM 호출 | 대상 | 트리거 | 모델 |
|----------|------|--------|------|
| Risk Signal Extraction | notes 분석 | notes 변경 시 | **Sonnet** (복합 추론) |
| Endorsement Comparison | 특약 비교 | endorsement 변경 시 | Haiku |
| Review Summary | 리뷰 요약 | flags 있는 정책 (lazy) | Haiku |
| Quote Personalization | 견적 개인화 | quotes 생성 시 | Haiku |

### Frontend UI

Jinja2 기반 7개 페이지:
- **Dashboard** — 배치 실행, 리스크 분포, 정책 목록 (pagination)
- **Review Detail** — Prior vs Renewal 나란히 비교, flags, field changes, LLM insights
- **Analytics** — 배치 이력, 리스크 분포 차트, 일별 트렌드
- **Quote Generator** — 5가지 절감 전략, 정책 타입별 맞춤
- **Portfolio Analyzer** — 교차 정책 번들 분석, 중복 보장 탐지
- **Eval** — Golden set 검증
- **Migration Comparison** — V1 vs V2 동일 정책 비교

---

## 4. Result — 달성한 것

### 정량 지표

| 지표 | 결과 |
|------|------|
| 코어 시스템 개발 | ~4시간 (반나절) |
| 전체 프로젝트 (5 실험 포함) | ~2일 |
| 속도 배율 | **10x** (5일 → ½일) |
| 코드 라인 | ~2,500줄 |
| 테스트 | **100개** (unit + property-based + integration) |
| API 엔드포인트 | 14+ |
| UI 페이지 | 7개 |
| 처리 성능 | 8,000건 < 1초 |
| LLM 선별 투입율 | 5-15% |

### 아키텍처 (Hexagonal)

```
renewal-review/
├── app/
│   ├── domain/          # 순수 비즈니스 로직 (외부 의존성 0)
│   │   ├── models/      #   Pydantic 모델 (8개)
│   │   ├── services/    #   도메인 서비스
│   │   └── ports/       #   Protocol 인터페이스
│   ├── application/     # 유스케이스 오케스트레이션
│   ├── api/             # Inbound 어댑터 (FastAPI)
│   ├── adaptor/         # Outbound (LLM, storage, DB)
│   │   ├── llm/         #   LLM client, prompts, analyzer
│   │   └── storage/     #   메모리/DB 저장소
│   └── infra/           # DI 와이어링
├── data/
│   ├── generate.py      # 8,000건 mock 생성기
│   └── samples/         # 테스트 fixture + golden eval
└── tests/               # 100 tests
```

### API Endpoints (주요)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard UI |
| GET | `/ui/review/{policy_number}` | Review detail UI |
| GET | `/ui/analytics` | Analytics UI |
| GET | `/ui/quotes/{policy_number}` | Quote generator UI |
| GET | `/ui/portfolio` | Portfolio analyzer UI |
| GET | `/health` | Health check |
| POST | `/reviews/compare` | 단일 정책 비교 |
| GET | `/reviews/{policy_number}` | 결과 조회 |
| POST | `/batch/run?sample=N` | 배치 처리 |
| GET | `/batch/status/{job_id}` | Job 상태 조회 |
| GET | `/batch/summary` | 배치 통계 |
| GET | `/quotes/{policy_number}` | 견적 생성 |
| GET | `/portfolio/analysis` | 포트폴리오 분석 |
| POST | `/eval/run` | Golden set eval |

### Tech Stack

- Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy + Jinja2
- Docker + PostgreSQL 16
- uv (프로젝트 관리)
- pytest + Hypothesis (property-based testing)
- OpenAI / Anthropic (LLM, config 전환)
- Langfuse (LLM observability)
- MCP Toolbox v0.27.0 (agent DB 접근)
- Pre-commit: Ruff + Gitleaks + Semgrep
- Claude Code Hooks (require-design-doc, require-experiment-log, remind-design-doc)

---

## 5. Experiments

5가지 실험을 순차적으로 진행. 각 실험은 이전 실험의 결과 위에 쌓인다.

| # | 실험 | 질문 | 핵심 결과 |
|---|------|------|-----------|
| 1 | SubAgent vs Agent Teams | 여러 agent를 동시에 돌릴 수 있는가? | 소규모(~300줄)에서는 SubAgent 실용적, 대규모에서 Teams 유리 |
| 2 | Triangular Verification | Agent끼리 서로 검증할 수 있는가? | 정보 격리로 기존 도구가 못 찾는 intent mismatch 9건 발견 (78% precision) |
| 3 | Self-Correcting Loop | 검증→수정까지 자동화할 수 있는가? | 1회 반복, 사람 개입 0, 81/81 테스트 통과 |
| 4 | Pipeline Reusability | 다른 기능에서도 재사용 가능한가? | 동일 파이프라인, 다른 도메인(Portfolio), 동일 결과. Claude Skill로 패키징 |
| 5 | Langfuse LLM Benchmark | 어떤 LLM이 이 도메인에 최적인가? | 벤치마크 결과를 반영하여 **task별 모델 라우팅 구현**: risk_signal → Sonnet, 나머지 → Haiku |

---

## 6. Rule vs LLM 판단 기준

LLM은 기본 꺼짐 (`RR_LLM_ENABLED=false`). 4가지 질문으로 적용 여부 판단:

| 질문 | → Rule | → LLM |
|------|--------|-------|
| 입력이 구조화되어 있는가? | boolean, numeric | free text, notes |
| 답이 결정적인가? | threshold check | context-dependent |
| 간단한 규칙으로 풀 수 있는가? | 1-line if | no simple logic |
| LLM 출력이 질적으로 다른가? | same quality | clearly richer |

3+ 답이 Rule → LLM 사용하지 않음.

코드 비율: Rule **42%** · LLM **19%** · Hybrid **25%** · 인프라 **14%**
유저 출력 기준: Rule **8/12** (67%) · LLM **4/12** (33%)

---

## 7. Skills for the Team

실험 결과를 재사용 가능한 형태로 패키징:

- **Claude Skill**: `self-correcting-loop` — PROMPT.md만 바꾸면 어떤 기능이든 자동 구현+검증
- **Team Guide**: `guide-self-correcting-loop.md` — 전제조건, 사용법, 트러블슈팅
- **목표**: 한 사람이 실험 → 패키징 → 팀 전체가 재사용

---

## Demo Flow

1. **Dashboard** → Run Sample (100) → 통계/분포 확인
2. Critical/High 정책 클릭 → Prior vs Renewal 비교 + Flags + LLM Insights
3. **Analytics** → 배치 여러 번 실행 후 이력 테이블 + 리스크 분포 차트
4. **Quote Generator** → 정책별 절감 전략 5가지 + LLM 맞춤 조언
5. **Portfolio** → 번들 분석 + 중복 보장 탐지
6. **Run Eval** → 정확도 100% 확인
7. Langfuse 대시보드 → LLM trace 확인
