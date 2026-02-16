# Renewal Review — Implementation Plan

> PM 요구사항: `docs/requirements.md` 참조

구현에 필요한 상세 규칙, 임계값, 데이터 구조, 에러 처리 등을 정의한다.

---

## 1. 데이터 구조

### 정책 필드

각 정책(Policy Snapshot) 포함 항목:

- **공통**: policy_number, policy_type(auto/home), carrier, effective_date, expiration_date, premium, state, notes
- **Auto**: auto_coverages (BI/PD limit, collision/comprehensive deductible, uninsured motorist, medical payments, rental reimbursement, roadside assistance), vehicles, drivers, endorsements
- **Home**: home_coverages (dwelling A~F, deductible, wind/hail deductible, water_backup, replacement_cost), endorsements

### 데이터 예시

**Auto — 보험료 증가 + 메모 추가:**

```json
{
  "prior": {
    "policy_number": "AUTO-2024-2282",
    "policy_type": "auto",
    "carrier": "Progressive",
    "effective_date": "2024-10-25",
    "expiration_date": "2025-10-25",
    "premium": 3932.46,
    "state": "GA",
    "notes": "",
    "auto_coverages": {
      "bodily_injury_limit": "50/100",
      "property_damage_limit": "25",
      "collision_deductible": 250,
      "comprehensive_deductible": 100,
      "uninsured_motorist": "50/100",
      "medical_payments": 1000,
      "rental_reimbursement": false,
      "roadside_assistance": false
    },
    "vehicles": [
      { "vin": "9SWK6CG7Y8TS31GJS", "year": 2015, "make": "Toyota", "model": "Camry", "usage": "personal" }
    ],
    "drivers": [
      { "license_number": "D7013790", "name": "Driver 2282-0", "age": 49, "violations": 1, "sr22": false }
    ],
    "endorsements": []
  },
  "renewal": {
    "policy_number": "AUTO-2024-2282",
    "premium": 4474.13,
    "notes": "Bundle discount removed — auto policy moved to different carrier",
    "...나머지 동일..."
  }
}
```

예상 결과: 보험료 +13.8% → `PREMIUM_INCREASE_HIGH` + `NOTES_CHANGED` → **Action Required**.

**Home — 특약 제거 + 보험료 감소:**

```json
{
  "prior": {
    "policy_number": "HOME-2024-0495",
    "policy_type": "home",
    "carrier": "USAA",
    "premium": 3465.22,
    "endorsements": [
      { "code": "HO 04 95", "description": "Water backup and sump overflow coverage", "premium": 71.76 },
      { "code": "FL01", "description": "Flood insurance supplement", "premium": 61.41 }
    ]
  },
  "renewal": {
    "premium": 3308.99,
    "endorsements": [
      { "code": "HO 04 95", "description": "Water backup and sump overflow coverage", "premium": 71.76 }
    ]
  }
}
```

예상 결과: 보험료 -4.5% → `PREMIUM_DECREASE` + `ENDORSEMENT_REMOVED` (FL01) → **Review Recommended**.

---

## 2. Basic Analytics — 비교 규칙

### 비교 대상 필드

| 카테고리 | 비교 항목 |
|----------|-----------|
| 공통 | premium, carrier, notes |
| Auto 보장 | BI/PD limit, collision/comprehensive deductible, uninsured motorist, medical payments, rental reimbursement, roadside assistance |
| Home 보장 | dwelling A~F, deductible, wind/hail deductible, water_backup, replacement_cost |
| 차량 | 추가/제거 (VIN 기준 set 비교) |
| 운전자 | 추가/제거 (면허번호 기준 set 비교) |
| 특약 | 추가/제거, 동일 코드 내 설명/보험료 변경 |

### 리스크 플래그

| 플래그 | 조건 |
|--------|------|
| Premium Increase — High | 보험료 증가율 ≥ 10% |
| Premium Increase — Critical | 보험료 증가율 ≥ 20% |
| Premium Decrease | 보험료 감소 |
| Carrier Change | 보험사 변경 |
| Liability Limit Decrease | 책임한도(BI, PD, liability, UM) 하락 |
| Deductible Increase | 자기부담금 증가 |
| Coverage Dropped | 보장 금액 감소 또는 boolean 보장 제거 (True→False) |
| Coverage Added | boolean 보장 추가 (False→True) |
| Vehicle Added / Removed | 차량 추가 / 제거 |
| Driver Added / Removed | 운전자 추가 / 제거 |
| Endorsement Added / Removed | 특약 추가 / 제거 |
| Notes Changed | 메모 변경 |

### 리스크 레벨

| 레벨 | 조건 |
|------|------|
| Urgent Review | Premium Increase Critical 또는 Liability Limit Decrease 존재 |
| Action Required | Premium Increase High 또는 Coverage Dropped 존재 |
| Review Recommended | 플래그 1개 이상, Urgent Review/Action Required 조건 미충족 |
| No Action Needed | 플래그 없음 |

### 에러 처리

- Prior 또는 Renewal 누락 → 어떤 데이터가 누락되었는지 반환
- 필수 항목(policy_number, policy_type, carrier, effective_date, premium) 누락 → 에러 + 누락 항목
- 존재하지 않는 정책 번호 조회 → 404

### 배치 동시성

- 이미 실행 중일 때 새 배치 요청 → 별도 실행 (거부하지 않음)
- 마지막 완료 배치가 Dashboard에 표시
- 처리 중 오류 → 해당 배치 전체 실패 (부분 성공 없음)
- 실패 배치는 이전 성공 결과에 영향 없음

---

## 3. LLM Analytics — LLM 분석 규칙

### 분석 대상 선별

하나 이상 충족 시 LLM 호출:
- 메모(notes) 변경 + 내용 있음
- 특약(endorsement) 설명 변경
- Home boolean 보장 변경

예상 LLM 대상 비율: 약 32% (주로 메모 변경 ~30%)

### 분석 유형

| 유형 | 입력 | 목적 |
|------|------|------|
| Risk Signal Extraction | 정책 메모 텍스트 | 메모에서 리스크 시그널 추출 |
| Endorsement Comparison | Prior/Renewal 특약 설명 | 특약 변경의 성격 판단 (확장/제한/중립) |
| Coverage Similarity | Prior/Renewal 보장 상태 | 보장 동등성 판단 |

각 분석은 결과, 신뢰도(0~100%), 근거를 반환한다.

### 리스크 상향

| 조건 | 상향 |
|------|------|
| 높은 신뢰도로 보장 "동등하지 않음" 판정 | → Action Required 이상 |
| 리스크 시그널 2개 이상 감지 | → Action Required 이상 |
| 특약 변경이 "제한(restriction)" | → Action Required 이상 |
| 위 조건 복합 충족 | → Urgent Review |

> 신뢰도 임계값은 디자인 단계에서 정의한다.

### 비용 제약

- 건당 LLM 호출 최대 3회
- 8,000건 전체 배치: 최대 ~$25
- 샘플 100건: 최대 ~$0.30

### LLM 실패 처리

- 타임아웃/에러/파싱 실패 → 해당 건은 룰 기반 리스크만으로 결정
- LLM 실패가 전체 배치를 중단시키지 않음
- 실패한 분석은 "분석 실패"로 기록, 리스크 상향에 반영 안 됨

### Eval

- Golden set: 예상 최소 리스크 + 예상 플래그 태깅
- 실제 리스크 ≥ 예상 리스크 & 예상 플래그 모두 포함 → 통과
- 전체 통과율을 백분율로 보고

### Migration 비교

- 동일 데이터를 Basic/LLM Analytics로 각각 처리, 차이 표시
- 확인 항목: 리스크 분포, 처리 시간, LLM 분석 건수, 리스크 변경 건 목록
- 리스크 변경 건 클릭 시 어떤 LLM 인사이트가 상향을 유발했는지 확인 가능

---

## 4. Batch Monitoring — 이력/추세 구현

### 기존 코드 컨텍스트

이 모듈이 통합되는 기존 코드:

**BatchSummary 모델** (`app/models/review.py`):
```python
class BatchSummary(BaseModel):
    total: int
    no_action_needed: int = 0
    review_recommended: int = 0
    action_required: int = 0
    urgent_review: int = 0
    llm_analyzed: int = 0
    processing_time_ms: float = 0.0
```

**배치 실행 흐름** (`app/routes/batch.py`):
1. `POST /batch/run` → `load_pairs()` → `process_batch(pairs)` 호출
2. `process_batch()`가 `(list[ReviewResult], BatchSummary)` 반환
3. 결과를 `_results_store`에 저장, `_last_summary`에 최신 summary 저장
4. `_jobs[job_id]["status"] = JobStatus.COMPLETED` 시점에서 배치 완료

**UI 구조**:
- nav bar (`base.html`): Dashboard | Migration 두 개 탭
- Dashboard (`dashboard.html`): 배치 실행 버튼, stats grid (6칸), risk distribution bar, review 목록 테이블
- stats grid 패턴: `.stat-card > .value + .label` 구조

### 생성/수정 파일

| 파일 | 작업 | 설명 |
|------|------|------|
| `app/models/analytics.py` | **생성** | BatchRunRecord, TrendPoint, AnalyticsSummary |
| `app/engine/analytics.py` | **생성** | compute_trends() 순수 함수 |
| `app/routes/analytics.py` | **생성** | GET /analytics/trends, /history + _history 저장소 |
| `app/routes/batch.py` | **수정** | _process() 내부에 히스토리 append 추가 |
| `app/routes/ui.py` | **수정** | GET /ui/analytics 라우트 추가 |
| `app/main.py` | **수정** | analytics 라우터 등록 |
| `app/templates/base.html` | **수정** | nav bar에 Batch Monitoring 링크 추가 |
| `app/templates/analytics.html` | **생성** | Batch Monitoring UI 페이지 |
| `tests/test_analytics.py` | **생성** | 유닛 + API 통합 테스트 |

### 계층 구조

```
models/analytics.py          ← 데이터 구조 정의 (의존성 없음)
    ↑
engine/analytics.py          ← 비즈니스 로직 (models만 import)
    ↑
routes/analytics.py          ← HTTP 엔드포인트 + 히스토리 저장소
    ↑                           (engine + models import)
routes/batch.py              ← 배치 완료 시 히스토리에 append
    ↑                           (routes/analytics에서 add_record import)
routes/ui.py                 ← Batch Monitoring UI 페이지 렌더링
    ↑                           (engine/analytics + routes/analytics에서 import)
main.py                      ← 라우터 등록
```

**Dependency Rules:**
- `models/` → 다른 레이어를 import하지 않음
- `engine/` → `models/`만 import
- `routes/` → `engine/` + `models/` import 가능. 다른 `routes/` 모듈에서 데이터 저장소만 import 가능
- 순환 의존성 금지

### 데이터 모델

**BatchRunRecord** (`app/models/analytics.py`) — 배치 실행 1회의 스냅샷:

| 필드 | 타입 | 값 소스 |
|------|------|---------|
| `id` | `str` | `batch.py`의 `job_id` (uuid[:8]) |
| `timestamp` | `datetime` | `datetime.now(UTC)` |
| `sample_size` | `int` | `len(pairs)` |
| `total` | `int` | `BatchSummary.total` |
| `no_action_needed` | `int` | `BatchSummary.no_action_needed` |
| `review_recommended` | `int` | `BatchSummary.review_recommended` |
| `action_required` | `int` | `BatchSummary.action_required` |
| `urgent_review` | `int` | `BatchSummary.urgent_review` |
| `llm_analyzed` | `int` | `BatchSummary.llm_analyzed` |
| `processing_time_ms` | `float` | `BatchSummary.processing_time_ms` |

**TrendPoint** (`app/models/analytics.py`) — 시계열 데이터 포인트 1개:

| 필드 | 타입 | 설명 |
|------|------|------|
| `timestamp` | `datetime` | 측정 시점 (= BatchRunRecord.timestamp) |
| `metric_name` | `str` | `"urgent_review_rate"`, `"action_required_rate"`, `"avg_processing_ms"` |
| `value` | `float` | 비율은 0.0~100.0% |

**AnalyticsSummary** (`app/models/analytics.py`) — 종합 분석 결과:

| 필드 | 타입 | 설명 |
|------|------|------|
| `total_runs` | `int` | 총 배치 실행 횟수 |
| `avg_processing_time_ms` | `float` | 평균 처리 시간 (소수점 1자리 반올림) |
| `risk_distribution` | `dict[str, float]` | 누적 리스크 비율 (%) — `{"no_action_needed": 15.2, ...}` |
| `trends` | `list[TrendPoint]` | 시계열 (timestamp 오름차순) |

### 데이터 흐름

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

### 히스토리 저장소

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

### batch.py 수정 상세

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
    no_action_needed=summary.no_action_needed,
    review_recommended=summary.review_recommended,
    action_required=summary.action_required,
    urgent_review=summary.urgent_review,
    llm_analyzed=summary.llm_analyzed,
    processing_time_ms=summary.processing_time_ms,
)
add_record(record)

# 기존 코드
_jobs[job_id]["status"] = JobStatus.COMPLETED
```

### compute_trends 서비스

**파일**: `app/engine/analytics.py`

**시그니처**: `compute_trends(history: list[BatchRunRecord]) -> AnalyticsSummary`

| 입력 | `total_runs` | `avg_processing_time_ms` | `risk_distribution` | `trends` |
|------|-------------|--------------------------|---------------------|----------|
| 빈 리스트 | 0 | 0.0 | 전부 0 | `[]` |
| 1건 `[{total:100, no_action:15, review:45, action:29, urgent:11, time:850}]` | 1 | 850.0 | `{"no_action_needed": 15.0, "review_recommended": 45.0, "action_required": 29.0, "urgent_review": 11.0}` | 3개 TrendPoint |
| 3건+ | N | `sum(time) / N` 반올림 1자리 | 전체 건수 기준 누적 비율 | 시점별 3 metric × N |

**risk_distribution 계산:**
- 3회 실행: [{total:100, no_action_needed:15}, {total:200, no_action_needed:40}, {total:50, no_action_needed:10}]
- 누적: total=350, no_action_needed=65 → no_action_needed_rate = 65/350 * 100 = 18.6%
- 모든 비율: `round(x, 1)`, total_sum=0이면 전부 0.0

**trends 생성:**
- 각 BatchRunRecord마다 3개 TrendPoint:
  - `urgent_review_rate` = `round(urgent_review / total * 100, 1)` (total=0이면 0.0)
  - `action_required_rate` = `round(action_required / total * 100, 1)` (total=0이면 0.0)
  - `avg_processing_ms` = processing_time_ms
- timestamp 오름차순 정렬

### API 라우트

**파일**: `app/routes/analytics.py`, **라우터**: `APIRouter(prefix="/analytics", tags=["analytics"])`

| 엔드포인트 | 응답 | 비고 |
|-----------|------|------|
| `GET /analytics/trends` | `AnalyticsSummary` | 빈 히스토리 → 기본값 (에러 아님) |
| `GET /analytics/history` | `list[BatchRunRecord]` | 최신순 (timestamp 내림차순) |

### UI 설계

**nav bar 수정** (`base.html`):
```html
<a href="/" ...>Dashboard</a>
<a href="/ui/migration" ...>Migration</a>
<a href="/ui/analytics" ...>Batch Monitoring</a>
```

**analytics.html** — `dashboard.html` 패턴을 따름:
1. `{% extends "base.html" %}` 상속
2. `stats-grid` 4칸 (Total Runs, Avg Time, Urgent Review Rate, Action Required Rate)
3. `.progress-bar` risk distribution (dashboard 패턴과 동일)
4. `<table>` history 목록 (Run ID, Time, Sample, Total, Low, Med, High, Crit, Processing Time)
5. 빈 상태: "No batch runs yet. Run a batch from Dashboard first."

**UI 라우트** (`app/routes/ui.py`):
```python
from app.engine.analytics import compute_trends
from app.routes.analytics import get_history

@router.get("/ui/analytics")
def analytics_page(request: Request):
    history = get_history()
    summary = compute_trends(history)
    return templates.TemplateResponse(
        "analytics.html",
        {"request": request, "active": "analytics", "summary": summary, "history": history[::-1]},
    )
```

### 엣지 케이스

- 이력 비어 있음 → 총 실행 0, 시계열 빈 목록, 분포 전부 0 (에러 아님)
- 특정 실행에서 total=0 → 해당 실행 비율 0.0%
- 이력 목록 조회 → 최신순(descending)
- FIFO: 새 이력 추가 시점에 100건 초과 시 가장 오래된 것부터 즉시 제거

### 테스트

**파일**: `tests/test_analytics.py`

**유닛 테스트 — compute_trends:**

| 테스트 | 입력 | 검증 |
|--------|------|------|
| `test_empty_history` | `[]` | total_runs=0, trends=[], distribution 전부 0 |
| `test_single_run` | 1건 (total=100, no_action=15, review=45, action=29, urgent=11) | total_runs=1, urgent_review_rate=11.0, action_required_rate=29.0 |
| `test_multiple_runs` | 3건 (각기 다른 분포) | 누적 비율 정확, trends 9개, timestamp 오름차순 |
| `test_risk_distribution_percentage` | 2건: [{total:100,no_action_needed:20}, {total:200,no_action_needed:60}] | no_action_needed_rate = 26.7 |
| `test_history_fifo_limit` | 101건 추가 | 길이 100, 가장 오래된 것 제거됨 |

**API 통합 테스트:**

| 테스트 | 동작 | 검증 |
|--------|------|------|
| `test_trends_empty` | GET /analytics/trends (배치 미실행) | 200, total_runs=0 |
| `test_history_empty` | GET /analytics/history (배치 미실행) | 200, 빈 리스트 |
| `test_trends_after_batch` | POST /batch/run → 완료 → GET /analytics/trends | total_runs=1 |
| `test_history_order` | 배치 2회 → GET /analytics/history | 최신 것이 첫 번째 |

---

## 5. 코딩 규칙

| 종류 | 패턴 | 예시 |
|------|------|------|
| 모델 클래스 | PascalCase | `BatchRunRecord`, `TrendPoint` |
| 서비스 함수 | snake_case | `compute_trends` |
| 라우트 함수 | snake_case | `get_trends`, `get_history` |
| 모듈 레벨 변수 | `_` prefix | `_history`, `MAX_HISTORY` |
| 테스트 함수 | `test_` prefix | `test_empty_history` |

- `convention.md` 준수 (docstring 금지, 300줄 제한, type hints 필수)
- `ruff check` 통과
- 기존 코드 패턴 준수: Pydantic BaseModel, APIRouter with prefix, engine/ 순수 함수, Jinja2 base.html 상속
