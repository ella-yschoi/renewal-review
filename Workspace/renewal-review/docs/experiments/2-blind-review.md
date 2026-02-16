# Blind Review — Analytics 모듈 행동 분석

> **Agent B 작성** | 2026-02-14
> 요구사항(requirements.md)을 읽지 않은 상태에서, 코드만 보고 관찰 가능한 행동을 기술한다.

---

## 1. 파일별 분석

### 1.1 `app/models/analytics.py`

**행동:**

이 파일은 analytics 도메인의 데이터 구조 3개를 정의한다. 모두 Pydantic BaseModel이며 직렬화/역직렬화/검증을 자동으로 제공한다.

- **BatchRunRecord**: 배치 실행 1회의 스냅샷을 나타낸다. 입력값은 `job_id`(문자열), 리스크 수준별 건수(`total`, `no_action_needed`, `review_recommended`, `action_required`, `urgent_review` — 모두 정수), 처리 시간(`processing_time_ms`, float), 생성 시각(`created_at`, datetime). 이 모델은 "배치 한 번 돌린 결과"를 숫자로 요약한 것이다.
- **TrendPoint**: 일별 집계를 나타낸다. `date`(문자열, 날짜 형식), `total_runs`(해당 일에 실행된 배치 횟수), `avg_processing_time_ms`(해당 일 평균 처리 시간), `urgent_review_ratio`(해당 일 critical 비율, float). 하루치 데이터를 한 점으로 요약한 구조.
- **AnalyticsSummary**: 전체 분석 요약. `total_runs`(총 배치 실행 수), `total_policies_reviewed`(총 검토 정책 수), `avg_processing_time_ms`(전체 평균 처리 시간), `risk_distribution`(리스크 수준별 합산 딕셔너리), `trends`(TrendPoint 리스트). 모든 기록을 종합한 대시보드 데이터 구조.

**컨벤션 위반:** 없음. docstring 미사용, 타입 힌트 충실, 파일 30줄로 간결.

**잠재적 이슈 / 엣지 케이스:**

- `BatchRunRecord.total`과 `no_action_needed + review_recommended + action_required + urgent_review`의 합이 일치하는지에 대한 검증(validator)이 없다. 외부에서 불일치하는 값을 넣어도 모델 수준에서 막지 않는다.
- `TrendPoint.date`가 `str`로 정의되어 있어 "YYYY-MM-DD" 형식을 강제하지 않는다. 잘못된 문자열이 들어올 수 있다(현재는 engine에서만 생성하므로 실질적 위험은 낮음).
- `risk_distribution`이 `dict[str, int]`로 느슨하게 정의되어, 키가 "no_action_needed"/"review_recommended"/"action_required"/"urgent_review" 4개인지 보장하지 않는다.
- `created_at`에 timezone 정보 유무를 강제하지 않는다. naive datetime과 aware datetime이 혼재할 수 있다.

---

### 1.2 `app/engine/analytics.py`

**행동:**

`compute_trends` 함수 하나를 정의한다. `BatchRunRecord` 리스트를 입력받아 `AnalyticsSummary`를 반환한다.

구체적 동작:

1. **빈 리스트 입력 시**: 모든 값이 0/빈 리스트인 AnalyticsSummary를 반환한다. risk_distribution은 4개 키 모두 0으로 초기화된다.
2. **레코드가 있을 때**:
   - `total_runs` = 레코드 개수 (len)
   - `total_policies_reviewed` = 모든 레코드의 `total` 필드 합산
   - `avg_processing_time_ms` = 모든 레코드의 `processing_time_ms` 합 / 레코드 수, 소수점 1자리 반올림
   - `risk_distribution` = 4개 리스크 수준(no_action_needed/review_recommended/action_required/urgent_review)별로 모든 레코드의 해당 필드 합산
   - `trends` = `created_at`의 날짜(YYYY-MM-DD) 기준 그룹핑 후, 날짜 오름차순 정렬하여 TrendPoint 리스트 생성
     - 각 TrendPoint: `date`=해당 일, `total_runs`=해당 일 레코드 수, `avg_processing_time_ms`=해당 일 평균(소수 1자리), `urgent_review_ratio`=해당 일 critical 합계 / total 합계 (소수 4자리), total이 0이면 0.0

**컨벤션 위반:** 없음. docstring 없음, 타입 힌트 사용, 단일 책임 함수, 54줄로 300줄 미만.

**잠재적 이슈 / 엣지 케이스:**

- **urgent_review_ratio 계산 기준**: `day_critical / day_total`에서 `day_total`은 해당 일의 `r.total` 합계(=검토된 총 정책 수)이다. 즉 urgent_review_ratio는 "해당 일 검토된 전체 정책 중 critical 비율"이다. 만약 "배치 실행 횟수 대비 critical 배치 비율"을 의도했다면 계산이 다르다. 현재 로직은 정책 건수 기반이다.
- **timezone 혼재 시 날짜 그룹핑 오류**: `created_at`이 서로 다른 timezone의 aware datetime이면, `strftime("%Y-%m-%d")`가 UTC 기준이 아니라 각 객체의 로컬 시간 기준으로 날짜를 잘라낸다. 예: UTC 23:30과 KST 08:30(같은 시점)이 다른 날짜로 그룹핑될 수 있다.
- **avg_processing_time_ms 반올림**: 전체 평균은 `round(..., 1)`이지만, 일별 평균도 `round(..., 1)`이다. 일관성은 있으나 round 함수의 banker's rounding(Python 3) 특성상 5로 끝나는 값의 반올림이 직관과 다를 수 있다.
- **risk_distribution에 total 키가 빠져 있다**: 4개 리스크 수준만 합산하고 total은 포함하지 않는다. total_policies_reviewed와 risk_distribution 값들의 합이 같은지 보장되지 않는다(원본 데이터에서 total != low+medium+high+critical일 수 있으므로).

---

### 1.3 `app/routes/analytics.py`

**행동:**

FastAPI APIRouter를 사용하며, prefix `/analytics`, 태그 `analytics`로 등록된다. 두 개의 GET 엔드포인트를 제공한다.

- **모듈 레벨 저장소**: `_history: list[BatchRunRecord] = []` — 인메모리 리스트. 서버 재시작 시 초기화된다.
- **`get_history_store()` 함수**: `_history` 리스트의 참조를 외부에 노출한다. 다른 모듈(batch.py)이 이 함수를 통해 리스트에 접근하여 append할 수 있도록 한다.
- **GET `/analytics/history`**: `_history` 리스트 전체를 `list[BatchRunRecord]`로 반환한다. 필터링/페이지네이션 없이 전체 히스토리를 돌려준다.
- **GET `/analytics/trends`**: `_history`를 `compute_trends`에 전달하고 그 결과인 `AnalyticsSummary`를 반환한다. 호출할 때마다 전체 히스토리를 대상으로 재계산한다.

**컨벤션 위반:** 없음.

**잠재적 이슈 / 엣지 케이스:**

- **인메모리 저장소**: 서버 재시작 시 모든 히스토리가 사라진다. 영속성이 없다.
- **동시성 문제**: 여러 배치가 동시에 실행되면 `_history.append()`가 동시에 호출될 수 있다. Python의 GIL이 list.append를 원자적으로 만들어주긴 하나, asyncio 환경에서 executor 내부에서 호출되므로 thread-safety 관점에서 주의가 필요하다.
- **페이지네이션 없음**: 히스토리가 누적되면 `/analytics/history` 응답이 점점 커진다.
- **캐싱 없음**: `/analytics/trends`는 매 요청마다 전체 레코드를 순회하며 계산한다. 레코드가 많아지면 느려질 수 있다.

---

### 1.4 `app/routes/batch.py` — Analytics 연동 부분

**행동:**

`run_batch` 엔드포인트의 `_process()` 내부 비동기 함수에서, 배치 처리 완료 후 analytics 기록을 생성한다.

구체적 흐름:

1. `process_batch()`가 성공적으로 완료되면 `results`와 `summary`(BatchSummary)를 얻는다.
2. 결과를 reviews 저장소에 저장하고, 잡 상태를 COMPLETED로 업데이트한다.
3. **analytics 연동**: `BatchSummary`의 필드(`total`, `no_action_needed`, `review_recommended`, `action_required`, `urgent_review`, `processing_time_ms`)를 사용하여 `BatchRunRecord`를 생성한다. `job_id`는 배치 잡의 UUID 앞 8자리, `created_at`은 `America/Vancouver` 타임존의 현재 시각.
4. `get_history_store().append(record)`로 analytics 히스토리에 추가한다.
5. 예외 발생 시에는 analytics 기록을 생성하지 않는다(try 블록 내에서 실패하면 except로 빠지므로).

**컨벤션 위반:**

- **함수 내부 import**: `datetime`, `ZoneInfo`, `BatchRunRecord`를 함수 내부에서 import한다. Python에서 기능적으로 문제는 없으나, 모듈 상단에 import를 모으는 것이 일반적이다. convention.md에 import 위치 규칙이 명시되어 있지는 않으므로 엄밀한 위반은 아니지만, 코드 가독성 측면에서 개선 여지가 있다.

**잠재적 이슈 / 엣지 케이스:**

- **하드코딩된 타임존**: `America/Vancouver`가 하드코딩되어 있다. 다른 지역에서 운영하거나, 테스트(UTC 사용)와 실제 환경의 타임존이 달라 날짜 그룹핑 결과가 일관되지 않을 수 있다. 테스트에서는 `datetime.now(UTC)`를 쓰고 실제 코드에서는 Vancouver를 쓰므로, trends의 날짜 경계가 다르게 나온다.
- **analytics 기록 실패 시 무시**: `get_history_store().append(record)` 전에 예외가 나면(이론적으로 BatchRunRecord 생성 시 검증 실패 등) 배치 자체는 COMPLETED인데 analytics 기록이 누락될 수 있다. 다만 현재 코드에서는 summary 필드를 그대로 매핑하므로 실질적 위험은 낮다.
- **`asyncio.create_task`로 비동기 실행**: `_process()`는 fire-and-forget 패턴이다. `run_batch`는 즉시 응답하고, 실제 처리는 백그라운드에서 진행된다. analytics 기록도 이 백그라운드 태스크 안에서 추가된다.

---

### 1.5 `app/main.py`

**행동:**

FastAPI 앱 인스턴스를 생성하고 5개의 라우터(ui, reviews, batch, eval, analytics)를 등록한다. analytics 라우터가 마지막에 포함되어 `/analytics/history`와 `/analytics/trends` 엔드포인트가 앱에 노출된다.

`/health` 엔드포인트는 `{"status": "ok"}`를 반환하는 헬스체크이다.

**컨벤션 위반:** 없음.

**잠재적 이슈 / 엣지 케이스:**

- 라우터 등록 순서에 따른 URL 충돌 가능성은 현재 없다(각 prefix가 고유함).

---

### 1.6 `tests/test_analytics.py`

**행동:**

5개의 테스트를 포함한다.

- **`_make_record` 헬퍼**: 기본값이 설정된 BatchRunRecord 팩토리 함수. `created_at` 미지정 시 `datetime.now(UTC)`를 사용한다.
- **`test_compute_trends_empty`**: 빈 리스트 입력 시 모든 값이 0/빈 리스트인 AnalyticsSummary가 반환되는지 검증한다.
- **`test_compute_trends_single_record`**: 레코드 1개 입력 시 `total_runs=1`, `total_policies_reviewed=10`, `avg_processing_time_ms=100.0`, `risk_distribution["urgent_review"]=1`, `trends` 길이 1인지 검증한다.
- **`test_compute_trends_multiple_records`**: 레코드 3개(모두 같은 시점에 생성되어 같은 날짜로 그룹핑)일 때 `total_runs=3`, `total_policies_reviewed=45`, `avg_processing_time_ms=150.0`, `risk_distribution` 합산값, `trends` 길이 1인지 검증한다.
- **`test_analytics_history_route`**: `_clear_history` fixture로 저장소 초기화 후, `GET /analytics/history`가 200 상태코드와 빈 리스트를 반환하는지 검증한다.
- **`test_analytics_trends_route`**: 저장소에 레코드 1개 추가 후, `GET /analytics/trends`가 200과 올바른 `total_runs`, `total_policies_reviewed`를 반환하는지 검증한다.

**컨벤션 위반:** 없음. 테스트 파일 명명(`test_*.py`) 규칙 준수, 비즈니스 로직 테스트 위주.

**잠재적 이슈 / 엣지 케이스:**

- **다른 날짜에 걸친 trends 테스트 부재**: 모든 레코드가 `datetime.now(UTC)`로 생성되어 같은 날짜로 그룹핑된다. 여러 날짜에 걸친 그룹핑/정렬 로직이 테스트되지 않는다.
- **urgent_review_ratio 검증 부재**: TrendPoint의 `urgent_review_ratio` 값이 올바른지 직접 검증하는 테스트가 없다.
- **avg_processing_time_ms 반올림 검증 부재**: 소수점 반올림이 정확한지 테스트하지 않는다.
- **동시성 시나리오 미테스트**: 여러 배치가 동시에 실행될 때의 히스토리 저장소 동작은 테스트하지 않는다.
- **`_clear_history` fixture가 `_`로 시작**: pytest에서 작동하지만, leading underscore는 보통 "사용하지 않는" 이름에 쓰인다. 소소한 네이밍 관례 차이.

---

## 2. 전체 모듈 행동 요약

### 이 모듈이 하는 일

Analytics 모듈은 **배치 리뷰 실행 이력을 추적하고 통계를 제공하는 기능**이다.

**데이터 흐름:**

1. 사용자가 `/batch/run`으로 배치 실행을 요청하면, 백그라운드에서 보험 갱신 정책을 검토한다.
2. 배치 처리가 완료되면, 그 실행 결과(검토 건수, 리스크 수준별 건수, 처리 시간)를 `BatchRunRecord`로 요약하여 인메모리 리스트(`_history`)에 추가한다.
3. 이후 사용자는 두 개의 API를 통해 이 데이터를 조회할 수 있다:
   - **`GET /analytics/history`**: 모든 배치 실행 기록을 시간순으로 반환한다(원본 리스트 그대로, 별도 정렬 없음 — append 순서).
   - **`GET /analytics/trends`**: 모든 기록을 집계하여 전체 통계(총 실행 수, 총 검토 정책 수, 평균 처리 시간, 리스크 분포)와 일별 트렌드(일별 실행 수, 일별 평균 처리 시간, 일별 critical 비율)를 반환한다.

**핵심 계산 로직 (`compute_trends`):**

- 전체 통계: 레코드 수, 정책 수 합계, 처리 시간 평균, 리스크 수준별 합산
- 일별 트렌드: `created_at`의 날짜(YYYY-MM-DD) 기준 그룹핑 후, 날짜 오름차순 정렬. 각 날짜별로 실행 수, 평균 처리 시간, critical 비율(critical 건수 / 총 정책 건수) 산출

**저장 방식:**

- 인메모리 리스트 (서버 재시작 시 초기화)
- 모듈 레벨 변수를 `get_history_store()` 함수로 노출하여 batch 라우터가 접근

**아키텍처:**

- 3계층 구조: models(데이터 구조) -> engine(비즈니스 로직) -> routes(API 엔드포인트)
- batch.py에서 analytics 모듈로의 단방향 의존성 (batch -> analytics)

---

## 3. 주요 관찰 사항 (불일치 비교용)

다음은 요구사항 대조 시 확인해볼 만한 행동 특성이다:

| # | 관찰된 행동 | 비고 |
|---|-----------|------|
| 1 | 리스크 수준은 4단계: no_action_needed, review_recommended, action_required, urgent_review | 다른 수준(예: none, info)은 없음 |
| 2 | urgent_review_ratio는 "정책 건수 기반" (critical건수 / total건수) | "배치 실행 횟수 기반"이 아님 |
| 3 | 타임존은 America/Vancouver 하드코딩 | 환경변수나 설정으로 관리되지 않음 |
| 4 | 인메모리 저장소 — 영속성 없음 | DB나 파일 저장 없음 |
| 5 | 페이지네이션/필터링 없음 | history는 전체 반환, trends는 전체 기간 집계 |
| 6 | BatchRunRecord에 total이 있지만 risk_distribution에는 total 키 없음 | total_policies_reviewed로 별도 제공 |
| 7 | trends는 날짜 오름차순 정렬 | 최신순이 아님 |
| 8 | 배치 실패 시 analytics 기록 미생성 | 실패 기록은 추적하지 않음 |
| 9 | job_id는 UUID 앞 8자리 | batch.py에서 생성, analytics에서는 그대로 저장 |
| 10 | processing_time_ms는 BatchSummary에서 가져옴 | analytics 자체에서 측정하지 않음 |
| 11 | /analytics 경로에 POST/PUT/DELETE 없음 | 읽기 전용 API |
| 12 | total != no_action_needed + review_recommended + action_required + urgent_review 검증 없음 | 모델 수준 validation 부재 |
| 13 | history 엔드포인트에 날짜 범위 필터 없음 | 전체 기록만 조회 가능 |
| 14 | compute_trends는 매 요청마다 전체 재계산 | 캐싱/증분 계산 없음 |
