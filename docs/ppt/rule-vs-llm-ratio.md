# Rule-based vs LLM 비율 분석

## 코드량 기준

| 구분 | 라인 | 비율 |
|------|------|------|
| **Rule-based** (engine/) | 1,110 | **39%** |
| **LLM** (llm/) | 692 | **24%** |
| **Hybrid/통합** (routes, aggregator) | 644 | 23% |
| **인프라** (models, config) | ~416 | 14% |

## 함수 기준

| 구분 | 함수 수 | 비율 |
|------|---------|------|
| **Pure rule-based** | 36 | **67%** |
| **Pure LLM** | 11 | **20%** |
| **Hybrid** | 7 | 13% |

## 파이프라인 단계별

```
Parse → Diff → Flag → Risk 판정    ← 100% rule-based (항상 실행)
                         │
                    LLM 분석?        ← opt-in (llm_enabled=true일 때만)
                         │
                    Aggregate        ← hybrid (rule 기반 + LLM 신호로 상향)
                         │
              Summary / Quotes /     ← LLM enrichment (lazy 또는 즉시)
              Portfolio
```

## LLM 6개 적용 포인트

| LLM 호출 | 대상 | 트리거 |
|----------|------|--------|
| Risk Signal Extraction | notes 분석 | notes 변경 시 |
| Endorsement Comparison | 특약 비교 | endorsement 변경 시 |
| Coverage Similarity | 보장 비교 | coverage 삭제 시 |
| Review Summary | 리뷰 요약 | flags 있는 정책 (lazy) |
| Quote Personalization | 견적 개인화 | quotes 생성 시 |
| Portfolio Analysis | 포트폴리오 분석 | analyze 클릭 시 |

## 핵심 포인트

- **코어 엔진은 100% rule-based** — 파싱, diff, 플래깅, 초기 risk 판정 전부
- **LLM은 additive** — `RR_LLM_ENABLED=false`(기본값)이면 LLM 없이 완전히 동작
- **실패해도 안전** — 모든 LLM 호출이 실패하면 rule-based fallback으로 복귀
- **비율 요약**: 전통적 프로그래밍 **~61%** / AI 기반 로직 **~24%** / 인프라 **~15%**

---

## Before / After LLM 적용 비교

### 1. Review Summary (리뷰 요약)

**Before — Rule-based**
```
"Flags: premium_increase_critical, coverage_dropped | Risk: urgent_review"
```
기계적 나열. flag 이름과 risk level만 표시.

**After — LLM**
```
"This renewal shows a 23% premium increase from $2,400 to $2,952
with water backup coverage dropped and deductible unchanged.
Prior water damage claim and aging roof noted — recommend
urgent broker review before binding."
```
맥락 기반 자연어 요약. 변경 원인·영향·권장 조치를 2-3문장으로 전달.

| 비교 항목 | Before | After |
|-----------|--------|-------|
| 형식 | `Flag: ... \| Risk: ...` | 자연어 2-3문장 |
| 맥락 | 없음 | premium 수치, 삭제된 보장, notes 내용 반영 |
| 실행 시점 | 배치 처리 중 즉시 | lazy — UI에서 정책 상세 열 때 |
| UI 표시 | 텍스트만 | ✨ sparkle + 텍스트 |
| fallback | — | LLM 실패 시 기존 기계적 형식 유지 |

---

### 2. Quote Personalization (견적 개인화)

**Before — Rule-based**
```
Trade-off: "Higher deductibles mean more out-of-pocket cost per claim"
Broker Tip: (하드코딩 STRATEGY_TIPS 테이블에서 선택)
  → "Recommended for clients with low claim history and emergency savings
     above the proposed deductible."
```
전략별 고정 문구. 모든 고객에게 동일한 텍스트.

**After — LLM**
```
Trade-off: "Raising the deductible to $2,500 saves 12.5% but means higher
           out-of-pocket costs given the prior water damage claim history."
Broker Tip: "Verify the client has emergency savings above $2,500 before
            recommending this option, especially with the aging roof."
```
정책 맥락(claim 이력, 차량, 보장 상태) 반영한 맞춤 조언.

| 비교 항목 | Before | After |
|-----------|--------|-------|
| Trade-off | 전략별 고정 1줄 (6개) | 정책 맥락 반영 맞춤 문구 |
| Broker Tip | STRATEGY_TIPS 테이블 (5개) | LLM 생성 맞춤 조언 |
| 개인화 수준 | 없음 — 같은 전략이면 같은 텍스트 | 높음 — claim, 차량, notes 반영 |
| 절감 계산 | rule-based (유지) | rule-based (유지) — LLM은 텍스트만 |
| UI 표시 | 텍스트만 | ✨ sparkle + 텍스트 |
| fallback | — | 원본 하드코딩 trade_off + STRATEGY_TIPS |

---

### 3. Portfolio Risk Aggregator (포트폴리오 분석)

**Before — Rule-based**

```
Verdict:  "Immediate Attention Required — 2 urgent, client follow-up needed"
          (urgentCount 기반 4단계 고정 메시지)

Bundle:   "Carrier consolidation opportunity — bundle discount available"
          (is_bundle / carrier_mismatch 조합 4가지 고정 메시지)

Actions:  "Review 2 urgent policies immediately"
          "Remove lower policy to reduce premium (AUTO-001, HOME-001)"
          (FLAG_ACTIONS 매핑 테이블 6개 + risk count 기반)
```

**After — LLM**

```
Verdict:  "Portfolio requires attention — 2 policies flagged urgent
           with significant premium increases and coverage gaps."

Recommendations:
  • "Consolidate carriers for bundle discount — estimated 5-10% savings"
  • "Remove duplicate medical coverage across auto/home policies"

Action Items:
  • HIGH: Review HOME-2024-0926 — urgent premium increase
  • MEDIUM: Consolidate medical payments across auto/home
  • LOW: Consider umbrella policy for liability exposure
```

| 비교 항목 | Before | After |
|-----------|--------|-------|
| Verdict | 4단계 고정 메시지 | 맥락 기반 자연어 요약 |
| Recommendations | bundle 조합 4가지 고정 | 구체적 전략 + 예상 절감액 |
| Action Items | FLAG_ACTIONS 6개 + count 기반 | HIGH/MEDIUM/LOW 우선순위 + 정책 특정 |
| 개인화 수준 | 없음 — 같은 조건이면 같은 텍스트 | 높음 — 개별 정책 상황 반영 |
| UI 표시 | 텍스트만 | 섹션 헤더 ✨ sparkle |
| fallback | — | 기존 rule-based 메시지 그대로 |

---

## 공통 패턴

모든 LLM 적용 포인트에서 동일한 아키텍처 패턴을 따른다:

```
1. Rule-based 결과를 먼저 생성 (항상)
2. settings.llm_enabled 체크
3. LLM 호출 → JSON 응답 파싱
4. 성공 시: LLM 결과로 교체 + sparkle 표시
5. 실패 시: 원본 rule-based 결과 유지 (사용자는 차이를 모름)
```

| 속성 | 값 |
|------|-----|
| LLM 기본값 | **꺼짐** (`RR_LLM_ENABLED=false`) |
| 실패 전략 | **graceful fallback** — rule-based 유지 |
| 부분 응답 | **partial match** — 있는 필드만 반영 |
| UI 구분 | **✨ sparkle** — LLM 생성 콘텐츠 시각적 구분 |
| 비용 영향 | Review ~800 tokens, Quote ~1,200 tokens, Portfolio ~1,600 tokens |
