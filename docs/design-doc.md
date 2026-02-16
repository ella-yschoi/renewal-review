# Renewal Review — System Design Document

---

## 1. Overview

보험 갱신(renewal) 정책을 자동으로 비교·분석하여 위험 수준을 판정하는 파이프라인 기반 대시보드 시각화.

- **Prior vs Renewal 비교**: 기존 정책과 갱신 정책의 모든 필드를 diff하고, 주의가 필요한 변경에 flag를 부여
- **Rule + LLM 하이브리드**: 규칙 기반 risk 판정 후, 조건 충족 시 LLM이 notes·endorsement를 심층 분석하여 risk를 상향 조정
- **대안 견적 생성**: flagged 정책에 대해 보장 조정 전략별 절감 견적(Quote)을 최대 3개 제안
- **Portfolio Risk Aggregator**: 클라이언트의 복수 정책을 묶어 교차 분석 — 번들 할인, 중복 보장, 노출도 평가 (rule-based)

**대상 사용자**: 보험 언더라이터, 갱신 심사 담당자

---

## 2. Architecture

### 헥사고날 아키텍처 (Ports & Adapters)

```
의존성 방향: api/ → application/ → domain/ ← adaptor/

               ┌───────────────────────────────────────────────┐
               │                  FastAPI App                   │
               └───────────────────────┬───────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
┌───────▼────────┐          ┌──────────▼──────────┐        ┌─────────▼──────────┐
│   api/ (인바운드) │──────▶│   application/       │        │  adaptor/ (아웃바운드) │
│   FastAPI 라우트  │         │   유스케이스 오케스트레이션 │◀───────│  LLM / Storage / DB │
└────────────────┘          └──────────┬──────────┘        └─────────┬──────────┘
                                       │                              │
                            ┌──────────▼──────────┐                  │
                            │   domain/ (내부 헥사곤) │◀─────────────────┘
                            │   순수 비즈니스 로직     │    ports/ Protocol 구현
                            │   models/ services/   │
                            │   ports/ (인터페이스)   │
                            └───────────────────────┘
                                       │
                            ┌──────────▼──────────┐
                            │   infra/             │
                            │   DI 와이어링 + DB     │
                            └───────────────────────┘
```

### 핵심 원칙

- `domain/`은 외부 모듈을 import하지 않는다 (`ports/` Protocol만 정의)
- `application/`은 `domain/` + `ports/`만 import한다 (구현체 X)
- 외부 시스템 변경은 `adaptor/`에서 흡수, 도메인으로 전파되지 않음

### 모듈 디렉토리

```
app/
├── main.py                    # 컴포지션 루트 — lifespan(init_db) + 라우터 등록
├── config.py                  # Settings + 중첩 설정 (Rules, Quotes, Portfolio, LLM)
├── data_loader.py             # 데이터 소스 팩토리 (→ adaptor/ 위임)
│
├── domain/                    # 내부 헥사곤 — 순수 비즈니스 로직
│   ├── models/
│   │   ├── enums.py           # Severity, UnbundleRisk, QuoteStrategy, AnalysisType, FlagType
│   │   ├── policy.py          # PolicySnapshot, RenewalPair, Coverages
│   │   ├── diff.py            # DiffFlag, FieldChange (frozen), DiffResult
│   │   ├── review.py          # RiskLevel, LLMInsight, ReviewResult, BatchSummary
│   │   ├── quote.py           # CoverageAdjustment, QuoteRecommendation
│   │   ├── portfolio.py       # CrossPolicyFlag, BundleAnalysis, PortfolioSummary
│   │   ├── analytics.py       # BatchRunRecord, TrendPoint, AnalyticsSummary
│   │   └── llm_schemas.py     # LLM 응답 검증 Pydantic 스키마
│   ├── services/
│   │   ├── parser.py          # raw dict → RenewalPair
│   │   ├── differ.py          # Prior ↔ Renewal diff
│   │   ├── rules.py           # flag 부여 (functional, no mutation)
│   │   ├── aggregator.py      # rule_risk + LLM → final risk
│   │   ├── quote_generator.py # 절감 전략 → QuoteRecommendation
│   │   ├── portfolio_analyzer.py # 교차 분석 (bundle, flags)
│   │   └── analytics.py       # compute_trends
│   └── ports/
│       ├── llm.py             # LLMPort Protocol
│       ├── storage.py         # ReviewStore, HistoryStore, JobStore Protocol
│       └── data_source.py     # DataSourcePort Protocol
│
├── application/               # 유스케이스 — 도메인 + 포트 오케스트레이션
│   ├── batch.py               # process_pair, process_batch, assign_risk_level
│   ├── llm_analysis.py        # should_analyze, analyze_pair, generate_summary
│   ├── quote_advisor.py       # personalize_quotes (LLM 개인화 오케스트레이션)
│   └── prompts.py             # 4개 LLM 프롬프트 템플릿 (ACORD 정렬)
│
├── api/                       # 인바운드 어댑터 — FastAPI 라우트 + Depends()
│   ├── reviews.py             # POST /reviews/compare, GET /reviews/{pn}
│   ├── batch.py               # POST /batch/run, GET /batch/status, GET /batch/summary
│   ├── analytics.py           # GET /analytics/history, GET /analytics/trends
│   ├── quotes.py              # POST /quotes/generate
│   ├── portfolio.py           # POST /portfolio/analyze
│   ├── eval.py                # POST /eval/run, POST /migration/comparison
│   └── ui.py                  # GET /, /ui/review/{pn}, /ui/analytics, /ui/quotes, /ui/portfolio
│
├── adaptor/                   # 아웃바운드 어댑터 — 외부 시스템 구현체
│   ├── llm/
│   │   ├── client.py          # create_llm_client() 팩토리
│   │   ├── openai.py          # OpenAIClient (LLMPort 구현)
│   │   ├── anthropic.py       # AnthropicClient (LLMPort 구현)
│   │   └── mock.py            # MockLLMClient
│   ├── storage/
│   │   └── memory.py          # InMemoryReviewStore, InMemoryHistoryStore, InMemoryJobStore
│   └── persistence/
│       ├── json_loader.py     # JsonDataSource (DataSourcePort 구현)
│       └── db_loader.py       # DbDataSource (DataSourcePort 구현)
│
├── infra/                     # 인프라 — DI 와이어링, DB
│   ├── db.py                  # SQLAlchemy async engine
│   ├── db_models.py           # ORM — RenewalPairRow, BatchResultRow
│   └── deps.py                # FastAPI Depends 와이어링 (싱글턴 스토어)
│
└── templates/
    ├── base.html, dashboard.html, review.html, analytics.html
    ├── quotes.html, portfolio.html, migration.html
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

### Enum 중앙 정의 (`app/domain/models/enums.py`)

| Enum | 값 | 사용처 |
|------|---|-------|
| `Severity` | info, warning, critical | CrossPolicyFlag.severity |
| `UnbundleRisk` | low, medium, high | BundleAnalysis.unbundle_risk |
| `QuoteStrategy` | raise_deductible, drop_optional, reduce_medical, drop_water_backup, reduce_personal_property | CoverageAdjustment.strategy |
| `AnalysisType` | risk_signal_extractor, endorsement_comparison | LLMInsight.analysis_type |
| `LLMTaskName` | risk_signal_extractor, endorsement_comparison, review_summary, quote_personalization | LLM 호출 trace_name, config.task_models 키 |
| `FlagType` | duplicate_medical, duplicate_roadside, high/low_liability_exposure, premium_concentration, high_portfolio_increase | CrossPolicyFlag.flag_type |

### Policy 도메인 (`app/domain/models/policy.py`)

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

### Diff 도메인 (`app/domain/models/diff.py`)

| 모델 | 설명 | 핵심 필드 |
|------|------|-----------|
| `FieldChange` | 단일 필드 변경 (frozen) | field, prior_value, renewal_value, change_pct, flag |
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

### Review 도메인 (`app/domain/models/review.py`)

| 모델 | 설명 | 핵심 필드 |
|------|------|-----------|
| `RiskLevel` | StrEnum — 4단계 | no_action_needed, review_recommended, action_required, urgent_review |
| `LLMInsight` | LLM 분석 1건 | analysis_type, finding, confidence, reasoning |
| `ReviewResult` | 최종 리뷰 결과 | policy_number, risk_level, diff, llm_insights, summary, pair |
| `BatchSummary` | 배치 실행 요약 | total, risk level별 카운트, llm_analyzed, processing_time_ms |

### Analytics 도메인 (`app/domain/models/analytics.py`)

| 모델 | 설명 | 핵심 필드 |
|------|------|-----------|
| `BatchRunRecord` | 배치 1회 기록 | job_id, total, risk level별 카운트, processing_time_ms, created_at |
| `TrendPoint` | 일별 집계 | date, total_runs, avg_processing_time_ms, urgent_review_ratio |
| `AnalyticsSummary` | 전체 분석 요약 | total_runs, total_policies_reviewed, avg_processing_time_ms, risk_distribution, trends |

### Quote 도메인 (`app/domain/models/quote.py`)

| 모델 | 설명 | 핵심 필드 |
|------|------|-----------|
| `CoverageAdjustment` | 개별 조정 항목 | field, original_value, proposed_value, strategy |
| `QuoteRecommendation` | 대안 견적 1건 | quote_id (Q1~Q3), adjustments, estimated_savings_pct, estimated_savings_dollar, trade_off, broker_tip |

### Portfolio 도메인 (`app/domain/models/portfolio.py`)

| 모델 | 설명 | 핵심 필드 |
|------|------|-----------|
| `CrossPolicyFlag` | 정책 간 교차 이슈 | flag_type, severity, description, affected_policies |
| `BundleAnalysis` | 번들 분석 결과 | has_auto, has_home, is_bundle, bundle_discount_eligible, carrier_mismatch, unbundle_risk |
| `PortfolioSummary` | 포트폴리오 전체 요약 | client_policies, total_premium, total_prior_premium, premium_change_pct, risk_breakdown, bundle_analysis, cross_policy_flags |

### DB 모델 (`app/infra/db_models.py`)

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
> (`app/application/batch.py:17-25`)

### LLM Risk Upgrade 조건 (`app/domain/services/aggregator.py`)

LLM 분석 결과에 따라 rule_risk보다 높은 level로 상향. 하향은 없음.

| 조건 | 상향 대상 |
|------|----------|
| risk_signal 2건 이상 (confidence ≥ 0.7) | → `action_required` 이상 |
| endorsement restriction (confidence ≥ 0.75) | → `action_required` 이상 |
| 위 조건 복합 (restriction + risk_signal ≥ 2) | → `urgent_review` |

### Flag 트리거 임계값 (`app/domain/services/rules.py`)

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

### Quote Generator 전략 (`app/domain/services/quote_generator.py`)

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
| POST | `/portfolio/analyze` | 포트폴리오 교차 분석 | `PortfolioSummary` | 200, 422 |

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
| GET | `/ui/insight` | LLM Insights (Basic vs LLM 비교) |
| GET | `/ui/quotes` | Quote Generator |
| GET | `/ui/portfolio` | Portfolio Risk Aggregator |

---

## 6. UI

| # | 페이지 | Route | 주요 기능 |
|---|--------|-------|----------|
| 1 | Dashboard | `GET /` | 전체 리뷰 목록 (severity 내림차순 정렬), 배치 요약 표시, 페이지네이션 (50건/page) |
| 2 | Review Detail | `GET /ui/review/{pn}` | 단건 리뷰 상세 — diff, flags, risk level, LLM insights. 파이프라인 라벨 표시 (Basic Analytics / LLM Analytics). ref 파라미터로 돌아갈 페이지 결정 |
| 3 | Analytics | `GET /ui/analytics` | 배치 이력 목록 + 트렌드 차트 (risk distribution, 일별 urgent_review_ratio) |
| 4 | Quote Generator | `GET /ui/quotes` | flagged 정책 목록 표시. "Generate Quotes" 클릭 → `/reviews/{pn}` + `/quotes/generate` 호출하여 대안 견적 모달 표시. 페이지네이션 |
| 5 | LLM Insights | `GET /ui/insight` | Basic vs LLM 비교 대시보드. element ID: `basic-*`, `llm-*`. 비동기 실행 후 polling으로 결과 표시 |
| 6 | Portfolio | `GET /ui/portfolio` | 정책 목록 표시, 복수 선택 → Analyze Portfolio 클릭 시 POST /portfolio/analyze 호출. Rule-based verdict/recommendations/action items 표시 |
| 7 | Base Layout | — | 공통 nav, footer |

**네비게이션 순서**: Dashboard → Analytics → LLM Insights → Quote Generator → Portfolio

---

## 7. LLM Integration

### 분석 진입 조건 (`app/application/llm_analysis.py:should_analyze`)

다음 중 하나라도 해당하면 LLM 분석 실행:

1. notes가 변경되었고 renewal에 notes가 존재
2. endorsement description이 변경됨

### 분석 흐름

```
should_analyze(diff, pair) ──▶ True?
       │                            │ No → skip
       │ Yes                        │
  analyze_pair(client, diff, pair)
       │
       ├── _analyze_notes()          ← RISK_SIGNAL_EXTRACTOR 프롬프트
       └── _analyze_endorsement()    ← ENDORSEMENT_COMPARISON 프롬프트
       │
  aggregate(policy_number, rule_risk, diff, insights) → ReviewResult
```

### Review Summary LLM 전환 (`app/application/llm_analysis.py:generate_summary`)

`should_analyze()` 결과와 무관하게, flag가 있는 모든 policy에 대해 LLM summary 생성.
기존 mechanical format (`"Risk: URGENT_REVIEW | Flags: 3"`)을 2-3문장 자연어 요약으로 대체.

- 입력: ReviewResult (policy 메타, diff, flags, LLM insights)
- key_changes: flag가 있는 변경을 우선으로 최대 5개 선택
- 실패 시 기존 mechanical summary 유지 (None 반환)

### Quote 개인화 (`app/application/quote_advisor.py:personalize_quotes`)

Quote의 hardcoded trade_off를 고객 맥락 기반 개인화 텍스트로 대체하고, broker_tip 추가.
전략 선택과 savings 계산은 rule-based 유지.

- 단일 LLM 호출로 최대 3개 quote를 일괄 처리
- `_build_policy_context(pair)` — 비어있지 않은 섹션만 포함
- partial match 지원: 3개 중 2개만 반환되면 나머지는 원본 유지
- `settings.llm_enabled` 토글 존중 (`app/api/quotes.py`)

### Fallback 동작

| 시나리오 | Summary | Quote |
|----------|---------|-------|
| `llm_enabled=false` | 기존 mechanical format | hardcoded trade_off, broker_tip="" |
| LLM API 에러 | mechanical summary 유지 | 원본 trade_off 유지, broker_tip="" |
| LLM 부분 응답 | N/A | 매칭된 quote만 개인화, 나머지 원본 |
| Flag 없는 policy | summary 생성 건너뜀 | quote 자체가 빈 리스트 |

### 4개 프롬프트 (`app/application/prompts.py`)

| 프롬프트 | 역할 | ACORD 정렬 | 출력 (JSON) |
|---------|------|-----------|------------|
| `RISK_SIGNAL_EXTRACTOR` | 갱신 notes에서 risk signal 추출 | 6개 signal type (claims_history, property_risk, driver_risk, coverage_gap, regulatory, other) | signals[], confidence, summary |
| `ENDORSEMENT_COMPARISON` | 특약 설명 변경의 material change 판단 | HO 04 xx / PP 03 xx form 참조, ACORD change type (A/C/D) | material_change, change_type, confidence, reasoning |
| `REVIEW_SUMMARY` | 리뷰 결과를 자연어 요약으로 변환 | liability limit (BI/PD/Coverage E) 우선, 브로커 액션 지향 | summary |
| `QUOTE_PERSONALIZATION` | Quote trade_off/broker_tip 개인화 | 보호 필드(BI, PD, UM, Cov A, Cov E) 감소 금지 명시 | quotes[{quote_id, trade_off, broker_tip}] |

### LLM 응답 검증 스키마 (`app/domain/models/llm_schemas.py`)

모든 LLM 응답은 Pydantic 모델로 `model_validate()` 검증 후 타입 안전하게 접근. 필드 누락 시 `ValidationError` → 기존 fallback 경로로 처리.

| 스키마 | 대상 프롬프트 | 핵심 필드 |
|--------|-------------|----------|
| `RiskSignalExtractorResponse` | `RISK_SIGNAL_EXTRACTOR` | signals: list[RiskSignal], confidence, summary |
| `EndorsementComparisonResponse` | `ENDORSEMENT_COMPARISON` | material_change, change_type, confidence, reasoning |
| `ReviewSummaryResponse` | `REVIEW_SUMMARY` | summary |
| `QuotePersonalizationResponse` | `QUOTE_PERSONALIZATION` | quotes: list[PersonalizedQuote] |

### Provider 구성 (`app/adaptor/llm/`)

- **OpenAI** (`openai.py`): `OpenAIClient(model=)` — model 주입 가능, 기본값 gpt-4o-mini
- **Anthropic** (`anthropic.py`): `AnthropicClient(model=)` — model 주입 가능, 기본값 claude-sonnet
- **Routing** (`app/adaptor/llm/client.py`): `LLMClient` — `trace_name` 기반 task별 모델 라우팅. `settings.llm.task_models` 매핑에 따라 provider+model 자동 선택. 동일 (provider, model) 조합은 인스턴스 재사용
- **MockLLMClient** (`app/adaptor/llm/mock.py`): 테스트·migration 비교용 하드코딩 응답
- **Langfuse tracing**: 각 provider에 내장. `LANGFUSE_PUBLIC_KEY` 환경변수 존재 시 자동 활성화

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
| 422 | `POST /portfolio/analyze` | 정책 수 부족 (< 2) 또는 리뷰 미존재 |

### Fallback 패턴

| 상황 | Fallback | 코드 위치 |
|------|----------|----------|
| DB 로드 실패 | JSON 파일로 폴백 | `app/data_loader.py:42-44` |
| LLM JSON 파싱 실패 | `{"error": ..., "raw_response": ...}` 반환 | `app/adaptor/llm/openai.py`, `anthropic.py` |
| LLM 분석 에러 / 응답 스키마 불일치 | confidence=0.0인 에러 LLMInsight 생성 | `app/application/llm_analysis.py` |
| LLM summary 실패 | 기존 mechanical summary 유지 | `app/application/batch.py` |
| LLM quote 개인화 실패 | 원본 trade_off 유지, broker_tip="" | `app/application/quote_advisor.py` |

### Async Job 실패

배치(`/batch/run`)와 migration(`/migration/comparison`) 비동기 작업:
- `_process()` 내부에서 Exception 발생 시 job status를 `"failed"`로 설정
- `error` 필드에 에러 메시지 저장
- 이후 status polling에서 클라이언트가 실패 상태 확인 가능

---

## 9. Non-Functional

### Storage

- **기본**: in-memory — `InMemoryReviewStore`, `InMemoryHistoryStore`, `InMemoryJobStore` (`app/adaptor/storage/memory.py`), `Depends()`로 주입 (`app/infra/deps.py`)
- **Optional**: PostgreSQL — `RR_DB_URL` 환경변수 설정 시 활성화. SQLAlchemy async engine (asyncpg) + sync fallback (psycopg). FastAPI lifespan에서 `init_db()` 호출하여 앱 시작 시 테이블 자동 생성

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
| Analytics history | `deque(maxlen=100)` — FIFO 100건 | `app/api/analytics.py:10-11` |
| Quote 최대 개수 | 3개 (`quotes[:3]`) | `app/domain/services/quote_generator.py` |
| Quote 최소 조건 | flags 존재 시에만 생성 | `app/domain/services/quote_generator.py` |
| UI 페이지네이션 | 50건/page (`PAGE_SIZE = 50`) | `app/api/ui.py:23` |
| Migration 비교 샘플 | 기본 50, 최소 1 (`Query(50, ge=1)`) | `app/api/eval.py:85` |

### Docker

- `Dockerfile`: python:3.13-slim + uv, 의존성 레이어 캐싱 (`pyproject.toml` + `uv.lock` 먼저 복사)
- `docker-compose.yml`: `db` (postgres:16-alpine, healthcheck) + `app` (소스 volume mount, `--reload`)
- `app` 서비스는 `environment.RR_DB_URL`로 호스트를 `db`(서비스명)로 오버라이드
- `depends_on: db: condition: service_healthy` — DB 준비 후 앱 시작
- `Makefile`: `compose-up` (빌드+실행), `compose-down` (중지), `dev`/`test`/`lint` (로컬용)
- `main.py` lifespan에서 `init_db()` 호출 → 앱 시작 시 테이블 자동 생성

### Timezone

- `America/Vancouver` — BatchRunRecord.created_at 생성 시 적용 (`app/api/batch.py:64-76`)

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
| LLM (optional) | OpenAI ≥ 2.18, Anthropic ≥ 0.43, Langfuse ≥ 3.14 — `pip install .[llm]` |
| DB 드라이버 | asyncpg ≥ 0.30, psycopg ≥ 3.1 |
| 컨테이너 | Docker (python:3.13-slim + uv), Docker Compose |
| DB | PostgreSQL 16 (alpine) |

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
| `RR_DATA_PATH` | `"data/renewals.json"` | 데이터 파일 경로 |
| `RR_DB_URL` | `""` | PostgreSQL URL (비어있으면 JSON 모드) |
| `LANGFUSE_PUBLIC_KEY` | — | 설정 시 Langfuse tracing 자동 활성화 |

### 중첩 설정 (`app/config.py`)

| 클래스 | 핵심 필드 | 참조 위치 |
|--------|----------|----------|
| `RuleThresholds` | premium_high_pct (10.0), premium_critical_pct (20.0) | `domain/services/rules.py` (파라미터 주입) |
| `QuoteConfig` | auto_collision/comprehensive_deductible, savings_* (12개) | `domain/services/quote_generator.py` (파라미터 주입) |
| `PortfolioThresholds` | high/low_liability, concentration_pct, portfolio_change_pct | `domain/services/portfolio_analyzer.py` (파라미터 주입) |
| `LLMConfig` | sonnet_model, haiku_model, max_tokens, task_models (ModelKey 사용) | `adaptor/llm/client.py` (라우팅), `anthropic.py` |

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

11개 파일, 100개 테스트.

| 파일 | 테스트 수 | 검증 대상 |
|------|----------|----------|
| `tests/test_rules.py` | 16 | premium 임계값, flag 부여 규칙, liability/deductible/coverage/endorsement |
| `tests/test_differ.py` | 14 | 필드별 diff 계산, 동일 정책 no-change, vehicle/endorsement/coverage 변경 |
| `tests/test_routes.py` | 9 | health, compare, get_review, batch run/status/summary |
| `tests/test_parser.py` | 8 | snapshot/pair 파싱, vehicle/driver/endorsement, 날짜 정규화, notes |
| `tests/test_quote_generator.py` | 12 | Auto/Home 전략, 이미 최적화된 케이스, liability 보호, 라우트 통합, LLM 개인화, malformed 응답 |
| `tests/test_batch.py` | 7 | process_pair, assign_risk_level 4단계, process_batch |
| `tests/test_llm_analyzer.py` | 13 | should_analyze 조건, notes/endorsement 분석, MockLLM 통합, generate_summary, malformed 응답 fallback |
| `tests/test_analytics.py` | 6 | compute_trends (empty/single/multiple), 라우트, FIFO 제한 |
| `tests/test_models.py` | 6 | 모델 구조, DiffFlag 값, risk level 순서 |
| `tests/test_portfolio.py` | 8 | bundle 분석, 중복 커버리지, unbundle risk, premium concentration |
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
