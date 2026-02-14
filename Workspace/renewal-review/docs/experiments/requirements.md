# Analytics Module — Requirements

## Overview

renewal-review 파이프라인에 Analytics 모듈을 추가한다. 배치 실행 이력을 저장하고, 시간에 따른 추세(trends)를 분석하는 기능.

---

## Functional Requirements

### FR-1: Batch History 저장

배치 실행(`POST /batch/run`) 완료 시 결과를 인메모리 히스토리에 저장한다.

**수락 기준:**
- 배치 실행 후 `BatchRunRecord`가 히스토리 리스트에 추가됨
- 기존 배치 라우트의 응답 형식은 변경하지 않음
- 히스토리는 최대 100건까지 보관 (FIFO)

### FR-2: Analytics 모델

3개의 Pydantic 모델을 정의한다.

**수락 기준:**
- `BatchRunRecord`: timestamp, total, low/medium/high/critical 카운트, processing_time_ms, llm_analyzed
- `TrendPoint`: timestamp, metric_name, value
- `AnalyticsSummary`: total_runs, avg_processing_time_ms, risk_distribution(dict), trends(list[TrendPoint])

### FR-3: Analytics 서비스

`compute_trends(history: list[BatchRunRecord]) -> AnalyticsSummary` 함수를 구현한다.

**수락 기준:**
- 빈 히스토리 → total_runs=0, 빈 trends
- 1건 히스토리 → total_runs=1, trends에 해당 시점 데이터
- 3건+ 히스토리 → 시간순 정렬된 trend points, 올바른 평균 계산
- risk_distribution은 전체 히스토리의 누적 비율 (%)

### FR-4: Analytics 라우트

2개의 GET 엔드포인트를 추가한다.

**수락 기준:**
- `GET /analytics/trends` → `AnalyticsSummary` 반환
- `GET /analytics/history` → `list[BatchRunRecord]` 반환 (최신순)
- 히스토리가 비어 있으면 빈 리스트/기본값 반환 (에러 아님)
- `app/main.py`에 라우터 등록

### FR-5: 테스트

Analytics 모듈의 핵심 시나리오를 테스트한다.

**수락 기준:**
- 0건 히스토리 케이스: 기본값 반환 확인
- 1건 히스토리 케이스: 단일 데이터 정확성
- 3건+ 히스토리 케이스: 추세 계산 정확성, 시간순 정렬
- API 엔드포인트 통합 테스트 (TestClient)
- `tests/test_analytics.py`에 작성

### FR-6: 기존 테스트 호환

기존 68개 테스트가 전부 통과해야 한다.

**수락 기준:**
- `uv run pytest -q` 실행 시 전체 통과
- 기존 배치 라우트 응답 형식 변경 없음
- 기존 import 경로 변경 없음

---

## Non-Functional Requirements

- 모든 코드는 `convention.md` 준수 (docstring 금지, 300줄 제한, type hints 필수)
- `ruff check` 통과
- 요구사항에 명시되지 않은 기능은 추가하지 않음
