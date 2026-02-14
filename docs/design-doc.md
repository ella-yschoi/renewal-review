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

배치 실행 후 `app/routes/batch.py`의 `_process()` 내부에서 BatchRunRecord를 생성하여 analytics history store에 추가.

## 2. Data Model

### BatchRunRecord
배치 실행 1회의 요약 기록. job_id, risk level별 카운트(total/low/medium/high/critical), processing_time_ms, created_at.

### TrendPoint
일별 집계 데이터. date(YYYY-MM-DD), total_runs, avg_processing_time_ms, critical_ratio.

### AnalyticsSummary
전체 분석 결과. total_runs, total_policies_reviewed, avg_processing_time_ms, risk_distribution(dict), trends(list[TrendPoint]).

## 3. Processing Pipeline

`compute_trends(records)`: BatchRunRecord 리스트를 받아 AnalyticsSummary를 반환.
- 빈 리스트 → 제로 기본값
- risk_distribution: 전체 레코드의 risk level별 합산
- trends: created_at 기준 일별 그룹핑 후 TrendPoint 생성

## 4. API Surface

| Method | Path | Response Model |
|--------|------|---------------|
| GET | /analytics/history | list[BatchRunRecord] |
| GET | /analytics/trends | AnalyticsSummary |

## 5. UI

파이프라인 네이밍: V1/V2 → **Basic Analytics** (규칙 기반) / **LLM Analytics** (규칙+LLM).

- `review.html` — 리뷰 상세에서 파이프라인 라벨 표시 (Basic Analytics / LLM Analytics)
- `migration.html` — Basic vs LLM 비교 대시보드. element ID: `basic-*`, `llm-*`. JS에서 `d.basic.*`, `d.llm.*` 참조

## 6. Error Handling

## 7. Testing Strategy

`tests/test_analytics.py` — 5개 테스트:
- compute_trends: empty(0건), single(1건), multiple(3건+) 케이스
- 라우트: /analytics/history 빈 응답, /analytics/trends 데이터 응답

## 8. Tech Stack
