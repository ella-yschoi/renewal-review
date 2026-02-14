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

## 실험 작업 로그

커밋 전에 `docs/experiment-log.md`에 작업 내역을 작성하고, 이 파일을 커밋에 포함한다.

### 작성 시점

- 의미 있는 작업 단위가 완료되었을 때 (사소한 커밋마다 X)
- 세팅/설정 작업 완료 시
- 실험 실행 전후
- 문제 해결 시

### 형식 (한국어)

```markdown
## YYYY-MM-DD HH:MM | `브랜치명`

### 무엇을 했는가
구체적 작업 내용. 어떤 기능을 만들었는지, 어떤 설정을 했는지, 어떤 문제를 해결했는지.

### 왜 했는가
프로젝트/실험 맥락에서 이 작업이 필요한 이유. 어떤 목표에 기여하는지.

### 어떻게 했는가
구현 방식, 세팅 과정, 사용한 도구/기술, 내린 결정과 그 이유.
선택지가 여러 개였다면 왜 이 방식을 골랐는지.
```

### 규칙

- 프레젠테이션 소스로 쓸 것이므로 구체적이고 맥락이 풍부하게 작성
- 커밋 메시지 수준이 아니라, "이 작업을 모르는 사람이 읽어도 이해할 수 있는" 수준
- 한국어로 작성 (나중에 영어로 번역 예정)
- 파일 목록은 불필요 — 의도와 맥락에 집중

## What NOT to Do

- Don't add docstrings, type annotations, or comments to code you didn't change.
- Don't create README/docs files unless explicitly asked.
- Don't install new dependencies without asking.
- Don't use `rm -rf`, `git push --force`, or `git reset --hard` without explicit approval.
- Don't guess URLs or API endpoints — ask or find them in code.
