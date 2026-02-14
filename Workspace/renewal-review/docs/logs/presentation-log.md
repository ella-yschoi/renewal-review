# Renewal Review — Presentation Log

> 커밋마다 자동 기록. 각 엔트리의 Context / Result / Insight를 채워서 프레젠테이션 소스로 활용한다.
>
> - **Context**: 이 커밋의 맥락과 의도 (왜 이 작업이 필요했는지)
> - **Result**: 결과 또는 변경 효과 (무엇이 달라졌는지)
> - **Insight**: 프레젠테이션에서 강조할 포인트 (청중이 기억할 한 문장)

---

### 2026-02-14 00:47 | `main` | 삼각 검증 실험

**실험 C: 삼각 검증(Triangular Verification)으로 코드 품질 검증**

_3 files generated: blind-review.md, discrepancy-report.md, experiment log_

> **Context**: 실험 A/B는 "얼마나 빠르게 만드는가"를 비교했다. 실험 C는 "만든 코드가 요구사항대로인가"를 검증한다. 3개 에이전트를 컨텍스트 격리하여 코드→설명→요구사항 역추적 방식으로 "의도 불일치"를 자동 탐지.
> **Result**: ruff+pytest+semgrep이 0개 잡은 상태에서, 삼각 검증은 Intent Mismatch 2건(FIFO 100건 미구현, 타임존 불일치), Missing Feature 2건, Extra Feature 3건을 추가 발견. Precision 78%. 소요 시간 ~19분.
> **Insight**: 기존 도구는 "코드가 깨졌는가"만 체크한다. 삼각 검증은 "코드가 의도대로인가"를 체크한다. FIFO 100건 제한이 빠진 건 테스트에도, 린터에도, 보안 스캐너에도 안 잡히지만 — 요구사항 문서와 코드 설명을 삼각 비교하면 바로 드러난다.

---

### 2026-02-14 00:00 | `experiment/subagent-analytics` | `17b2756`

**feat: add analytics module via subagent experiment**

_8 files changed, 334 insertions(+)_

> **Context**: SubAgent vs Agent Teams 비교 실험의 첫 번째 실행. 동일 과제(Batch Monitoring 모듈 추가)를 SubAgent 4단계 파이프라인(리서치→모델+서비스→라우트+main→테스트)으로 구현. 2단계와 3단계를 병렬 디스패치하여 시간 단축.
> **Result**: 354초(~6분)에 모델 3종 + 서비스 + API 2개 + 테스트 5개 완성. 73/73 테스트 통과. ruff 수정 8건 포함. 기존 코드 패턴을 정확히 따르는 코드 생성.
> **Insight**: SubAgent 방식의 강점은 오케스트레이터가 "무엇을 만들지"를 구체적으로 지시할 수 있다는 점 — 인터페이스 스펙(필드명, 시그니처)을 프롬프트에 명시하면 의존성 없이 병렬 작업이 가능하다. 6분 만에 production-ready 모듈이 나온 것은 리서치→구현 파이프라인이 잘 동작한 결과.

---

### 2026-02-14 00:10 | `experiment/teams-analytics` | `15f7545`

**feat: add analytics module via agent teams experiment**

_8 files changed, 335 insertions(+)_

> **Context**: SubAgent vs Agent Teams 비교 실험의 두 번째 실행. 동일 과제를 TeamCreate + TaskCreate/TaskUpdate + SendMessage 기반 Agent Teams 방식으로 구현. 3인 팀(modeler, router, tester)을 순차 스폰하여 의존성 기반으로 작업 진행.
> **Result**: 318초(~5분)에 동일한 모듈 완성. 73/73 테스트 통과. ruff 수정 0건 — 첫 시도에 클린. 태스크 자동 완료 마킹도 정상 동작.
> **Insight**: Agent Teams는 태스크 의존성(blockedBy)이 명시적이라 "누가 뭘 기다리는지"가 투명하다. 하지만 이 실험 규모(~300줄)에서는 순차 스폰 오버헤드가 병렬화 이점을 상쇄. 대규모 프로젝트에서 팀원 수를 늘릴 때 진가가 나올 구조.

---

### 2026-02-14 00:20 | 실험 비교 분석

**SubAgent vs Agent Teams — 최종 비교**

> **Context**: 동일 과제를 두 가지 오케스트레이션 모델로 수행한 결과 비교. SubAgent는 Task tool 기반 fire-and-forget, Teams는 TeamCreate/TaskCreate 기반 구조적 협업.
> **Result**: 시간(354 vs 318초), 코드량(334 vs 335줄), 테스트(73/73) 모두 거의 동일. 차이는 병렬화 전략과 오케스트레이션 오버헤드.
> **Insight**: 두 방식 모두 6분 안에 production-ready 모듈을 생성했다. **차이는 "만드는 속도"가 아니라 "조율하는 방식"에 있다.** 소규모는 SubAgent(오버헤드 적음, 병렬화 자유), 대규모는 Teams(태스크 추적, 의존성 관리, 확장성)가 유리.
