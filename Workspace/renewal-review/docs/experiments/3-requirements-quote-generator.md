# Requirements: Smart Quote Generator

## 개요

기존 renewal-review 파이프라인은 prior vs renewal 변경 사항을 **탐지**하고 위험도를 **분류**한다.
Quote Generator는 그 다음 단계 — 위험 플래그가 발생한 정책에 대해 **보험료를 줄이면서 핵심 보장을 유지하는 대안 견적**을 자동 생성한다.

---

## 기능 요구사항

### FR-1: 대안 견적 생성

`ReviewResult`(diff + flags + risk level + RenewalPair)를 입력받아 **최대 3개의 대안 견적**을 반환한다.

- 각 견적은 renewal 정책을 기반으로 특정 커버리지를 조정한 변형이다.
- 각 견적에 **예상 절감액(달러)**과 **절감률(%)**을 포함한다.
- 대안이 없는 경우(이미 최소 구성) 빈 리스트를 반환한다.

### FR-2: 커버리지 조정 전략

Auto 정책과 Home 정책 각각에 대해 다음 전략을 적용한다:

**Auto 전략:**
| 전략 | 조정 내용 | 예상 절감 비율 |
|------|----------|---------------|
| raise_deductible | collision 500→1000, comprehensive 250→500 | 8-12% |
| drop_optional | rental_reimbursement, roadside_assistance 제거 | 3-5% |
| reduce_medical | medical_payments 5000→2000 | 2-3% |

**Home 전략:**
| 전략 | 조정 내용 | 예상 절감 비율 |
|------|----------|---------------|
| raise_deductible | deductible 1000→2500 | 10-15% |
| drop_water_backup | water_backup 제거 | 2-4% |
| reduce_personal_property | coverage_c를 coverage_a의 50%로 축소 | 3-5% |

### FR-3: 보호 제약 조건

**절대 조정 불가 항목 (hard constraints):**
- bodily_injury_limit — 변경 금지
- property_damage_limit — 변경 금지
- coverage_e_liability (Home) — 변경 금지
- uninsured_motorist — 변경 금지
- coverage_a_dwelling (Home) — 변경 금지

위 항목 중 하나라도 조정된 견적은 생성하지 않는다.

### FR-4: 이미 최적화된 항목 건너뛰기

전략이 적용될 수 없는 경우를 올바르게 처리한다:
- collision_deductible이 이미 1000 이상 → raise_deductible 건너뛰기
- rental_reimbursement가 이미 False → drop_optional에서 해당 항목 제외
- water_backup이 이미 False → drop_water_backup 건너뛰기
- coverage_c가 이미 coverage_a의 50% 이하 → reduce_personal_property 건너뛰기

### FR-5: 데이터 모델

새 파일 `app/models/quote.py`에 다음 모델을 정의한다:

- `CoverageAdjustment`: 개별 조정 항목
  - `field: str` — 조정된 필드명
  - `original_value: str` — 원래 값
  - `proposed_value: str` — 제안 값
  - `strategy: str` — 적용된 전략명

- `QuoteRecommendation`: 대안 견적
  - `quote_id: str` — 고유 ID (예: "Q1", "Q2", "Q3")
  - `adjustments: list[CoverageAdjustment]` — 조정 목록
  - `estimated_savings_pct: float` — 예상 절감률 (%)
  - `estimated_savings_dollar: float` — 예상 절감액 ($)
  - `trade_off: str` — 고객에게 설명할 트레이드오프 요약 (1문장)

### FR-6: 엔진 함수

새 파일 `app/engine/quote_generator.py`에 핵심 함수를 정의한다:

```python
def generate_quotes(pair: RenewalPair, diff: DiffResult) -> list[QuoteRecommendation]
```

- Auto/Home 타입에 따라 해당 전략만 적용
- 각 전략을 독립적으로 적용하여 개별 견적 생성 (전략 조합 X)
- 절감액 = renewal premium × 절감률 (전략별 고정 비율 사용)
- 절감률은 FR-2의 범위 중간값 사용 (Auto: 10%, 4%, 2.5% / Home: 12.5%, 3%, 4%)

### FR-7: API 엔드포인트

새 파일 `app/routes/quotes.py`에 엔드포인트를 정의한다:

```
POST /quotes/generate
```

- 입력: RenewalPair (JSON body)
- 내부에서 diff → flag → generate_quotes 순서로 처리
- 출력: `list[QuoteRecommendation]`
- 정책에 flags가 없으면 빈 리스트 반환 (대안 불필요)

### FR-8: 라우터 등록

`app/main.py`에 quotes 라우터를 등록한다.

### FR-9: 테스트

새 파일 `tests/test_quote_generator.py`에 다음 케이스를 테스트한다:

1. **Auto 정책 — 전략 3개 모두 적용 가능**: 3개 견적 반환, 각각 절감률 확인
2. **Home 정책 — 전략 3개 모두 적용 가능**: 3개 견적 반환
3. **이미 최적화된 Auto 정책**: deductible 이미 높음, optional 이미 없음 → 빈 리스트 또는 적용 가능한 것만
4. **보호 제약 검증**: 모든 견적에서 liability 필드가 변경되지 않았는지 확인
5. **flags 없는 정책**: 빈 리스트 반환
6. **기존 테스트 regression 없음**: 전체 테스트 통과

---

## 수락 기준

- [ ] `POST /quotes/generate`가 Auto/Home 모두에서 올바른 견적 반환
- [ ] 모든 견적에서 liability 필드 불변 (hard constraint)
- [ ] 이미 최적화된 항목은 건너뛰기
- [ ] 절감률이 전략별 범위 내
- [ ] FR-9의 6개 테스트 케이스 전부 통과
- [ ] 기존 테스트 전부 통과 (regression 없음)
- [ ] ruff check 통과
- [ ] convention.md 준수 (no docstrings, type hints, < 300줄/파일)
