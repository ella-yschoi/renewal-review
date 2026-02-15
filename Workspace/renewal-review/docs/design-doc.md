# Renewal Review — System Design Document

---

## 1. Overview

보험 갱신(renewal) 정책을 자동으로 비교·분석하여 위험 수준을 판정하는 파이프라인.

- **Prior vs Renewal 비교**: 기존 정책과 갱신 정책의 모든 필드를 diff하고, 주의가 필요한 변경에 flag를 부여
- **Rule + LLM 하이브리드**: 규칙 기반 risk 판정 후, 조건 충족 시 LLM이 notes·endorsement·coverage를 심층 분석하여 risk를 상향 조정
- **대안 견적 생성**: flagged 정책에 대해 보장 조정 전략별 절감 견적(Quote)을 최대 3개 제안

**대상 사용자**: 보험 언더라이터, 갱신 심사 담당자

---

## 2. Architecture

```
                          ┌─────────────────────────┐
                          │        FastAPI App       │
                          │      (app/main.py)       │
                          └────────────┬────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
     ┌────────▼────────┐    ┌─────────▼─────────┐   ┌─────────▼─────────┐
     │   Routes Layer   │    │   Engine Layer     │   │    LLM Sidecar    │
     │                  │    │                    │   │                   │
     │ reviews.py       │    │ batch.py           │   │ analyzer.py       │
     │ batch.py         │───▶│ differ.py          │◀──│ client.py         │
     │ analytics.py     │    │ rules.py           │   │ prompts.py        │
     │ quotes.py        │    │ analytics.py       │   │ mock.py           │
     │ eval.py          │    │ quote_generator.py │   └─────────┬─────────┘
     │ ui.py            │    │ parser.py          │             │
     └────────┬─────────┘    └────────────────────┘    OpenAI / Anthropic
              │                                        + Langfuse tracing
              │
     ┌────────▼────────────────────────────────────┐
     │              Storage Layer                   │
     │                                              │
     │  In-memory: dict / deque (default)           │
     │  Optional: PostgreSQL (asyncpg / psycopg)    │
     │  JSON file: data/renewals.json (fallback)    │
     └──────────────────────────────────────────────┘
```

### 모듈 디렉토리

```
app/
├── __init__.py
├── main.py               # FastAPI 앱 생성, 라우터 등록
├── config.py             # Settings (env_prefix=RR_)
├── data_loader.py        # load_pairs — DB 또는 JSON 로드 + 캐시
├── db.py                 # SQLAlchemy async engine, Base, 세션 팩토리
├── aggregator.py         # rule_risk + LLM insights → final risk 결정
│
├── engine/
│   ├── __init__.py
│   ├── parser.py         # raw dict → PolicySnapshot / RenewalPair 변환
│   ├── differ.py         # Prior ↔ Renewal 필드별 diff 계산
│   ├── rules.py          # diff flags 부여 + premium/liability/coverage 규칙
│   ├── batch.py          # process_pair, process_batch, assign_risk_level
│   ├── analytics.py      # compute_trends — BatchRunRecord → AnalyticsSummary
│   └── quote_generator.py # 정책 타입별 절감 전략 적용 → QuoteRecommendation
│
├── llm/
│   ├── __init__.py
│   ├── analyzer.py       # should_analyze, analyze_pair, generate_summary
│   ├── client.py         # LLMClient — OpenAI/Anthropic + Langfuse
│   ├── prompts.py        # 5개 프롬프트 템플릿
│   ├── mock.py           # MockLLMClient — 테스트/migration 비교용
│   └── quote_advisor.py  # personalize_quotes — Quote LLM 개인화
│
├── models/
│   ├── __init__.py
│   ├── policy.py         # PolicySnapshot, RenewalPair, Auto/HomeCoverages 등
│   ├── diff.py           # DiffFlag(15종), FieldChange, DiffResult
│   ├── review.py         # RiskLevel, LLMInsight, ReviewResult, BatchSummary
│   ├── analytics.py      # BatchRunRecord, TrendPoint, AnalyticsSummary
│   ├── quote.py          # CoverageAdjustment, QuoteRecommendation
│   └── db_models.py      # SQLAlchemy ORM — RenewalPairRow, BatchResultRow
│
├── routes/
│   ├── __init__.py
│   ├── reviews.py        # POST /reviews/compare, GET /reviews/{policy_number}
│   ├── batch.py          # POST /batch/run, GET /batch/status/{job_id}, GET /batch/summary
│   ├── analytics.py      # GET /analytics/history, GET /analytics/trends
│   ├── quotes.py         # POST /quotes/generate
│   ├── eval.py           # POST /eval/run, POST /migration/comparison, GET /migration/status/{job_id}
│   └── ui.py             # GET /, /ui/review/{pn}, /ui/analytics, /ui/quotes, /ui/migration
│
└── templates/
    ├── base.html         # 공통 레이아웃 (nav, footer)
    ├── dashboard.html    # 메인 대시보드
    ├── review.html       # 리뷰 상세
    ├── analytics.html    # 분석 트렌드
    ├── quotes.html       # Quote Generator
    └── migration.html    # Basic vs LLM 비교
```

### 데이터 흐름 요약

```
JSON/DB → load_pairs → [RenewalPair]
                           │
         process_pair ◄────┘
              │
    compute_diff ──▶ flag_diff ──▶ assign_risk_level
                                         │
                         ┌───── LLM 조건? ─┤
                         │ Yes             │ No
                   analyze_pair      ReviewResult 반환
                         │
                    aggregate ──▶ ReviewResult (risk 상향 가능)
                         │
            ┌── flags 있고 LLM client? ──┐
            │ Yes                        │ No
     generate_summary()           기존 mechanical summary 유지
            │
    store (dict) ──▶ UI 렌더링
```

---

## 3. Data Model

### Policy 도메인 (`app/models/policy.py`)

| 모델 | 설명 | 핵심 필드 |
|------|------|-----------|
| `PolicyType` | StrEnum — `auto`, `home` | — |
| `PolicySnapshot` | 정책 1건의 스냅샷 | policy_number, policy_type, carrier, effective_date, expiration_date, premium, state, notes, auto_coverages, home_coverages, vehicles, drivers, endorsements |
| `RenewalPair` | Prior + Renewal 한 쌍 | prior: PolicySnapshot, renewal: PolicySnapshot |
| `AutoCoverages` | 자동차 보장 항목 | bodily_injury_limit, property_damage_limit, collision_deductible, comprehensive_deductible, uninsured_motorist, medical_payments, rental_reimbursement, roadside_assistance |
| `HomeCoverages` | 주택 보장 항목 | coverage_a~f, deductible, wind_hail_deductible, water_backup, replacement_cost |
| `Vehicle` | 차량 정보 | vin, year, make, model, usage |
| `Driver` | 운전자 정보 | license_number, name, age, violations, sr22 |
| `Endorsement` | 특약 | code, description, premium |

### Diff 도메인 (`app/models/diff.py`)

| 모델 | 설명 | 핵심 필드 |
|------|------|-----------|
| `FieldChange` | 단일 필드 변경 | field, prior_value, renewal_value, change_pct, flag |
| `DiffResult` | 한 정책의 전체 diff | policy_number, changes: list[FieldChange], flags: list[DiffFlag] |

**DiffFlag 전체 목록 (15개)**:

| Flag | 트리거 조건 |
|------|------------|
| `premium_increase_high` | 보험료 +10% 이상 |
| `premium_increase_critical` | 보험료 +20% 이상 |
| `premium_decrease` | 보험료 감소 |
| `carrier_change` | 보험사 변경 |
| `liability_limit_decrease` | liability 한도 감소 |
| `deductible_increase` | 공제액 증가 |
| `coverage_dropped` | 보장 항목 축소/제거 |
| `coverage_added` | 보장 항목 추가 |
| `vehicle_added` | 차량 추가 |
| `vehicle_removed` | 차량 제거 |
| `driver_added` | 운전자 추가 |
| `driver_removed` | 운전자 제거 |
| `endorsement_added` | 특약 추가 |
| `endorsement_removed` | 특약 제거 |
| `notes_changed` | 비고 변경 |

### Review 도메인 (`app/models/review.py`)

| 모델 | 설명 | 핵심 필드 |
|------|------|-----------|
| `RiskLevel` | StrEnum — 4단계 | no_action_needed, review_recommended, action_required, urgent_review |
| `LLMInsight` | LLM 분석 1건 | analysis_type, finding, confidence, reasoning |
| `ReviewResult` | 최종 리뷰 결과 | policy_number, risk_level, diff, llm_insights, summary, pair |
| `BatchSummary` | 배치 실행 요약 | total, risk level별 카운트, llm_analyzed, processing_time_ms |

### Analytics 도메인 (`app/models/analytics.py`)

| 모델 | 설명 | 핵심 필드 |
|------|------|-----------|
| `BatchRunRecord` | 배치 1회 기록 | job_id, total, risk level별 카운트, processing_time_ms, created_at |
| `TrendPoint` | 일별 집계 | date, total_runs, avg_processing_time_ms, urgent_review_ratio |
| `AnalyticsSummary` | 전체 분석 요약 | total_runs, total_policies_reviewed, avg_processing_time_ms, risk_distribution, trends |

### Quote 도메인 (`app/models/quote.py`)

| 모델 | 설명 | 핵심 필드 |
|------|------|-----------|
| `CoverageAdjustment` | 개별 조정 항목 | field, original_value, proposed_value, strategy |
| `QuoteRecommendation` | 대안 견적 1건 | quote_id (Q1~Q3), adjustments, estimated_savings_pct, estimated_savings_dollar, trade_off, broker_tip |

### DB 도메인 (`app/models/db_models.py`)

| 모델 | 테이블명 | 설명 |
|------|---------|------|
| `RenewalPairRow` | `renewal_pairs` | 정책 쌍 영구 저장. prior_json, renewal_json으로 원본 보존 |
| `BatchResultRow` | `batch_results` | 배치 결과. job_id, risk_level, flags_json |

---

## 4. Processing Pipeline

### 단계별 흐름

```
1. Data Loading     load_pairs()           DB 또는 JSON에서 RenewalPair 로드
       │
2. Diff             compute_diff(pair)     필드별 변경 감지 → DiffResult
       │
3. Flagging         flag_diff(diff, pair)  규칙 기반 flag 부여
       │
4. Risk Assignment  assign_risk_level()    flag 조합으로 risk level 결정
       │
5. LLM Analysis     should_analyze() →     조건 충족 시 LLM 분석
   (조건부)          analyze_pair()
       │
6. Aggregation      aggregate()            rule_risk + LLM insights → final risk
```

### Risk Level 결정 조건표 (Rule-Based)

| Risk Level | 조건 | 해당 Flags |
|-----------|------|-----------|
| `urgent_review` | URGENT flag 1개 이상 | `premium_increase_critical`, `liability_limit_decrease` |
| `action_required` | ACTION flag 1개 이상 | `premium_increase_high`, `coverage_dropped` |
| `review_recommended` | flag 존재하지만 위 해당 없음 | 기타 모든 flag |
| `no_action_needed` | flag 없음 | — |

> 판정 우선순위: urgent_review > action_required > review_recommended > no_action_needed
> (`app/engine/batch.py:18-26`)

### LLM Risk Upgrade 조건 (`app/aggregator.py`)

LLM 분석 결과에 따라 rule_risk보다 높은 level로 상향. 하향은 없음.

| 조건 | 상향 대상 |
|------|----------|
| coverage NOT equivalent (confidence ≥ 0.8) | → `action_required` 이상 |
| risk_signal 2건 이상 (confidence ≥ 0.7) | → `action_required` 이상 |
| endorsement restriction (confidence ≥ 0.75) | → `action_required` 이상 |
| 위 조건 복합 (coverage/restriction + risk_signal ≥ 2) | → `urgent_review` |

### Flag 트리거 임계값 (`app/engine/rules.py`)

| 규칙 | 임계값 | 결과 Flag |
|------|--------|----------|
| 보험료 증가 | ≥ 10% | `premium_increase_high` |
| 보험료 증가 | ≥ 20% | `premium_increase_critical` |
| 보험료 감소 | < 0% | `premium_decrease` |
| Liability 감소 | prior > renewal (합산 비교) | `liability_limit_decrease` |
| Deductible 증가 | prior < renewal | `deductible_increase` |
| Coverage 수치 감소 | prior > renewal | `coverage_dropped` |
| Boolean coverage 제거 | True → False | `coverage_dropped` |
| Boolean coverage 추가 | False → True | `coverage_added` |

### Quote Generator 전략 (`app/engine/quote_generator.py`)

정책 타입별 최대 3개 전략을 독립 적용하여 대안 견적 생성.

**Auto 전략**:

| 전략 | 절감률 | 조건 (건너뛰기) |
|------|--------|----------------|
| `raise_deductible` | 10% | collision_deductible ≥ 1000 AND comprehensive_deductible ≥ 500 |
| `drop_optional` | 4% | rental_reimbursement=False AND roadside_assistance=False |
| `reduce_medical` | 2.5% | medical_payments ≤ 2000 |

**Home 전략**:

| 전략 | 절감률 | 조건 (건너뛰기) |
|------|--------|----------------|
| `raise_deductible` | 12.5% | deductible ≥ 2500 |
| `drop_water_backup` | 3% | water_backup=False |
| `reduce_personal_property` | 4% | coverage_c ≤ dwelling × 0.5 |

**보호 필드** — 어떤 전략에서도 절대 변경 불가:

`bodily_injury_limit`, `property_damage_limit`, `coverage_e_liability`, `uninsured_motorist`, `coverage_a_dwelling`

---

## 5. API Surface

### Core API

| Method | Path | Description | Response | Status Codes |
|--------|------|-------------|----------|-------------|
| GET | `/health` | 헬스체크 | `{"status": "ok"}` | 200 |
| POST | `/reviews/compare` | 단건 정책 비교 | `ReviewResult` | 200, 422 |
| GET | `/reviews/{policy_number}` | 리뷰 결과 조회 | `ReviewResult` | 200, 404 |
| POST | `/quotes/generate` | 대안 견적 생성 | `list[QuoteRecommendation]` | 200, 422 |

### Batch / Async

| Method | Path | Description | Response | Status Codes |
|--------|------|-------------|----------|-------------|
| POST | `/batch/run` | 배치 실행 (비동기) | `{"job_id", "status", "total"}` | 200, 404 |
| GET | `/batch/status/{job_id}` | 배치 진행 상태 | job 상세 (status, processed, total) | 200, 404 |
| GET | `/batch/summary` | 마지막 배치 요약 | `BatchSummary \| null` | 200 |
| POST | `/eval/run` | Golden eval 실행 | accuracy + 시나리오별 결과 | 200, 404 |
| POST | `/migration/comparison` | Basic vs LLM 비교 (비동기) | `{"job_id", "status", "total"}` | 200, 404 |
| GET | `/migration/status/{job_id}` | Migration 진행 상태 | job 상세 | 200, 404 |

### Analytics

| Method | Path | Description | Response | Status Codes |
|--------|------|-------------|----------|-------------|
| GET | `/analytics/history` | 배치 실행 이력 (최대 100건) | `list[BatchRunRecord]` | 200 |
| GET | `/analytics/trends` | 일별 트렌드 + 요약 | `AnalyticsSummary` | 200 |

### Async Job 라이프사이클

```
POST /batch/run  →  {"job_id": "abc12345", "status": "running"}
                            │
         GET /batch/status/abc12345  (polling)
                            │
              status: "running"  →  processed / total 갱신
              status: "completed" →  summary 포함
              status: "failed"   →  error 메시지 포함
```

### UI Pages

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard |
| GET | `/ui/review/{policy_number}` | 리뷰 상세 |
| GET | `/ui/analytics` | Analytics |
| GET | `/ui/quotes` | Quote Generator |
| GET | `/ui/migration` | Basic vs LLM 비교 |

---

## 6. UI

| # | 페이지 | Route | 주요 기능 |
|---|--------|-------|----------|
| 1 | Dashboard | `GET /` | 전체 리뷰 목록 (severity 내림차순 정렬), 배치 요약 표시, 페이지네이션 (50건/page) |
| 2 | Review Detail | `GET /ui/review/{pn}` | 단건 리뷰 상세 — diff, flags, risk level, LLM insights. 파이프라인 라벨 표시 (Basic Analytics / LLM Analytics). ref 파라미터로 돌아갈 페이지 결정 |
| 3 | Analytics | `GET /ui/analytics` | 배치 이력 목록 + 트렌드 차트 (risk distribution, 일별 urgent_review_ratio) |
| 4 | Quote Generator | `GET /ui/quotes` | flagged 정책 목록 표시. "Generate Quotes" 클릭 → `/reviews/{pn}` + `/quotes/generate` 호출하여 대안 견적 모달 표시. 페이지네이션 |
| 5 | Migration | `GET /ui/migration` | Basic vs LLM 비교 대시보드. element ID: `basic-*`, `llm-*`. 비동기 실행 후 polling으로 결과 표시 |
| 6 | Base Layout | — | 공통 nav (Dashboard, Analytics, Quotes, Migration), footer |

**네비게이션 순서**: Dashboard → Analytics → Quotes → Migration

---

## 7. LLM Integration

### 분석 진입 조건 (`app/llm/analyzer.py:should_analyze`)

다음 중 하나라도 해당하면 LLM 분석 실행:

1. notes가 변경되었고 renewal에 notes가 존재
2. endorsement description이 변경됨
3. Home 정책에서 water_backup 상태가 변경됨

### 분석 흐름

```
should_analyze(diff, pair) ──▶ True?
       │                            │ No → skip
       │ Yes                        │
  analyze_pair(client, diff, pair)
       │
       ├── _analyze_notes()          ← RISK_SIGNAL_EXTRACTOR 프롬프트
       ├── _analyze_endorsement()    ← ENDORSEMENT_COMPARISON 프롬프트
       └── _analyze_coverage()       ← COVERAGE_SIMILARITY 프롬프트
       │
  aggregate(policy_number, rule_risk, diff, insights) → ReviewResult
```

### Review Summary LLM 전환 (`app/llm/analyzer.py:generate_summary`)

`should_analyze()` 결과와 무관하게, flag가 있는 모든 policy에 대해 LLM summary 생성.
기존 mechanical format (`"Risk: URGENT_REVIEW | Flags: 3"`)을 2-3문장 자연어 요약으로 대체.

- 입력: ReviewResult (policy 메타, diff, flags, LLM insights)
- key_changes: flag가 있는 변경을 우선으로 최대 5개 선택
- 실패 시 기존 mechanical summary 유지 (None 반환)

### Quote 개인화 (`app/llm/quote_advisor.py:personalize_quotes`)

Quote의 hardcoded trade_off를 고객 맥락 기반 개인화 텍스트로 대체하고, broker_tip 추가.
전략 선택과 savings 계산은 rule-based 유지.

- 단일 LLM 호출로 최대 3개 quote를 일괄 처리
- `_build_policy_context(pair)` — 비어있지 않은 섹션만 포함
- partial match 지원: 3개 중 2개만 반환되면 나머지는 원본 유지
- `settings.llm_enabled` 토글 존중 (`app/routes/quotes.py`)

### Fallback 동작

| 시나리오 | Summary | Quote |
|----------|---------|-------|
| `llm_enabled=false` | 기존 mechanical format | hardcoded trade_off, broker_tip="" |
| LLM API 에러 | mechanical summary 유지 | 원본 trade_off 유지, broker_tip="" |
| LLM 부분 응답 | N/A | 매칭된 quote만 개인화, 나머지 원본 |
| Flag 없는 policy | summary 생성 건너뜀 | quote 자체가 빈 리스트 |

### 5개 프롬프트 (`app/llm/prompts.py`)

| 프롬프트 | 역할 | 입력 | 출력 (JSON) |
|---------|------|------|------------|
| `RISK_SIGNAL_EXTRACTOR` | 갱신 notes에서 risk signal 추출 | notes 텍스트 | signals[], confidence, summary |
| `ENDORSEMENT_COMPARISON` | 특약 설명 변경의 material change 판단 | prior/renewal description | material_change, change_type, confidence, reasoning |
| `COVERAGE_SIMILARITY` | 두 coverage의 동등성 비교 | prior/renewal coverage 텍스트 | equivalent, confidence, reasoning |
| `REVIEW_SUMMARY` | 리뷰 결과를 자연어 요약으로 변환 | policy 메타 + flags + changes + insights | summary |
| `QUOTE_PERSONALIZATION` | Quote trade_off/broker_tip 개인화 | policy context + quotes 배열 | quotes[{quote_id, trade_off, broker_tip}] |

### Provider 구성 (`app/llm/client.py`)

- **OpenAI**: gpt-4o-mini (temperature=0.1, json_object mode)
- **Anthropic**: claude-sonnet-4-5-20250929 (max_tokens=1024)
- **MockLLMClient** (`app/llm/mock.py`): 테스트·migration 비교용 하드코딩 응답
- **Langfuse tracing**: `LANGFUSE_PUBLIC_KEY` 환경변수 존재 시 자동 활성화. 각 LLM 호출을 generation observation으로 기록

---

## 8. Error Handling

### HTTP 에러

| Status | 경로 | 조건 |
|--------|------|------|
| 404 | `GET /reviews/{pn}` | 해당 policy_number 리뷰 없음 |
| 404 | `GET /batch/status/{job_id}` | 해당 job_id 없음 |
| 404 | `GET /migration/status/{job_id}` | 해당 job_id 없음 |
| 404 | `GET /ui/review/{pn}` | 해당 policy_number 리뷰 없음 |
| 404 | `POST /batch/run` | 데이터 없음 (JSON 파일 미생성) |
| 404 | `POST /eval/run` | Golden eval 파일 없음 |
| 404 | `POST /migration/comparison` | 데이터 없음 |
| 422 | `POST /reviews/compare` | 입력 JSON 파싱 실패 (KeyError, ValidationError) |
| 422 | `POST /quotes/generate` | 입력 JSON 파싱 실패 |

### Fallback 패턴

| 상황 | Fallback | 코드 위치 |
|------|----------|----------|
| DB 로드 실패 | JSON 파일로 폴백 | `app/data_loader.py:42-44` |
| LLM JSON 파싱 실패 | `{"error": ..., "raw_response": ...}` 반환 | `app/llm/client.py:57-58` |
| LLM 분석 에러 | confidence=0.0인 에러 LLMInsight 생성 | `app/llm/analyzer.py:34-40`, `64-68`, `84-88` |
| LLM summary 실패 | 기존 mechanical summary 유지 | `app/engine/batch.py` |
| LLM quote 개인화 실패 | 원본 trade_off 유지, broker_tip="" | `app/llm/quote_advisor.py` |

### Async Job 실패

배치(`/batch/run`)와 migration(`/migration/comparison`) 비동기 작업:
- `_process()` 내부에서 Exception 발생 시 job status를 `"failed"`로 설정
- `error` 필드에 에러 메시지 저장
- 이후 status polling에서 클라이언트가 실패 상태 확인 가능

---

## 9. Non-Functional

### Storage

- **기본**: in-memory — `_results_store: dict[str, ReviewResult]`, `_history: deque[BatchRunRecord]`
- **Optional**: PostgreSQL — `RR_DB_URL` 환경변수 설정 시 활성화. SQLAlchemy async engine (asyncpg) + sync fallback (psycopg)

### Caching

- `app/data_loader.py`: 모듈 레벨 `_cached_pairs` — 최초 load 후 캐시. `invalidate_cache()`로 초기화 가능
- 배치 실행 시 results_store를 clear 후 새 결과로 교체

### Concurrency

- `asyncio.create_task()`: 배치, migration 작업을 비동기 태스크로 실행
- `loop.run_in_executor(None, ...)`: CPU-bound 처리(diff, flag, LLM 호출)를 thread pool에서 실행
- progress callback으로 실시간 진행률 업데이트

### Limits

| 항목 | 제한 | 코드 위치 |
|------|------|----------|
| Analytics history | `deque(maxlen=100)` — FIFO 100건 | `app/routes/analytics.py:10-11` |
| Quote 최대 개수 | 3개 (`quotes[:3]`) | `app/engine/quote_generator.py:231` |
| Quote 최소 조건 | flags 존재 시에만 생성 | `app/engine/quote_generator.py:214-215` |
| UI 페이지네이션 | 50건/page (`PAGE_SIZE = 50`) | `app/routes/ui.py:23` |
| Migration 비교 샘플 | 기본 50, 최소 1 (`Query(50, ge=1)`) | `app/routes/eval.py:85` |

### Timezone

- `America/Vancouver` — BatchRunRecord.created_at 생성 시 적용 (`app/routes/batch.py:64-76`)

---

## 10. Tech Stack

### Runtime

| 항목 | 버전 / 값 |
|------|-----------|
| Python | ≥ 3.13 (`requires-python` in pyproject.toml) |
| 패키지 매니저 | uv |
| 웹 프레임워크 | FastAPI ≥ 0.115 |
| ASGI 서버 | uvicorn ≥ 0.34 |
| ORM | SQLAlchemy ≥ 2.0 (asyncio) |
| 검증 | Pydantic ≥ 2.10 |
| 템플릿 | Jinja2 ≥ 3.1 |
| LLM | OpenAI ≥ 2.18 (기본), Anthropic ≥ 0.43 (선택) |
| Observability | Langfuse ≥ 3.14 |
| DB 드라이버 | asyncpg ≥ 0.30, psycopg ≥ 3.1 |

### Dev Dependencies

| 패키지 | 버전 | 용도 |
|--------|------|------|
| pytest | ≥ 8.3 | 테스트 프레임워크 |
| hypothesis | ≥ 6.120 | Property-based 테스트 |
| httpx | ≥ 0.28 | TestClient (FastAPI 테스트 의존성) |
| ruff | ≥ 0.9 | Linter + formatter |

### 환경변수 (`RR_` prefix, `app/config.py`)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `RR_LLM_ENABLED` | `false` | LLM 분석 활성화 |
| `RR_LLM_PROVIDER` | `"openai"` | LLM provider (`openai` \| `anthropic`) |
| `RR_DATA_PATH` | `"data/renewals.json"` | 데이터 파일 경로 |
| `RR_DB_URL` | `""` | PostgreSQL URL (비어있으면 JSON 모드) |
| `LANGFUSE_PUBLIC_KEY` | — | 설정 시 Langfuse tracing 자동 활성화 |

### Ruff 설정 (`pyproject.toml`)

- target: Python 3.13
- line-length: 99
- lint rules: E, F, I, N, UP, B, SIM

### Data 디렉토리

```
data/
├── renewals.json             # 전체 정책 데이터 (generate.py로 생성)
└── samples/
    ├── auto_pair.json        # Auto 정책 샘플 (테스트/데모)
    ├── home_pair.json        # Home 정책 샘플
    └── golden_eval.json      # Golden eval 5개 시나리오
```

---

## 11. Testing

### 테스트 현황

11개 파일, 89개 테스트.

| 파일 | 테스트 수 | 검증 대상 |
|------|----------|----------|
| `tests/test_rules.py` | 15 | premium 임계값, flag 부여 규칙, liability/deductible/coverage/endorsement |
| `tests/test_differ.py` | 13 | 필드별 diff 계산, 동일 정책 no-change, vehicle/endorsement/coverage 변경 |
| `tests/test_routes.py` | 9 | health, compare, get_review, batch run/status/summary |
| `tests/test_parser.py` | 8 | snapshot/pair 파싱, vehicle/driver/endorsement, 날짜 정규화, notes |
| `tests/test_quote_generator.py` | 11 | Auto/Home 전략, 이미 최적화된 케이스, liability 보호, 라우트 통합, LLM 개인화 |
| `tests/test_batch.py` | 7 | process_pair, assign_risk_level 4단계, process_batch |
| `tests/test_llm_analyzer.py` | 11 | should_analyze 조건, notes/endorsement/coverage 분석, MockLLM 통합, generate_summary |
| `tests/test_analytics.py` | 6 | compute_trends (empty/single/multiple), 라우트, FIFO 제한 |
| `tests/test_models.py` | 6 | 모델 구조, DiffFlag 값, risk level 순서 |
| `tests/test_main.py` | 1 | /health 엔드포인트 |
| `tests/conftest.py` | — | 공통 fixture (auto_pair, home_pair 등) |

### Golden Eval (`data/samples/golden_eval.json`)

5개 시나리오:

| # | 설명 |
|---|------|
| 1 | 10% premium increase with rate adjustment note |
| 2 | 25% premium increase, water backup dropped, deductible raised, claim history note |
| 3 | Carrier switch, liability downgrade, vehicle removed, teen driver added |
| 4 | Clean renewal with minor premium increase (2.2%) |
| 5 | Inflation guard with endorsement description update and 10% premium increase |

`POST /eval/run`으로 실행. 각 케이스에 대해 expected_min_risk와 expected_flags를 실제 결과와 대조하여 accuracy 산출.
