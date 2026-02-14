# 실험 작업 로그

> Quandri 인터뷰(2/17) 발표 준비 과정 기록. 프레젠테이션 소스로 활용.

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
