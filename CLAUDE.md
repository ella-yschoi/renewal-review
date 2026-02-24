# CLAUDE.md — Agent Instructions

## Read First

Before making any code change, read `.claude/rules/conventions.md` in the repo root. All style, process, and workflow decisions must follow that file.

## Core Rules

1. **No method docstrings.** Do not add docstrings to functions or methods. Use clear naming and type hints instead. Only add inline comments for non-obvious logic.
2. **Reference .claude/rules/conventions.md.** On every task, verify your approach against `.claude/rules/conventions.md`. If a convention is missing, propose adding it — don't invent ad-hoc rules.
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
- **Branching:** Follow `.claude/rules/conventions.md` branch naming. Create branches from `main`.
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

## Experiment Logs (experiment/ branches only)

When committing on an experiment/ branch, **both files** must be written and staged. The hook checks both and blocks the commit if either is missing.

### 1. Experiment Log — `docs/logs/experiments-log.md`

```markdown
## YYYY-MM-DD HH:MM | `branch-name`

### What was done
Specific work performed. Include quantitative results (time, file count, test count).

### Why it was done
Why this work was needed in the context of the project/experiment.

### How it was done
Implementation approach, tools used, decisions and rationale.
```

### 2. Presentation Log — `docs/logs/presentation-log.md`

```markdown
### YYYY-MM-DD HH:MM | `branch-name` | `hash`

**Commit message**

_diff stats_

> **Context**: The context and intent of this commit
> **Result**: Outcome or effect of the change
> **Insight**: One sentence the audience should remember
```

### Rules

- **Reverse chronological order** — new entries always go at the top. Applies to both log files.
- **Vancouver time** — use the timestamp from `TZ=America/Vancouver date "+%Y-%m-%d %H:%M"`. Do not estimate.
- Write with enough detail and context to serve as a presentation source
- Not commit-message level — write so that "someone unfamiliar with this work can still understand it"
- Write in English
- Focus on intent and context — no need to list files

## Design Doc Auto-Update

When changing code (`app/`, `tests/`), update the relevant section of `docs/design-doc.md` alongside it.
This is done automatically without a separate request. The hook blocks commits if design-doc.md is not staged.

| Change Target | Section to Update |
|--------------|-------------------|
| New module/file added, layer structure change | 1. Architecture |
| Pydantic/SQLAlchemy models | 2. Data Model |
| engine/ business logic | 3. Processing Pipeline |
| routes/ endpoints | 4. API Surface |
| templates/ HTML | 5. UI |
| Error handling, exception handling | 6. Error Handling |
| tests/ test additions | 7. Testing Strategy |
| pyproject.toml dependencies | 8. Tech Stack |

### Rules

- Do not touch sections unrelated to the change
- If a section is still empty, write it for the first time based on the change
- If existing content exists, only update the changed parts
- Write only accurate content that matches the implementation (no guessing)

## Insurance Domain

Insurance renewal review system. ACORD standard-based Personal Lines (Auto + Home).
Key terms: Renewal, Endorsement, Premium, Deductible, Liability Limit, Coverage, Bundle, SR-22 (high-risk certification).
When modifying `domain/models/`, `domain/services/`, or `adaptor/llm/`, refer to the `/insurance-domain` skill.
Current models lack UIM/PIP, Loss History, HO Form Type, etc. compared to ACORD standards — gap analysis included in the skill.

## What NOT to Do

- Don't add docstrings, type annotations, or comments to code you didn't change.
- Don't create README/docs files unless explicitly asked.
- Don't install new dependencies without asking.
- Don't use `rm -rf`, `git push --force`, or `git reset --hard` without explicit approval.
- Don't guess URLs or API endpoints — ask or find them in code.
