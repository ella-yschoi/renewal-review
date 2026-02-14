# Discrepancy Report — 삼각 검증 (Agent C)

> **작성일**: 2026-02-14
> **검증 대상**: Batch Monitoring (Stage 3) analytics 모듈
> **비교 문서**: `requirements.md` (요구사항) vs `blind-review.md` (코드 행동 분석)
> **검증 원칙**: 코드를 직접 읽지 않고, 두 문서의 기술 내용만으로 판단한다.

---

## 1. 요구사항 충족 검증 (Requirements Met)

### R1. 배치 완료 시 이력을 자동 저장한다 (4.3)

**판정: 충족**

blind-review 1.4절에서 확인: "배치 처리가 완료되면, 그 실행 결과(검토 건수, 리스크 수준별 건수, 처리 시간)를 `BatchRunRecord`로 요약하여 인메모리 리스트(`_history`)에 추가한다." `_process()` 내부에서 `process_batch()` 성공 후 `get_history_store().append(record)`로 자동 저장한다.

### R2. 추세 분석 — 총 실행 횟수 (4.3)

**판정: 충족**

blind-review 1.2절: `total_runs` = 레코드 개수(len). AnalyticsSummary에 `total_runs` 필드로 포함.

### R3. 추세 분석 — 평균 처리 시간 (4.3)

**판정: 충족**

blind-review 1.2절: `avg_processing_time_ms` = 전체 레코드의 처리 시간 합 / 레코드 수, 소수점 1자리 반올림. AnalyticsSummary에 포함.

### R4. 추세 분석 — 누적 리스크 분포 (4.3)

**판정: 충족**

blind-review 1.2절: `risk_distribution` = 4개 리스크 수준(low/medium/high/critical)별로 모든 레코드의 해당 필드 합산. AnalyticsSummary에 포함.

### R5. 추세 분석 — 시계열 추이 (4.3)

**판정: 충족**

blind-review 1.2절: `trends` = `created_at`의 날짜(YYYY-MM-DD) 기준 그룹핑 후, 날짜 오름차순 정렬하여 TrendPoint 리스트 생성. 각 TrendPoint에 일별 실행 수, 평균 처리 시간, critical 비율 포함.

### R6. 4단계 리스크 레벨 (4.1)

**판정: 충족**

blind-review 관찰사항 #1: "리스크 수준은 4단계: low, medium, high, critical." 요구사항의 Critical / High / Medium / Low와 정확히 일치(케이스만 다름).

### R7. Batch Monitoring 추가 시 기존 기능/테스트 영향 없음 (4.4)

**판정: 충족**

blind-review 1.5절: analytics 라우터가 별도 prefix(`/analytics`)로 등록되며 기존 라우터(ui, reviews, batch, eval)와 독립적. 1.4절에서 batch.py는 analytics에 단방향 의존성만 가지며, analytics 실패 시에도 배치 자체는 COMPLETED 처리됨(1.4 잠재적 이슈 참조).

### R8. 서버 재시작 시 결과/이력 영구 보존 — Out of Scope (6)

**판정: 일치**

요구사항 6절 Out of Scope에서 "서버 재시작 시 결과/이력 영구 보존"을 명시적으로 제외. blind-review에서 "인메모리 리스트. 서버 재시작 시 초기화된다"로 확인. 이는 의도된 설계.

### R9. Batch Monitoring 이력 삭제/편집/내보내기 — Out of Scope (6)

**판정: 일치**

요구사항 6절에서 제외. blind-review 관찰사항 #11: "/analytics 경로에 POST/PUT/DELETE 없음. 읽기 전용 API." Out of Scope과 정확히 일치.

### R10. 차트/그래프 시각화 — Out of Scope (6)

**판정: 확인 불가 (API만 분석됨)**

요구사항에서는 "테이블과 숫자로 충분"이라고 명시. blind-review는 API 엔드포인트(JSON 반환)만 분석하며 UI 템플릿은 분석 대상에 포함되지 않음. API 수준에서는 차트용 데이터가 아닌 숫자/리스트를 반환하므로 위반 증거 없음.

---

## 2. 요구사항 미충족 (Requirements Missed)

### M1. 최대 100건 FIFO 제한 (4.3)

**판정: 미충족 - 심각**

요구사항 4.3: "배치 완료 시 이력을 자동 저장한다 **(최대 100건, FIFO)**"

blind-review 전체를 통해 FIFO나 100건 제한에 대한 언급이 **전혀 없다**. 반대로:
- 1.3절: "필터링/페이지네이션 없이 전체 히스토리를 돌려준다"
- 잠재적 이슈: "히스토리가 누적되면 `/analytics/history` 응답이 점점 커진다"
- 잠재적 이슈: "전체 레코드를 순회하며 계산한다. 레코드가 많아지면 느려질 수 있다"

이는 FIFO 제한이 구현되지 않았음을 강하게 시사한다. 100건 초과 시 메모리 누수, 응답 크기 증가, 계산 성능 저하가 발생할 수 있다.

### M2. Batch Monitoring 페이지 UI — 요약 카드, 리스크 분포 바, 이력 테이블 (4.3)

**판정: 확인 불가**

요구사항 4.3: "Batch Monitoring 페이지에서 요약 카드, 리스크 분포 바, 이력 테이블을 제공한다"

blind-review는 API 엔드포인트와 백엔드 로직만 분석하며, UI 템플릿(HTML)은 분석 대상에 포함되지 않았다. API가 필요한 데이터를 제공하는지는 확인 가능하지만, UI가 실제로 "요약 카드", "리스크 분포 바", "이력 테이블" 3가지 컴포넌트를 렌더링하는지는 이 검증으로 판단할 수 없다.

다만, API 수준에서:
- 요약 카드 데이터: `GET /analytics/trends`의 AnalyticsSummary(total_runs, total_policies_reviewed, avg_processing_time_ms) -- 제공됨
- 리스크 분포 데이터: AnalyticsSummary의 `risk_distribution` -- 제공됨
- 이력 테이블 데이터: `GET /analytics/history`의 BatchRunRecord 리스트 -- 제공됨

API는 UI 구성에 필요한 데이터를 모두 제공하고 있다.

### M3. 데이터 소스 전환 가능 — JSON vs PostgreSQL (4.4)

**판정: 미충족 (analytics 한정)**

요구사항 4.4: "데이터 소스 전환이 설정 변경만으로 가능 (JSON <-> PostgreSQL)"

blind-review 1.3절: analytics 히스토리 저장소는 인메모리 리스트(`_history: list[BatchRunRecord] = []`)로 구현됨. JSON이나 PostgreSQL로 전환할 수 있는 추상화 계층이 없다. 다만, 이 요구사항은 전체 시스템의 데이터 소스에 대한 것일 수 있으며(정책 데이터 입력 소스), analytics 이력 저장소에는 해당하지 않을 수 있다. 요구사항의 의도가 모호하나, Out of Scope에서 "서버 재시작 시 영구 보존"을 제외한 점을 고려하면 analytics 이력까지 DB 전환을 요구하지 않는 것으로 해석 가능하다.

**판정 조정: 경미 (해석에 따라 다름)**

---

## 3. 초과 구현 (Extra Behavior)

### E1. critical_ratio 계산

**판정: 초과 구현**

요구사항 4.3에서 시계열 추이에 요구하는 항목: "총 실행 횟수, 평균 처리 시간, 누적 리스크 분포, 시계열 추이"

blind-review 1.2절: TrendPoint에 `critical_ratio`(해당 일 critical 합계 / total 합계)를 포함한다. 이는 요구사항에 명시적으로 요청된 항목이 아니다. "누적 리스크 분포"는 AnalyticsSummary의 `risk_distribution`으로 충족되며, 일별 critical 비율은 별도로 요구되지 않았다.

**심각도: 낮음** -- 유용한 추가 정보이며 해가 되지 않는다.

### E2. total_policies_reviewed 집계

**판정: 초과 구현 (경미)**

요구사항에서 "총 검토 정책 수"는 명시적으로 요구하지 않았다. 추세 분석 항목은 "총 실행 횟수, 평균 처리 시간, 누적 리스크 분포, 시계열 추이"이다.

blind-review 1.2절: AnalyticsSummary에 `total_policies_reviewed`(모든 레코드의 total 합산)가 포함되어 있다.

**심각도: 낮음** -- 유용한 메타데이터이며 제거할 이유 없음.

### E3. job_id UUID 앞 8자리 절단

**판정: 관찰 (판단 보류)**

blind-review 관찰사항 #9: "job_id는 UUID 앞 8자리." 요구사항에서 job_id 형식에 대한 명세가 없으므로 구현 세부사항으로 볼 수 있다. 다만 8자리 절단은 충돌 가능성이 있다(8,000건 배치에서 UUID v4 앞 8자리 충돌 확률은 극히 낮으나 이론적으로는 존재).

---

## 4. 의도 불일치 (Intent Mismatch)

### I1. FIFO 100건 제한 미구현 -- 가장 심각한 불일치

**요구사항**: 4.3 "배치 완료 시 이력을 자동 저장한다 (최대 100건, FIFO)"
**코드 행동**: 무제한 append. 제한 없음.

이것은 명확한 의도 불일치이다. 요구사항은 최대 100건의 FIFO(선입선출) 방식을 명시하고 있으나, 구현체에는 이 제한이 없다. 결과:
- 100건 초과 시 오래된 기록이 제거되지 않음
- 메모리가 지속적으로 증가
- `/analytics/history` 응답 크기 무제한 증가
- `/analytics/trends` 계산 시간 무제한 증가

**심각도: 높음** -- 요구사항에 수치까지 명시된 제한이 구현되지 않았다.

### I2. 하드코딩된 타임존 (America/Vancouver)

**요구사항**: 명시적 타임존 요구사항 없음.
**코드 행동**: blind-review 1.4절 -- `created_at`은 `America/Vancouver` 타임존의 현재 시각으로 하드코딩.

요구사항에 타임존이 명시되지 않았으나, blind-review가 지적하듯 테스트(UTC)와 프로덕션 코드(Vancouver)의 타임존이 다르다. 이로 인해:
- 테스트에서의 날짜 그룹핑 경계와 프로덕션의 경계가 다를 수 있음
- 의도 불일치라기보다는 **잠재적 버그**에 가까움

**심각도: 중간** -- 기능 오류는 아니지만, 테스트와 프로덕션의 일관성 부재.

---

## 5. 컨벤션 위반 (Convention Violations)

### C1. 함수 내부 import (batch.py)

blind-review 1.4절: "`datetime`, `ZoneInfo`, `BatchRunRecord`를 함수 내부에서 import한다." blind-review 자체도 "엄밀한 위반은 아니지만, 코드 가독성 측면에서 개선 여지가 있다"로 평가.

CLAUDE.md의 convention.md 참조 규칙에 따르면 import 위치에 대한 명시적 규칙이 있는지 확인이 필요하나, 이 검증에서는 convention.md를 직접 읽지 않으므로 blind-review의 판단을 인용한다.

**심각도: 낮음**

### C2. `_clear_history` fixture 네이밍

blind-review 1.6절: "leading underscore는 보통 '사용하지 않는' 이름에 쓰인다. 소소한 네이밍 관례 차이."

**심각도: 매우 낮음**

### C3. 나머지 파일 -- 위반 없음

blind-review는 models, engine, routes, main.py에서 컨벤션 위반을 발견하지 않았다. "docstring 미사용, 타입 힌트 충실, 파일 30줄로 간결" 등 CLAUDE.md의 핵심 규칙(No method docstrings, clear naming + types)과 일치.

---

## 6. 검증 요약 (Verification Summary)

| Category | Count | Details |
|----------|-------|---------|
| Requirements Met | 9 | R1-R9: 이력 자동 저장, 추세 분석 4항목, 4단계 리스크, 기존 기능 무영향, Out of Scope 항목 준수 |
| Requirements Missed | 2 | M1: FIFO 100건 제한 미구현, M2: UI 검증 불가 (blind-review 범위 밖) |
| Extra Behavior | 3 | E1: critical_ratio, E2: total_policies_reviewed, E3: job_id 8자리 절단 |
| Intent Mismatch | 2 | I1: FIFO 100건 제한 미구현 (가장 심각), I2: 하드코딩 타임존 불일치 |
| Convention Violation | 2 | C1: 함수 내부 import, C2: fixture 네이밍 |
| Potential Edge Case | 7 | total 합계 불일치 검증 부재, timezone 혼재 시 날짜 그룹핑 오류, banker's rounding, 동시성 문제, 다중 날짜 trends 테스트 부재, critical_ratio 테스트 부재, 반올림 테스트 부재 |

---

## 7. 종합 판정

### 판정: 조건부 통과 (Conditional Pass)

핵심 기능(이력 저장, 추세 분석, API 엔드포인트)은 요구사항에 부합하게 구현되어 있다. 아키텍처와 코드 품질도 컨벤션을 준수한다. 그러나 **FIFO 100건 제한 미구현**은 요구사항에 수치까지 명시된 항목이 빠진 것으로, 반드시 수정이 필요하다.

### 이슈 심각도 순위

| 순위 | 이슈 | 심각도 | 유형 |
|------|------|--------|------|
| 1 | FIFO 100건 제한 미구현 (I1/M1) | **높음** | Intent Mismatch + Missing Feature |
| 2 | 하드코딩 타임존 (I2) | 중간 | Intent Mismatch (잠재적 버그) |
| 3 | UI 검증 불가 (M2) | 중간 | 검증 범위 한계 |
| 4 | total 합계 검증 부재 | 낮음 | Edge Case |
| 5 | 함수 내부 import (C1) | 낮음 | Convention Violation |
| 6 | 다중 날짜 / critical_ratio 테스트 부재 | 낮음 | Test Coverage Gap |
| 7 | critical_ratio 초과 구현 (E1) | 매우 낮음 | Extra Feature |

### 권고사항

1. **[필수]** `_history` 리스트에 FIFO 100건 제한을 구현한다. `collections.deque(maxlen=100)` 또는 append 후 길이 체크 방식으로 구현 가능. 이것이 이 검증에서 발견된 유일한 블로킹 이슈이다.

2. **[권장]** 타임존 처리를 환경 설정 또는 UTC 통일로 변경한다. 테스트와 프로덕션 코드의 타임존이 다른 것은 날짜 경계 관련 미묘한 버그를 유발할 수 있다.

3. **[권장]** UI(Batch Monitoring 페이지)에 대한 별도 검증을 수행한다. 요구사항 4.3의 "요약 카드, 리스크 분포 바, 이력 테이블" 3개 컴포넌트가 실제로 구현되어 있는지 blind-review 범위를 확장하거나 별도 UI 리뷰를 진행한다.

4. **[선택]** 다중 날짜에 걸친 trends 테스트, critical_ratio 검증 테스트를 추가하여 테스트 커버리지를 보강한다.

5. **[선택]** `BatchRunRecord`의 `total`과 `low + medium + high + critical` 합계가 일치하는지 Pydantic validator를 추가한다.

---

> **검증 한계**: 이 보고서는 requirements.md와 blind-review.md 두 문서의 텍스트 비교만으로 작성되었다. 코드를 직접 읽지 않았으므로, blind-review가 놓친 행동이나 blind-review의 오독이 있다면 이 검증에도 반영되지 않는다. 특히 UI 템플릿(HTML)과 기존 모듈(review, eval, migration)에 대한 영향은 이 검증의 범위 밖이다.
