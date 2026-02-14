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

- **Always reference this file** (`convention.md`) when making style or process decisions.
- **Update plans frequently.** After every significant step, update the current plan or task list.
- **Token-aware workflow:** Keep context lean. Summarize long outputs. Avoid reading entire large files when a targeted grep/glob suffices.
- **No speculative changes.** Only modify code you have read and understood.
- **Minimal diffs.** Prefer the smallest change that ships the feature or fix.

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
