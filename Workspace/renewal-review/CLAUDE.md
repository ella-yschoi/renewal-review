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

## What NOT to Do

- Don't add docstrings, type annotations, or comments to code you didn't change.
- Don't create README/docs files unless explicitly asked.
- Don't install new dependencies without asking.
- Don't use `rm -rf`, `git push --force`, or `git reset --hard` without explicit approval.
- Don't guess URLs or API endpoints — ask or find them in code.
