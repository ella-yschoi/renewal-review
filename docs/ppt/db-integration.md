# PostgreSQL DB 연동 — AI Agent로 백엔드 인프라 구축

## 배경

초기 구현은 JSON 파일(`data/renewals.json`)에서 8,000건을 메모리로 로드하는 방식.
프레젠테이션에서 **"실제 DB에서 쿼리로 데이터를 가져온다"**는 것을 보여주기 위해 PostgreSQL로 전환.
추가로 **Google MCP Toolbox**를 연결해 Agent가 DB를 직접 도구로 사용할 수 있게 구성.

> 프론트엔드 개발자인데 AI agents 덕분에 Docker + PostgreSQL + SQLAlchemy + MCP DB 연동을 순조롭게 완료했다.

---

## 구현 내용

### 인프라

| 구성요소 | 상세 |
|---------|------|
| **PostgreSQL 16** | Docker 컨테이너 (Alpine) |
| **포트** | 5432:5432 (표준 포트) |
| **드라이버** | asyncpg (API) + psycopg (data_loader sync) |
| **ORM** | SQLAlchemy (async engine + sync Session) |
| **MCP** | Google genai-toolbox v0.27.0 (Postgres prebuilt) |

### 데이터 흐름: Before → After

```
[Before]  renewals.json → json.loads → parse_pair → 메모리 캐시

[After]   Docker Postgres → SQLAlchemy query → parse_pair → 메모리 캐시
            ↑ seed_db.py로 8,000건 투입
            └ 연결 실패 시 JSON 폴백 (graceful degradation)

[MCP]    AI Agent → genai-toolbox MCP → Postgres (직접 SQL 실행)
```

### 핵심 파일

| 파일 | 역할 |
|------|------|
| `docker-compose.yml` | Postgres 16 Alpine 컨테이너 정의 |
| `app/db.py` | async engine + session factory |
| `app/models/db_models.py` | `RenewalPairRow` ORM 모델 |
| `scripts/seed_db.py` | JSON → DB 시딩 (8,000건, 500건 배치) |
| `app/data_loader.py` | DB 우선 로드, JSON 폴백 |
| `.env` | `RR_DB_URL` 연결 문자열 |
| `.mcp.json` | MCP Toolbox Postgres 서버 설정 |
| `toolbox` | Google genai-toolbox 바이너리 (v0.27.0) |

---

## MCP Toolbox 연결 — Agent가 DB를 직접 도구로 사용

### 왜 MCP인가

| | MCP 없이 | MCP 연결 시 |
|--|---------|------------|
| 앱 데이터 흐름 | SQLAlchemy → Postgres | 동일 (변경 없음) |
| Agent의 DB 접근 | Python 스크립트 / docker exec | SQL 직접 실행 |
| 디버깅 | 매번 우회 코드 작성 | 즉시 쿼리로 확인 |
| 프레젠테이션 가치 | "DB 연동 완료" | + "Agent가 DB까지 도구로 사용" |

앱의 런타임은 SQLAlchemy로 동작하고, MCP는 **AI Agent가 개발/디버깅 시 DB를 직접 조회**하는 채널.

### 구성

[Google MCP Toolbox for Databases](https://github.com/googleapis/genai-toolbox) — Google이 만든 오픈소스 MCP 서버.

```
genai-toolbox (v0.27.0, darwin/arm64)
  └─ --prebuilt postgres --stdio
      └─ 127.0.0.1:5432/renewal_review (Docker Postgres)
```

`.mcp.json`:
```json
{
  "mcpServers": {
    "postgres": {
      "command": "./toolbox",
      "args": ["--prebuilt", "postgres", "--stdio"],
      "env": {
        "POSTGRES_HOST": "127.0.0.1",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DATABASE": "renewal_review",
        "POSTGRES_USER": "rr_user",
        "POSTGRES_PASSWORD": "rr_local_dev"
      }
    }
  }
}
```

### Agent가 할 수 있는 것

```sql
-- 테이블 목록 확인
list_tables

-- 리스크 분포 조회
SELECT state, count(*) FROM renewal_pairs GROUP BY state;

-- 특정 정책 확인
SELECT policy_number, premium_prior, premium_renewal
FROM renewal_pairs WHERE premium_renewal / premium_prior > 1.5;
```

Python 스크립트 작성 없이, Agent가 MCP 도구로 SQL을 직접 실행.

---

## Agent가 해결한 문제들

프론트엔드 경험만으로는 직접 디버깅하기 어려운 백엔드 이슈들을 Agent가 순차적으로 해결:

| 문제 | 원인 | Agent의 해결 |
|------|------|-------------|
| 포트 충돌 | 로컬 Postgres(brew)가 5432 점유 | brew services stop 후 표준 5432로 통일 |
| seed 실패 `'str' has no toordinal` | asyncpg가 date 객체 요구 | `date.fromisoformat()` 변환 추가 |
| data_loader `RuntimeError` | FastAPI 이벤트 루프 안에서 `asyncio.run()` 호출 | sync psycopg 드라이버로 전환 |
| ORM 매핑 실패 | `conn.execute()`가 raw tuple 반환 | `Session` 사용으로 ORM 객체 정상 매핑 |

**4개 이슈를 연쇄적으로 진단 → 수정 → 검증**, 별도 검색이나 StackOverflow 없이 완료.

---

## 프레젠테이션 포인트

### 말할 것

> "처음에는 JSON 파일에서 메모리로 올리는 방식이었는데, 실제 프로덕션처럼 보이려면 DB가 필요했다.
> Docker로 Postgres를 띄우고, 8,000건을 시딩하고, SQLAlchemy로 쿼리해서 가져오는 구조로 바꿨다.
> 포트 충돌, 드라이버 호환성, async/sync 이슈 같은 백엔드 인프라 문제가 연달아 터졌는데,
> AI agent가 연쇄적으로 진단하고 수정해줘서 프론트엔드 개발자인 내가 순조롭게 DB 연동을 완료했다.
> 거기서 한 발 더 나아가서, Google의 MCP Toolbox로 Agent가 DB를 직접 도구로 쓸 수 있게 연결했다.
> Agent한테 '리스크 분포 보여줘'라고 하면 Python 스크립트 없이 바로 SQL 쿼리로 답이 나온다."

### 보여줄 것

1. `docker ps` — Postgres 컨테이너 실행 확인
2. Dashboard → Run Sample → 결과 확인 (DB에서 쿼리로 가져온 데이터)
3. `data_loader.py` 코드 — DB 우선, JSON 폴백 구조
4. MCP로 Agent에게 DB 쿼리 요청 → 즉시 SQL 결과 반환 데모

---

## 프로덕션 확장 — BMS 배치 Ingestion

현재는 mock data 8,000건이지만, 실제 Quandri 흐름을 감안한 아키텍처 방향.

### 실제 데이터 흐름

```
보험사 (갱신 시즌)
  → BMS (Epic) 에 배치로 renewal 데이터 전송
    → Quandri Epic SDK 가 주기적 polling
      → 배치 단위로 DB INSERT
        → 리뷰 파이프라인 실행
```

### 현재 vs 프로덕션 차이

| | 현재 (Mock) | 프로덕션 |
|--|------------|---------|
| 유입 빈도 | 1회 seed | 갱신 시즌에 주기적 (일/주 단위) |
| 중복 처리 | 없음 | policy_number 기준 upsert |
| 캐시 갱신 | 서버 재시작 시 | 배치 ingest 후 자동 무효화 |

### 필요한 변경 3가지

1. **Upsert** — `ON CONFLICT (policy_number) DO UPDATE` 로 중복 방지
2. **Ingestion API** — `POST /ingest/batch` 로 Epic SDK polling 결과 수신
3. **캐시 무효화** — ingest 완료 시 `invalidate_cache()` 호출

**파이프라인 자체(diff engine → rule flagger → risk level)는 그대로 사용 가능.**

### 프레젠테이션 멘트

> "현재는 mock data 8,000건으로 시뮬레이션하고 있지만,
> 실제로는 보험사가 갱신 시즌에 BMS로 배치 데이터를 내려보내고 Epic SDK로 주기적으로 가져오는 흐름이다.
> 바꿔야 할 건 ingestion 레이어(upsert + API + 캐시)뿐이고,
> 분석 파이프라인 자체는 그대로 쓸 수 있는 구조로 만들었다."

---

## 검증

```bash
# 컨테이너 상태
docker ps  # postgres:16-alpine on 5432

# DB 데이터 확인
docker exec <container> psql -U rr_user -d renewal_review \
  -c "SELECT count(*) FROM renewal_pairs;"
# → 8000

# 앱에서 DB 로드 확인
uv run python -c "
from app.data_loader import load_pairs, invalidate_cache
invalidate_cache()
pairs = load_pairs()
print(f'{len(pairs)} pairs loaded from DB')
"
# → 8000 pairs loaded from DB
```
