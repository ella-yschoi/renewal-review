# Background Agent Workflow — 팀 가이드

메인 작업을 하면서 **코드 리뷰, 문서 검증 등 품질 작업을 백그라운드로 병렬 실행**하는 워크플로우.

Claude Code의 `Task` 도구를 `run_in_background: true`로 호출하면, 별도 프로세스로 에이전트가 생성되어 메인 대화를 블로킹하지 않는다.

> 참고: [Agent-Native Engineering](https://www.generalintelligencecompany.com/writing/agent-native-engineering) 아티클의 "Parallel Work Streams: Sync + Async" 패턴.

---

## 동작 구조

```
엔지니어 (Sync)              Background (Async)
  │ 메인 작업                 ├─ Agent A (코드 리뷰)
  │ 기능 구현                 │   Read, Grep, Bash 등
  │ UI 작업                   │   독립 컨텍스트 윈도우
  │                           │
  │                           ├─ Agent B (문서 검증)
  │                           │   코드 ↔ design-doc 비교
  │                           │
  ▼                           ▼
  결과 수신 ◄──────────── 완료 알림 (자동)
```

**핵심**: 각 에이전트는 독립적인 컨텍스트 윈도우를 가지며, 메인 대화와 도구를 공유하지 않는다. 완료 시 `<task-notification>`으로 결과가 자동 전달된다.

---

## 사용법

### 1단계: 백그라운드 에이전트 실행

Claude Code 세션에서 자연어로 요청:

```
커밋 b0807f8에 대한 코드 리뷰를 background agent로 실행해줘.
컨벤션 준수, 버그 위험, 보안, 개선점을 검토해줘.
```

내부적으로 Claude Code가 호출하는 것:

```python
Task(
    prompt="커밋 b0807f8 코드 리뷰: 컨벤션, 버그, 보안, 개선점",
    subagent_type="general-purpose",
    run_in_background=True,  # 핵심: 백그라운드 실행
)
```

여러 에이전트를 **동시에** 실행 가능 — 한 메시지에 여러 Task 호출을 병렬로 보내면 된다.

### 2단계: 메인 작업 계속

에이전트가 돌아가는 동안 메인 대화에서 다른 작업을 계속한다. 블로킹 없음.

### 3단계: 진행 상황 확인 (선택)

```python
TaskOutput(task_id="aaaa191", block=False)
```

또는 출력 파일 직접 확인:

```bash
tail -20 /private/tmp/claude-501/.../tasks/aaaa191.output
```

### 4단계: 결과 수신

에이전트 완료 시 자동 알림:

```xml
<task-notification>
  <task-id>aaaa191</task-id>
  <status>completed</status>
  <result>코드 리뷰 결과...</result>
  <usage>
    total_tokens: 60394
    tool_uses: 19
    duration_ms: 134295
  </usage>
</task-notification>
```

---

## 이 프로젝트에서의 적용 사례

### Self Code Review (Agent A)

| 항목 | 값 |
|------|-----|
| 대상 | 커밋 `b0807f8` (9파일, +208/-30) |
| 검토 항목 | 컨벤션 준수, 버그 위험, 보안, 개선점 |
| 도구 호출 | 19회 (Read, Grep, Bash) |
| 소요 시간 | 134초 (~2분 14초) |
| 결과 | 0 Critical, 5 Warning, 10 Info |

주요 발견:
- `sort`/`order` 파라미터 미검증 (`str` → `Literal` 권장)
- 폴링 루프에 타임아웃/최대 반복 없음
- 폴링 `fetch`에 네트워크 에러 핸들링 없음
- `seed_db.py`가 `prior`에서 읽지만 런타임은 `renewal` 사용

### Design-doc Verification (Agent B)

| 항목 | 값 |
|------|-----|
| 대상 | `docs/design-doc.md` ↔ 실제 코드 전체 |
| 검증 방식 | 삼각 검증 스타일 (문서 ↔ 코드 필드별 대조) |
| 도구 호출 | 37회 (Read, Grep, Bash, Glob) |
| 소요 시간 | 153초 (~2분 33초) |
| 결과 | 17개 섹션 중 6개 MISMATCH |

주요 발견:
- `POST /reviews/compare` 엔드포인트: 문서에 있지만 코드에서 삭제됨
- `ReviewResult.llm_summary_generated` 필드: 코드에 있지만 문서에 없음
- `test_routes.py` 테스트 수: 문서 9개 vs 실제 4개
- Analytics deque 위치: 문서의 코드 참조가 틀림

---

## 적합한 작업

| 작업 | 적합도 | 이유 |
|------|--------|------|
| 코드 리뷰 (컨벤션, 보안) | ✅ 높음 | 읽기 전용, 독립적 |
| 문서 ↔ 코드 정합성 검증 | ✅ 높음 | 읽기 전용, 시간 소요 |
| 테스트 커버리지 분석 | ✅ 높음 | 독립 실행 가능 |
| 의존성 보안 감사 | ✅ 높음 | 외부 도구 호출 |
| 기능 구현 | ❌ 낮음 | 파일 충돌 위험, 메인 작업과 겹침 |
| DB 마이그레이션 | ❌ 낮음 | 상태 변경, 순서 의존 |

**원칙**: 읽기 전용 + 독립적 + 시간이 걸리는 작업에 적합.

---

## 기존 워크플로우와의 비교

| 항목 | 기존 (동기) | Background Agent |
|------|-------------|------------------|
| 코드 리뷰 | 사람이 PR 보고 코멘트 | Agent가 비동기로 검증, 결과만 수신 |
| 문서 검증 | 수동 대조 또는 안 함 | Agent가 필드별 자동 대조 |
| 컨텍스트 스위칭 | 리뷰 ↔ 코딩 왔다갔다 | 없음 — 메인 작업 유지 |
| 비용 | 사람 시간 | API 토큰 (60K tokens ≈ $0.05) |

---

## 주의사항

1. **파일 쓰기 충돌**: 백그라운드 에이전트가 파일을 수정하면 메인 작업과 충돌할 수 있다. 읽기 전용 작업에만 사용 권장.
2. **권한**: 백그라운드 에이전트도 동일한 권한 모드를 따른다. Bash 실행이 거부될 수 있다.
3. **토큰 비용**: 각 에이전트가 독립 컨텍스트를 사용하므로 토큰이 별도로 소비된다.
4. **출력 크기**: 결과가 길면 truncate된다. 출력 파일에서 전체 내용 확인 가능.
