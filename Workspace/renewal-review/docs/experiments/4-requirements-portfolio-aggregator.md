# Portfolio Risk Aggregator — Requirements

## Overview

동일 고객이 보유한 여러 정책(auto + home)을 묶어서 분석하는 모듈.
현재 시스템은 정책을 개별 분석하지만, 고객 단위의 교차 분석(번들 해체 위험, 중복 보장, 총 노출 한도)은 없음.

## Functional Requirements

### FR-1: Portfolio Analysis Endpoint
- `POST /portfolio/analyze` — body: `{"policy_numbers": ["AUTO-2024-1234", "HOME-2024-5678"]}`
- 2개 이상의 policy_number를 받아 교차 분석 결과를 반환
- 각 policy_number는 이미 batch review가 완료된 상태여야 함 (results_store에 존재)
- 존재하지 않는 policy_number가 있으면 422 에러

### FR-2: Portfolio Summary Model
- `PortfolioSummary` Pydantic 모델:
  - `client_policies`: list[str] — 분석 대상 policy numbers
  - `total_premium`: float — 전체 보험료 합계 (renewal 기준)
  - `total_prior_premium`: float — 이전 보험료 합계
  - `premium_change_pct`: float — 전체 보험료 변동률
  - `risk_breakdown`: dict[str, int] — risk level별 정책 수
  - `bundle_analysis`: BundleAnalysis
  - `cross_policy_flags`: list[CrossPolicyFlag]

### FR-3: Bundle Analysis
- `BundleAnalysis` Pydantic 모델:
  - `has_auto`: bool
  - `has_home`: bool
  - `is_bundle`: bool — auto와 home 모두 있으면 True
  - `bundle_discount_eligible`: bool — 동일 carrier이면 True
  - `carrier_mismatch`: bool — auto와 home의 carrier가 다르면 True
  - `unbundle_risk`: str — "low" | "medium" | "high"
    - high: 번들인데 한쪽이 action_required 이상
    - medium: 번들인데 한쪽이 review_recommended
    - low: 그 외

### FR-4: Cross-Policy Flags
- `CrossPolicyFlag` Pydantic 모델:
  - `flag_type`: str — 플래그 종류
  - `severity`: str — "info" | "warning" | "critical"
  - `description`: str — 사람이 읽을 수 있는 설명
  - `affected_policies`: list[str] — 관련 policy numbers

### FR-5: Duplicate Coverage Detection
- auto의 `medical_payments`와 home의 `coverage_f_medical`이 모두 존재하면 `duplicate_medical` 플래그 생성 (severity: "warning")
- auto의 `roadside_assistance`와 home의 endorsement에 roadside/towing 관련 코드가 있으면 `duplicate_roadside` 플래그 생성 (severity: "info")

### FR-6: Total Exposure Calculation
- home `coverage_e_liability` + auto `bodily_injury_limit` (첫 번째 숫자 × 1000)을 합산한 `total_liability_exposure`를 계산
- total_liability_exposure가 $500,000 초과이면 `high_liability_exposure` 플래그 (severity: "info")
- total_liability_exposure가 $200,000 미만이면 `low_liability_exposure` 플래그 (severity: "warning")

### FR-7: Premium Concentration Risk
- 한 정책의 보험료가 전체의 70% 이상이면 `premium_concentration` 플래그 (severity: "warning")
- 전체 보험료 변동이 15% 이상이면 `high_portfolio_increase` 플래그 (severity: "critical")

### FR-8: Edge Cases
- policy_numbers가 1개만 제공되면 422 에러 ("Portfolio analysis requires at least 2 policies")
- 빈 리스트면 422 에러
- 동일 policy_number 중복이면 중복 제거 후 분석
- auto만 있거나 home만 있어도 분석 가능 (번들 아님으로 표시)

### FR-9: Testing
- 최소 8개 테스트 케이스:
  1. auto + home 번들: 정상 분석, is_bundle=True
  2. auto만: is_bundle=False, home 관련 분석 스킵
  3. 중복 medical 탐지
  4. unbundle_risk 계산 (high 케이스)
  5. premium_concentration 탐지
  6. high_portfolio_increase 탐지
  7. 1개 정책 → 422 에러
  8. 존재하지 않는 policy → 422 에러

## Non-Functional Requirements

- 기존 코드 패턴 준수 (convention.md)
- 기존 테스트 전부 통과 (regression 없음)
- ruff check 0 errors
- semgrep 0 findings
- 파일당 300줄 미만
