# Renewal Review — Design Document

> 요구사항: `docs/requirements.md` 참조
> 구현 계획: `docs/implementation-plan.md` 참조

_프로젝트 진행 중 작성 예정. 구현이 안정화되면 아래 섹션을 채운다._

---

## 1. Architecture

Analytics 모듈은 기존 계층 구조를 따라 3개 레이어로 구성:

- `app/models/analytics.py` — Pydantic 모델 (BatchRunRecord, TrendPoint, AnalyticsSummary)
- `app/engine/analytics.py` — 비즈니스 로직 (compute_trends)
- `app/routes/analytics.py` — API 엔드포인트 (/analytics/history, /analytics/trends)

히스토리 저장소는 `deque(maxlen=100)`으로 FIFO 100건 제한 적용. 배치 실행 후 `app/routes/batch.py`의 `_process()` 내부에서 BatchRunRecord를 생성하여 analytics history store에 추가. 100건 초과 시 가장 오래된 레코드가 자동 제거됨.

`app/data_loader.py`는 DB 로드 실패(비동기 컨텍스트 충돌) 시 JSON 파일로 폴백.

Quote Generator 모듈도 동일 패턴:

- `app/models/quote.py` — Pydantic 모델 (CoverageAdjustment, QuoteRecommendation)
- `app/engine/quote_generator.py` — 비즈니스 로직 (generate_quotes)
- `app/routes/quotes.py` — API 엔드포인트 (POST /quotes/generate)

Portfolio Risk Aggregator 모듈:

- `app/models/portfolio.py` — Pydantic 모델 (CrossPolicyFlag, BundleAnalysis, PortfolioSummary)
- `app/engine/portfolio_analyzer.py` — 비즈니스 로직 (analyze_portfolio)
- `app/routes/portfolio.py` — API 엔드포인트 (POST /portfolio/analyze)

## 2. Data Model

### BatchRunRecord
배치 실행 1회의 요약 기록. job_id, risk level별 카운트(total/no_action_needed/review_recommended/action_required/urgent_review), processing_time_ms, created_at.

### TrendPoint
일별 집계 데이터. date(YYYY-MM-DD), total_runs, avg_processing_time_ms, urgent_review_ratio.

### AnalyticsSummary
전체 분석 결과. total_runs, total_policies_reviewed, avg_processing_time_ms, risk_distribution(dict), trends(list[TrendPoint]).

### CoverageAdjustment
개별 커버리지 조정 항목. field(조정 필드명), original_value, proposed_value, strategy(적용 전략명).

### QuoteRecommendation
대안 견적. quote_id("Q1"~"Q3"), adjustments(list[CoverageAdjustment]), estimated_savings_pct(%), estimated_savings_dollar($), trade_off(트레이드오프 설명).

### CrossPolicyFlag
교차 정책 이슈. flag_type(이슈 종류), severity("info"/"warning"/"critical"), description(사람이 읽는 설명), affected_policies(관련 policy numbers).

### BundleAnalysis
번들 분석. has_auto, has_home, is_bundle, bundle_discount_eligible(동일 carrier 여부), carrier_mismatch, unbundle_risk("low"/"medium"/"high").

### PortfolioSummary
포트폴리오 요약. client_policies, total_premium, total_prior_premium, premium_change_pct, risk_breakdown(dict), bundle_analysis(BundleAnalysis), cross_policy_flags(list[CrossPolicyFlag]).

## 3. Processing Pipeline

`compute_trends(records)`: BatchRunRecord 리스트를 받아 AnalyticsSummary를 반환.
- 빈 리스트 → 제로 기본값
- risk_distribution: 전체 레코드의 risk level별 합산 (no_action_needed/review_recommended/action_required/urgent_review)
- trends: created_at 기준 일별 그룹핑 후 TrendPoint 생성

`generate_quotes(pair, diff)`: RenewalPair와 DiffResult를 받아 최대 3개의 QuoteRecommendation 반환.
- flags가 없으면 빈 리스트 (대안 불필요)
- Auto/Home 타입별 3가지 전략 독립 적용
- Auto: raise_deductible(10%), drop_optional(4%), reduce_medical(2.5%)
- Home: raise_deductible(12.5%), drop_water_backup(3%), reduce_personal_property(4%)
- 보호 제약: bodily_injury_limit, property_damage_limit, coverage_e_liability, uninsured_motorist, coverage_a_dwelling 절대 변경 불가
- 이미 최적화된 항목은 건너뛰기 (예: deductible이 이미 높은 경우)

`analyze_portfolio(policy_numbers, results_store)`: 정책 번호 리스트와 결과 저장소를 받아 PortfolioSummary 반환.
- 중복 정책 번호 제거 (dict.fromkeys)
- 번들 분석: auto + home 모두 존재 시 is_bundle, 동일 carrier면 bundle_discount_eligible
- unbundle_risk: 번들에서 action_required/urgent_review → high, review_recommended → medium
- 중복 보장 탐지: auto medical_payments + home coverage_f_medical → duplicate_medical, auto roadside + home endorsement(roadside/towing) → duplicate_roadside
- 총 노출 계산: home coverage_e_liability + auto bodily_injury_limit(first number × 1000) 합산, >$500K → high_liability_exposure, <$200K → low_liability_exposure
- 보험료 집중도: 단일 정책 ≥ 70% → premium_concentration, 전체 변동 ≥ 15% → high_portfolio_increase

## 4. API Surface

| Method | Path | Response Model |
|--------|------|---------------|
| GET | /analytics/history | list[BatchRunRecord] |
| GET | /analytics/trends | AnalyticsSummary |
| POST | /quotes/generate | list[QuoteRecommendation] |
| POST | /portfolio/analyze | PortfolioSummary |

## 5. UI

파이프라인 네이밍: V1/V2 → **Basic Analytics** (규칙 기반) / **LLM Analytics** (규칙+LLM).

- `review.html` — 리뷰 상세에서 파이프라인 라벨 표시 (Basic Analytics / LLM Analytics)
- `quotes.html` — Quote Generator UI. flagged 정책 목록 표시, "Generate Quotes" 클릭 시 JS로 `/reviews/{policy_number}` → `/quotes/generate` 호출하여 대안 견적 표시. 라우트: `GET /ui/quotes`
- `migration.html` — Basic vs LLM 비교 대시보드. element ID: `basic-*`, `llm-*`. JS에서 `d.basic.*`, `d.llm.*` 참조
- `portfolio.html` — Portfolio Risk Aggregator UI. 체크박스 테이블로 정책 선택 (최소 2개), "Analyze Portfolio" 클릭 시 JS로 `POST /portfolio/analyze` 호출. 모달 결과 표시 순서: (1) Health Verdict 배너 — risk_breakdown + cross_policy_flags에서 JS로 도출한 한 줄 건강 요약 (red/yellow/blue/green 4단계), (2) stats grid (premium/change/count), (3) risk distribution bar — 라벨에 건수+퍼센트 표시, 바 세그먼트 안에 건수 (폭 ≥15%), (4) bundle analysis — 권고 문장 (번들 할인 확인/캐리어 통합/교차 판매) + unbundle risk 경고 + 기존 check/cross 그리드, (5) cross-policy flags — severity-colored left border cards + FLAG_ACTIONS 맵 기반 액션 라인, (6) Action Items 체크리스트 — 모든 섹션에서 도출된 액션을 priority별 정렬 (critical → warning → info) 번호 리스트. 체크박스 직접 클릭 시 행 하이라이트 동기화. 라우트: `GET /ui/portfolio`

## 6. Error Handling

## 7. Testing Strategy

`tests/test_analytics.py` — 6개 테스트:
- compute_trends: empty(0건), single(1건), multiple(3건+) 케이스
- 라우트: /analytics/history 빈 응답, /analytics/trends 데이터 응답
- FIFO: 105건 추가 후 100건 유지 + 가장 오래된 5건 제거 확인

`tests/test_quote_generator.py` — 8개 테스트:
- Auto 전략 3개 모두 적용: 3개 견적 반환, 전략명/절감률 확인
- Home 전략 3개 모두 적용: 3개 견적 반환
- 이미 최적화된 Auto: 모든 전략 건너뛰기 → 빈 리스트
- 보호 제약 검증: 모든 견적에서 liability 필드 불변
- flags 없는 정책: 빈 리스트
- 라우트 통합 테스트: POST /quotes/generate (Auto, Home)

`tests/test_portfolio.py` — 8개 테스트:
- auto + home 번들: is_bundle=True, premium 합산 검증
- auto만: is_bundle=False
- 중복 medical 탐지: duplicate_medical flag 생성
- unbundle_risk high: ACTION_REQUIRED 포함 시
- premium_concentration: 한 정책 70% 이상
- high_portfolio_increase: 전체 변동 15% 이상
- 1개 정책 → 422 에러
- 존재하지 않는 policy → 422 에러

## 8. Tech Stack
