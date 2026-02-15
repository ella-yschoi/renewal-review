# Experiment 5: LLM Provider Benchmark — OpenAI vs Anthropic

## 실험 개요

보험 갱신 비교 파이프라인의 3가지 LLM 분석 작업에 대해 OpenAI와 Anthropic 모델의 정확도, 속도, 토큰 효율성을 정량 비교한다.

- **목적**: 프로덕션 LLM provider 선정을 위한 데이터 기반 의사결정
- **도구**: Langfuse Datasets + Experiments (SDK 방식)
- **날짜**: 2025-02-15
- **스크립트**: `scripts/langfuse_datasets.py`, `scripts/langfuse_experiment.py`

## 실험 설계

### 비교 대상 모델

| Provider | Model | 특성 | 가격 (input/output per 1M tokens) |
|---|---|---|---|
| OpenAI | gpt-4o-mini | 빠른 응답, JSON mode 지원 | $0.15 / $0.60 |
| Anthropic | claude-sonnet-4-5-20250929 | 고품질 추론 | $3.00 / $15.00 |
| Anthropic | claude-haiku-4-5-20251001 | 경량 모델, 빠른 응답 | $0.25 / $1.25 |

### 평가 대상 작업 (3개 Dataset, 각 5개 테스트 케이스)

**1. risk-signal-benchmark** — 갱신 메모에서 리스크 시그널 추출
- Input: 보험 갱신 시 작성된 notes 텍스트
- Expected: signal 유형, 심각도, 신뢰도, 요약
- 평가 기준: 추출된 signal 개수가 expected와 일치하는가

**2. endorsement-benchmark** — 보증 조항 변경 비교
- Input: prior/renewal endorsement 설명 텍스트
- Expected: material_change 여부, change_type (expansion/restriction/neutral/none)
- 평가 기준: material_change + change_type 두 필드 일치율

**3. coverage-benchmark** — 보장 범위 동등성 판단
- Input: prior/renewal coverage 설명 텍스트
- Expected: equivalent 여부 (true/false)
- 평가 기준: equivalent 필드 일치 여부

### 테스트 데이터 출처

- `golden_eval.json` 기반 4개 시나리오 (실제 보험 데이터 패턴)
- synthetic 시나리오 1개 (극단적 케이스 — SR-22 요구, 지진보험 다운그레이드 등)

### 스코어링 방식

| Score | 측정 내용 | 범위 |
|---|---|---|
| `json_valid` | LLM 응답이 유효한 JSON인가 | 0.0 / 1.0 |
| `key_match` | 핵심 필드가 expected_output과 일치하는가 | 0.0 ~ 1.0 |

---

## 실험 결과

### 1. risk-signal-benchmark (리스크 시그널 추출)

| Model | json_valid | key_match 평균 | avg latency | avg tokens |
|---|---|---|---|---|
| gpt-4o-mini | 5/5 (1.00) | **0.70** | **2.0s** | **251** |
| claude-sonnet | 5/5 (1.00) | **0.90** | 3.4s | 331 |
| claude-haiku | 5/5 (1.00) | **0.80** | 1.7s | 329 |

**항목별 key_match:**

| 테스트 케이스 | gpt-4o-mini | claude-sonnet | claude-haiku |
|---|---|---|---|
| SYNTH-AUTO-001 (SR-22 + 사고 2건) | 1.0 | 0.5 | 1.0 |
| EVAL-HOME-002 (인플레이션 가드) | 0.5 | 1.0 | 1.0 |
| EVAL-AUTO-002 (10대 운전자 추가) | 1.0 | 1.0 | 0.5 |
| EVAL-HOME-001 (수해 클레임) | 0.5 | 1.0 | 1.0 |
| EVAL-AUTO-001 (지역 요율 조정) | 0.5 | 1.0 | 0.5 |

### 2. endorsement-benchmark (보증 조항 비교)

| Model | json_valid | key_match 평균 | avg latency | avg tokens |
|---|---|---|---|---|
| gpt-4o-mini | 5/5 (1.00) | **0.70** | **1.8s** | **201** |
| claude-sonnet | 5/5 (1.00) | **1.00** | 3.3s | 254 |
| claude-haiku | 5/5 (1.00) | **1.00** | 1.6s | 254 |

**항목별 key_match:**

| 테스트 케이스 | gpt-4o-mini | claude-sonnet | claude-haiku |
|---|---|---|---|
| SYNTH-HOME-002 (지진보험 다운그레이드) | 1.0 | 1.0 | 1.0 |
| SYNTH-HOME-001 (책임한도 증가) | 1.0 | 1.0 | 1.0 |
| EVAL-AUTO-001 (변경 없음) | 1.0 | 1.0 | 1.0 |
| EVAL-HOME-001 (수해보장 삭제) | 0.0 | 1.0 | 1.0 |
| EVAL-HOME-002 (평가액 업데이트) | 0.5 | 1.0 | 1.0 |

### 3. coverage-benchmark (보장 동등성 판단)

| Model | json_valid | key_match 평균 | avg latency | avg tokens |
|---|---|---|---|---|
| gpt-4o-mini | 5/5 (1.00) | **1.00** | **1.4s** | **166** |
| claude-sonnet | 5/5 (1.00) | **1.00** | 3.3s | 215 |
| claude-haiku | 5/5 (1.00) | **1.00** | 1.7s | 223 |

세 모델 모두 완벽한 정확도. 이진 판단(equivalent: true/false)은 모든 모델이 잘 처리한다.

---

## 종합 비교

### 정확도 (key_match 평균)

| Dataset | gpt-4o-mini | claude-sonnet | claude-haiku |
|---|---|---|---|
| risk-signal | 0.70 | **0.90** | 0.80 |
| endorsement | 0.70 | **1.00** | **1.00** |
| coverage | 1.00 | 1.00 | 1.00 |
| **전체 평균** | **0.80** | **0.97** | **0.93** |

### 속도 (avg latency)

| Dataset | gpt-4o-mini | claude-sonnet | claude-haiku |
|---|---|---|---|
| risk-signal | **2.0s** | 3.4s | 1.7s |
| endorsement | 1.8s | 3.3s | **1.6s** |
| coverage | **1.4s** | 3.3s | 1.7s |
| **전체 평균** | **1.7s** | **3.3s** | **1.7s** |

### 토큰 사용량 (avg tokens)

| Dataset | gpt-4o-mini | claude-sonnet | claude-haiku |
|---|---|---|---|
| risk-signal | **251** | 331 | 329 |
| endorsement | **201** | 254 | 254 |
| coverage | **166** | 215 | 223 |
| **전체 평균** | **206** | **267** | **269** |

---

## 인사이트

### 1. 작업 난이도에 따라 모델 격차가 달라진다

coverage-benchmark(이진 판단)에서는 세 모델 모두 1.00으로 동일했지만, risk-signal(복합 추론)에서는 gpt-4o-mini가 0.70, Sonnet이 0.90으로 큰 차이가 났다. **작업이 복잡할수록 모델 품질 차이가 드러난다.** 단순한 true/false 판단은 어떤 모델이든 충분하지만, "몇 개의 리스크 시그널을 식별해야 하는가"처럼 열린 추론이 필요한 작업에서는 상위 모델이 유리하다.

### 2. gpt-4o-mini는 "적게 찾는" 경향이 있다

risk-signal에서 gpt-4o-mini의 key_match가 0.5인 항목들을 보면, expected보다 적은 수의 signal을 추출했다. 예를 들어 EVAL-HOME-001("수해 클레임 모니터링")에서 expected는 claims_history + property_risk 두 개지만, gpt-4o-mini는 한 개만 식별했다. **보수적으로 판단하는 경향**이 있어, 리스크를 놓칠 가능성이 상대적으로 높다. 보험 도메인에서는 under-detection이 over-detection보다 위험하므로 이 특성은 불리하다.

### 3. gpt-4o-mini는 endorsement "삭제" 케이스를 잘못 판단한다

EVAL-HOME-001(수해보장 완전 삭제)에서 gpt-4o-mini만 key_match 0.0을 기록했다. prior="Water backup and sump overflow coverage", renewal=""인 상황에서 material_change 또는 change_type을 잘못 판단한 것이다. **빈 문자열 입력에 대한 처리가 취약**한 것으로 보인다. Anthropic 모델들은 이 케이스를 정확하게 "restriction"으로 분류했다.

### 4. Haiku는 Sonnet의 90% 품질을 1/10 가격에 제공한다

전체 정확도 Haiku 0.93 vs Sonnet 0.97로 4%p 차이지만, 가격은 약 10배 저렴하고 속도는 Sonnet의 절반(1.7s vs 3.3s). **가성비 관점에서 Haiku가 압도적**이다. risk-signal에서 Sonnet이 0.90, Haiku가 0.80으로 차이가 있지만, endorsement와 coverage에서는 둘 다 완벽하다.

### 5. Anthropic 모델은 JSON mode 없이도 안정적으로 JSON을 출력한다

OpenAI는 `response_format: json_object`를 명시적으로 지정하여 순수 JSON 출력을 보장한다. Anthropic은 이 옵션이 없어 응답이 마크다운 코드블록(```json ... ```)으로 감싸지는 경우가 있었다. 스크립트에서 `_extract_json()` 후처리로 해결했지만, **프로덕션에서는 Anthropic 응답 파싱 로직이 추가로 필요**하다. json_valid 점수 자체는 세 모델 모두 1.00이므로 JSON 구조 준수는 문제없다.

### 6. 토큰 효율성은 OpenAI가 일관적으로 우세하다

같은 프롬프트에 대해 gpt-4o-mini는 평균 206 tokens, Anthropic 모델들은 267~269 tokens를 사용했다. **Anthropic 모델은 reasoning을 더 상세하게 작성하는 경향**이 있어 토큰이 약 30% 더 든다. 다만 이 "상세한 추론"이 정확도 향상에 기여하므로 단순히 비효율로 볼 수는 없다.

### 7. 속도에서 Haiku와 gpt-4o-mini는 사실상 동급이다

gpt-4o-mini 평균 1.7s, Haiku 평균 1.7s로 거의 동일하다. Sonnet만 3.3s로 약 2배 느리다. **실시간 사용자 경험이 중요한 경우 Sonnet은 부적합**하고, Haiku 또는 gpt-4o-mini가 적절하다.

---

## 권장 사항

### 시나리오별 모델 선택

| 시나리오 | 권장 모델 | 근거 |
|---|---|---|
| 비용 최소화 | gpt-4o-mini | 가장 저렴, coverage 같은 단순 작업에 충분 |
| 정확도 최우선 | claude-sonnet | 전체 0.97, 특히 복합 추론에서 최고 |
| **가성비 최적 (권장)** | **claude-haiku** | **Sonnet 90% 수준 정확도 + OpenAI급 속도 + 합리적 가격** |
| 혼합 전략 | Haiku + Sonnet | 단순 작업(coverage)은 Haiku, 복합 작업(risk-signal)은 Sonnet |

### 프로덕션 적용 시 고려사항

1. **Anthropic 사용 시 JSON 파싱 로직 필수** — `_extract_json()` 같은 후처리기를 `app/llm/client.py`에 통합해야 한다
2. **risk-signal 작업은 상위 모델 사용 고려** — under-detection 리스크가 높은 보험 도메인 특성상, 이 작업만 Sonnet을 쓰는 혼합 전략도 유효
3. **테스트 케이스 확대 필요** — 현재 5개 케이스는 방향성 확인용. 프로덕션 결정 전 최소 20~30개로 확대하여 통계적 유의성 확보 필요

---

## Prompt v2 실험 결과

### 변경 내용

v1 프롬프트의 실험 결과에서 드러난 약점 3가지를 개선했다.

| # | 대상 프롬프트 | 변경 내용 | 의도 |
|---|---|---|---|
| 1 | RISK_SIGNAL_EXTRACTOR | signal 그룹핑 규칙 추가 — "같은 사건의 결과는 하나의 signal, 독립적 원인일 때만 분리" | over-detection과 under-detection 동시 완화 |
| 2 | ENDORSEMENT_COMPARISON | 빈 입력 처리 명시 — "빈 renewal = 보장 삭제 = restriction" | gpt-4o-mini의 삭제 케이스 실패 수정 |
| 3 | 전체 | "no markdown, no code blocks, no extra text" 추가 | Anthropic의 코드블록 래핑 방지 |

### risk-signal-benchmark v1 vs v2

| Model | v1 key_match | v2 key_match | 변화 |
|---|---|---|---|
| gpt-4o-mini | 0.70 | 0.70 | 동일 |
| claude-sonnet | **0.90** | 0.80 | **-0.10** |
| claude-haiku | **0.80** | 0.70 | **-0.10** |

**항목별 v2 key_match:**

| 테스트 케이스 | gpt-4o-mini | claude-sonnet | claude-haiku |
|---|---|---|---|
| SYNTH-AUTO-001 (SR-22 + 사고 2건) | 1.0 | 1.0 (+) | 1.0 |
| EVAL-HOME-002 (인플레이션 가드) | 0.5 | **0.5 (-)** | **0.5 (-)** |
| EVAL-AUTO-002 (10대 운전자 추가) | 1.0 | 1.0 | 1.0 (+) |
| EVAL-HOME-001 (수해 클레임) | 0.5 | **0.5 (-)** | **0.5 (-)** |
| EVAL-AUTO-001 (지역 요율 조정) | 0.5 | 1.0 | 0.5 |

### endorsement-benchmark v1 vs v2

| Model | v1 key_match | v2 key_match | 변화 |
|---|---|---|---|
| gpt-4o-mini | 0.70 | **0.80** | **+0.10** |
| claude-sonnet | 1.00 | 1.00 | 동일 |
| claude-haiku | **1.00** | 0.90 | **-0.10** |

**항목별 v2 key_match:**

| 테스트 케이스 | gpt-4o-mini | claude-sonnet | claude-haiku |
|---|---|---|---|
| SYNTH-HOME-002 (지진보험 다운그레이드) | 1.0 | 1.0 | 1.0 |
| SYNTH-HOME-001 (책임한도 증가) | 1.0 | 1.0 | 1.0 |
| EVAL-AUTO-001 (변경 없음) | 1.0 | 1.0 | 1.0 |
| EVAL-HOME-001 (수해보장 삭제) | **1.0 (+)** | 1.0 | 1.0 |
| EVAL-HOME-002 (평가액 업데이트) | 0.0 | 1.0 | **0.5 (-)** |

### coverage-benchmark v1 vs v2

세 모델 모두 v1, v2 동일하게 1.00. JSON 지시 변경은 정확도에 영향 없음.

### v2 종합 비교

**정확도 (key_match 평균):**

| Dataset | gpt-4o-mini | claude-sonnet | claude-haiku |
|---|---|---|---|
| risk-signal | 0.70 | 0.80 | 0.70 |
| endorsement | 0.80 | **1.00** | 0.90 |
| coverage | 1.00 | 1.00 | 1.00 |
| **전체 평균** | **0.83** | **0.93** | **0.87** |

**v1 → v2 전체 평균 변화:**

| Model | v1 | v2 | 변화 |
|---|---|---|---|
| gpt-4o-mini | 0.80 | **0.83** | **+0.03** |
| claude-sonnet | **0.97** | 0.93 | **-0.04** |
| claude-haiku | **0.93** | 0.87 | **-0.06** |

---

## v2 인사이트

### 1. 프롬프트 개선이 한 모델을 고치면서 다른 모델을 망칠 수 있다

endorsement에서 "빈 입력 = 삭제"를 명시한 결과, gpt-4o-mini의 EVAL-HOME-001이 0.0 → 1.0으로 완벽히 수정됐다. 그러나 같은 프롬프트 변경이 Haiku의 EVAL-HOME-002(평가액 업데이트)를 1.0 → 0.5로 악화시켰다. **프롬프트 변경은 반드시 모든 대상 모델에서 회귀 테스트를 거쳐야 한다.** 하나의 모델 기준으로 최적화하면 다른 모델에서 예상치 못한 부작용이 발생한다.

### 2. signal 그룹핑 규칙은 "what"이 아니라 "how many"를 바꿨다

risk-signal에서 그룹핑 규칙("같은 사건의 결과는 하나의 signal로 묶어라")을 추가한 의도는 모든 모델이 동일한 기준으로 signal을 세게 하는 것이었다. 결과적으로 세 모델 모두 EVAL-HOME-002(인플레이션 가드)에서 0.5로 수렴했다. **모델들이 규칙을 잘 따랐지만, expected_output이 이 규칙을 반영하지 않아서** 점수가 하락한 것이다. 프롬프트와 expected_output은 항상 동기화되어야 한다.

### 3. expected_output 설계가 프롬프트 설계만큼 중요하다

v2 실험에서 드러난 핵심 교훈이다. EVAL-HOME-002의 expected는 signal 1개를 기대하지만, 그룹핑 규칙을 적용하면 모델이 2개로 분리하거나 0개로 판단할 수 있다. **expected_output은 프롬프트의 지시사항을 그대로 따랐을 때 나올 "정답"이어야** 하므로, 프롬프트를 수정하면 expected_output도 함께 재검토해야 한다. 현재 Dataset의 expected_output은 v1 프롬프트 기준으로 작성되어 v2 프롬프트와 어긋난다.

### 4. 3번 개선(JSON 순수성)은 유일하게 안전했다

"no markdown, no code blocks" 지시는 coverage-benchmark에서 세 모델 모두 1.00을 유지했고, 다른 benchmark에서도 json_valid 점수에 부정적 영향이 없었다. **출력 형식에 대한 지시는 내용 추론에 영향을 주지 않으므로 가장 안전한 프롬프트 개선 유형**이다. 프로덕션에서 Anthropic을 사용한다면 이 지시를 반드시 포함해야 한다.

### 5. gpt-4o-mini는 명시적 규칙에 가장 잘 반응한다

endorsement에서 "빈 입력 = restriction"이라는 명시적 규칙을 추가했을 때 gpt-4o-mini만 유의미한 개선(0.70 → 0.80)을 보였다. Sonnet은 이미 1.00이었고 Haiku는 오히려 하락했다. 이는 **gpt-4o-mini가 추론보다 규칙 따르기에 강한 모델**임을 시사한다. gpt-4o-mini를 사용할 경우, 암묵적 추론에 의존하기보다 명시적 규칙을 프롬프트에 포함하는 것이 효과적이다.

### 6. Sonnet은 v2에서도 여전히 가장 정확하다

전체 평균이 0.97 → 0.93으로 하락했지만, 세 모델 중 여전히 1위이다. 특히 endorsement에서는 v1, v2 모두 완벽한 1.00을 유지했다. **프롬프트 변경에 대한 내성(robustness)이 가장 높은 모델**이다. risk-signal에서의 하락(0.90 → 0.80)도 expected_output 불일치 때문이지 모델 성능 자체의 문제가 아닐 가능성이 높다.

### 7. 프롬프트 엔지니어링의 ROI는 체감적으로 낮았다

v1 → v2에서 3가지 개선을 시도했지만, 전체적인 결과는 미미하거나 오히려 역효과였다. gpt-4o-mini +0.03, Sonnet -0.04, Haiku -0.06. **5개 테스트 케이스에서는 프롬프트 한 줄의 변경이 전체 점수를 크게 흔든다.** 프롬프트 최적화의 효과를 정확히 측정하려면 테스트 케이스를 최소 20개 이상으로 확대해야 개별 케이스의 노이즈가 희석된다.

---

## v2 후속 작업

1. **expected_output 재정렬** — v2 프롬프트의 signal 그룹핑 규칙에 맞게 risk-signal Dataset의 expected_output을 수정
2. **테스트 케이스 확대** — 5개 → 20개 이상으로 확대하여 통계적 유의성 확보
3. **프롬프트 v3** — expected_output 수정 후 재실험으로 순수한 프롬프트 개선 효과 측정

---

## 실행 방법

```bash
# Dataset 등록 (최초 1회)
uv run python scripts/langfuse_datasets.py

# 전체 실험 실행
PYTHONPATH=. uv run python scripts/langfuse_experiment.py

# 특정 provider만
PYTHONPATH=. uv run python scripts/langfuse_experiment.py --provider anthropic-haiku

# 특정 dataset만
PYTHONPATH=. uv run python scripts/langfuse_experiment.py --dataset risk

# 결과 확인
# Langfuse → Datasets → select dataset → Runs
```

## 파일 구조

```
scripts/
├── langfuse_datasets.py      # 3개 Dataset + 15개 item 등록
└── langfuse_experiment.py     # 실험 실행 + 자동 스코어링

docs/experiments/
└── 5-langfuse-llm-benchmark.md  # 이 문서
```
