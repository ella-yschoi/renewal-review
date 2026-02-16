# Renewal Review — Product Requirements

## 1. Problem Statement

보험 에이전시는 갱신 시즌마다 수천 건의 정책을 수동으로 비교한다.
Prior(현행)과 Renewal(갱신) 사이의 보장 축소, 보험료 급등 등 리스크를 식별하는 작업으로,
현재 다음과 같은 문제가 있다:

- **시간**: 8,000건 규모를 사람이 한 건씩 처리 — 수일 소요
- **정확도**: 수동 비교 과정에서 누락 위험 상존
- **텍스트 리스크 사각지대**: 메모, 특약 설명 등 비정형 텍스트에 숨은 리스크를 정량 비교로 잡아내지 못함
- **추세 부재**: 배치 실행 시 마지막 결과만 남아, 시간에 따른 리스크 추세를 파악할 수 없음
- **교차 리스크 사각지대**: 정책 단건 리뷰로는 동일 고객의 복수 정책 간 중복 보장, 번들 할인 기회, 보장 갭을 발견하기 어려움

## 2. Proposed Solution

Prior/Renewal 정책 쌍을 자동 비교하여 변경 사항을 감지하고 리스크를 분류하는 웹 도구를 제공한다.
5단계 점진적 확장으로 가치를 빠르게 전달한다:

| 단계 | 이름 | 핵심 가치 |
|------|------|-----------|
| 1 | **Basic Analytics** | 룰 기반 자동 비교 + 리스크 분류 → 수일 → 수분 |
| 2 | **LLM Analytics** | LLM 분석 추가 → 텍스트 기반 리스크 사각지대 해소 |
| 3 | **Broker Workflow** | 브로커 연락/견적 추적 + 대안 견적 추천 → 실무 워크플로우 지원 |
| 4 | **Portfolio Aggregator** | 계정 단위 교차 리스크 분석 → 번들 할인·보장 갭 발견 |
| 5 | **Batch Monitoring** | 배치 이력 보관 + 추세 분석 → 시간에 따른 리스크 모니터링 |

## 3. User Stories

### Underwriter / Reviewer

- 정책 쌍을 입력하면 변경 사항과 리스크 레벨을 즉시 확인할 수 있다
- 수천 건을 배치로 실행하고, 리스크가 높은 건부터 우선 검토할 수 있다
- 특정 정책만 선택하여 리뷰할 수 있다 (전체 배치 외 선택 배치)
- 메모나 특약 설명에 숨은 리스크 시그널을 LLM이 감지하여 놓치지 않는다
- 이전 배치와 비교하여 리스크 추세가 악화되는지 확인할 수 있다
- 고위험 정책에 대해 보장 조정 전략별 대안 견적을 LLM이 추천해 준다

### Broker / Agent

- 리뷰 완료 후 각 정책에 브로커 연락 여부를 기록할 수 있다
- 견적 생성 여부를 추적하여 후속 조치 현황을 관리할 수 있다
- 배치 진행 상황을 프로그레스 바로 실시간 확인할 수 있다

### Agency Manager

- Dashboard에서 전체 리스크 분포를 한눈에 파악할 수 있다
- Broker Workflow 지표(연락률, 견적률)로 팀 업무 현황을 모니터링할 수 있다
- 동일 고객의 복수 정책을 묶어 교차 리스크(보장 갭, 번들 기회)를 확인할 수 있다
- Batch Monitoring 페이지에서 배치 이력과 추세를 모니터링할 수 있다
- Basic Analytics → LLM Analytics 전환 시 리스크 판단이 어떻게 달라지는지 사전에 확인할 수 있다

## 4. Requirements

### 4.1 Functional — Basic Analytics (룰 기반 비교)

- 정책 쌍의 모든 필드를 비교하여 변경 사항을 도출한다
- 변경 사항에 리스크 플래그를 부여한다 (보험료 변동, 보장 변경, 차량/운전자 변경, 특약 변경 등)
- 플래그 조합에 따라 4단계 리스크 레벨(Critical / High / Medium / Low)로 분류한다
- 단건 비교, 선택 배치, 전체 배치(전체 또는 샘플)를 지원한다
- Dashboard에서 배치 결과 요약, 리스크 분포, 개별 리뷰 상세를 확인할 수 있다
- Dashboard에 Account(insured_name) 컬럼을 표시하고 정렬할 수 있다
- 배치 실행 시 프로그레스 바로 진행률과 예상 잔여 시간을 표시한다
- 리뷰 결과와 배치 이력을 DB에 영구 저장한다 (SQLAlchemy + SQLite/PostgreSQL)

### 4.2 Functional — LLM Analytics (룰 + LLM)

- 분석이 필요한 건만 선별하여 LLM을 호출한다
- 메모에서 리스크 시그널을 추출하고, 특약 변경의 성격을 판단하고, 보장 동등성을 판단한다
- LLM 결과에 따라 리스크 레벨을 상향할 수 있다 (하향 불가)
- LLM 실패 시 룰 기반 결과만으로 처리한다 (배치 중단 없음)
- Golden set 기반 정확도 평가(Eval)를 제공한다
- Basic → LLM Analytics Migration 비교를 제공한다 (리스크 변경 건 확인, DB 영구 저장)
- LLM 기반 AI Summary를 flagged 정책에 자동 생성한다 (lazy enrichment)

### 4.3 Functional — Broker Workflow (브로커 실무 지원)

- 각 정책에 브로커 연락 여부(contacted)를 토글할 수 있다
- 각 정책에 견적 생성 여부(quote_generated)를 토글할 수 있다
- Broker Workflow 지표를 Dashboard에 표시한다 (Pending, 연락률, 견적률 등)
- 고위험 정책에 LLM 기반 대안 견적(Quote Recommendation)을 생성한다
  - 보장 조정 전략별 절감 견적 최대 3개 제안
  - trade_off: 구체적 시나리오/금액 설명, broker_tip: actionable 대화 가이드

### 4.4 Functional — Portfolio Risk Aggregator (교차 리스크 분석)

- 계정(account_id) 단위로 정책을 그룹핑하여 목록을 표시한다
- 계정별 유형(Auto / Home / Bundle), 총 보험료, 최고 리스크를 집계한다
- 복수 정책(2+) 계정에 대해 교차 리스크 분석을 제공한다 (보장 중복, 번들 할인, 보장 갭)
- Account 정렬(오름차순/내림차순)과 페이지네이션을 지원한다
- 분석 결과를 모달로 표시한다 (verdict, recommendations, action items)

### 4.5 Functional — Batch Monitoring (배치 이력 + 추세 분석)

- 배치 완료 시 이력을 자동 저장한다 (최대 100건, 오래된 것부터 자동 제거)
- 추세 분석을 제공한다: 총 실행 횟수, 평균 처리 시간, 누적 리스크 분포, 시계열 추이
- Batch Monitoring 페이지에서 요약 카드, 리스크 분포 바, 이력 테이블을 제공한다

### 4.6 Non-Functional

- 8,000건 룰 기반 배치 10초 이내
- 리뷰 결과 및 배치 이력 DB 영구 저장 (SQLAlchemy, JSON/PostgreSQL 선택 가능)
- 데이터 소스 전환이 설정 변경만으로 가능 (JSON ↔ PostgreSQL)
- LLM provider 선택 가능 (OpenAI / Anthropic), 비활성화 시 Basic Analytics 정상 동작
- LLM 추적 연동 (Langfuse), 비활성화 가능
- 각 단계 추가 시 기존 기능/테스트 영향 없음

## 5. Success Criteria

| 지표 | 목표 |
|------|------|
| 처리 시간 | 8,000건 배치를 10초 이내에 완료 (기존 수일 → 수분) |
| 리스크 감지 정확도 | Golden set 대비 Eval 통과율 90% 이상 |
| 텍스트 리스크 커버리지 | LLM Analytics 전환 시 Basic 대비 High 이상 리스크 감지 건수 10%+ 증가 |
| 시스템 안정성 | LLM 장애 시에도 Basic Analytics 기능 100% 동작 |
| Broker Workflow 가시성 | 연락률/견적률 지표를 Dashboard에서 실시간 확인 가능 |
| 교차 리스크 감지 | 번들 계정의 보장 갭/중복을 Portfolio에서 식별 가능 |

## 6. Scope

### In Scope

- Auto / Home 두 유형의 정책 비교
- 약 8,000건 규모의 배치 처리
- 웹 기반 Dashboard, Review Detail, LLM Insights, Portfolio, Batch Monitoring UI
- JSON 파일 및 PostgreSQL 데이터 소스
- SQLAlchemy 기반 리뷰 결과·배치 이력 DB 영구 저장
- Langfuse 기반 LLM 추적
- Broker Workflow (연락/견적 추적, 대안 견적 추천)
- Portfolio Risk Aggregator (계정 단위 교차 리스크 분석)

### Out of Scope

- 인증/권한, 다중 사용자, 실시간 알림
- 외부 보험사 시스템 연동
- 프로덕션 배포 (CI/CD, 컨테이너 오케스트레이션)
- 차트/그래프 시각화 (테이블과 숫자로 충분)
- Batch Monitoring 이력 삭제/편집/내보내기

## 7. Go-to-Market

| 단계 | 내용 | 산출물 |
|------|------|--------|
| Basic Analytics 출시 | 룰 기반 비교 + Dashboard | 8,000건 배치 처리, 리스크 분류 |
| LLM Analytics 출시 | LLM 분석 통합 + Migration 비교 | Eval 통과율 보고, Basic/LLM 비교 리포트 |
| Broker Workflow 출시 | 연락/견적 추적 + 대안 견적 추천 | Dashboard Broker 지표, Quote Recommendations |
| Portfolio Aggregator 출시 | 계정 단위 교차 리스크 분석 | Portfolio 페이지, Bundle 분석 |
| Batch Monitoring 출시 | 이력 저장 + 추세 분석 UI | Batch Monitoring 페이지, 추세 모니터링 |

각 단계는 이전 단계의 기능을 유지하면서 점진적으로 확장한다.
