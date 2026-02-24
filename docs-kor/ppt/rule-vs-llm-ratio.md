# Rule-based vs LLM 비율 분석

## 코드량 기준

| 구분 | 라인 | 비율 |
|------|------|------|
| **Rule-based** (engine/) | 1,110 | **42%** |
| **LLM** (llm/) | 499 | **19%** |
| **Hybrid/통합** (routes, aggregator) | 644 | 25% |
| **인프라** (models, config) | ~370 | 14% |

## 함수 기준

| 구분 | 함수 수 | 비율 |
|------|---------|------|
| **Pure rule-based** | 36 | **69%** |
| **Pure LLM** | 8 | **15%** |
| **Hybrid** | 8 | 16% |

## 파이프라인 단계별

```
Parse → Diff → Flag → Risk 판정    ← 100% rule-based (항상 실행)
                         │
                    LLM 분석?        ← opt-in (llm_enabled=true일 때만)
                         │
                    Aggregate        ← hybrid (rule 기반 + LLM 신호로 상향)
                         │
              Summary / Quotes       ← LLM enrichment (lazy 또는 즉시)
```

## LLM 4개 적용 포인트

| LLM 호출 | 대상 | 트리거 |
|----------|------|--------|
| Risk Signal Extraction | notes 분석 | notes 변경 시 |
| Endorsement Comparison | 특약 비교 | endorsement 변경 시 |
| Review Summary | 리뷰 요약 | flags 있는 정책 (lazy) |
| Quote Personalization | 견적 개인화 | quotes 생성 시 |

## Rollback한 2개 포인트

| 포인트 | Rollback 근거 |
|--------|--------------|
| Coverage Similarity | boolean 비교 = 1줄 if문, LLM 불필요. 입력이 구조화되어 있어 의미 해석 불필요 |
| Portfolio Analysis | 100% 구조화된 입력(premium, risk levels, flags). JS에 이미 4단계 verdict + FLAG_ACTIONS 매핑 존재 |

## 핵심 포인트

- **코어 엔진은 100% rule-based** — 파싱, diff, 플래깅, 초기 risk 판정 전부
- **LLM은 additive** — `RR_LLM_ENABLED=false`(기본값)이면 LLM 없이 완전히 동작
- **실패해도 안전** — 모든 LLM 호출이 실패하면 rule-based fallback으로 복귀
- **LLM 적용 기준**: 비정형 텍스트 해석 + 다중 맥락 합성에만 적용. 구조화된 입력의 결정적 판단은 rule-based
- **비율 요약**: 전통적 프로그래밍 **~67%** / AI 기반 로직 **~19%** / 인프라 **~14%**

---

## Before → After 비율 변화

### User-facing 출력 기준

| # | 출력 | Before | After |
|---|------|--------|-------|
| 1 | Risk Level 판정 | Rule | Rule |
| 2 | Diff flags | Rule | Rule |
| 3 | **Review Summary** | Rule | **LLM** |
| 4 | LLM Insights | LLM | LLM |
| 5 | Quote 전략 + 절감액 | Rule | Rule |
| 6 | **Quote Trade-off 텍스트** | Rule | **LLM** |
| 7 | **Quote Broker Tip** | Rule | **LLM** |
| 8 | Portfolio Verdict | Rule | Rule |
| 9 | Portfolio Recommendations | Rule | Rule |
| 10 | Portfolio Action Items | Rule | Rule |
| 11 | Dashboard 테이블 | Rule | Rule |
| 12 | Analytics 차트 | Rule | Rule |

```
Before:  LLM  1/12 ( 8%)  ·  Rule 11/12 (92%)
After:   LLM  4/12 (33%)  ·  Rule  8/12 (67%)
```

### 코드량 기준

```
Before:  LLM 338줄 (14%)  ·  Rule 1,110줄 (46%)  ·  기타 962줄 (40%)
After:   LLM 499줄 (19%)  ·  Rule 1,110줄 (42%)  ·  기타 1,014줄 (39%)
                  ↑ +161줄 (+48% 성장)
```

### 함수 기준

```
Before:  LLM  8/50 (16%)  ·  Rule 40/50 (80%)  ·  Hybrid  2/50 (4%)
After:   LLM  8/52 (15%)  ·  Rule 36/52 (69%)  ·  Hybrid  8/52 (16%)
```

> Rule-based 코드는 한 줄도 삭제하지 않고, LLM 레이어만 위에 얹은 구조.
> 유저가 보는 출력 기준 8% → 33%로 LLM 비중이 늘었지만, 엔진 코어는 그대로.
> Portfolio는 rule-based가 충분히 정확하여 LLM 적용에서 제외.

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
| UI 표시 | 텍스트만 | sparkle + 텍스트 |
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
| UI 표시 | 텍스트만 | sparkle + 텍스트 |
| fallback | — | 원본 하드코딩 trade_off + STRATEGY_TIPS |

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
| UI 구분 | **sparkle** — LLM 생성 콘텐츠 시각적 구분 |
| 비용 영향 | Review ~800 tokens, Quote ~1,200 tokens |
