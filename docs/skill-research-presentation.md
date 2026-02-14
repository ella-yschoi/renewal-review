# Claude Code 프로젝트 도구 맵
## Community Skills & Open Source

---

# 전체 구조

```
Layer 1   개발 환경 자동화        uv, Just, pre-commit+Ruff, Git worktree
Layer 2   Claude Code 고급 기능   Hooks, Slash commands, Subagents, MCP, Plan mode
Layer 2.5 Community Skills        Superpowers, Skills CLI, 보안/테스트/React skills
Layer 3   LLM Observability       Langfuse, LiteLLM
Layer 4   보안 파이프라인          Gitleaks, Semgrep, Trivy
```

---

# 왜 Skills인가?

Claude Code의 내장 기능만으로는 부족한 영역:

- **개발 방법론** — 코드부터 짜지 않게 만드는 프로세스
- **도메인 지식** — Python/React 베스트 프랙티스, 보안 규칙
- **품질 관리** — AI가 만든 코드/텍스트/UI의 "AI 티" 제거

Skills = Claude에게 주입하는 **전문가의 체크리스트**

---

# 핵심 Skill 4개 (설치 완료)

---

## 1. Superpowers — "코드부터 짜지 않는 에이전트"

**GitHub ★ 4.1만 | Skill 생태계 1위**

7단계 워크플로우:
1. 브레인스토밍
2. Git Worktree 생성
3. 계획 수립 (2~5분 단위 태스크)
4. 서브에이전트 배분
5. TDD (RED → GREEN → REFACTOR)
6. 2단계 코드리뷰
7. 브랜치 마무리

**임팩트:** 기존 Plan mode + Subagent + Worktree를 하나의 파이프라인으로 통합

---

## 2. Find Skills — Skill 생태계 관리 도구

**Vercel Labs 공식 | 38개+ 에이전트 지원**

```bash
npx skills find    # 키워드 검색
npx skills add     # 즉시 설치
npx skills check   # 업데이트 확인
npx skills update  # 일괄 갱신
```

**임팩트:** Skill 관리 자체를 하나의 워크플로우로 자동화

---

## 3. UI/UX Pro Max — "AI 티" 없는 디자인

**67 스타일 | 96 팔레트 | 57 폰트 조합 | 13 프레임워크**

핵심: **안티패턴 검출**
- 보라+분홍 그라디언트
- 이모지 아이콘 남발
- 기본 템플릿 레이아웃

→ 정확히 잡아내고 업종 맞춤 대안 제시

---

## 4. Humanizer — AI 글쓰기 24개 패턴 필터

Wikipedia AI Cleanup 팀 기반

6개 카테고리:
- 콘텐츠 패턴 (의미 부풀리기, 홍보성 언어)
- 언어 패턴 (AI 특유 어휘: "testament", "landscape")
- 스타일 패턴 (엠대시 남발, 볼드 과용)
- 소통 패턴 ("I hope this helps!")
- 필러/헤징 (과도한 완곡 표현)

→ `/humanizer` 한 번이면 "사람이 쓴 것 같은 문장"으로 변환

---

# 추가 추천 Skills

---

## 스택 매칭 Skills (바로 쓸 것)

| Skill | 출처 | 핵심 가치 |
|---|---|---|
| **modern-python** | Trail of Bits | uv, ruff, pytest 규칙을 Claude에 주입 |
| **webapp-testing** | Anthropic 공식 | Playwright E2E — Claude가 브라우저 직접 테스트 |
| **react-best-practices** | Vercel | React 패턴 + 성능 최적화 (109K+ 설치) |
| **differential-review** | Trail of Bits | Git diff 보안 리뷰 |
| **mcp-builder** | Anthropic 공식 | 커스텀 MCP 서버 구축 가이드 |

---

## 선택적 Skills

| Skill | 용도 |
|---|---|
| **property-based-testing** | Hypothesis + fast-check 엣지케이스 탐색 |
| **static-analysis** | CodeQL, Semgrep 통합 취약점 분석 |
| **agent-guardrails** | convention.md 준수 강제 |
| **Few-Word** | 긴 출력 → 파일 오프로드, 토큰 절약 |

---

# 오픈소스 도구 (Skill이 아닌 것)

---

## 보안 파이프라인 (pre-commit에 추가)

| 도구 | 역할 | 설치 |
|---|---|---|
| **Gitleaks** | 시크릿 탐지 (API 키, 토큰 노출 방지) | `brew install gitleaks` |
| **Semgrep** | SAST (SQL injection, XSS 등 OWASP) | `pip install semgrep` |
| **Trivy** | 의존성 + 컨테이너 취약점 스캔 | `brew install trivy` |

AI가 생성한 코드 → Ruff(스타일) + Semgrep(보안) + Gitleaks(시크릿) 3중 검증

---

## 테스트 도구

| 도구 | 역할 | 설치 |
|---|---|---|
| **Hypothesis** | Python property-based 테스트 | `uv add --dev hypothesis` |
| **Playwright MCP** | Claude Code가 직접 브라우저 테스트 | `npm i -g @anthropic-ai/playwright-mcp` |
| **Playwright Agents** (v1.56+) | E2E 테스트 자동 생성 + 자가 복구 | `npm i -D @playwright/test` |

---

## 기타 도구

| 도구 | 역할 | 언제 쓰나 |
|---|---|---|
| **PR-Agent** (Qodo) | AI PR 리뷰 | GitHub PR 자동 리뷰 |
| **MkDocs Material** | 문서 사이트 | 아키텍처 문서 필요할 때 |
| **Mockoon** | API 목킹 | 프론트엔드 독립 개발 시 |
| **DevPod** | 재현 가능 환경 | worktree별 dev container |

---

# 주목할 트렌드

## llms.txt

프로젝트 루트에 LLM 최적화 요약 파일
→ AI 에이전트가 전체 문서 대신 이것만 읽으면 됨
→ llmstxt.org

## Playwright Agents (v1.56+)

3개 내장 AI 에이전트:
- **Planner** — 테스트 전략 설계
- **Generator** — 테스트 코드 작성
- **Healer** — 깨진 셀렉터 자동 복구

---

# Superpowers가 흡수하는 기존 Layer 2

| 기존 항목 | 적용 후 |
|---|---|
| Plan mode | → Superpowers Step 2~3이 대체 |
| Custom subagents | → Step 4 (자동 배분)이 대체 |
| Git worktree | → Step 2 (자동 생성)가 통합 |
| **Hooks** | **유지** — 독립 동작 |
| **Slash commands** | **유지** — 병행 가능 |
| **MCP (Notion)** | **유지** — Skill 범위 밖 |
| **Auto memory** | **유지** — 별도 관심사 |

---

# 설치 순서 요약

```
Day 0 — 인프라
  npx skills add vercel-labs/skills
  npx skills add obra/superpowers
  brew install gitleaks && pip install semgrep

스택 매칭
  npx skills add trailofbits/skills --skill modern-python
  npx skills add anthropics/skills --skill webapp-testing
  npx skills add vercel-labs/agent-skills --skill vercel-react-best-practices
  npx skills add trailofbits/skills --skill differential-review

필요할 때
  npx skills add nextlevelbuilder/ui-ux-pro-max-skill
  npx skills add blader/humanizer
  npm i -g @anthropic-ai/playwright-mcp
```

---

# 우선순위 TOP 3

1. **Gitleaks + Semgrep** — pre-commit에 추가만 하면 끝. 즉시 보안 커버리지
2. **Playwright MCP** — Claude가 프론트엔드를 직접 테스트
3. **modern-python** — 이미 쓰는 도구의 규칙을 Claude에게 강제
