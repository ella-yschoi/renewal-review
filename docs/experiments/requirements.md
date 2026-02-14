# Analytics Module — Requirements

## Overview

renewal-review 파이프라인에 Analytics 모듈을 추가한다.
현재 배치 실행(`POST /batch/run`)은 마지막 결과만 보관하고 이전 기록은 사라진다.
이 모듈은 **배치 실행 이력을 보관**하고, **시간에 따른 리스크 추세를 분석**하며,
**Dashboard에 Analytics 탭을 추가**해 시각화한다.

---

## 기존 코드 컨텍스트

이 모듈이 통합되는 기존 코드를 먼저 이해해야 한다.

### 기존 BatchSummary 모델 (`app/models/review.py`)

```python
class BatchSummary(BaseModel):
    total: int
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0
    llm_analyzed: int = 0
    processing_time_ms: float = 0.0
```

### 기존 배치 실행 흐름 (`app/routes/batch.py`)

1. `POST /batch/run` → `load_pairs()` → `process_batch(pairs)` 호출
2. `process_batch()`가 `(list[ReviewResult], BatchSummary)` 반환
3. 결과를 `_results_store`에 저장, `_last_summary`에 최신 summary 저장
4. `_jobs[job_id]["status"] = JobStatus.COMPLETED` 시점에서 배치 완료

### 기존 UI 구조

- **nav bar** (`base.html`): Dashboard | Migration 두 개 탭
- **Dashboard** (`dashboard.html`): 배치 실행 버튼, stats grid (6칸), risk distribution bar, review 목록 테이블
- **stats grid 패턴**: `.stat-card > .value + .label` 구조, 색상은 risk level별 지정

---

## Functional Requirements

### FR-1: BatchRunRecord 모델

배치 실행 1회의 스냅샷을 저장하는 Pydantic 모델.

**파일**: `app/models/analytics.py`

**필드 정의:**

| 필드 | 타입 | 설명 | 값 소스 |
|------|------|------|---------|
| `id` | `str` | 실행 ID | `batch.py`의 `job_id` (uuid[:8]) |
| `timestamp` | `datetime` | 실행 완료 시각 | `datetime.now(UTC)` |
| `sample_size` | `int` | 처리한 pair 수 | `len(pairs)` |
| `total` | `int` | 전체 결과 수 | `BatchSummary.total` |
| `low` | `int` | Low risk 수 | `BatchSummary.low` |
| `medium` | `int` | Medium risk 수 | `BatchSummary.medium` |
| `high` | `int` | High risk 수 | `BatchSummary.high` |
| `critical` | `int` | Critical risk 수 | `BatchSummary.critical` |
| `llm_analyzed` | `int` | LLM 분석 건수 | `BatchSummary.llm_analyzed` |
| `processing_time_ms` | `float` | 처리 시간 | `BatchSummary.processing_time_ms` |

### FR-2: TrendPoint 모델

시계열 데이터 포인트 1개.

**파일**: `app/models/analytics.py`

| 필드 | 타입 | 설명 |
|------|------|------|
| `timestamp` | `datetime` | 측정 시점 (= BatchRunRecord.timestamp) |
| `metric_name` | `str` | 지표 이름: `"critical_rate"`, `"high_rate"`, `"avg_processing_ms"` |
| `value` | `float` | 지표 값 (비율은 0.0~100.0 범위의 %) |

### FR-3: AnalyticsSummary 모델

전체 히스토리의 종합 분석 결과.

**파일**: `app/models/analytics.py`

| 필드 | 타입 | 설명 |
|------|------|------|
| `total_runs` | `int` | 총 배치 실행 횟수 |
| `avg_processing_time_ms` | `float` | 평균 처리 시간 (소수점 1자리 반올림) |
| `risk_distribution` | `dict[str, float]` | 누적 리스크 비율 (%) — `{"low": 15.2, "medium": 44.8, ...}` |
| `trends` | `list[TrendPoint]` | 시계열 데이터 (timestamp 오름차순 정렬) |

### FR-4: Batch History 저장

배치 실행 완료 시 `BatchRunRecord`를 히스토리에 추가한다.

**수정 파일**: `app/routes/batch.py`

**통합 위치**: `_process()` 함수 내부, `_jobs[job_id]["status"] = JobStatus.COMPLETED` 직전.

**동작:**
1. `BatchSummary`에서 `BatchRunRecord`를 생성 (필드 매핑은 FR-1 참조)
2. 히스토리 저장소(모듈 레벨 리스트)에 append
3. 히스토리가 100건을 초과하면 가장 오래된 것부터 제거 (FIFO)
4. 기존 `POST /batch/run`의 응답 형식은 변경하지 않음

**히스토리 저장소 위치**: `app/routes/analytics.py`에 `_history: list[BatchRunRecord]`를 정의하고, `batch.py`에서 import해서 사용.

### FR-5: compute_trends 서비스

히스토리 리스트를 받아 종합 분석 결과를 반환하는 **순수 함수**.

**파일**: `app/engine/analytics.py`

**시그니처**: `compute_trends(history: list[BatchRunRecord]) -> AnalyticsSummary`

**동작 상세:**

| 입력 | `total_runs` | `avg_processing_time_ms` | `risk_distribution` | `trends` |
|------|-------------|--------------------------|---------------------|----------|
| 빈 리스트 | 0 | 0.0 | `{"low": 0, "medium": 0, "high": 0, "critical": 0}` | `[]` |
| 1건 `[{total:100, low:15, med:45, high:29, crit:11, time:850}]` | 1 | 850.0 | `{"low": 15.0, "medium": 45.0, "high": 29.0, "critical": 11.0}` | 3개 TrendPoint (critical_rate=11.0, high_rate=29.0, avg_processing_ms=850.0) |
| 3건 이상 | N | `sum(time) / N` 반올림 1자리 | 전체 건수 기준 누적 비율 | 시점별 3개 metric × N개 = 최대 3N개 TrendPoint |

**risk_distribution 계산 예시:**
- 3회 실행: [{total:100, low:15}, {total:200, low:40}, {total:50, low:10}]
- 누적: total=350, low=65
- low_rate = 65/350 * 100 = 18.6%

**trends 생성 규칙:**
- 각 `BatchRunRecord`마다 3개의 `TrendPoint` 생성:
  - `critical_rate` = critical / total * 100
  - `high_rate` = high / total * 100
  - `avg_processing_ms` = processing_time_ms
- timestamp 오름차순 정렬

### FR-6: Analytics API 라우트

**파일**: `app/routes/analytics.py`

**라우터**: `APIRouter(prefix="/analytics", tags=["analytics"])`

#### GET /analytics/trends

- 응답: `AnalyticsSummary`
- 히스토리가 비어 있으면 기본값 반환 (에러 아님)

#### GET /analytics/history

- 응답: `list[BatchRunRecord]`
- 최신순 정렬 (timestamp 내림차순)
- 히스토리가 비어 있으면 빈 리스트 반환

**main.py 등록:**
```python
from app.routes.analytics import router as analytics_router
app.include_router(analytics_router)
```

### FR-7: Dashboard UI에 Analytics 탭 추가

기존 Dashboard와 동일한 디자인 시스템으로 Analytics 페이지를 추가한다.

**수정 파일**: `app/templates/base.html`, `app/routes/ui.py`
**생성 파일**: `app/templates/analytics.html`

**nav bar 변경:**
```
Dashboard | Migration | Analytics
```

**Analytics 페이지 (`GET /ui/analytics`):**

1. **Summary 카드** — stats-grid 패턴 사용:
   - Total Runs (총 실행 횟수)
   - Avg Time (평균 처리 시간 ms)
   - Critical Rate (누적 critical 비율 %)
   - High Rate (누적 high 비율 %)

2. **Risk Distribution Bar** — 기존 dashboard와 동일한 `.progress-bar` 패턴으로 누적 분포 표시

3. **History 테이블** — 최신순 배치 실행 기록:

   | Run ID | Time | Sample | Total | Low | Med | High | Crit | Processing |
   |--------|------|--------|-------|-----|-----|------|------|------------|

4. 히스토리가 비어 있으면 "No batch runs yet. Run a batch from Dashboard first." 메시지 표시

**UI 라우트** (`app/routes/ui.py`에 추가):
```python
@router.get("/ui/analytics")
def analytics_page(request: Request):
    # GET /analytics/trends 호출해서 데이터 가져오기
    # GET /analytics/history 호출해서 히스토리 가져오기
    ...
```

### FR-8: 테스트

**파일**: `tests/test_analytics.py`

#### 유닛 테스트 — compute_trends

| 테스트 | 입력 | 검증 |
|--------|------|------|
| `test_empty_history` | `[]` | total_runs=0, trends=[], risk_distribution 전부 0 |
| `test_single_run` | 1건 BatchRunRecord (total=100, low=15, med=45, high=29, crit=11) | total_runs=1, avg_time 정확, critical_rate=11.0, high_rate=29.0 |
| `test_multiple_runs` | 3건 BatchRunRecord (각기 다른 분포) | 누적 비율 계산 정확, trends 3×3=9개, timestamp 오름차순 |
| `test_risk_distribution_percentage` | 2건: [{total:100,low:20}, {total:200,low:60}] | low_rate = (20+60)/(100+200)*100 = 26.7 |
| `test_history_fifo_limit` | 101건 추가 | 히스토리 길이 100, 가장 오래된 것 제거됨 |

#### API 통합 테스트

| 테스트 | 동작 | 검증 |
|--------|------|------|
| `test_trends_empty` | GET /analytics/trends (배치 미실행) | 200, total_runs=0 |
| `test_history_empty` | GET /analytics/history (배치 미실행) | 200, 빈 리스트 |
| `test_trends_after_batch` | POST /batch/run → 완료 대기 → GET /analytics/trends | total_runs=1, 값 일치 |
| `test_history_order` | 배치 2회 실행 → GET /analytics/history | 최신 것이 첫 번째 |

### FR-9: 기존 테스트 호환

- `uv run pytest -q` 실행 시 기존 68개 + 새 테스트 전부 통과
- 기존 `POST /batch/run` 응답 형식 변경 없음
- 기존 모든 import 경로 변경 없음
- 기존 `_last_summary`, `_results_store` 동작 변경 없음

---

## Non-Functional Requirements

- 모든 코드는 `convention.md` 준수 (docstring 금지, 300줄 제한, type hints 필수)
- `ruff check` 통과
- 요구사항에 명시되지 않은 기능은 추가하지 않음 (캐싱, DB 저장, WebSocket 등 불필요)
- 기존 코드의 패턴을 따름:
  - 모델: Pydantic BaseModel + StrEnum (review.py 패턴)
  - 라우트: APIRouter with prefix (batch.py 패턴)
  - 서비스: engine/ 디렉토리에 순수 함수 (batch.py 패턴)
  - UI: Jinja2 templates + base.html 상속 (dashboard.html 패턴)
