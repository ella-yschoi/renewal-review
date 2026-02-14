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

## 2. Data Model

### BatchRunRecord
배치 실행 1회의 요약 기록. job_id, risk level별 카운트(total/low/medium/high/critical), processing_time_ms, created_at.

### TrendPoint
일별 집계 데이터. date(YYYY-MM-DD), total_runs, avg_processing_time_ms, critical_ratio.

### AnalyticsSummary
전체 분석 결과. total_runs, total_policies_reviewed, avg_processing_time_ms, risk_distribution(dict), trends(list[TrendPoint]).

### CoverageAdjustment
개별 커버리지 조정 항목. field(조정 필드명), original_value, proposed_value, strategy(적용 전략명).

### QuoteRecommendation
대안 견적. quote_id("Q1"~"Q3"), adjustments(list[CoverageAdjustment]), estimated_savings_pct(%), estimated_savings_dollar($), trade_off(트레이드오프 설명).

## 3. Processing Pipeline

`compute_trends(records)`: BatchRunRecord 리스트를 받아 AnalyticsSummary를 반환.
- 빈 리스트 → 제로 기본값
- risk_distribution: 전체 레코드의 risk level별 합산
- trends: created_at 기준 일별 그룹핑 후 TrendPoint 생성

`generate_quotes(pair, diff)`: RenewalPair와 DiffResult를 받아 최대 3개의 QuoteRecommendation 반환.
- flags가 없으면 빈 리스트 (대안 불필요)
- Auto/Home 타입별 3가지 전략 독립 적용
- Auto: raise_deductible(10%), drop_optional(4%), reduce_medical(2.5%)
- Home: raise_deductible(12.5%), drop_water_backup(3%), reduce_personal_property(4%)
- 보호 제약: bodily_injury_limit, property_damage_limit, coverage_e_liability, uninsured_motorist, coverage_a_dwelling 절대 변경 불가
- 이미 최적화된 항목은 건너뛰기 (예: deductible이 이미 높은 경우)

## 4. API Surface

| Method | Path | Response Model |
|--------|------|---------------|
| GET | /analytics/history | list[BatchRunRecord] |
| GET | /analytics/trends | AnalyticsSummary |
| POST | /quotes/generate | list[QuoteRecommendation] |

## 5. UI

파이프라인 네이밍: V1/V2 → **Basic Analytics** (규칙 기반) / **LLM Analytics** (규칙+LLM).

- `review.html` — 리뷰 상세에서 파이프라인 라벨 표시 (Basic Analytics / LLM Analytics)
- `migration.html` — Basic vs LLM 비교 대시보드. element ID: `basic-*`, `llm-*`. JS에서 `d.basic.*`, `d.llm.*` 참조

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

## 8. Tech Stack
