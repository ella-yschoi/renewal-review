# Convention Guide

## Code Style

- **No method docstrings.** Code should be self-documenting. Only add inline comments when logic is non-obvious.
- Use type hints (Python) or TypeScript types — let the type system document intent.
- Prefer small, single-responsibility functions over large ones.
- Keep files under 300 lines. Split when approaching this limit.

## Git Workflow

- Branch naming: `feat/`, `fix/`, `hotfix/`, `experiment/`, `chore/`
- Commit messages: imperative mood, < 72 chars. E.g., `fix: resolve race condition in auth flow`
- One logical change per commit. Never mix refactors with feature work.
- Worktrees live in `.worktrees/` — one Claude session per worktree for parallel dev.

## Agent-Native Rules

- **Always reference this file** (`.claude/rules/conventions.md`) when making style or process decisions.
- **Update plans frequently.** After every significant step, update the current plan or task list.
- **Token-aware workflow:** Keep context lean. Summarize long outputs. Avoid reading entire large files when a targeted grep/glob suffices.
- **No speculative changes.** Only modify code you have read and understood.
- **Minimal diffs.** Prefer the smallest change that ships the feature or fix.

## Architecture (Hexagonal)

의존성 방향: `api/` → `application/` → `domain/` ← `adaptor/`

- `domain/`은 외부 모듈을 import하지 않는다 (`ports/` Protocol만 정의)
- `application/`은 `domain/` + `ports/`만 import한다 (구현체 X)
- `api/`와 `adaptor/`는 어떤 레이어든 import 가능
- `infra/`는 와이어링 전용

## Design Patterns

1. 유한 값 집합 필드는 `StrEnum` 사용 (bare `str` 금지)
2. engine 숫자 리터럴 임계값 금지 → `config.py`에 정의
3. 라우트에 모듈 레벨 mutable state 금지 → `Depends()`로 접근
4. engine 함수는 입력 파라미터 mutation 금지 → `model_copy(update=...)` 사용

## File Organization

- Config files live at repo root.
- Shared utilities go in `shared/` or `lib/`.
- Each project is a self-contained directory with its own README.

## Testing

- Write tests for business logic. Skip trivial getter/setter tests.
- Test file naming: `*.test.ts`, `*_test.py`, or `test_*.py`.
- Run tests before committing. CI must pass before merge.

## Security

- Never commit secrets, `.env` files, or credentials.
- Validate all external input at system boundaries.
- Review OWASP Top 10 for any web-facing changes.
