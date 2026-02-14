# CLAUDE.md — Agent Instructions

## Read First

Before making any code change, read `convention.md` in the repo root. All style, process, and workflow decisions must follow that file.

## Core Rules

1. **No method docstrings.** Do not add docstrings to functions or methods. Use clear naming and type hints instead. Only add inline comments for non-obvious logic.
2. **Reference convention.md.** On every task, verify your approach against `convention.md`. If a convention is missing, propose adding it — don't invent ad-hoc rules.
3. **Update plans frequently.** After completing each significant step, update the task list or plan. This keeps the human and other agents in sync.
4. **Token-aware workflow.** Minimize context usage:
   - Use `Grep`/`Glob` before reading full files.
   - Summarize long command outputs rather than dumping raw text.
   - Prefer targeted reads (`offset`/`limit`) for large files.
   - Avoid re-reading files already in context.
5. **Minimal diffs.** Make the smallest shippable change. Don't refactor surrounding code, add features beyond scope, or "improve" code you weren't asked to touch.
6. **No speculative changes.** Read code before modifying it. Understand existing patterns before proposing new ones.

## Workflow

- **Worktrees:** Use `.worktrees/wt-feat-{1,2,3}` for features, `wt-research` for research, `wt-hotfix` for urgent fixes, `wt-experiment` for spikes.
- **Research:** Always use subagents (Task tool) for research tasks. Use `wt-research` worktree for research work, separate from feature development.
- **Branching:** Follow `convention.md` branch naming. Create branches from `main`.
- **Commits:** Imperative mood, < 72 chars, one logical change per commit.
- **Before committing:** Run linter + tests. Never skip pre-commit hooks.

## Security Pipeline

- Pre-commit hooks: Gitleaks (secret detection), Semgrep (SAST). Do not bypass these.
- AI-generated code must pass Ruff + Semgrep + Gitleaks before commit.

## Environment

- Python: 3.13.7
- Node: v22.14.0
- Git: 2.39.2
- Main branch: `main`

## 실험 로그 (experiment 브랜치 전용)

experiment/ 브랜치에서 커밋할 때 **두 파일 모두** 작성하고 staging에 포함해야 한다. 훅이 둘 다 체크하며, 누락 시 커밋을 차단한다.

### 1. 실험 로그 — `docs/logs/experiments-log.md`

```markdown
## YYYY-MM-DD HH:MM | `브랜치명`

### 무엇을 했는가
구체적 작업 내용. 정량 결과 (시간, 파일 수, 테스트 수) 포함.

### 왜 했는가
프로젝트/실험 맥락에서 이 작업이 필요한 이유.

### 어떻게 했는가
구현 방식, 도구, 결정과 그 이유.
```

### 2. 프레젠테이션 로그 — `docs/logs/presentation-log.md`

```markdown
### YYYY-MM-DD HH:MM | `브랜치명` | `해시`

**커밋 메시지**

_diff 통계_

> **Context**: 이 커밋의 맥락과 의도
> **Result**: 결과 또는 변경 효과
> **Insight**: 청중이 기억할 한 문장
```

### 규칙

- 프레젠테이션 소스로 쓸 것이므로 구체적이고 맥락이 풍부하게 작성
- 커밋 메시지 수준이 아니라, "이 작업을 모르는 사람이 읽어도 이해할 수 있는" 수준
- 한국어로 작성 (나중에 영어로 번역 예정)
- 의도와 맥락에 집중 — 파일 목록 나열 불필요

## Design Doc 자동 업데이트

코드(`app/`, `tests/`)를 변경하면 `docs/design-doc.md`의 관련 섹션을 함께 업데이트한다.
별도 요청 없이 자동으로 수행하며, 커밋 시 design-doc.md가 staging에 없으면 훅이 블록한다.

| 변경 대상 | 업데이트 섹션 |
|-----------|--------------|
| 새 모듈/파일 추가, 계층 구조 변경 | 1. Architecture |
| Pydantic/SQLAlchemy 모델 | 2. Data Model |
| engine/ 비즈니스 로직 | 3. Processing Pipeline |
| routes/ 엔드포인트 | 4. API Surface |
| templates/ HTML | 5. UI |
| 에러 처리, 예외 핸들링 | 6. Error Handling |
| tests/ 테스트 추가 | 7. Testing Strategy |
| pyproject.toml 의존성 | 8. Tech Stack |

### 규칙

- 변경과 무관한 섹션은 건드리지 않는다
- 아직 비어 있는 섹션은 해당 변경에 맞춰 처음 작성한다
- 기존 내용이 있으면 변경 부분만 업데이트한다
- 구현과 일치하는 정확한 내용만 작성한다 (추측 금지)

## What NOT to Do

- Don't add docstrings, type annotations, or comments to code you didn't change.
- Don't create README/docs files unless explicitly asked.
- Don't install new dependencies without asking.
- Don't use `rm -rf`, `git push --force`, or `git reset --hard` without explicit approval.
- Don't guess URLs or API endpoints — ask or find them in code.
