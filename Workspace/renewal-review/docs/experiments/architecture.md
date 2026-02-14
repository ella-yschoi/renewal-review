# Analytics Module — Architecture

## 생성/수정 파일 목록

| 파일 | 작업 | 설명 |
|------|------|------|
| `app/models/analytics.py` | **생성** | BatchRunRecord, TrendPoint, AnalyticsSummary |
| `app/engine/analytics.py` | **생성** | compute_trends() 순수 함수 |
| `app/routes/analytics.py` | **생성** | GET /analytics/trends, /history + _history 저장소 |
| `app/routes/batch.py` | **수정** | _process() 내부에 히스토리 append 추가 |
| `app/routes/ui.py` | **수정** | GET /ui/analytics 라우트 추가 |
| `app/main.py` | **수정** | analytics 라우터 등록 |
| `app/templates/base.html` | **수정** | nav bar에 Analytics 링크 추가 |
| `app/templates/analytics.html` | **생성** | Analytics UI 페이지 |
| `tests/test_analytics.py` | **생성** | 유닛 + API 통합 테스트 |

## 계층 구조

```
models/analytics.py          ← 데이터 구조 정의 (의존성 없음)
    ↑
engine/analytics.py          ← 비즈니스 로직 (models만 import)
    ↑
routes/analytics.py          ← HTTP 엔드포인트 + 히스토리 저장소
    ↑                           (engine + models import)
routes/batch.py              ← 배치 완료 시 히스토리에 append
    ↑                           (routes/analytics에서 _history import)
routes/ui.py                 ← Analytics UI 페이지 렌더링
    ↑                           (routes/analytics에서 데이터 import)
main.py                      ← 라우터 등록
```

## Dependency Rules

- `models/` → 다른 레이어를 import하지 않음
- `engine/` → `models/`만 import. `routes/`를 절대 import하지 않음
- `routes/` → `engine/` + `models/` import 가능. 다른 `routes/` 모듈에서 데이터 저장소만 import 가능 (기존 패턴: `batch.py`가 `reviews.py`의 `get_results_store()` import)
- 순환 의존성 금지

## 데이터 흐름

```
1. POST /batch/run 호출
2. process_batch(pairs) 실행 → (results, summary) 반환
3. _results_store에 결과 저장 (기존 동작, 변경 없음)
4. _last_summary에 저장 (기존 동작, 변경 없음)
5. [NEW] BatchRunRecord 생성 (summary 필드 매핑 + job_id + timestamp)
6. [NEW] _history에 append (100건 초과 시 FIFO)
7. _jobs[job_id]["status"] = COMPLETED

--- 별도 요청 시 ---

8. GET /analytics/trends → compute_trends(_history) → AnalyticsSummary
9. GET /analytics/history → _history[::-1] (최신순)
10. GET /ui/analytics → trends + history 데이터로 HTML 렌더링
```

## 히스토리 저장소 설계

**위치**: `app/routes/analytics.py` 모듈 레벨

```python
_history: list[BatchRunRecord] = []
MAX_HISTORY = 100

def add_record(record: BatchRunRecord) -> None:
    _history.append(record)
    if len(_history) > MAX_HISTORY:
        _history.pop(0)

def get_history() -> list[BatchRunRecord]:
    return _history
```

**batch.py에서 사용:**
```python
from app.routes.analytics import add_record
```

이 패턴은 기존 `batch.py`가 `reviews.py`의 `get_results_store()`를 import하는 패턴과 동일하다.

## batch.py 수정 상세

`_process()` 함수 내부, COMPLETED 설정 직전에 추가:

```python
# 기존 코드
_last_summary = summary
store = get_results_store()
store.clear()
for r in results:
    store[r.policy_number] = r

# [추가] 히스토리 기록
from app.models.analytics import BatchRunRecord
from app.routes.analytics import add_record
record = BatchRunRecord(
    id=job_id,
    sample_size=len(pairs),
    total=summary.total,
    low=summary.low,
    medium=summary.medium,
    high=summary.high,
    critical=summary.critical,
    llm_analyzed=summary.llm_analyzed,
    processing_time_ms=summary.processing_time_ms,
)
add_record(record)

# 기존 코드
_jobs[job_id]["status"] = JobStatus.COMPLETED
```

## UI 설계

### base.html nav bar 수정

```html
<!-- 기존 -->
<a href="/" ...>Dashboard</a>
<a href="/ui/migration" ...>Migration</a>

<!-- 추가 -->
<a href="/ui/analytics" ...>Analytics</a>
```

`active` 변수로 현재 탭 하이라이트 (기존 패턴 동일).

### analytics.html 구조

`dashboard.html` 패턴을 따름:

1. `{% extends "base.html" %}` 상속
2. `stats-grid` 4칸 (Total Runs, Avg Time, Critical Rate, High Rate)
3. `.progress-bar` risk distribution (dashboard의 `#distribution-bar` 패턴과 동일)
4. `<table>` history 목록 (dashboard의 `#results-section` 테이블 패턴과 동일)
5. 히스토리가 비어 있으면 빈 상태 메시지

## Naming Conventions

| 종류 | 패턴 | 예시 |
|------|------|------|
| 모델 클래스 | PascalCase | `BatchRunRecord`, `TrendPoint`, `AnalyticsSummary` |
| 서비스 함수 | snake_case | `compute_trends` |
| 라우트 함수 | snake_case | `get_trends`, `get_history` |
| 저장소 함수 | snake_case | `add_record`, `get_history` |
| 테스트 함수 | `test_` prefix | `test_empty_history`, `test_single_run` |
| 모듈 레벨 변수 | `_` prefix | `_history`, `MAX_HISTORY` |
