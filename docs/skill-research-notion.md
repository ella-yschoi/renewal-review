# Community Skills & Open Source 리서치 — Claude Code 프로젝트 도구 맵

---

## Layer 2.5: Community Skills (npx skills로 관리)

### 인프라: Find Skills (vercel-labs/skills)

- Skill 설치/검색/업데이트 관리 CLI. Skill을 1개라도 쓸 거면 이것부터.
- 명령어: `npx skills find / add / list / check / update / remove / init`
- 38개+ 에이전트 지원 (Claude Code, Codex, Cursor, Gemini CLI, Windsurf 등)
- 설치: `npx skills add vercel-labs/skills`
- [GitHub](https://github.com/vercel-labs/skills)

---

## 실제로 쓸 것

### Superpowers (obra/superpowers) — 7단계 개발 워크플로우

- GitHub ★ 4.1만. Skill 생태계 사실상 1위
- 에이전트가 코드부터 짜지 않게 만드는 개발 방법론
- 7단계: 브레인스토밍 → Worktree 생성 → 계획 수립 → 서브에이전트 배분 → TDD (RED-GREEN-REFACTOR) → 코드리뷰 → 브랜치 마무리
- 작업을 2~5분 단위로 쪼개서 독립 하위 에이전트에 배분, 2단계 자동 리뷰
- **이 프로젝트에서의 판단:** Layer 2의 Plan mode + Subagent + Worktree를 하나의 파이프라인으로 통합. 기존 셋업과 겹치는 부분은 Superpowers 쪽으로 통합하면 중복 제거 가능
- **데모 포인트:** "코드부터 짜지 않는 에이전트" — 오랜 시간 자율적으로 작업해도 계획에서 벗어나지 않음
- 설치: `npx skills add obra/superpowers`
- [GitHub](https://github.com/obra/superpowers)

### modern-python (Trail of Bits) — Python 베스트 프랙티스

- uv, ruff, pytest, pyproject.toml, ty(타입체크), detect-secrets, pip-audit 규칙 내장
- 이미 쓰는 도구(uv, ruff, pre-commit)의 규칙을 Claude에게 직접 주입
- 설치: `npx skills add https://github.com/trailofbits/skills --skill modern-python`
- [GitHub](https://github.com/trailofbits/skills)

### webapp-testing (Anthropic 공식) — E2E 테스트

- Playwright로 React 프론트엔드 E2E 테스트. Claude가 직접 브라우저 띄워서 검증
- 설치: `npx skills add https://github.com/anthropics/skills --skill webapp-testing`
- [GitHub](https://github.com/anthropics/skills)

### vercel-react-best-practices (Vercel) — React 패턴

- React 컴포넌트 패턴, Server Components, 성능 최적화. 109K+ 설치로 2위 인기
- 설치: `npx skills add https://github.com/vercel-labs/agent-skills --skill vercel-react-best-practices`
- [GitHub](https://github.com/vercel-labs/agent-skills)

### differential-review (Trail of Bits) — 보안 코드 리뷰

- Git diff 보안 리뷰. Worktree 간 머지 전 보안 검사
- 설치: `npx skills add https://github.com/trailofbits/skills --skill differential-review`
- [GitHub](https://github.com/trailofbits/skills)

### mcp-builder (Anthropic 공식) — MCP 서버 구축

- 커스텀 MCP 서버 구축 가이드. Notion MCP 외 추가 연동 시 필요
- 설치: `npx skills add https://github.com/anthropics/skills --skill mcp-builder`
- [GitHub](https://github.com/anthropics/skills)

---

## 선택적 사용 (프로젝트 성격에 따라)

### UI/UX Pro Max (nextlevelbuilder) — 디자인 엔진

- 67가지 UI 스타일, 96개 색상 팔레트, 57개 폰트 조합, 100개 업종별 추론 규칙 내장
- 지원: React, Next.js, Vue, Svelte, SwiftUI, Flutter 등 13개 프레임워크
- **핵심 가치:** 안티패턴 검출 — AI가 만든 UI에서 보라+분홍 그라디언트, 이모지 아이콘, 기본 템플릿 레이아웃을 정확히 잡아내고 대안 제시
- **판단:** 프론트엔드 작업(CANVAS-frontend 등) 시 활성화. 백엔드/API 작업에선 불필요
- 설치: `npx skills add nextlevelbuilder/ui-ux-pro-max-skill`
- [GitHub](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)

### Humanizer (blader) — AI 텍스트 필터

- Wikipedia AI Cleanup 팀 기반 24개 패턴 검출 + 교정
- 6개 카테고리: 콘텐츠 패턴(6), 언어 패턴(6), 스타일 패턴(6), 소통 패턴(3), 필러/헤징(3)
- "testament", "landscape", "showcasing" 등 AI 특유 어휘 자동 검출
- **판단:** 코드 작업에선 불필요. README, 블로그, 발표자료 등 글쓰기에 `/humanizer`로 호출. 한국어 적용은 별도 커스텀 필요
- 설치: `npx skills add blader/humanizer`
- [GitHub](https://github.com/blader/humanizer)

### property-based-testing (Trail of Bits) — 엣지케이스 탐색

- Hypothesis(Python) + fast-check(JS) 기반 엣지케이스 자동 탐색
- 설치: `npx skills add https://github.com/trailofbits/skills --skill property-based-testing`

### static-analysis (Trail of Bits) — 취약점 분석

- CodeQL, Semgrep, SARIF 통합 취약점 분석
- 설치: `npx skills add https://github.com/trailofbits/skills --skill static-analysis`

### agent-guardrails (jzOcb) — 에이전트 규칙 강제

- 에이전트가 프로젝트 규칙 벗어나지 않게 강제. convention.md 준수 보장
- [GitHub](https://github.com/jzOcb/agent-guardrails)

### Few-Word (sheeki03) — 토큰 절약

- 긴 출력을 파일로 오프로드해 토큰 절약. CLAUDE.md의 토큰 절약 규칙과 일치
- [GitHub](https://github.com/sheeki03/Few-Word)

---

## 오픈소스 도구 (Skill이 아닌 것)

### 바로 쓸 것 (pre-commit / 기존 파이프라인에 바로 붙음)

| 도구 | 역할 | 왜 필요한가 | 설치 |
| --- | --- | --- | --- |
| Gitleaks | 시크릿 탐지 | AI가 코드 생성 시 예시 API 키/토큰 노출 방지. pre-commit hook으로 즉시 통합 | `brew install gitleaks` + pre-commit hook |
| Semgrep | SAST 보안 스캐닝 | Ruff가 못 잡는 SQL injection, XSS 등 OWASP 취약점 탐지. pre-commit에 추가 | `pip install semgrep` + pre-commit hook |
| Hypothesis | Property-based 테스트 | Claude가 Hypothesis 테스트 작성 → 수백 개 엣지케이스 자동 생성 | `uv add --dev hypothesis` |
| Playwright MCP | 브라우저 자동화 MCP | Claude Code에 MCP 서버로 연결. React 앱 E2E 테스트를 Claude가 직접 수행 | `npm i -g @anthropic-ai/playwright-mcp` |

### 선택적 (규모 커질 때)

| 도구 | 역할 | 왜 필요한가 | 설치 |
| --- | --- | --- | --- |
| PR-Agent (Qodo) | AI PR 리뷰 | GitHub PR에 자동 리뷰/개선/설명 생성. Anthropic 모델 지원 | `pip install pr-agent` 또는 GitHub Action |
| MkDocs Material | 문서 사이트 | Markdown → 검색 가능한 문서 사이트. docstring 없는 규칙에 맞는 아키텍처 문서용 | `uv add --dev mkdocs-material` |
| Trivy | 의존성/컨테이너 스캔 | npm, pip 패키지 취약점 + Docker 이미지 스캔 | `brew install trivy` |
| Mockoon | API 목킹 | 프론트엔드 개발 시 백엔드 없이 로컬 REST API 목업 | `npm i -g @mockoon/cli` |
| DevPod | 재현 가능 환경 | worktree별 독립 dev container. Just task로 자동화 가능 | `brew install devpod` |

---

## 주목할 트렌드

- **llms.txt** — 프로젝트 루트에 LLM 최적화 요약 파일을 두는 새 컨벤션. AI 에이전트가 전체 문서 대신 이것만 읽으면 됨 ([llmstxt.org](https://llmstxt.org/))
- **Playwright Agents (v1.56+)** — Planner/Generator/Healer 3개 내장 AI 에이전트로 E2E 테스트 자동 생성+유지보수

---

## 기존 Layer 2와의 관계 정리

| 기존 Layer 2 항목 | Superpowers 적용 후 |
| --- | --- |
| Plan mode | → Superpowers Step 2~3 (계획 수립)이 대체 |
| Custom subagents | → Step 4 (서브에이전트 자동 배분)이 대체 |
| Git worktree | → Step 2 (worktree 자동 생성)가 통합 관리 |
| Hooks | 유지 — Superpowers와 독립적으로 동작 |
| Slash commands | 유지 — /review 등은 Superpowers와 병행 가능 |
| MCP (Notion) | 유지 — 외부 연동은 Skill 범위 밖 |
| Auto memory | 유지 — 세션 간 학습은 별도 관심사 |

---

## 설치 순서

```bash
# Day 0 — 인프라
npx skills add vercel-labs/skills

# 핵심 워크플로우
npx skills add obra/superpowers

# 스택 매칭
npx skills add https://github.com/trailofbits/skills --skill modern-python
npx skills add https://github.com/anthropics/skills --skill webapp-testing
npx skills add https://github.com/vercel-labs/agent-skills --skill vercel-react-best-practices
npx skills add https://github.com/trailofbits/skills --skill differential-review
npx skills add https://github.com/anthropics/skills --skill mcp-builder

# 보안 (pre-commit에 추가)
brew install gitleaks
pip install semgrep

# 선택적 — 필요할 때
npx skills add nextlevelbuilder/ui-ux-pro-max-skill
npx skills add blader/humanizer
```
