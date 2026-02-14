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

Quote Generator 모듈도 동일한 3계층 구조:

- `app/models/quote.py` — Pydantic 모델 (CoverageAdjustment, QuoteRecommendation)
- `app/engine/quote_generator.py` — 전략 기반 견적 생성 (generate_quotes)
- `app/routes/quotes.py` — API 엔드포인트 (POST /quotes/generate)

## 2. Data Model

### BatchRunRecord
배치 실행 1회의 요약 기록. job_id, risk level별 카운트(total/low/medium/high/critical), processing_time_ms, created_at.

### TrendPoint
일별 집계 데이터. date(YYYY-MM-DD), total_runs, avg_processing_time_ms, critical_ratio.

### AnalyticsSummary
전체 분석 결과. total_runs, total_policies_reviewed, avg_processing_time_ms, risk_distribution(dict), trends(list[TrendPoint]).

### CoverageAdjustment
개별 커버리지 조정 항목. field, original_value, proposed_value, strategy.

### QuoteRecommendation
대안 견적. quote_id, adjustments(list[CoverageAdjustment]), estimated_savings_pct, estimated_savings_dollar, trade_off.

## 3. Processing Pipeline

`generate_quotes(pair, diff)`: RenewalPair + DiffResult를 받아 최대 3개 QuoteRecommendation 반환. Auto/Home 각 3가지 전략을 독립 적용. PROTECTED_FIELDS(liability 등 5개)는 절대 조정 불가. 이미 최적화된 항목은 건너뛰기.

`compute_trends(records)`: BatchRunRecord 리스트를 받아 AnalyticsSummary를 반환.
- 빈 리스트 → 제로 기본값
- risk_distribution: 전체 레코드의 risk level별 합산
- trends: created_at 기준 일별 그룹핑 후 TrendPoint 생성

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

`tests/test_quote_generator.py` — 8개 테스트:
- Auto 전략 3개 적용 가능 / Home 전략 3개 적용 가능
- 이미 최적화된 Auto (빈 리스트) / 보호 필드 불변 검증
- flags 없는 정책 (빈 리스트) / 기존 테스트 regression
- 라우트 통합: Auto + Home POST /quotes/generate

`tests/test_analytics.py` — 6개 테스트:
- compute_trends: empty(0건), single(1건), multiple(3건+) 케이스
- 라우트: /analytics/history 빈 응답, /analytics/trends 데이터 응답
- FIFO: 105건 추가 후 100건 유지 + 가장 오래된 5건 제거 확인

## 8. Tech Stack
