# Claude Code Distribution - Quick Reference

**Last Updated**: February 14, 2026

---

## TL;DR Decision Tree

```
What are you distributing?
│
├─ Development instructions, patterns, workflows
│  └─ Use: Project Skills (.claude/skills/ in repo)
│     ⭐⭐⭐⭐⭐ Easiest for teams
│
├─ Organization-wide policies/standards
│  └─ Use: Organization Skills API + Private Marketplace
│     ⭐⭐⭐⭐⭐ Best for enterprises
│
├─ Code quality enforcement
│  └─ Use: Claude Code Hooks (.claude/hooks/ in repo)
│     ⭐⭐⭐⭐⭐ Deterministic, automatic
│
├─ Executable CLI tools
│  ├─ JavaScript tools → Private npm package + MCP
│  ├─ Python tools → Private pip package + MCP
│  └─ Complex dependencies → Docker containers
│     ⭐⭐⭐⭐ Standard package management
│
└─ Complex agent workflows/pipelines
   └─ Use: Claude Agent SDK as Python library
      ⭐⭐⭐⭐ Most flexible, requires dev skills
```

---

## Quick Comparison Table

| Method | Ease | Privacy | Reuse | Integration | Best For |
|--------|------|---------|-------|-------------|----------|
| **Project Skills** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Workflows, patterns |
| **Org Skills API** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Enterprise policies |
| **Private Marketplace** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Governed distribution |
| **Hooks** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Quality enforcement |
| **Agent SDK** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Complex workflows |
| **npm Package** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | JS/TS CLI tools |
| **pip Package** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Python CLI tools |
| **Git Submodules** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | Fast-changing deps |
| **Docker** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Complex deps |

---

## 1. Project Skills (Recommended for Teams)

**Setup (5 minutes):**
```bash
# In your repo root
mkdir -p .claude/skills/code-review
cat > .claude/skills/code-review/SKILL.md << 'EOF'
---
name: code-review
description: Review code for quality and security. Use when reviewing PRs or code changes.
---

# Code Review Checklist

- [ ] Logic is correct
- [ ] No security vulnerabilities
- [ ] Tests are adequate
- [ ] Code follows conventions
EOF

git add .claude/skills/
git commit -m "Add code-review skill"
```

**✅ Pros:**
- Zero setup for team members (just clone repo)
- Version controlled with your code
- Works immediately in Claude Code

**❌ Cons:**
- Visible to anyone with repo access
- Can't update without new commit

---

## 2. Organization Skills (Enterprise)

**Setup (Team/Enterprise plans only):**
1. Go to Claude.ai Organization Settings
2. Upload skills or use `/v1/skills` API endpoint
3. Skills appear for all workspace members

**✅ Pros:**
- Centralized management
- Auto-updates
- Governed distribution

**❌ Cons:**
- Requires Team/Enterprise plan
- No peer-to-peer sharing

---

## 3. Hooks (Quality Enforcement)

**Setup:**
```bash
# In your repo
mkdir -p .claude/hooks
cat > .claude/hooks/auto-format.json << 'EOF'
{
  "event": "PostToolUse",
  "matcher": "Edit(*.py)",
  "type": "command",
  "command": "ruff check --fix $FILE_PATH && ruff format $FILE_PATH"
}
EOF
```

**✅ Pros:**
- Deterministic execution
- Enforces standards automatically
- No AI token cost

**❌ Cons:**
- PostToolUse can't undo actions
- No native PreCommit/PostCommit hooks
- Shell scripts may be OS-specific

---

## 4. Private npm Package

**Setup:**
```bash
# Create package
mkdir my-tool && cd my-tool
npm init --scope=@myorg

# Publish to private registry
npm publish --access restricted

# Users install
npm install @myorg/my-tool
```

**✅ Pros:**
- Familiar to JS devs
- Scoped packages private by default
- Version management built-in

**Best with:** Verdaccio, AWS CodeArtifact, or npm private packages

---

## 5. Private pip Package

**Setup:**
```bash
# Create package
mkdir my_tool && cd my_tool
cat > pyproject.toml << 'EOF'
[project]
name = "my-tool"
version = "1.0.0"
dependencies = ["claude-agent-sdk"]
EOF

# Publish to private PyPI
python -m build
twine upload --repository-url https://your-pypi dist/*

# Users install
pip install my-tool --index-url https://your-pypi
```

**✅ Pros:**
- Standard Python ecosystem
- Highly portable

**❌ Cons:**
- Private PyPI requires VPN/auth setup

---

## 6. Agent SDK (Complex Workflows)

**Setup:**
```bash
pip install claude-agent-sdk

# Create reusable workflow
cat > my_agent.py << 'EOF'
from claude_agent_sdk import ClaudeSDKClient

async def run_workflow():
    client = ClaudeSDKClient(api_key="...")
    # Your workflow logic
    pass
EOF
```

**✅ Pros:**
- Full programmatic control
- Can be packaged as library
- Works in CI/CD pipelines

**❌ Cons:**
- Requires Python dev skills
- Not native to Claude Code CLI

---

## 7. Docker (Complex Dependencies)

**Setup:**
```bash
# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.13-alpine
COPY my_tool.py /app/
CMD ["python", "/app/my_tool.py"]
EOF

# Build and push
docker build -t myorg/my-tool .
docker push myorg/my-tool

# Users run
docker run myorg/my-tool [args]
```

**✅ Pros:**
- Perfect environment consistency
- Works anywhere Docker runs

**❌ Cons:**
- Slower startup
- May have filesystem access limitations

---

## Recommended Stack for Most Teams

```
.claude/
├── skills/              # Development patterns & workflows
│   ├── code-review/
│   ├── commit-message/
│   └── testing-strategy/
├── hooks/               # Quality enforcement
│   ├── auto-format.json
│   ├── run-tests.json
│   └── check-secrets.json
└── settings.json        # MCP servers (for npm/pip tools)
```

**Plus:**
- Private npm/pip packages for executable tools
- Organization Skills API for enterprise-wide policies (if Team/Enterprise plan)

---

## Installing Skills - Quick Commands

**From CLI:**
```bash
npx add-skill [repo-name]                    # Fastest method
```

**From Plugin Marketplace:**
```bash
/plugin install anthropics/skills            # Official skills
/plugin marketplace add your-org/skills      # Private marketplace
```

**Manual:**
```bash
git clone https://github.com/org/skills ~/.claude/skills/my-skill
```

**Organization (API):**
```bash
curl -X POST https://api.anthropic.com/v1/skills \
  -H "x-api-key: $API_KEY" \
  -d @skill.json
```

---

## Skill File Structure

**Minimal:**
```
my-skill/
└── SKILL.md              # Required
```

**Complete:**
```
my-skill/
├── SKILL.md              # Required - main instructions
├── reference.md          # Optional - detailed docs
├── examples.md           # Optional - usage examples
└── scripts/              # Optional - executable code
    ├── validate.py
    └── helper.sh
```

**SKILL.md Format:**
```yaml
---
name: my-skill
description: What it does and when to use it (max 1024 chars)
---

# Instructions

[Markdown content, keep under 500 lines]
```

---

## Current State (Feb 2026)

**✅ Available Now:**
- Agent Skills open standard (Dec 2025)
- Organization skills provisioning
- Private plugin marketplaces
- Claude Agent SDK (Python & TypeScript)
- Claude Opus 4.6 (Feb 5, 2026)
- MCP tool annotations (Feb 13, 2026)
- Hooks with PreToolUse input modification

**❌ Not Available:**
- Individual peer-to-peer skill sharing
- Dedicated PreCommit/PostCommit hooks

**📊 Ecosystem:**
- 160,000+ community skills
- Multiple marketplaces (SkillHub, SkillsMP)
- Active GitHub ecosystem

---

## Key Resources

- **Docs**: https://code.claude.com/docs/en/skills
- **Spec**: https://agentskills.io/specification
- **SDK**: https://github.com/anthropics/claude-agent-sdk-python
- **Official Skills**: https://github.com/anthropics/skills
- **Marketplace Guide**: https://code.claude.com/docs/en/plugin-marketplaces
- **Hooks Guide**: https://code.claude.com/docs/en/hooks-guide

---

## Pro Tips

1. **Start with Project Skills** - Easiest to set up, version controlled
2. **Add Hooks for quality** - Auto-format, test, validate
3. **Use private packages for tools** - Standard dependency management
4. **Keep SKILL.md under 500 lines** - Better performance
5. **Use progressive disclosure** - Link to reference files for details
6. **Write third-person descriptions** - "Reviews code..." not "I can review..."
7. **Include trigger terms** - Help Claude know when to use the skill
8. **Commit skills to Git** - Team members get them automatically

---

## Common Mistakes to Avoid

❌ Creating skills in `~/.cursor/skills-cursor/` (reserved for Cursor internal)
❌ Windows-style paths in scripts (`scripts\file.py` → use `scripts/file.py`)
❌ Vague skill names (`helper`, `utils` → use `analyzing-spreadsheets`)
❌ First-person descriptions ("I can..." → use "Analyzes...")
❌ Deeply nested references (keep one level deep from SKILL.md)
❌ Time-sensitive info ("Before Aug 2025..." → use "Current method" section)

---

## Need More Details?

See full research document: `/Users/yeonsuchoi/Workspace/docs/claude-code-distribution-research.md`
