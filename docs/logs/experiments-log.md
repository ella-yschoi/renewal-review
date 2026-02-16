# 실험 작업 로그

> Quandri 인터뷰(2/17) 발표 준비 과정 기록. 프레젠테이션 소스로 활용.
> **최신순 정렬** — 새 엔트리는 항상 맨 위에 추가한다.

---

## 2026-02-16 13:11 | `main`

### 무엇을 했는가
Self-Correcting Loop 스킬을 renewal-review 전용에서 **프로젝트 무관(project-agnostic) 글로벌 스킬**로 범용화. 5개 파일을 `~/.agents/skills/self-correcting-loop/`에 작성/이동하고, renewal-review의 프로젝트 로컬 파일 3개를 삭제. 가이드 문서를 글로벌 스킬 안내로 교체.

**신규 파일 2개**:
- `detect-project.sh`: 프로젝트 자동 감지 라이브러리 — `detect_project_type`, `detect_lint_cmd`, `detect_test_cmd`, `detect_security_cmd`, `detect_src_dirs`, `detect_instruction_files`, `detect_design_docs`, `detect_changed_files`, `print_detected_config` 9개 함수. Python/Node/Rust/Go 지원, ENV → Makefile → package.json → 도구 존재 확인 순서로 감지, `uv.lock` → `uv run`, `poetry.lock` → `poetry run` Python runner 자동 감지
- `PROMPT-TEMPLATE.md`: 프로젝트 무관한 범용 PROMPT 템플릿 (copy-and-fill 형태)

**재작성 3개**:
- `self-correcting-loop.sh`: `PROMPT_FILE`/`REQUIREMENTS_FILE` 필수화, `$LINT_CMD`/`$TEST_CMD`/`$SECURITY_CMD` 자동 감지 사용, `$OUTPUT_DIR` 기반 아티팩트 경로
- `triangular-verify.sh`: `detect_instruction_files`/`detect_design_docs`/`detect_changed_files` 동적 삽입
- `SKILL.md`: 지원 프로젝트 타입 테이블, 환경변수 오버라이드 테이블, 다국어 예제

**삭제 3개**: `.claude/skills/self-correcting-loop/SKILL.md`, `scripts/self-correcting-loop.sh`, `scripts/triangular-verify.sh`

검증: ruff 0 errors, pytest 116/116 passed. renewal-review에서 자동 감지 정상 동작(Python, make lint, make test, semgrep, app/).

### 왜 했는가
기존 스킬이 renewal-review에 하드코딩되어 있어(ruff, pytest, semgrep, `app/`, `docs/experiments/` 등), 다른 프로젝트에서는 사용 불가능했다. 프레젠테이션에서 "팀 전체를 빠르게 만드는 것"을 주장하려면, 스킬이 실제로 어떤 프로젝트에서든 동작해야 한다. PROMPT.md만 바꾸면 어떤 기능이든 자동 구현할 수 있다는 실험 4의 결론을 프로젝트 레벨에서도 증명 — PROMPT.md만 바꾸는 것에서 나아가, 프로젝트 자체를 바꿔도 동작하도록 확장.

### 어떻게 했는가
`detect-project.sh`를 공유 라이브러리로 설계하여 양 스크립트가 `. "$(dirname "$0")/detect-project.sh"`로 source. 각 감지 함수는 idempotent(이미 설정된 ENV var가 있으면 skip) — 환경변수 오버라이드가 항상 자동 감지보다 우선. `_has_makefile_target`, `_has_npm_script`, `_python_runner` 헬퍼로 프로젝트별 분기. `PROMPT_FILE`/`REQUIREMENTS_FILE`은 `${VAR:?ERROR}` 패턴으로 필수 강제(기본값 제거). 출력 경로를 `$OUTPUT_DIR`(기본 `.self-correcting-loop/`)로 통일하여 프로젝트의 기존 디렉토리 구조에 의존하지 않음. INSTRUCTION_FILES 중복 제거를 위해 `seen` 패턴 적용.

---

## 2026-02-16 03:34 | `main`

### 무엇을 했는가
8-Phase 대규모 리팩토링 실행. Phase 0(코드 정리) → Phase 1(도메인 모델 + DB 스키마) → Phase 2(규칙 확장) → Phase 3(DB write-through) → Phase 4-5(Dashboard 강화 + Quote 통합) → Phase 6(Analytics 브로커 관점 개편) → Phase 7(LLM Insights 설명) → Phase 8(문서 + 정리). 테스트 100→117개, DiffFlag 15→23개. 3개 PATCH 엔드포인트, 1개 GET 엔드포인트 추가. quotes.html 삭제, Quote Generator 페이지 제거 → Review Detail에 인라인 통합. DB 테이블 3개(raw_renewals, rule_results, llm_results) 재설계. Analytics에서 시간 지표 삭제, 브로커 워크플로우 지표(Contact Needed, Contacted, Quotes Generated, Reviewed) 추가.

### 왜 했는가
핵심 문제: DB에 아무것도 저장되지 않아 앱 재시작 시 모든 결과 소실. 동시에 브로커 관점의 워크플로우 추적(연락 여부, 견적 생성, 리뷰 완료)이 없어 실용성이 부족했다. Rule-based 리스크 판별도 구조화 필드(violations, SR-22, 25세 미만)와 notes 키워드 매칭이 빠져 있어 실제 보험 도메인의 위험 요소를 충분히 감지하지 못했다.

### 어떻게 했는가
Phase 간 의존성 그래프에 따라 순차 실행. Phase 0에서 중복 코드 헬퍼 추출(`_bool_change`, `_diff_entities`, `risk_distribution`), Pydantic mutation 수정(`model_copy`), LLM 클라이언트 싱글턴 팩토리 도입. Phase 1에서 DiffFlag 8개 확장, ReviewResult 3개 필드 추가, DB 테이블 3개 재설계. Phase 2에서 `_flag_drivers`, `_flag_coverage_gap`, `notes_rules.py` 키워드 매칭 추가. Phase 3에서 `ResultWriter` Protocol + `DbResultWriter`(try/except graceful) + `NoopResultWriter` + lifespan cache restore. Phase 4-5에서 PATCH 3개, Dashboard 필터/체크박스, Review Detail 인라인 Quote + reviewed_at 자동 기록. Phase 6에서 `AnalyticsSummary`/`TrendPoint`에서 `avg_processing_time_ms` 제거, `BrokerMetrics` 모델 + `compute_broker_metrics()` + `/analytics/broker` 엔드포인트 추가. Phase 7에서 migration.html에 LLM 분석 맥락 설명 추가. 매 Phase 후 `ruff check` + `pytest` 검증.

---

## 2026-02-15 18:06 | `main`

### 무엇을 했는가
Langfuse 벤치마크(실험 5) 결과를 반영하여 task별 모델 라우팅을 구현했다. 기존에는 `RR_LLM_PROVIDER` 단일 설정으로 4개 LLM 작업 모두 동일 모델을 사용했으나, 이제 `LLMClient`가 `trace_name` 기반으로 작업별 최적 모델을 자동 선택한다.

라우팅 결과: `risk_signal_extractor` → Sonnet (정확도 0.90, 복합 추론), 나머지 3개(`endorsement_comparison`, `review_summary`, `quote_personalization`) → Haiku (Sonnet 동급 정확도 + 2배 빠르고 10배 저렴). `RR_LLM_PROVIDER` 환경변수 제거.

검증: ruff 0 errors, pytest 100/100 passed. design-doc 3개 섹션 업데이트.

### 왜 했는가
실험 5에서 3개 모델(gpt-4o-mini, Sonnet, Haiku)을 3개 작업에 대해 정량 비교했으나, 그 결과가 프로덕션 코드에 반영되지 않은 상태였다. 모든 작업에 동일 모델을 사용하면 벤치마크를 실행한 의미가 없다. 벤치마크의 핵심 발견 — "작업 복잡도에 따라 모델 격차가 달라진다" — 을 코드로 실현해야 했다.

### 어떻게 했는가
4개 파일 변경. `LLMConfig`에 `sonnet_model`, `haiku_model`, `task_models` dict 추가. `OpenAIClient`와 `AnthropicClient`의 constructor에 `model` 파라미터를 추가하여 외부에서 모델 주입 가능하게 변경. `LLMClient`를 라우팅 클라이언트로 재작성 — `trace_name` → `task_models` dict → `(provider, model)` 해석 → 해당 클라이언트에 위임. 동일 (provider, model) 조합은 인스턴스를 캐싱하여 재사용. `LLMPort` 인터페이스(domain 레이어)는 변경 없음 — 헥사고날 아키텍처의 "외부 변경은 adaptor에서 흡수" 원칙을 따름.

---

## 2026-02-15 17:03 | `main`

### 무엇을 했는가
`app/adaptor/llm/mock.py`의 `risk_signal_extractor` mock 응답에 `regulatory` 타입 signal 1개 추가. 기존 `claims_history`, `property_risk` 2개에서 3개로 확장.

추가한 signal: `"SR-22 filing active — state-mandated proof of insurance required for continued compliance"` (severity: high).

검증: ruff 0 errors, pytest 100/100 passed.

### 왜 했는가
프롬프트(`prompts.py`)에 `regulatory`가 signal type으로 정의되어 있지만 mock에서 테스트되지 않는 상태였다. mock이 프롬프트의 signal 카테고리를 커버하지 않으면, 실제 LLM 응답에서 regulatory signal이 반환됐을 때의 흐름을 검증할 수 없다.

또한, CLAUDE.md의 Insurance Domain 섹션에 명시된 `adaptor/llm/` 변경 시 `/insurance-domain` 스킬 참조 파이프라인(L1→L2)이 실제로 작동하는지 검증하는 의도도 있었다.

### 어떻게 했는가
CLAUDE.md 109행의 트리거 조건(`adaptor/llm/` 변경 시 `/insurance-domain` 스킬 참조)에 따라 Skill tool로 insurance-domain 스킬을 호출. 스킬의 Core Terminology 테이블에서 SR-22 정의("고위험 운전자 증명서, 주가 요구하는 최소 보험 증빙")와 prompts.py의 regulatory 카테고리 정의("State filing requirements, SR-22 mandates, minimum limit compliance")를 교차 참조하여 signal 내용을 작성. ruff E501(line-length) 위반 → implicit string concatenation으로 해결.

---

## 2026-02-15 14:51 | `main`

### 무엇을 했는가
ACORD 표준 기반 보험 도메인 지식을 LLM 프롬프트, mock 응답, 샘플 데이터, design-doc에 반영. 2단계(P0: 프롬프트+mock, P1: 샘플+문서)로 나눠 실행.

**P0 — LLM 프롬프트 ACORD 정렬 (4개 프롬프트)**:
- `ENDORSEMENT_COMPARISON`: HO 04 xx / PP 03 xx form 참조, ACORD change type (A/C/D), liability 우선 materiality 규칙 추가
- `RISK_SIGNAL_EXTRACTOR`: signal type에 `regulatory` 추가 (총 6개), ACORD Prior Loss 섹션 참조하는 카테고리별 설명 강화
- `REVIEW_SUMMARY`: liability limit(BI, PD, Coverage E) 변경 우선순위, 브로커 액션 지향 지시문 추가
- `QUOTE_PERSONALIZATION`: 보호 필드(BI, PD, UM, Coverage A, Coverage E) 감소 금지 명시, 위반 시 브로커 확인 요구

**P0 — mock 응답 수정 (2건)**:
- `signal_type: "property_condition"` → `"property_risk"` (프롬프트 enum에 없던 값 — 실제 LLM이 반환하면 validation 실패할 수 있는 버그)
- endorsement reasoning: 제네릭("Coverage scope narrowed") → 구체적("HO 04 95 removed — sewer/drain coverage dropped")

**P1 — 샘플 데이터 ACORD form number 정렬**:
- `WB01` → `HO 04 95` (Water Backup/Sump Overflow 표준 form)
- `HO-61` → `HO 04 61` (Scheduled Personal Property 표준 form)
- 영향 범위: `home_pair.json`, `golden_eval.json`, `generate.py`, `implementation-plan.md`, `test_differ.py`

**P1 — design-doc 실제 코드 동기화**:
- `app/llm/` 디렉토리 제거 (client.py가 `adaptor/llm/`으로 이동 완료)
- `client.py`, `quote_advisor.py` 경로 `adaptor/llm/`으로 수정
- DB models 경로 `app/infra/db_models.py`로 수정
- 프롬프트 테이블에 ACORD 정렬 컬럼 추가

검증: ruff 0 errors, pytest 100/100 passed.

### 왜 했는가
이전 세션에서 ACORD 표준 기반 갭 분석을 수행하고 CLAUDE.md + Custom Skill로 도메인 지식 인프라를 구축했지만, 실제 코드에는 아직 반영되지 않은 상태였다. 데모에서 "보험 도메인 지식이 코드에 스며든 상태"를 보여주려면, LLM이 사용하는 프롬프트와 샘플 데이터가 업계 표준 용어를 사용해야 한다.

핵심 문제: mock의 `property_condition`은 프롬프트 enum에 없는 값이었고, endorsement code `WB01`은 업계에서 인식되지 않는 임의 코드였다. 데모에서 이 데이터가 보이면 "도메인 전문가가 검토하지 않은 코드"로 보인다.

### 어떻게 했는가
이전 세션에서 만든 `.claude/skills/insurance-domain/SKILL.md`의 ACORD 매핑 테이블을 참조하여 수정. 다만, 이번 세션에서는 skill이 session-start 시 자동 로드된 것이 아니라 이전 세션 continuation의 system-reminder로 컨텍스트에 포함되어 있었다. Skill → 코드 반영 파이프라인이 설계 의도대로 작동한 것은 아님 — fresh session에서 검증 필요.

ruff E501(line-length 99) 위반이 프롬프트 문자열에서 5건 발생 → triple-quoted string 내 줄바꿈으로 해결. golden_eval.json 코드 변경 후 test_differ.py의 `"WB01" in prior_value` 하드코딩도 함께 수정.

---

## 2026-02-15 12:37 | `experiment/portfolio-aggregator`

### 무엇을 했는가
헥사고날 아키텍처 + 디자인 패턴 4종을 기존 flat 구조(`engine/`, `models/`, `routes/`, `llm/`)에 적용하여 전체 앱을 `domain/`, `application/`, `api/`, `adaptor/`, `infra/` 5개 레이어로 리팩토링. 8단계 실행, 44개 파일 변경(740줄 추가, 578줄 삭제), 100/100 테스트 유지.

**구조 변경**: `git mv`로 33개+ 파일을 새 디렉토리 구조로 이동. 구 디렉토리(`engine/`, `models/`, `routes/`) 삭제.

**디자인 패턴 4종 적용**:
1. **Enum**: `enums.py`에 6개 StrEnum 중앙 정의(Severity, UnbundleRisk, QuoteStrategy, AnalysisType, FlagType). 모든 bare string 리터럴 → enum 교체.
2. **Config 중앙화**: `config.py`에 4개 중첩 설정 클래스(RuleThresholds, QuoteConfig, PortfolioThresholds, LLMConfig). rules.py/quote_generator.py/portfolio_analyzer.py의 매직넘버 12개+ 제거.
3. **Immutability**: `FieldChange`에 `frozen=True` 적용. `rules.py`를 functional 스타일로 리라이트 — `c.flag = X` 직접 mutation 제거 → `model_copy(update={"flag": X})`.
4. **DI**: `infra/deps.py`에 싱글턴 스토어 3개(Review/History/Job), 모든 route에서 `Depends()` 사용. 모듈 레벨 global dict/deque 전면 제거.

**포트 & 어댑터**: `domain/ports/`에 Protocol 3개(LLMPort, ReviewStore, DataSourcePort). `adaptor/llm/`에 OpenAI/Anthropic 클라이언트 분리, `adaptor/persistence/`에 JSON/DB 로더 분리, `adaptor/storage/memory.py`에 인메모리 구현체 3종.

**LLM 응답 Pydantic 스키마**: `adaptor/llm/schemas.py`에 4개 응답 검증 모델(`RiskSignalExtractorResponse`, `EndorsementComparisonResponse`, `ReviewSummaryResponse`, `QuotePersonalizationResponse`) 신규 생성. 기존 `dict[str, Any]` 반환 → `model_validate()` 후 타입 안전 접근으로 전환. `llm_analysis.py`의 3개 함수(`_analyze_notes`, `_analyze_endorsement`, `generate_summary`)와 `quote_advisor.py`의 `personalize_quotes`에서 `.get()` 수동 파싱 제거, `ValidationError` catch → 기존 fallback과 동일한 경로로 처리. malformed 응답 테스트 4건 추가(notes/endorsement/summary/quote).

검증: ruff 0 errors, pytest 100/100 passed, semgrep 0 findings (305 rules). `domain/` → 외부 import 0건 (헥사고날 경계 검증 통과).

### 왜 했는가
BMS(Broker Management System) 교체 시나리오 대비. 현재 flat 구조에서는 데이터 포맷 변경 시 도메인 로직, 라우트, LLM 코드가 모두 영향을 받음. 헥사고날 아키텍처로 의존성 방향을 `api/ → application/ → domain/ ← adaptor/`로 잡으면, 외부 시스템 변경이 `adaptor/`에서 흡수되고 도메인 로직은 무변경. 프레젠테이션에서 "코드를 빠르게 만드는 것"을 넘어 "유지보수 가능한 구조를 자동화하는 것"을 보여주기 위한 작업.

### 어떻게 했는가
8단계 순차 실행, 각 단계마다 `ruff check` + `pytest` 통과 확인. Step 1(파일 이동)에서 linter 훅이 import 편집을 되돌리는 문제 발생 → Python bulk replacement 스크립트로 해결. Step 4(immutability)에서 `_flag_changes` → `_detect_flag` + `_flag_changes` 2단 분리로 깔끔한 functional 패턴 구현. Step 6(DI)에서 ruff B008 규칙(Depends() in defaults)과 충돌 → `pyproject.toml`에 `extend-immutable-calls` 추가. LLM 스키마 도입은 기존 `client.complete() → dict[str, Any]` 반환 구조는 유지하면서, 소비자 레이어(`application/llm_analysis.py`, `adaptor/llm/quote_advisor.py`)에서만 `model_validate()`로 검증 — 클라이언트/mock은 변경 없이 동일한 validation 경로를 테스트. convention.md에 헥사고날 레이어 규칙 + 디자인 패턴 4개 규칙 추가.

---

## 2026-02-15 12:03 | `main`

### 무엇을 했는가
LLM 적용 포인트 6개를 4가지 기준(입력 형태, 의미 해석 필요성, Rule 대안의 한계, 출력 품질 차이)으로 평가하여, rule-based로 충분한 2개를 rollback. 12개 파일 수정, 54줄 추가 / 432줄 삭제. 96 tests passed, ruff all checks passed.

- **Coverage Similarity 제거**: `_analyze_coverage()` 함수, COVERAGE_SIMILARITY 프롬프트, mock, 테스트 삭제. aggregator.py에서 "NOT equivalent" 조건 제거. 입력이 이미 boolean으로 정규화되어 있어 `if prior == True and renewal == False` 1줄로 해결되는 문제에 LLM API를 호출하고 있었음.
- **Portfolio Analysis 제거**: `portfolio_advisor.py` 파일 삭제, PORTFOLIO_ANALYSIS 프롬프트/mock 삭제, PortfolioSummary에서 LLM 필드 4개(llm_verdict, llm_recommendations, llm_action_items, llm_enriched) 삭제, routes/portfolio.py에서 LLM enrichment 호출 제거, portfolio.html에서 LLM 분기 3곳(verdict, recommendations, action items) 제거, 테스트 4건 삭제. JS에 이미 4단계 verdict + FLAG_ACTIONS 매핑이 잘 작동하고 있었음.
- **문서 업데이트**: design-doc.md 전체 LLM 관련 섹션 4개 포인트로 정리(프롬프트 6→4개, 테스트 101→96개), rule-vs-llm-ratio.md 전면 재작성(Rollback 근거 섹션 추가, 비율 수치 업데이트).

### 왜 했는가
프레젠테이션에서 "왜 이 부분에 LLM을 적용했는가"를 근거와 함께 설명하려면, 각 포인트가 rule-based로는 해결하기 어려운 문제인지 평가해야 한다. 4가지 기준(입력 형태, 의미 해석, rule 대안 한계, 출력 품질 차이) 중 3개 이상 "LLM 적합"인 포인트만 유지하고, 나머지는 rollback하여 "LLM을 적용한 이유가 명확한" 상태로 만들었다. 핵심 메시지: "LLM은 비정형 텍스트 해석과 다중 맥락 합성에만 적용했다. 구조화된 입력의 결정적 판단은 rule-based가 더 정확하고 비용 효율적이다."

### 어떻게 했는가
평가 프레임워크 4가지 기준을 6개 포인트에 적용. Coverage Similarity(4/4 Rule)와 Portfolio Analysis(3.5/4 Rule)를 rollback 대상으로 선정. 기존 rule-based 로직(rules.py의 coverage_dropped flag, JS의 verdict/FLAG_ACTIONS)이 이미 해당 케이스를 커버하므로 기능 손실 없이 코드를 제거. aggregator.py의 risk upgrade 조건에서 coverage 관련 조건만 제거하고, endorsement restriction + risk signal 복합 조건은 유지.

---

## 2026-02-15 03:45 | `experiment/portfolio-aggregator`

### 무엇을 했는가
UI 레이아웃 개선 3건: insight 페이지 Compare 버튼 통일 (50/200 → 100 단일), portfolio 테이블 full-width + 버튼 같은 줄 배치 + 새로고침 시 선택 초기화, dashboard Quality Check 제목-정확도 같은 줄 배치 + 설명 텍스트 추가.

### 왜 했는가
데모 시 일관된 UX 필요. insight 페이지의 200건 비교는 프로덕션 LLM 비용 대비 불필요. portfolio 테이블 오른쪽 공간 낭비 및 버튼 위치 부자연스러움. Quality Check 결과가 제목과 분리되어 시인성 저하.

### 어떻게 했는가
3개 템플릿 수정. migration.html 버튼 단일화. portfolio.html에 `table-layout:fixed` + 컬럼 % 지정, flex로 헤더-버튼 같은 줄, `portfolio-navigating` sessionStorage 플래그로 새로고침 vs 페이지네이션 구분. dashboard.html에 flex로 제목-accuracy 같은 줄 + 회색 설명 추가.

---

## 2026-02-15 03:15 | `experiment/portfolio-aggregator`

### 무엇을 했는가
전체 템플릿(6개) 대상 브로커 친화적 용어 감사 및 수정. analytics.html의 risk_distribution 키 불일치 수정 (500 에러 해결).
- analytics.html: `low/medium/high/critical` → `no_action_needed/review_recommended/action_required/urgent_review` (Jinja + JS), 시간 ms → 초, 헤더 용어 정리
- dashboard.html: "Run Sample" → "Review Sample", "Run Eval" → "Quality Check", "Total Processed" → "Total Reviewed", 시간 ms → 초
- migration.html: "vs" → "vs.", "LLM" → "AI", "Sample Size" → "Policies Compared", "Delta" → "Comparison", 시간 ms → 초
- review.html: "Field Changes" → "Policy Changes", "LLM Insights" → "AI Insights"

검증: ruff 0 errors, pytest 89/89 passed.

### 왜 했는가
데모 대상이 보험 브로커이므로, "Batch Run", "Job ID", "Eval", "LLM", "Delta", "Latency" 같은 개발자 용어가 혼란을 줄 수 있음. analytics.html은 risk_distribution 키가 이전 모델 키(`low/medium/high/critical`)를 참조하여 500 에러 발생.

### 어떻게 했는가
6개 템플릿을 순회하며 개발자 중심 용어를 식별, 브로커가 이해할 수 있는 단어로 치환. ms 단위 시간 표시를 전부 초 단위로 변환 (Jinja: `/ 1000 + "s"`, JS: `.toFixed(1) + 's'`). analytics.html의 Jinja 변수명과 JS getElementById를 실제 데이터 모델 필드에 맞춰 일괄 수정.

---

## 2026-02-15 02:30 | `experiment/portfolio-aggregator`

### 무엇을 했는가
Portfolio 모달을 브로커 친화적으로 개선하고 UI/UX 버그 수정 및 네비게이션 정리. 변경 파일 6개:
- `portfolio.html`: 체크박스 행 하이라이트 버그 수정, Health Verdict 배너(4단계 색상), Risk Distribution 건수+퍼센트 라벨, Bundle 권고 문장, Flag별 액션 라인(FLAG_ACTIONS 맵), Action Items 체크리스트(priority 정렬), sessionStorage 기반 크로스페이지 정책 선택
- `analytics.html`: 누락 템플릿 복원 (500 에러 해결)
- `base.html`: 네비게이션 순서 재배치 (분석→액션 그룹핑), "LLM Analytics" → "Analytics" 라벨 수정
- `migration.html`: URL `/ui/migration` → `/ui/insight`, 제목에서 "Migration" 제거
- `ui.py`: 라우트 URL 변경 + portfolio 라우트 추가
- `design-doc.md`: UI 섹션에 portfolio.html 상세 기술 추가

검증: ruff 0 errors, pytest 89/89 passed.

### 왜 했는가
자가 수정 루프로 생성된 Portfolio Aggregator의 백엔드는 완성됐지만, 모달이 raw 데이터만 보여줘서 브로커가 "이 포트폴리오가 괜찮은지?", "무엇을 해야 하는지?" 즉시 판단할 수 없었음. 또한 체크박스 버그, 페이지 간 선택 초기화, analytics 500 에러 등 실사용 시 발견되는 문제들을 수정하여 데모 가능한 수준으로 끌어올림.

### 어떻게 했는가
단일 파일(portfolio.html) 중심 JS+CSS 수정. 백엔드 API 변경 없이 프론트엔드에서 기존 데이터를 가공하여 브로커 관점의 정보(verdict, 권고, 액션 리스트)를 도출. 크로스페이지 선택은 sessionStorage로 해결 — 페이지 이동 시 선택 유지, DOMContentLoaded에서 복원. 네비게이션은 브로커 워크플로우(전체 현황 → 개별 액션) 순서로 재배치.

---

## 2026-02-15 01:32 | `experiment/portfolio-aggregator`

### 무엇을 했는가
Langfuse Datasets + Experiments SDK로 LLM provider 벤치마크 파이프라인 구축. gpt-4o-mini, claude-sonnet, claude-haiku 3개 모델을 3개 보험 분석 작업(risk-signal, endorsement, coverage) x 5개 테스트 케이스로 비교. 자동 스코어링(json_valid, key_match) 포함. 프롬프트 v1 실행 후 3가지 개선(signal 그룹핑 규칙, 빈 입력 처리, JSON 순수성)을 적용한 v2까지 총 90회 API 호출 실행.

### 왜 했는가
프로덕션 LLM provider 선정을 감이 아닌 정량 데이터로 결정하기 위해. 또한 Langfuse의 Dataset/Experiment 기능을 활용한 재현 가능한 벤치마크 프로세스를 확립하여, 프롬프트 변경 시 회귀 테스트를 자동화하기 위해.

### 어떻게 했는가
`scripts/langfuse_datasets.py`로 3개 Dataset(각 5개 item, golden_eval.json 기반 4개 + synthetic 1개) 등록. `scripts/langfuse_experiment.py`로 각 모델별 순차 실행, Langfuse `run_experiment` API + `Evaluation` 객체로 자동 스코어링. Anthropic 응답의 마크다운 코드블록 래핑 문제는 `_extract_json()` 후처리로 해결. v2 프롬프트 개선 후 재실험으로 v1 vs v2 비교.

---

## 2026-02-15 00:45 | `experiment/portfolio-aggregator`

### 무엇을 했는가
Self-Correcting Loop Run 2 — Portfolio Risk Aggregator 기능 구현. Skill 오케스트레이션(방법 B) 사용. 5개 파일 생성/수정:
- `app/models/portfolio.py` (27줄): CrossPolicyFlag, BundleAnalysis, PortfolioSummary 모델
- `app/engine/portfolio_analyzer.py` (182줄): analyze_portfolio + 번들분석 + 중복보장탐지 + 노출계산 + 보험료집중도
- `app/routes/portfolio.py` (27줄): POST /portfolio/analyze 엔드포인트
- `app/main.py` (수정): portfolio 라우터 등록
- `tests/test_portfolio.py` (193줄): 8개 테스트 케이스

검증 결과: ruff 0 errors, pytest 89/89 passed (기존 81 + 신규 8), semgrep 0 findings, TRIANGULAR_PASS.

### 왜 했는가
실험 3에서 Quote Generator로 검증한 자가 수정 루프 파이프라인의 **재사용성 증명**. 동일 파이프라인(PROMPT → 구현 → 품질 게이트 → 삼각 검증)에 다른 PROMPT를 투입하여, 완전히 다른 도메인(교차 정책 위험 분석)의 기능이 1회 반복 만에 자동 구현됨을 확인.

### 어떻게 했는가
Skill 오케스트레이션(방법 B) — Claude Code 세션 안에서 `self-correcting-loop` skill을 호출. Phase 1(직접 구현) → Phase 2(ruff/pytest/semgrep 직접 실행) → Phase 3(Task tool로 Agent B/C subagent 병렬 실행) → Phase 4(TRIANGULAR_PASS 확인). ruff line length 이슈는 Phase 2 내부에서 즉시 수정. 삼각 검증에서 advisory 이슈 3건(BI 파싱 edge case, 네이밍 불일치, pair-less 불일치) 발견되었으나 요구사항 위반은 없음.

---

## 2026-02-14 22:30 | `experiment/portfolio-aggregator`

### 무엇을 했는가
실험 4 (Portfolio Risk Aggregator) 사전 준비. 3개 파일 신규 작성, 2개 스크립트 파라미터화:
- `docs/experiments/4-requirements-portfolio-aggregator.md`: FR-1~FR-9 (9개 기능 요구사항 + 8개 테스트 케이스)
- `docs/experiments/4-PROMPT-portfolio-aggregator.md`: 자가 수정 루프용 에이전트 프롬프트
- `docs/guide-self-correcting-loop.md`: 팀원용 Skill 사용 가이드
- `scripts/self-correcting-loop.sh`, `scripts/triangular-verify.sh`: 환경변수(`PROMPT_FILE`, `REQUIREMENTS_FILE`)로 경로 주입 가능하도록 수정

### 왜 했는가
실험 3에서 검증한 자가 수정 루프 파이프라인의 **재사용성 증명**이 실험 4의 핵심 목표. Quote Generator와 완전히 다른 도메인(교차 정책 분석)의 기능을 동일 파이프라인으로 구현하여, PROMPT.md만 바꾸면 어떤 기능이든 자동 구현 가능함을 입증한다. 팀 가이드 작성으로 개인 도구에서 팀 도구로 전환.

### 어떻게 했는가
스크립트 하드코딩 경로를 `${VAR:-default}` 패턴으로 파라미터화 — 기존 experiment 3 기본값 유지하면서 새 실험 파일을 환경변수로 주입 가능. 팀 가이드는 전제 조건, 파이프라인 구조, 3단계 사용법, 삼각 검증 설명, 트러블슈팅까지 포함.

---

## 2026-02-14 15:30 | `experiment/self-correcting-loop`

### 무엇을 했는가
Self-Correcting Loop Phase 1 — Smart Quote Generator 구현. 5개 파일 생성/수정:
- `app/models/quote.py` (16줄): CoverageAdjustment, QuoteRecommendation 모델
- `app/engine/quote_generator.py` (211줄): generate_quotes + Auto 3전략 + Home 3전략
- `app/routes/quotes.py` (24줄): POST /quotes/generate 엔드포인트
- `app/main.py` (수정): quotes 라우터 등록
- `tests/test_quote_generator.py` (218줄): 8개 테스트 케이스
- `docs/design-doc.md` (수정): 아키텍처, 데이터 모델, 파이프라인, API, 테스트 섹션 업데이트

검증 결과: ruff 0 errors, pytest 81/81 passed (기존 73 + 신규 8), semgrep 0 findings.

### 왜 했는가
실험 3의 핵심 구현 단계. Self-Correcting Loop가 "구현 → 검증 → 삼각검증 → 수정" 사이클을 자동화할 수 있는지 검증하기 위한 실제 기능 구현. Quote Generator는 보험 갱신 파이프라인의 다음 단계 — 위험 플래그가 발생한 정책에 대해 보험료를 줄이면서 핵심 보장을 유지하는 대안 견적을 자동 생성.

### 어떻게 했는가
- 기존 3계층 패턴(models → engine → routes) 준수하여 모듈 구조 설계
- 전략 패턴: Auto/Home 각 3가지 전략을 독립 함수로 분리, 전략 리스트에 등록하여 순회 적용
- 보호 제약: PROTECTED_FIELDS 상수로 liability 필드 명시, 전략 함수에서 해당 필드 조정 불가
- 이미 최적화 감지: 각 전략 함수 시작부에 현재 값 체크 (예: deductible >= 1000이면 raise_deductible 건너뛰기)
- 절감률: FR-2 범위의 중간값 사용 (Auto: 10%, 4%, 2.5% / Home: 12.5%, 3%, 4%)
- 테스트 설계: 헬퍼 함수(_make_auto_pair, _make_home_pair)로 테스트 데이터 생성을 파라미터화하여 각 시나리오 커버

---

## 2026-02-14 14:45 | 실험 3 최종 비교 분석

### 자동 루프 vs 수동 대조군

| 지표 | 자동 루프 | 수동 (대조군) | Winner |
|------|-----------|-------------|--------|
| 소요 시간 | 641초 | 549초 | 수동 (-92초) |
| 반복 횟수 | 1 | 1 (+재실행) | 동일 |
| Phase 2 실패 | 0 | 0 | 동일 |
| Phase 3 실패 | 0 | 1 | 자동 |
| 자가 수정 이슈 | 0 | N/A | — |
| 사람 개입 | 0 | 1 | 자동 |
| 테스트 | 81/81 | 82/82 | 동일 |
| 삼각 검증 | PASS | PASS (2차) | 동일 |

### 핵심 인사이트

1. **자동화의 가치 ≠ 속도**: 자동 루프가 92초 느렸지만, 사람 개입 0으로 완료. 수동은 Agent B 프롬프트 실수를 감지하고 수정하는 오버헤드 발생.
2. **자가 수정 미작동**: 두 방식 모두 첫 시도에 품질 게이트 통과 — 과제 난이도가 자가 수정을 필요로 하지 않았음. 더 복잡한 과제에서 재검증 필요.
3. **프롬프트 민감도**: 수동 실행에서 Agent B가 잘못된 모듈을 리뷰한 사례. 자동 스크립트는 `git diff`로 파일 목록을 자동 추출하여 이 문제를 구조적으로 회피.
4. **`claude --print` 버퍼링 오버헤드**: 자동 루프의 시간 불이익 원인. 스트리밍 출력 + 로깅 분리로 개선 가능.

### 실험 1→2→3 최종 스토리

```
실험 1: "agent를 여러 명 굴릴 수 있다" → SubAgent vs Teams, 시간/품질 동등
실험 2: "agent가 서로 검증할 수 있다" → 삼각 검증 precision 78%, intent mismatch 탐지
실험 3: "검증 → 수정까지 자동이다" → 1회 완료, 사람 개입 0, 신뢰성 입증
```

---

## 2026-02-14 14:32 | `experiment/manual-baseline` (대조군)

### 무엇을 했는가

실험 3 대조군 — 동일한 Smart Quote Generator를 Claude Code 세션에서 수동 오케스트레이션으로 구현. 549초 소요.

1. **구현**: requirements를 직접 읽고 코드 작성 — quote.py(17줄), quote_generator.py(141줄), quotes.py(18줄), main.py 수정, test_quote_generator.py(142줄).
2. **품질 게이트**: ruff PASS, 82/82 pytest PASS, semgrep PASS.
3. **삼각 검증 1차**: Agent B가 Analytics 모듈을 잘못 리뷰 → FAIL.
4. **삼각 검증 2차**: Agent B 프롬프트 수정 후 재실행 → TRIANGULAR_PASS.

### 왜 했는가

자동 루프(641초)와 정량 비교하기 위한 대조군. 동일 과제를 수동으로 실행하여 시간, 사람 개입, 오류율을 비교.

### 어떻게 했는가

- Claude Code 세션 내에서 직접 코드 작성 (자동 루프처럼 `claude --print`가 아닌 직접 Write/Edit)
- Agent B/C를 Task tool subagent로 실행
- Agent B 첫 실행에서 잘못된 모듈 리뷰 → 파일 목록을 더 명시적으로 지정하여 재실행. 이 과정이 "사람 개입 1회"로 기록됨

---

## 2026-02-14 14:30 | `experiment/self-correcting-loop`

### 무엇을 했는가

실험 3 (Self-Correcting Agent Loop) 준비 — 브랜치 세팅, 실험 문서 복사, 자동화 스크립트 2개 작성.

1. **브랜치 생성**: `wt-experiment` 워크트리에서 `experiment/self-correcting-loop` 브랜치를 main 기반으로 생성. 기존 `experiment/wt-exp`(초기 커밋)에서 전환하여 renewal-review 전체 파일 확보.
2. **실험 문서 복사**: 계획서(`3-self-correcting-agent-loop.md`), 요구사항(`3-requirements-quote-generator.md`), PROMPT(`3-PROMPT-quote-generator.md`) 3개를 워크트리에 복사.
3. **`scripts/triangular-verify.sh` 작성** (50줄): Agent B(blind review) → Agent C(discrepancy report) → PASS/FAIL 판정. `unset CLAUDECODE`로 nested claude 호출 가능하게 처리.
4. **`scripts/self-correcting-loop.sh` 작성** (110줄): Ralph-style while 루프. Phase 1(구현) → Phase 2(ruff+pytest+semgrep) → Phase 3(삼각 검증) → Phase 4(완료). 실패 시 피드백을 다음 반복에 전달. `max_iterations` 안전장치, 타이밍 로그 기록.
5. **검증**: `bash -n` 구문 검사 통과, `chmod +x` 실행 권한 부여.

### 왜 했는가

실험 1(agent 병렬 협업)과 실험 2(삼각 검증)를 하나의 자동화 파이프라인으로 통합하는 실험의 사전 준비. "기능을 PROMPT.md에 정의하면, 코드 작성 → 품질 검증 → 의도 검증 → 자가 수정까지 사람 개입 없이 돌아가는 파이프라인"을 만드는 것이 목표. 실험 과제는 Smart Quote Generator(보험 대안 견적 생성) — analytics 모듈과 다른 비즈니스 로직으로 삼각 검증의 의미를 유지.

### 어떻게 했는가

- **브랜치 전략**: `git checkout -b experiment/self-correcting-loop main`으로 main 기반 브랜치 생성. 워크트리가 초기 커밋에 있었으므로 main에서 분기해야 모든 프로젝트 파일이 존재.
- **스크립트 설계**: 계획서의 의사코드를 실제 셸 스크립트로 구현. `set -euo pipefail`로 안전성 확보. Phase 2의 품질 게이트는 ruff → pytest → semgrep 순서로 비용이 낮은 것부터 실행 (fast-fail). Phase 간 피드백 전달은 `/tmp/self-correcting-loop-feedback.txt` 파일 경유.
- **Claude CLI 호환**: `unset CLAUDECODE`를 스크립트 시작에 배치하여, 사용자가 터미널에서 실행할 때 nested claude 호출이 가능하도록 처리. `claude --print -p "..."` 형식으로 비대화형 실행.
- **로깅**: `log()` 함수로 stdout + 파일(`docs/logs/loop-execution.log`)에 동시 기록. 각 iteration의 소요 시간 측정.

---

## 2026-02-14 00:47 | `main`

### 무엇을 했는가

**실험 C 완료 — 삼각 검증(Triangular Verification)으로 기존 Analytics 모듈 검증.**

기존 Analytics 코드(실험 A/B 산출물)를 대상으로 3-에이전트 삼각 검증을 실행했다. 동일 모델(Claude)이지만 컨텍스트 격리로 독립성을 확보하고, 코드→설명→요구사항 역추적으로 "의도 불일치"를 자동 탐지하는 실험.

#### 실험 흐름

| 단계 | 에이전트 | 입력 | 출력 |
|------|---------|------|------|
| 1. 사전 문서 | — | 기존 requirements.md, design-doc.md 활용 | — |
| 2. 구현 | Agent A (기존 코드) | 이미 main에 존재하는 analytics 모듈 | 코드 6파일 |
| 3. 해석 | Agent B (subagent) | 코드 + convention + design-doc (요구사항 X) | blind-review.md |
| 4. 비교 | Agent C (subagent) | 요구사항 + blind-review (코드 X) | discrepancy-report.md |

#### 정량 결과

| 지표 | Standard (ruff+pytest+semgrep) | Triangular | Delta |
|------|-------------------------------|------------|-------|
| 발견 이슈 수 | 0 | 9 | +9 |
| Intent Mismatch | 0 | 2 | +2 |
| Missing Feature | 0 | 2 | +2 |
| Extra Feature | 0 | 3 | +3 |
| Convention Violation | 0 | 2 | +2 |
| False Positive | — | 2 | — |
| Precision | — | 78% (7/9) | — |
| 소요 시간 | 1초(ruff) + 1초(pytest) + 30초(semgrep) | ~19분 | +18분 |

#### 핵심 발견

1. **FIFO 100건 제한 미구현** (Intent Mismatch, 심각도: 높음) — 요구사항에 "(최대 100건, FIFO)"라고 수치까지 명시했으나, 코드는 무제한 append. ruff/pytest/semgrep 어느 것도 이를 잡지 못함.
2. **타임존 하드코딩 불일치** (Intent Mismatch, 심각도: 중간) — 프로덕션 코드는 America/Vancouver, 테스트는 UTC 사용. 날짜 경계 관련 미묘한 버그 가능성.
3. **UI 검증 한계** — Agent B가 API만 분석하여 UI 템플릿 검증 불가. 삼각 검증의 범위 한계 확인.

#### 판정: 조건부 통과 (Conditional Pass)

### 왜 했는가

실험 A/B에서 "코드를 얼마나 빠르게 만드는가"를 비교했다면, 실험 C는 **"만든 코드가 요구사항대로 되어있는가"**를 검증한다. 프레젠테이션의 핵심 메시지: "기존 도구(ruff, pytest, semgrep)는 구문/보안 오류만 잡고, '의도대로 만들었는가'는 검증하지 못한다. 삼각 검증은 이 갭을 메운다."

FIFO 100건 제한 미구현은 완벽한 증거 — ruff는 구문만, pytest는 테스트 케이스에 없으면 모르고, semgrep은 보안 패턴만 체크한다. 삼각 검증만이 "요구사항에 100건이라고 적혀있는데 코드에는 없다"를 발견했다.

### 어떻게 했는가

**컨텍스트 격리 전략:**
- Agent B에게 `requirements.md` 접근을 금지하고, 코드 + convention + design-doc만 제공. "이 코드가 뭘 하는지" 순수하게 설명하도록 유도.
- Agent C에게 코드 접근을 금지하고, requirements + blind-review만 제공. 두 문서의 텍스트 비교만으로 불일치를 식별하도록 유도.
- 두 에이전트 모두 별도 subagent(Task tool, general-purpose)로 실행하여 메인 세션의 컨텍스트와 격리.

**기존 코드 활용:**
- Analytics 모듈이 이미 main에 존재하므로 Agent A의 구현 단계를 생략. 기존 코드를 Agent A 산출물로 사용.
- 이 접근은 "이미 배포된 코드를 사후 검증"하는 시나리오와 동일 — 실제 워크플로우에서 더 실용적.

**이슈 분류 체계:**
- Intent Mismatch: 요구사항 X인데 코드 Y (가장 심각)
- Missing Feature: 요구사항에 있는데 코드에 없음
- Extra Feature: 요구사항에 없는데 코드에 있음
- Convention Violation: 아키텍처/컨벤션 위반

---

## 2026-02-14 00:20 | 실험 A vs B 비교 분석

### 정량 비교

| 지표 | SubAgent (A) | Agent Teams (B) | Winner |
|------|-------------|-----------------|--------|
| 소요 시간 | 354초 (~5m54s) | 318초 (~5m18s) | Teams |
| 커밋 수 | 1 | 1 | 동일 |
| 생성/수정 파일 | 8 | 8 | 동일 |
| 추가된 줄 | 334 | 335 | 동일 |
| 테스트 수 | 5 (73 total) | 5 (73 total) | 동일 |
| 전체 테스트 통과 | Yes | Yes | 동일 |
| 린트 수정 횟수 | 1 (ruff format) | 0 | Teams |
| pre-commit 통과 | Yes | Yes | 동일 |
| 토큰 사용량 | 164,293 (4 subagent) | 측정 불가* | SubAgent |

\* Teams 방식은 teammate가 토큰 메타데이터를 반환하지 않아 정확한 측정 불가. SubAgent는 Task tool 반환값에 토큰 정보가 포함됨.

### 정성 분석

**SubAgent 방식의 강점:**
- **병렬화 유연성** — 오케스트레이터가 인터페이스 스펙을 프롬프트에 직접 명시하면, 의존 관계가 있는 작업도 병렬로 디스패치 가능. 모델+서비스와 라우트+main을 동시에 진행.
- **낮은 오버헤드** — Task tool 한 번 호출로 subagent가 작업하고 결과를 바로 반환. 팀 생성, 태스크 등록, 메시지 전송 같은 조정 과정이 없음.
- **오케스트레이터의 통제력** — 모든 코드의 정확한 내용을 오케스트레이터가 지시. 결과를 즉시 검증하고 수정 가능.

**Agent Teams 방식의 강점:**
- **구조적 태스크 관리** — TaskCreate/TaskUpdate/blockedBy로 의존성이 명시적. 작업 상태 추적이 체계적.
- **독립적 팀원** — 각 팀원이 convention.md를 직접 읽고 기존 패턴을 따름. 오케스트레이터가 모든 코드를 프롬프트에 넣지 않아도 됨.
- **확장 가능성** — 팀원 수를 늘리거나 역할을 세분화하기 쉬움. 복잡한 프로젝트에서 유리.

**이 실험에서의 한계:**
- 과제 크기가 ~300줄로 작아서 두 방식 간 극적 차이가 나지 않음
- Teams의 의존성 설정(blockedBy)이 순차 실행을 강제해 병렬화 이점을 활용 못함
- SubAgent의 린트 수정 1회는 프롬프트에서 ruff format 규칙을 더 명시했으면 방지 가능했음
- 동일 세션에서 두 실험을 진행했기 때문에, Teams 실험 시 이미 코드 구조/패턴 지식이 컨텍스트에 남아 있는 캐리오버 효과가 있을 수 있음

### 결론

소규모 과제(~300줄)에서는 **SubAgent가 더 실용적**. 병렬화가 자유롭고 오버헤드가 적다. Agent Teams는 여러 사람이 참여하거나 태스크 간 복잡한 의존성이 있는 대규모 프로젝트에서 진가를 발휘할 것으로 예상.

### 한계 보완 방안

#### 1. 과제 크기 (~300줄) — 재실험 필요도: 높음

가장 중요한 한계. 1,000줄+ 규모의 과제(예: 독립 모듈 2~3개를 동시에 추가)로 재실험하면 Teams의 태스크 추적/의존성 관리 장점과 SubAgent의 오케스트레이터 컨텍스트 비대화 문제가 드러날 것으로 예상. 기존 renewal-review에 "Notification 모듈 + Report 모듈"을 동시에 추가하는 과제를 설계하면 Teams의 병렬 장점도 자연스럽게 테스트 가능.

#### 2. Teams의 순차 실행 강제 — 재실험 필요도: 중간

이번 실험은 하나의 모듈을 3단계(모델→라우트→테스트)로 쪼개서 순차 의존성이 불가피했다. 의존성 없는 독립 태스크를 병렬로 설계(예: "모듈 A 전체"와 "모듈 B 전체"를 동시에 2명에게 배정)하면 Teams의 진짜 병렬화 성능을 측정할 수 있다. 이 설계 자체가 "Teams를 순차가 아닌 병렬 구조로 설계했어야 했다"는 인사이트.

#### 3. 린트 수정 1회 — 재실험 필요도: 낮음

실험 설계의 문제가 아니라 프롬프트 튜닝의 문제. SubAgent 프롬프트에 "ruff format + ruff check를 실행하라"를 명시하면 해결 가능. 오히려 "프롬프트 품질이 agent 출력 품질을 결정한다"는 인사이트로 발표에서 활용 가능.

#### 4. 캐리오버 효과 (동일 세션) — 재실험 필요도: 중간~높음

가장 과학적으로 의미 있는 한계. 보완 방법:
- **A**: 완전히 별도 세션(별도 터미널)에서 각 실험 실행 — 컨텍스트 공유 없음
- **B**: 실험 순서를 뒤집어 Teams → SubAgent 순으로 재실행 — 순서 효과 측정
- **C**: A/B를 각각 2회씩 실행하여 분산 확인

다만 두 실험의 결과가 거의 동일(334 vs 335줄, 354 vs 318초)하므로 캐리오버가 있더라도 극적 차이를 만들진 않았을 가능성이 높다.

#### 종합 판단

현재 실험의 가치는 "동일 과제, 동일 결과, 다른 조율 방식" — 차이가 없다는 것 자체가 인사이트다. 한계를 솔직하게 명시하고 "대규모에서는 이런 차이가 예상된다"는 가설을 제시하는 것이 정직하고 과학적인 접근. 추가 실험을 한다면 **한계 1번(과제 크기 확대)**이 ROI가 가장 높다.

---

## 2026-02-14 00:10 | `experiment/teams-analytics`

### 무엇을 했는가

실험 B — Agent Teams 방식으로 Analytics 모듈을 구현했다. 실험 A(SubAgent)와 동일한 요구사항.

생성/수정한 구성요소:
- Pydantic 모델 3종 (BatchRunRecord, TrendPoint, AnalyticsSummary)
- 비즈니스 로직 (compute_trends — 일별 그룹핑, 리스크 분포 집계)
- API 라우트 2개 (GET /analytics/history, /analytics/trends)
- 배치 라우트 수정 (실행 완료 시 history 자동 저장, 밴쿠버 타임존)
- 테스트 5개 (0건/1건/3건+ 케이스 + 라우트 2개)

결과: 기존 68개 + 신규 5개 = 73개 테스트 전체 통과.

#### 토큰 사용량

Agent Teams 방식에서는 각 팀원(teammate)이 독립 프로세스로 실행되며, 완료 시 토큰 사용량을 반환하지 않는다. SubAgent의 Task tool은 결과와 함께 토큰 메타데이터를 반환하지만, Teams의 SendMessage/TaskUpdate 프로토콜에는 토큰 보고가 포함되지 않음.

> **측정 불가** — Langfuse가 세션 레벨 trace를 기록하지만, 개별 teammate별 토큰 분리는 현재 지원되지 않음. 향후 실험에서는 각 teammate의 시작/종료 시점에 Langfuse span을 수동으로 삽입하여 측정 가능.

### 왜 했는가

SubAgent 방식(실험 A)과 Agent Teams 방식의 생산성 비교 실험(실험 B). 동일한 과제를 다른 오케스트레이션 모델로 수행하여 차이를 측정.

### 어떻게 했는가

**Agent Teams 3인 팀 구성:**

1. **팀 생성** — TeamCreate로 "analytics-feature" 팀 생성. 태스크 3개를 TaskCreate로 등록하고 의존성 설정: task #1(모델+서비스) → task #2(라우트+배치) → task #3(테스트).

2. **modeler 팀원** (general-purpose) — task #1 담당. `app/models/analytics.py`와 `app/engine/analytics.py` 작성. 완료 후 태스크를 completed로 마킹.

3. **router 팀원** (general-purpose) — task #2 담당. modeler 완료 후 스폰. `app/routes/analytics.py` 생성, `app/routes/batch.py` 수정, `app/main.py` 수정. 태스크 자동 완료 마킹.

4. **tester 팀원** (general-purpose) — task #3 담당. router 완료 후 스폰. `tests/test_analytics.py` 작성, 테스트 실행 검증.

**SubAgent 방식과의 차이점:**
- Teams 방식은 TaskCreate/TaskUpdate로 태스크를 명시적으로 정의하고 의존성(blockedBy)을 설정
- 각 팀원이 독립된 agent로 스폰되어 SendMessage/TaskList로 협조
- 의존성 때문에 순차 실행이 강제됨 (modeler → router → tester)
- SubAgent 방식에서는 modeler와 router를 병렬 디스패치할 수 있었으나, Teams에서는 blockedBy로 순차 처리
- 팀 리더가 각 팀원의 완료를 확인하고 다음 팀원을 스폰하는 오케스트레이션 오버헤드 발생

---

## 2026-02-14 00:00 | `experiment/subagent-analytics`

### 무엇을 했는가

**실험 A 완료 — SubAgent 방식으로 Analytics 모듈 구현.**

`wt-feat-1` 워크트리에서 동일 과제(Batch Monitoring 모듈 추가)를 SubAgent 방식으로 실행했다. 4개의 subagent를 파이프라인으로 조합해서 모델/서비스/라우트/테스트를 생성.

#### 정량 결과

| 지표 | 결과 |
|------|------|
| 소요 시간 | **354초 (~5.9분)** |
| 커밋 수 | 1 |
| 생성/수정 파일 | 8 (코드 6 + 문서 2) |
| 추가된 줄 | 334 |
| 신규 테스트 | 5개 |
| 전체 테스트 통과 | 73/73 (기존 68 + 신규 5) |
| ruff check | 통과 (수정 후) |

#### 토큰 사용량

| SubAgent | 토큰 수 | Tool 호출 |
|----------|---------|----------|
| 리서치 (Explore) | 88,549 | 13 |
| 모델+서비스 (general-purpose) | 23,531 | 3 |
| 라우트+main (general-purpose) | 28,690 | 11 |
| 테스트 (general-purpose) | 23,523 | 2 |
| **합계** | **164,293** | **29** |

> 리서치 subagent가 전체 토큰의 54%를 사용. 기존 코드 패턴을 탐색하는 Explore 타입이 가장 많은 컨텍스트를 소비함. 구현 subagent들은 각각 23k~29k로 균등.

#### 생성된 파일

| 파일 | 줄 수 | 역할 |
|------|-------|------|
| `app/models/analytics.py` | 29 | Pydantic 모델 3종 (BatchRunRecord, TrendPoint, AnalyticsSummary) |
| `app/engine/analytics.py` | 54 | compute_trends 서비스 — 일별 그룹핑, 리스크 분포 집계 |
| `app/routes/analytics.py` | 22 | GET /analytics/history, /analytics/trends |
| `app/routes/batch.py` | +18 | 배치 실행 완료 시 history 자동 저장 |
| `app/main.py` | +2 | analytics 라우터 등록 |
| `tests/test_analytics.py` | 116 | 5개 테스트 (empty/single/multi + 라우트 2개) |
| `docs/design-doc.md` | +56 | Architecture, Data Model 등 6개 섹션 업데이트 |
| `docs/experiment-log.md` | +37 | 실험 로그 엔트리 |

### 왜 했는가

SubAgent vs Agent Teams 비교 실험의 첫 번째 그룹. 동일 과제를 두 방식으로 수행하여 시간·토큰·품질을 정량 비교하기 위함. 프레젠테이션에서 "어떤 Agent 패턴이 언제 적합한가"를 데이터로 보여주기 위한 근거.

### 어떻게 했는가

**SubAgent 4단계 파이프라인:**

1. **리서치 subagent** (Explore) — 기존 코드 패턴 조사. models/routes/engine/tests의 import 패턴, 네이밍 컨벤션, DB 모델 구조, main.py 라우터 등록 방식 분석. 구조화된 요약 반환.

2. **모델+서비스 subagent** (general-purpose) — `app/models/analytics.py`와 `app/engine/analytics.py` 작성. 리서치 결과 기반으로 기존 패턴을 정확히 따르는 코드 생성.

3. **라우트+main subagent** (general-purpose) — `app/routes/analytics.py` 생성, `app/routes/batch.py` 수정, `app/main.py` 수정. **2번과 병렬 실행** — 서로 다른 파일을 다루므로 동시 디스패치 가능.

4. **테스트 subagent** (general-purpose) — `tests/test_analytics.py` 작성. 2, 3번 완료 후 순차 실행 (생성된 코드를 참조해야 하므로).

**병렬화 전략:** 오케스트레이터가 각 subagent에게 모델 필드명, import 경로, 함수 시그니처를 프롬프트에 명시 → 의존성 없이 독립 작업 가능하게 함. 2번과 3번이 동시에 실행되어 전체 시간 단축.

**린트 수정:** ruff check에서 import 정렬(I001), datetime.UTC alias(UP017), 라인 길이(E501) 발견 → `ruff --fix` 자동 수정 5건, 수동 수정 3건.

**코드 품질 관찰:**
- 기존 패턴(Pydantic 모델 분리, TestClient 사용, conftest fixture 스타일)을 정확히 따름
- compute_trends의 edge case(빈 리스트, 단건, 다건) 커버
- 불필요한 over-engineering 없이 요구사항만 구현

---

## 2026-02-13 18:30 | `main`

### 무엇을 했는가

실험 2개(SubAgent vs Teams, 삼각 검증)를 실행하기 위한 사전 인프라를 세팅했다.

1. **Langfuse 토큰 추적 활성화** — Claude Code의 `settings.json`에 Langfuse 환경변수 5개를 추가해서, 이미 만들어 둔 Stop hook(`langfuse_hook.py`)이 실제로 trace를 전송하도록 활성화했다.

2. **PostgreSQL Docker 통합** — 기존 인메모리 JSON 방식에서 PostgreSQL로 데이터 소스를 확장했다. Docker Compose로 postgres:16-alpine 컨테이너를 정의하고, SQLAlchemy async 모델(`RenewalPairRow`, `BatchResultRow`)과 seed 스크립트를 만들었다. `data_loader.py`는 `RR_DB_URL` 환경변수가 있으면 DB에서 로드하고, 없으면 기존 JSON 파일로 폴백하도록 이중 경로를 구현했다. 기존 68개 테스트는 JSON 폴백 경로로 전부 통과.

3. **삼각 검증 실험용 문서** — `requirements.md`(FR-1~FR-6, 수락 기준 포함)와 `architecture.md`(계층 구조, 의존성 규칙, 네이밍 컨벤션)를 작성했다. 이 문서들은 삼각 검증에서 Agent A/B/C에게 선택적으로 제공되어 정보 격리를 만드는 핵심 도구다.

4. **작업 로그 시스템** — 처음에는 셸 훅으로 커밋 메타데이터를 자동 기록하려 했으나, 커밋 메시지만으로는 "왜, 어떻게"를 담을 수 없었다. PreToolUse 훅 + CLAUDE.md 컨벤션 조합으로 전환: 훅이 `git commit` 시 experiment-log.md의 staging 여부를 체크해서 미작성 시 커밋을 차단하고, Claude Code가 전체 맥락을 담아 프레젠테이션급 로그를 직접 작성하도록 했다.

5. **순수 개발 시간 추정** — AI agent 없이 동일 시스템을 만들었을 때의 시간을 Phase별로 추정했다. AI ~4시간 vs 순수 ~37시간(5일), 약 9배 차이.

### 왜 했는가

발표의 핵심 스토리 중 하나가 "AI Agent로 인프라 세팅부터 실험 실행까지 매끄럽게 진행"이다. 특히:

- **PostgreSQL 전환** → "메모리 기반에서 실제 DB로 마이그레이션하는 것도 agent가 처리" 스토리
- **Langfuse 추적** → 실험 중 토큰 사용량을 정량적으로 비교하기 위한 관측 인프라
- **요구사항/아키텍처 문서** → 삼각 검증 실험의 전제 조건. Agent A는 요구사항+아키텍처를 보고 구현하고, Agent B는 요구사항 없이 코드만 해석하고, Agent C는 코드 없이 요구사항과 B의 해석을 비교한다. 이 정보 격리가 삼각 검증의 핵심.
- **개발 시간 추정** → "일주일 걸릴 작업을 하루에" 주장의 근거 데이터

### 어떻게 했는가

- **의존성 관리**: `pyproject.toml`에 `sqlalchemy[asyncio]`, `asyncpg`, `psycopg[binary]` 추가 후 `uv sync --extra dev`로 설치. optional-dependencies 구조라 dev 그룹을 별도로 sync해야 했다.
- **DB 이중 경로**: `data_loader.py`의 `load_pairs()` 인터페이스는 그대로 유지하면서, 내부에서 `settings.db_url` 유무로 DB/JSON 분기. 기존 코드를 호출하는 쪽은 변경 없음.
- **SA 모델 설계**: Pydantic 모델(API 레이어)과 SQLAlchemy 모델(DB 레이어)을 분리. `prior_json`/`renewal_json` 컬럼에 원본 JSON을 통째로 저장해서, DB에서 로드할 때 기존 `parse_pair()` 파서를 그대로 재사용.
- **문서 작성 기준**: `requirements.md`는 FR-1~FR-9 체계로 확장. 기존 코드 컨텍스트(BatchSummary 모델, batch.py 실행 흐름, UI 구조), 구체적 필드 정의(타입+값 소스 매핑 테이블), 계산 예시(risk_distribution), 테스트 케이스(입력→검증 매핑)를 모두 포함. `architecture.md`는 batch.py 수정 위치까지 코드 레벨로 명시.
- **테스트 검증**: `RR_DB_URL=""` 환경변수로 DB 경로를 비활성화한 상태에서 기존 68개 테스트 전부 통과 확인. ruff check도 통과.

---
