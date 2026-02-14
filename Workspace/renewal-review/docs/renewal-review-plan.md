# Renewal Review — Implementation Plan

## Context

Quandri Software Engineer 인터뷰(2/17)를 위한 데모 프로젝트.
**"Agent-Native Project Delivery: Renewal Review on Large-Scale Data"** — agent-native 방식으로 복잡한 보험 갱신 심사 시스템을 1-2일 안에 구축한 경험을 보여준다.

**핵심 메시지:** iteration engine이 아니라, 실제 프로젝트를 끝낸 경험 + 그때 사용한 파이프라인.

**일정:** 수(2/11) 파이프라인 완성 → 금(2/13) 발표연습 → 월(2/17) 인터뷰

---

## Architecture

### V1: Rule-Based (Day 1)
```
8,000건 정책 (mock JSON)
  → Parser (ACORD 필드 정규화)
  → Diff Engine (전년 vs 갱신 필드별 비교)
  → Rule Flagger (임계값 규칙 → DiffFlag)
  → Batch Processor (일괄 처리 + 통계)
  → FastAPI (결과 조회 + 배치 실행)
```

### V2: LLM Hybrid Migration (Day 2)
```
8,000건 정책
  → Parser (동일)
  → Diff Engine (구조화 필드 → 규칙, 빠르고 무료)
  → LLM Analyzer (비정형 텍스트만 선별 투입, 5-15%)
       ├ coverage_similarity — 커버리지 동등성 판단
       ├ endorsement_parser — 자연어 배서 비교
       └ risk_signal_extractor — 메모에서 위험 시그널 추출
  → Risk Aggregator (규칙 + LLM 종합)
  → 결과 + reasoning + Langfuse trace
```

**V1→V2 마이그레이션 원칙:**
- 동일 API 계약 유지 (llm_insights 필드만 추가)
- `RR_LLM_ENABLED=false` 시 V1과 동일 동작
- LLM은 flag 건만 선별 투입 (비용 최적화)
- LLM provider 전환 가능 (OpenAI / Anthropic config 지원)

---

## Directory Structure

```
renewal-review/
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app + router mounts (~60 lines)
│   ├── config.py                # pydantic-settings (~50 lines)
│   │
│   ├── models/
│   │   ├── policy.py            # PolicySnapshot, AutoCoverages, HomeCoverages, RenewalPair (~150 lines)
│   │   ├── diff.py              # DiffFlag enum, FieldChange, DiffResult (~100 lines)
│   │   └── review.py            # RiskLevel, LLMInsight, ReviewResult, BatchSummary (~80 lines)
│   │
│   ├── engine/
│   │   ├── parser.py            # JSON → PolicySnapshot 정규화 (~120 lines)
│   │   ├── differ.py            # 필드별 비교 → DiffResult (~200 lines)
│   │   ├── rules.py             # 임계값 규칙 → DiffFlag 생성 (~180 lines)
│   │   └── batch.py             # 일괄 처리 + 통계 집계 (~100 lines)
│   │
│   ├── llm/                     # V2
│   │   ├── client.py            # LLM client (OpenAI/Anthropic) + Langfuse tracing (~120 lines)
│   │   ├── prompts.py           # 프롬프트 템플릿 3종 (~100 lines)
│   │   └── analyzer.py          # LLM 투입 판단 + 분석 오케스트레이션 (~150 lines)
│   │
│   ├── aggregator.py            # V2: 규칙 + LLM 결과 종합 (~100 lines)
│   │
│   └── routes/
│       ├── reviews.py           # POST /reviews/compare, GET /reviews/{id} (~120 lines)
│       └── batch.py             # POST /batch/run, GET /batch/summary (~100 lines)
│
├── data/
│   ├── generate.py              # 8,000건 mock 데이터 생성기 (~250 lines)
│   └── samples/                 # 테스트 fixture (커밋 대상)
│       ├── auto_pair.json
│       ├── home_pair.json
│       └── golden_eval.json     # V2 LLM eval golden set
│
└── tests/
    ├── conftest.py              # 공유 fixture (~80 lines)
    ├── test_models.py           # 모델 검증 (~60 lines)
    ├── test_parser.py           # 파서 유닛 테스트 (~80 lines)
    ├── test_differ.py           # diff + Hypothesis property-based (~150 lines)
    ├── test_rules.py            # 규칙 임계값 경계 테스트 (~120 lines)
    ├── test_batch.py            # 배치 통합 테스트 (~80 lines)
    ├── test_routes.py           # API 통합 테스트 (~100 lines)
    └── test_llm_analyzer.py     # V2: mock LLM으로 분석기 테스트 (~100 lines)
```

---

## Implementation Phases

### Phase 0: Scaffolding (30min)

1. `uv init` 으로 프로젝트 생성
2. `pyproject.toml` 의존성:
   - Runtime: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`
   - Dev: `pytest`, `hypothesis`, `httpx`, `ruff`
   - LLM (optional): `openai`, `anthropic`, `langfuse`
3. `app/main.py` — health endpoint
4. `tests/test_main.py` — health 테스트
5. `pytest` + `ruff check` 통과 확인

**Commit:** `feat: scaffold renewal-review project`

### Phase 1A: Models + Parser (1.5hr)

1. `app/models/policy.py` — ACORD 기반 Pydantic 모델
   - PolicySnapshot, AutoCoverages, HomeCoverages, Vehicle, Driver, Endorsement, RenewalPair
2. `app/models/diff.py` — DiffFlag(15종 enum), FieldChange, DiffResult
3. `app/models/review.py` — RiskLevel, ReviewResult, BatchSummary
4. `app/engine/parser.py` — JSON → PolicySnapshot 변환
5. `data/samples/auto_pair.json`, `home_pair.json` — 수동 fixture
6. 테스트: `test_models.py`, `test_parser.py`

**Commit:** `feat: add ACORD policy models and parser`

### Phase 1B: Diff Engine + Rules (2hr)

1. `app/engine/differ.py`:
   - `diff_universal_fields()` — premium, carrier, dates, endorsements
   - `diff_auto_coverages()` — BI/PD limits, deductibles
   - `diff_home_coverages()` — Coverage A-F, deductibles
   - `diff_vehicles()` — VIN 매칭, 추가/제거
   - `diff_drivers()` — 면허번호 매칭, 추가/제거
   - `compute_diff(pair) -> DiffResult` — 오케스트레이터
2. `app/engine/rules.py`:
   - 임계값 상수: PREMIUM_THRESHOLD_HIGH=10%, CRITICAL=20%
   - `flag_diff(diff, pair) -> DiffResult` — 모든 규칙 적용
3. `tests/test_differ.py` — 유닛 + **Hypothesis property-based:**
   - 동일 정책 diff → 플래그 0개
   - premium_change_pct = (renewal - prior) / prior * 100 (모든 양수 쌍)
   - 모든 DiffFlag에 대응하는 FieldChange 존재
4. `tests/test_rules.py` — 임계값 경계 테스트 (9.99% vs 10.01%)

**Commits:**
- `feat: implement policy diff engine`
- `feat: add rule-based risk flagging`
- `test: add property-based tests for diff engine`

### Phase 1C: Mock Data Generator (1.5hr)

1. `data/generate.py` (standalone script):
   - 8,000건 생성 (4,800 auto + 3,200 home)
   - 분포: clean 25%, premium변경 100%, inflation guard 70%(home), endorsement churn 20%, vehicle 변경 10%(auto), carrier 변경 5%
   - 30% 정책에 자연어 notes 포함 (V2 LLM 분석 대상)
   - 캐리어 10개, endorsement 코드 10종, 주소 50개 풀
2. 출력: `data/renewals.json` (~15-25MB, .gitignore 대상)

**Commit:** `feat: add mock data generator for 8k renewal pairs`

### Phase 1D: Batch Processor + API (2hr)

1. `app/config.py` — Settings (env prefix `RR_`, llm_enabled toggle)
2. `app/engine/batch.py`:
   - `process_pair()` → diff + flag + risk level 판정
   - `process_batch()` → 전체 처리 + BatchSummary
   - Risk: CRITICAL(>20% or liability↓), HIGH(>10% or coverage↓), MEDIUM(any flag), LOW(no flag)
3. `app/routes/reviews.py` — `POST /reviews/compare`, `GET /reviews/{policy_number}`
4. `app/routes/batch.py` — `POST /batch/run?sample=N`, `GET /batch/summary`
5. 테스트: `test_batch.py`, `test_routes.py` (TestClient 통합)

**Commits:**
- `feat: add batch processor with risk level assignment`
- `feat: add API routes for reviews and batch processing`
- `test: add integration tests for V1 pipeline`

**V1 완료 검증:**
- [ ] `pytest` 전체 통과
- [ ] 8,000건 배치 < 5초
- [ ] `/batch/run?sample=100` 에서 현실적 분포 (LOW ~25%, MED ~50%, HIGH ~20%, CRIT ~5%)

**Tag:** `v1.0.0`

---

### Phase 2A: LLM Client + Prompts (1.5hr)

1. `app/llm/client.py`:
   - `LLMClient` — OpenAI/Anthropic 전환 가능 (config.llm_provider)
   - Langfuse trace 자동 연동 (trace_name으로 프롬프트별 비용 추적)
   - `LLMClientProtocol` — 테스트용 Protocol 클래스
2. `app/llm/prompts.py` — 3종 프롬프트 템플릿:
   - `COVERAGE_SIMILARITY` — "Water damage" vs "Water backup" 동등성 판단
   - `ENDORSEMENT_COMPARISON` — 자연어 배서 텍스트 비교
   - `RISK_SIGNAL_EXTRACTOR` — 메모에서 위험 시그널 추출
   - 모두 JSON 출력 강제 (structured output)

**Commit:** `feat: add LLM client with Langfuse tracing and prompt templates`

### Phase 2B: LLM Analyzer + Aggregator (2hr)

1. `app/llm/analyzer.py`:
   - `should_analyze(diff, pair) -> bool` — LLM 투입 판단
   - `analyze_pair(diff, pair) -> list[LLMInsight]` — 필요한 프롬프트만 실행
   - 투입 조건: endorsement 설명 변경, notes 변경, coverage 텍스트 불일치
2. `app/aggregator.py`:
   - 규칙 flags + LLM insights → 최종 ReviewResult
   - LLM high-confidence signal → risk level 상향
3. `app/engine/batch.py` 업데이트:
   - `llm_enabled=True` 시 flag 건에 LLM 추가 분석
   - V1 호환: `llm_enabled=False` 시 동일 동작
4. `tests/test_llm_analyzer.py` — mock LLM으로 routing/analysis 검증

**Commits:**
- `feat: add LLM analyzer for unstructured text review`
- `feat: add risk aggregator combining rules and LLM`
- `refactor: update batch processor for V2 hybrid pipeline`

### Phase 2C: Eval + Migration Demo (1.5hr)

1. `data/samples/golden_eval.json` — 15-20개 수동 eval case
2. `POST /eval/run` — golden set 정확도 측정
3. `POST /migration/comparison?sample=50`:
   - V1 vs V2 결과 나란히 비교
   - delta: risk_level 변경 수, LLM이 찾은 새 insight 수, 비용, 지연시간
4. Langfuse 대시보드에서 trace 확인

**Commits:**
- `feat: add LLM eval suite with golden-set`
- `feat: add V1/V2 migration comparison endpoint`

**V2 완료 검증:**
- [ ] V1 테스트 전부 통과 (regression 없음)
- [ ] V2 mock 테스트 통과
- [ ] `/migration/comparison` 에서 V1 vs V2 delta 확인
- [ ] Langfuse에 LLM trace 표시
- [ ] 8,000건 중 5-15%만 LLM 호출

**Tag:** `v2.0.0`

---

## API Endpoints

| Method | Path | Ver | Description |
|--------|------|-----|-------------|
| GET | `/health` | V1+ | Health check |
| POST | `/reviews/compare` | V1+ | 단일 RenewalPair 비교 |
| GET | `/reviews/{policy_number}` | V1+ | 마지막 배치 결과 조회 |
| POST | `/batch/run?sample=N` | V1+ | 일괄 처리 (전체 또는 샘플) |
| GET | `/batch/summary` | V1+ | 마지막 배치 통계 |
| POST | `/eval/run` | V2 | LLM eval suite 실행 |
| POST | `/migration/comparison?sample=N` | V2 | V1 vs V2 비교 |

---

## Testing Strategy

- **Unit:** models, parser, differ, rules — 각 함수 격리 테스트
- **Property-based (Hypothesis):** diff 엔진 핵심 속성 검증 (동일 정책→0 플래그, premium_pct 계산, flag↔change 대응)
- **Integration:** API endpoints TestClient, batch end-to-end
- **LLM Eval:** golden-set 15-20 cases, mock(CI) + real(수동)

---

## Tech Stack

- Python 3.13 + FastAPI + Pydantic v2
- uv (프로젝트 관리)
- pytest + hypothesis
- openai + anthropic (LLM, config 전환)
- langfuse (LLM observability)
- Pre-commit: Ruff + Gitleaks + Semgrep

---

## Key Design Decisions

1. **규칙 우선, LLM은 보조** — 85-90% 구조화 필드는 규칙으로 무료/즉시 처리. LLM은 비정형 텍스트만.
2. **Feature flag (`RR_LLM_ENABLED`)** — V1/V2 동일 코드베이스, 토글로 전환. 데모에서 실시간 비교 가능.
3. **In-memory 결과 저장** — 데모용. 프로덕션이면 PostgreSQL + async queue 언급.
4. **LLM provider 추상화** — OpenAI/Anthropic config 전환. 데모에서 유연성 어필.
5. **300줄 파일 제한** — convention.md 준수, 모듈 분리로 가독성 확보.

---

## Verification Checklist

- [ ] `uv sync && pytest` 전체 통과
- [ ] `ruff check && ruff format --check` 통과
- [ ] `pre-commit run --all-files` 통과
- [ ] `uvicorn app.main:app` 기동 → `/health` 200
- [ ] `POST /batch/run` 8,000건 < 5초
- [ ] `POST /migration/comparison?sample=50` V1 vs V2 delta 출력
- [ ] Langfuse 대시보드에 LLM trace 표시
- [ ] git tag v1.0.0, v2.0.0 생성
