---
name: insurance-domain
description: "Use when modifying domain/models/, domain/services/, adaptor/llm/, or any business logic involving insurance terms, coverages, or risk rules. Also use when adding new fields, endorsements, or coverage types."
---

# Insurance Domain Knowledge (ACORD-Based)

ACORD (Association for Cooperation in Operations Research and Development) defines the insurance industry's data standards. This project covers Personal Lines — Auto (ACORD 90) and Homeowners (ACORD 80).

## Core Terminology

| Term | Definition | ACORD Context |
|------|-----------|---------------|
| **Renewal** | 기존 정책의 갱신. Prior(이전) vs Renewal(갱신) 비교가 핵심 | ACORD 80/90 Status: `Renew` |
| **Endorsement** | 정책 중간 변경 또는 추가 특약. 보장 범위를 확대/축소 | ACORD 70 (HO), 71 (Auto): change type A/C/D |
| **Premium** | 보험료. 갱신 시 변동률이 risk 판정의 1차 지표 | ACORD `WrittenAmt` |
| **Deductible** | 공제액. 보험금 청구 시 가입자가 먼저 부담하는 금액 | ACORD `DeductibleAmt` |
| **Liability Limit** | 배상 책임 한도. 절대 자동 축소하면 안 되는 보호 필드 | ACORD `BI`, `PD`, Coverage E |
| **Coverage Dropped** | 보장 항목 제거. True→False 또는 금액 감소 시 flag | DiffFlag.COVERAGE_DROPPED |
| **Material Change** | 보장 범위에 실질적 영향을 미치는 변경 | LLM endorsement_comparison 판단 대상 |
| **Risk Signal** | 갱신 notes에서 추출한 위험 요소 (사고 이력, 재산 상태 등) | LLM risk_signal_extractor 출력 |
| **Bundle** | 동일 고객의 Auto + Home 묶음. 할인 가능, 해체 시 위험 | Portfolio 분석의 핵심 개념 |
| **SR-22** | 고위험 운전자 증명서. 주(state)가 요구하는 최소 보험 증빙 | ACORD Driver 필드 |

## Coverage Types (ACORD Code Mapping)

### Auto Coverages

| ACORD Code | 이름 | 현재 모델 필드 | 비고 |
|-----------|------|--------------|------|
| `BI` | Bodily Injury | `bodily_injury_limit` | split limit "100/300" |
| `PD` | Property Damage | `property_damage_limit` | |
| `COLL` | Collision | `collision_deductible` | |
| `COMP` | Comprehensive | `comprehensive_deductible` | |
| `UM` | Uninsured Motorist | `uninsured_motorist` | |
| `MEDPM` | Medical Payments | `medical_payments` | |
| `TL` | Towing/Roadside | `roadside_assistance` | bool only — ACORD는 금액 |
| `RENTAL` | Rental Reimbursement | `rental_reimbursement` | bool only — ACORD는 일/최대 한도 |
| `UNDUM` | Underinsured Motorist | **미구현** | UM과 별도, 다수 주 필수 |
| `PIP` | Personal Injury Protection | **미구현** | 무과실(no-fault) 주 필수 |
| `UMPD` | UM Property Damage | **미구현** | 일부 주 별도 커버리지 |

### Home Coverages

| ACORD Code | 이름 | 현재 모델 필드 | 비고 |
|-----------|------|--------------|------|
| `DWELL` | Coverage A (Dwelling) | `coverage_a_dwelling` | 보호 필드 |
| `OTSTR` | Coverage B (Other Structures) | `coverage_b_other_structures` | 보통 A의 10% |
| `PP` | Coverage C (Personal Property) | `coverage_c_personal_property` | |
| `ALE` | Coverage D (Loss of Use) | `coverage_d_loss_of_use` | |
| `PL` | Coverage E (Liability) | `coverage_e_liability` | 보호 필드 |
| `MEDPM` | Coverage F (Medical) | `coverage_f_medical` | |
| `WIND` | Wind/Hail | `wind_hail_deductible` | deductible only |
| — | Water Backup | `water_backup` | bool only — ACORD는 한도액 |
| `EQ` | Earthquake | **미구현** | CA/WA/OR 필수급 |
| `FLOOD` | Flood | **미구현** | NFIP 별도 정책 |

## ACORD Gap Analysis — 현재 모델의 알려진 한계

### 높은 우선순위 (갱신 리뷰 직접 영향)

1. **UIM/PIP/UMPD 미구현** — 주별 필수 커버리지를 비교할 수 없음
2. **Boolean 커버리지에 금액 없음** — rental($30/day), roadside($75/occ), water_backup($5K) 등 한도 비교 불가
3. **사고 이력(Loss History) 없음** — ACORD 80/90의 Prior Loss 섹션. 갱신 보험료의 핵심 결정 요인
4. **HO Form Type 없음** — HO-3(broad), HO-5(open), HO-6(condo) 등. 보장 범위가 근본적으로 다름
5. **Territory Code 없음** — 보험료 산정의 기본 변수

### 중간 우선순위 (분석 정밀도 향상)

6. **Driver DOB** — age 대신 DOB 사용이 ACORD 표준. 정확한 나이 계산 가능
7. **Vehicle 연간 주행거리** — `EstimatedAnnualDistance`. 보험료 주요 요인
8. **Driver 관계/혼인** — `RelationshipToInsured`, `MaritalStatus`. 할인 요인
9. **Endorsement limit/deductible** — 특약의 보장 한도 비교 불가
10. **Prior Carrier** — ACORD 80 Prior Coverage 섹션. 갱신 맥락

## 보호 필드 (Protected Fields) — 절대 자동 변경 금지

ACORD 기준으로 다음 필드는 감소 시 법적/계약적 위험:

- `bodily_injury_limit` — 대인 배상 한도
- `property_damage_limit` — 대물 배상 한도
- `uninsured_motorist` — 무보험 차량 사고 보장
- `coverage_a_dwelling` — 주택 재건축 비용
- `coverage_e_liability` — 개인 배상 책임

## Endorsement Form 체계

ACORD는 단일 코드 목록이 아닌 Form Number 체계 사용:

- **Auto**: PP 시리즈 (PP 03 06, PP 03 22, PP 03 23 등)
- **Home**: HO 시리즈 (HO 04 10, HO 04 61, HO 04 90, HO 04 95 등)
- **Change Request**: ACORD 70 (HO), ACORD 71 (Auto) — type A(Add)/C(Change)/D(Delete)

현재 `Endorsement.code`는 자유 텍스트. 향후 ISO/AAIS form number 매핑 시 validation 추가 가능.

## 적용 규칙

1. **새 커버리지 필드 추가 시**: 위 ACORD 코드 매핑 테이블 참조하여 네이밍
2. **DiffFlag 추가 시**: 해당 커버리지의 업계 중요도 고려 (liability 계열 → URGENT)
3. **LLM 프롬프트 수정 시**: 보험 용어의 정확한 의미 확인 후 사용
4. **Quote 전략 추가 시**: 보호 필드 목록 재확인. 보호 필드는 어떤 전략에서도 변경 불가
