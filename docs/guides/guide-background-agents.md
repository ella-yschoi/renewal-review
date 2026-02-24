# Background Agent Workflow — Team Guide

A workflow for **running quality tasks such as code review and documentation verification in the background in parallel** while performing your main work.

When Claude Code calls the `Task` tool with `run_in_background: true`, a separate agent process is spawned that does not block the main conversation.

> Reference: The "Parallel Work Streams: Sync + Async" pattern from the [Agent-Native Engineering](https://www.generalintelligencecompany.com/writing/agent-native-engineering) article.

---

## How It Works

```
Engineer (Sync)                Background (Async)
  │ Main work                  ├─ Agent A (Code Review)
  │ Feature implementation     │   Read, Grep, Bash, etc.
  │ UI work                    │   Independent context window
  │                            │
  │                            ├─ Agent B (Doc Verification)
  │                            │   Code ↔ design-doc comparison
  │                            │
  ▼                            ▼
  Receive results ◄──────── Completion notification (automatic)
```

**Key point**: Each agent has its own independent context window and does not share tools with the main conversation. Upon completion, results are automatically delivered via `<task-notification>`.

---

## Usage

### Step 1: Launch a Background Agent

Request in natural language from a Claude Code session:

```
Run a code review on commit b0807f8 as a background agent.
Review convention compliance, bug risks, security, and improvements.
```

What Claude Code internally calls:

```python
Task(
    prompt="Code review for commit b0807f8: conventions, bugs, security, improvements",
    subagent_type="general-purpose",
    run_in_background=True,  # Key: background execution
)
```

Multiple agents can be run **simultaneously** — just send multiple Task calls in parallel in a single message.

### Step 2: Continue Main Work

Continue working on other tasks in the main conversation while agents are running. No blocking.

### Step 3: Check Progress (Optional)

```python
TaskOutput(task_id="aaaa191", block=False)
```

Or check the output file directly:

```bash
tail -20 /private/tmp/claude-501/.../tasks/aaaa191.output
```

### Step 4: Receive Results

Automatic notification upon agent completion:

```xml
<task-notification>
  <task-id>aaaa191</task-id>
  <status>completed</status>
  <result>Code review results...</result>
  <usage>
    total_tokens: 60394
    tool_uses: 19
    duration_ms: 134295
  </usage>
</task-notification>
```

---

## Application Examples in This Project

### Self Code Review (Agent A)

| Item | Value |
|------|-------|
| Target | Commit `b0807f8` (9 files, +208/-30) |
| Review Items | Convention compliance, bug risks, security, improvements |
| Tool Calls | 19 (Read, Grep, Bash) |
| Duration | 134s (~2m 14s) |
| Results | 0 Critical, 5 Warning, 10 Info |

Key findings:
- `sort`/`order` parameter not validated (`str` → `Literal` recommended)
- No timeout/max iteration limit in polling loop
- No network error handling in polling `fetch`
- `seed_db.py` reads from `prior` but runtime uses `renewal`

### Design-doc Verification (Agent B)

| Item | Value |
|------|-------|
| Target | `docs/design-doc.md` ↔ entire actual codebase |
| Verification Method | Triangulation-style (document ↔ code field-by-field comparison) |
| Tool Calls | 37 (Read, Grep, Bash, Glob) |
| Duration | 153s (~2m 33s) |
| Results | 6 MISMATCH out of 17 sections |

Key findings:
- `POST /reviews/compare` endpoint: present in docs but deleted from code
- `ReviewResult.llm_summary_generated` field: present in code but missing from docs
- `test_routes.py` test count: docs say 9 vs actual 4
- Analytics deque location: code reference in docs is incorrect

---

## Suitable Tasks

| Task | Suitability | Reason |
|------|-------------|--------|
| Code review (conventions, security) | ✅ High | Read-only, independent |
| Document ↔ code consistency verification | ✅ High | Read-only, time-consuming |
| Test coverage analysis | ✅ High | Can run independently |
| Dependency security audit | ✅ High | External tool invocation |
| Feature implementation | ❌ Low | Risk of file conflicts, overlaps with main work |
| DB migration | ❌ Low | State-changing, order-dependent |

**Principle**: Best suited for read-only + independent + time-consuming tasks.

---

## Comparison with Traditional Workflows

| Item | Traditional (Synchronous) | Background Agent |
|------|---------------------------|------------------|
| Code review | Human reads PR and leaves comments | Agent verifies asynchronously, only results received |
| Doc verification | Manual comparison or not done at all | Agent automatically compares field by field |
| Context switching | Switching back and forth between review ↔ coding | None — main work continues uninterrupted |
| Cost | Human time | API tokens (60K tokens ≈ $0.05) |

---

## Caveats

1. **File write conflicts**: If a background agent modifies files, it may conflict with main work. Recommended for read-only tasks only.
2. **Permissions**: Background agents follow the same permission mode. Bash execution may be denied.
3. **Token cost**: Each agent uses an independent context, so tokens are consumed separately.
4. **Output size**: Results may be truncated if too long. Full content can be checked in the output file.
