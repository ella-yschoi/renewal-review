# Analytics Module — Architecture

## Directory Structure

```
app/
├── models/
│   └── analytics.py          # BatchRunRecord, TrendPoint, AnalyticsSummary
├── engine/
│   └── analytics.py          # compute_trends() 서비스 함수
├── routes/
│   ├── batch.py              # (수정) 배치 실행 시 히스토리 저장
│   └── analytics.py          # GET /analytics/trends, /analytics/history
└── main.py                   # (수정) analytics 라우터 등록

tests/
└── test_analytics.py         # 0건, 1건, 3건+ 케이스 + API 통합
```

## Design Patterns

### 모델 계층

- **Pydantic BaseModel** 사용 (기존 패턴 동일)
- 파일 위치: `app/models/analytics.py`
- 기존 `app/models/review.py`의 `BatchSummary`와 구조적으로 유사하나, 히스토리 추적용 필드(timestamp) 추가

### 서비스 계층

- **순수 함수**: `compute_trends(history) -> AnalyticsSummary`
- 파일 위치: `app/engine/analytics.py`
- 의존성: `app.models.analytics`만 import
- 외부 상태(DB, 파일) 접근 없음 — 테스트 용이성 확보

### 라우트 계층

- **FastAPI APIRouter** 사용 (기존 패턴 동일)
- prefix: `/analytics`
- 파일 위치: `app/routes/analytics.py`
- 히스토리 저장소: 모듈 레벨 리스트 (`_history: list[BatchRunRecord]`)

### 상태 관리

- **인메모리 리스트**로 배치 히스토리 관리
- `app/routes/batch.py`에서 배치 실행 완료 시 히스토리에 append
- 히스토리 접근은 `app/routes/analytics.py`에서 import
- 최대 100건 제한 (FIFO)

## Dependency Rules

```
routes/analytics.py  →  engine/analytics.py  →  models/analytics.py
routes/batch.py      →  (히스토리 저장소 import)
main.py              →  routes/analytics.py (라우터 등록)
```

- 순환 의존성 금지
- `engine/` 모듈은 `routes/`를 import하지 않음
- `models/` 모듈은 다른 레이어를 import하지 않음

## Naming Conventions

- 모델 클래스: PascalCase (`BatchRunRecord`, `TrendPoint`)
- 서비스 함수: snake_case (`compute_trends`)
- 라우트 함수: snake_case (`get_trends`, `get_history`)
- 테스트 함수: `test_` prefix (`test_empty_history`, `test_single_run`)

## Integration Points

### batch.py 수정

- `POST /batch/run` 핸들러 끝에 `BatchRunRecord` 생성 → 히스토리 append
- `BatchSummary`(기존)의 필드를 `BatchRunRecord`에 매핑
- 기존 응답 형식 변경 없음

### main.py 수정

- `from app.routes.analytics import router as analytics_router` 추가
- `app.include_router(analytics_router)` 추가
