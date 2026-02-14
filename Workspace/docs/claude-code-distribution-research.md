# Claude Code Skills & Agent Distribution Research

**Research Date**: February 14, 2026
**Researcher**: Claude Code Agent

---

## Executive Summary

This document provides a comprehensive analysis of distribution methods for internal AI agent tools, skills, and workflows, specifically focused on Claude Code and the Claude Agent SDK ecosystem as of February 2026. It covers official distribution channels, private/internal distribution strategies, and alternative approaches for enterprise teams.

---

## 1. Claude Code Skills: Structure & Distribution

### 1.1 What Are Agent Skills?

[Agent Skills](https://agentskills.io/home) are organized folders of instructions, scripts, and resources that AI agents can discover and load dynamically to perform better at specific tasks. Originally developed by Anthropic and [released as an open standard on December 18, 2025](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills), they have been adopted by Microsoft, OpenAI, Atlassian, and Figma.

### 1.2 Technical Structure

Skills follow the [Agent Skills open standard specification](https://github.com/agentskills/agentskills), with each skill being a directory containing:

**Required:**
- `SKILL.md` - Main instruction file with YAML frontmatter and markdown body

**Optional:**
- `references/` - Additional documentation loaded on-demand
- `scripts/` - Executable code (Python, Bash, JavaScript)
- `assets/` - Templates and resources
- `examples.md` - Usage examples

#### SKILL.md Format

```yaml
---
name: skill-name                    # Max 64 chars, lowercase/hyphens only
description: Brief description of what this skill does and when to use it
license: Apache-2.0                 # Optional
metadata:                           # Optional
  author: example-org
  version: "1.0"
---

# Skill Content (Markdown)

Instructions, workflows, examples...
```

**Key Requirements:**
- SKILL.md should be under 500 lines for optimal performance
- Description must be specific, third-person, and include trigger terms
- File references should be one level deep from SKILL.md
- Use progressive disclosure for detailed content

### 1.3 Storage Locations

| Type | Path | Scope | Distribution |
|------|------|-------|--------------|
| **Personal** | `~/.cursor/skills/` or `~/.claude/skills/` | Individual user across all projects | Manual installation per user |
| **Project** | `.claude/skills/` in repo root | All users of the repository | Version controlled via Git |
| **Organization** | Managed via API/Settings | All workspace members | Centralized, auto-updated |

### 1.4 Installation Methods

**Individual Users:**
- Manual: Download skill folder → place in skills directory
- CLI: `npx add-skill [repo-name]` ([fastest method](https://medium.com/vibe-coding/the-easiest-way-to-extend-claude-code-cloudflare-complicates-it-4995e8b4cab3))
- Web: Upload via Claude.ai Settings → Capabilities → Skills
- Plugin: `/plugin marketplace add anthropics/skills`

**Organizations:**
- [Organization Owners can provision skills for all users](https://support.claude.com/en/articles/12512180-using-skills-in-claude) (Team/Enterprise plans)
- Skills appear automatically in every team member's Skills list
- Can be set as enabled or disabled by default
- **Limitation**: Individual peer-to-peer skill sharing is NOT available

### 1.5 Evaluation Summary: Skills Distribution

| Criterion | Rating | Notes |
|-----------|--------|-------|
| **Ease of Use** | ⭐⭐⭐⭐ | Simple directory structure, CLI installation available |
| **Privacy** | ⭐⭐⭐⭐ | Project skills in private repos, org-level provisioning for enterprises |
| **Reusability** | ⭐⭐⭐⭐⭐ | Open standard, works across Claude.ai, Claude Code, and API |
| **Claude Code Integration** | ⭐⭐⭐⭐⭐ | Native integration, automatic discovery |

**Best For**: Instructions, workflows, domain knowledge, and reusable development patterns.

---

## 2. Claude Code Marketplace & Plugin System

### 2.1 Official Marketplace

The [Plugin Marketplace](https://code.claude.com/docs/en/plugin-marketplaces) is a centralized registry system for Claude Code plugins, with 40+ plugins defined in `.claude-plugin/marketplace.json`. Users can:

- Browse via `/plugin > Discover` in the UI
- Install via `/plugin install {plugin-name}@claude-plugin-directory`
- Access through the [CCPM (Claude Code Plugin Manager) registry](https://medium.com/@markchen69/claude-code-has-a-skills-marketplace-now-a-beginner-friendly-walkthrough-8adeb67cdc89)

### 2.2 Private/Internal Marketplaces

Claude Code supports creating [private plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) for internal distribution:

**Key Capabilities:**
- **Private Repository Support**: Install plugins from private Git repositories using existing credential helpers
- **Access Control**: Restrict marketplaces using regex pattern matching for internal git servers
- **Central Registry**: Tools like [LiteLLM AI Gateway](https://docs.litellm.ai/docs/tutorials/claude_code_plugin_marketplace) can act as central registries where admins govern which plugins are available organization-wide

**Setup Process:**
1. Create a Git repository with marketplace.json
2. Define plugins with their source locations and metadata
3. Configure Claude Code to use your internal marketplace
4. Control access via Git permissions and Claude Code settings

### 2.3 Community Marketplaces

As of February 2026, there are several community marketplaces:
- [SkillHub](https://www.skillhub.club/) - 7,000+ AI-evaluated skills
- [SkillsMP](https://skillsmp.com/) - 160,000+ agent skills
- [GitHub community collections](https://github.com/topics/claude-code-skills) - Various curated skill repositories

**Important**: Anthropic recommends preferring official marketplaces first and treating community marketplaces like open-source code.

### 2.4 Evaluation Summary: Plugin Marketplace

| Criterion | Rating | Notes |
|-----------|--------|-------|
| **Ease of Use** | ⭐⭐⭐⭐ | Simple installation, UI browsing available |
| **Privacy** | ⭐⭐⭐⭐⭐ | Full support for private marketplaces with access control |
| **Reusability** | ⭐⭐⭐⭐ | Works within Claude Code ecosystem |
| **Claude Code Integration** | ⭐⭐⭐⭐⭐ | Native integration, governed distribution |

**Best For**: Internal tools, approved plugin libraries, managed skill collections for enterprises.

---

## 3. Claude Agent SDK: Standalone Pipelines

### 3.1 Overview

The [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview) (formerly Claude Code SDK) provides the same tools, agent loop, and context management that power Claude Code, programmable in Python and TypeScript.

**Installation:**
```bash
pip3 install claude-agent-sdk
```

### 3.2 Key Features for Reusable Workflows

1. **Custom Tools**: Python functions that Claude can invoke as needed, implemented as in-process MCP servers
2. **Session Management**: `ClaudeSDKClient` for interactive, multi-turn conversations
3. **Async Streaming API**: `query()` returns an `AsyncIterator` of messages
4. **Multi-Agent Workflows**: Compose Claude agents with other agents (Azure OpenAI, GitHub Copilot, etc.) in sequential, concurrent, handoff, and group chat workflows

### 3.3 Pipeline Use Cases

The SDK is [customizable and minimal](https://datapoetica.medium.com/the-definitive-guide-to-the-claude-agent-sdk-building-the-next-generation-of-ai-69fda0a0530f), with lightweight scripts ideal for:
- **Non-interactive pipelines**: Background jobs, CI pipelines (collect all messages at once)
- **Custom agent workflows**: Turn "plan → build → run" workflow into real, programmable agents
- **Reusable packages**: Package your flow into a shareable tool

### 3.4 Distribution as Python Library

**Publishing to PyPI:**
- Package your agent workflow as a standard Python package
- Use `setup.py` or `pyproject.toml` to define dependencies
- Publish to public PyPI or private PyPI server
- Users install via `pip install your-agent-package`

**Example Structure:**
```
your-agent-package/
├── src/
│   └── your_agent/
│       ├── __init__.py
│       ├── agent.py          # Main agent logic
│       ├── tools.py          # Custom tools
│       └── workflows/        # Reusable workflows
├── pyproject.toml
└── README.md
```

### 3.5 Recent Updates (February 2026)

- [February 13, 2026 release](https://github.com/anthropics/claude-agent-sdk-python/releases): MCP tool annotations support, thinking configuration
- Works with [Claude Opus 4.6](https://datapoetica.medium.com/the-definitive-guide-to-the-claude-agent-sdk-building-the-next-generation-of-ai-69fda0a0530f) (released Feb 5, 2026)
- [Multi-agent orchestration](https://devblogs.microsoft.com/semantic-kernel/build-ai-agents-with-claude-agent-sdk-and-microsoft-agent-framework/) with Microsoft Agent Framework integration

### 3.6 Evaluation Summary: Agent SDK

| Criterion | Rating | Notes |
|-----------|--------|-------|
| **Ease of Use** | ⭐⭐⭐ | Requires Python development skills, more complex setup |
| **Privacy** | ⭐⭐⭐⭐⭐ | Full control, can use private PyPI or internal distribution |
| **Reusability** | ⭐⭐⭐⭐⭐ | Standard Python package, highly portable |
| **Claude Code Integration** | ⭐⭐⭐ | Not native to Claude Code, but can be invoked via custom tools |

**Best For**: Complex agent workflows, CI/CD pipelines, standalone automation tools, programmatic agent orchestration.

---

## 4. Claude Code Hooks: Pipeline Workflows

### 4.1 What Are Hooks?

[Claude Code hooks](https://code.claude.com/docs/en/hooks-guide) are user-defined shell commands that execute at specific points in Claude Code's lifecycle, providing deterministic control over behavior.

### 4.2 Hook Events

- **UserPromptSubmit**: Before a prompt is processed
- **PreToolUse**: Before a tool is executed (can modify tool inputs since v2.0.10)
- **PostToolUse**: After successful tool execution
- **PermissionRequest**: When Claude requests permission (doesn't fire in non-interactive mode)
- **Stop/SubagentStop**: When a task concludes

### 4.3 Hook Types

1. **Command Hooks** (`type: "command"`): Run shell commands
2. **Prompt Hooks** (`type: "prompt"`): Single-turn LLM evaluation
3. **Agent Hooks** (`type: "agent"`): Multi-turn verification with tool access

### 4.4 Common Use Cases

From the [DataCamp tutorial](https://www.datacamp.com/tutorial/claude-code-hooks) and [workflow automation guides](https://www.eesel.ai/blog/hooks-in-claude-code):

- **Code quality**: Auto-format, lint, run tests after code changes
- **Security**: Block dangerous operations, scan for secrets
- **Notifications**: Send alerts when tasks complete
- **Validation**: Enforce commit message formats, check documentation updates
- **Pipeline steps**: Chain multiple tools in sequence

**Example**: Auto-format and test after code changes
```json
{
  "event": "PostToolUse",
  "matcher": "Edit(*)",
  "type": "command",
  "command": "ruff check --fix $FILE_PATH && pytest tests/"
}
```

### 4.5 Limitations

From [GitHub Issue #4834](https://github.com/anthropics/claude-code/issues/4834) and [hooks documentation](https://www.eesel.ai/blog/hooks-reference-claude-code):

1. **PostToolUse cannot undo actions** - Tool has already executed
2. **No dedicated PreCommit/PostCommit hooks** - Workaround: PostToolUse with `Bash(git commit:*)` matcher, but suboptimal for blocking commits
3. **Cannot inject information during commit** - Difficult to add Co-authored-by tags or enforce commit message formats
4. **PermissionRequest doesn't fire in non-interactive mode** - Must use PreToolUse for automated permission decisions

### 4.6 Evaluation Summary: Hooks

| Criterion | Rating | Notes |
|-----------|--------|-------|
| **Ease of Use** | ⭐⭐⭐ | Requires understanding of hook events and JSON configuration |
| **Privacy** | ⭐⭐⭐⭐⭐ | Fully local, can enforce security policies |
| **Reusability** | ⭐⭐⭐ | Hook configs can be shared via Git, but shell scripts may be OS-specific |
| **Claude Code Integration** | ⭐⭐⭐⭐⭐ | Native integration, deterministic execution |

**Best For**: Enforcing code quality, security policies, automated testing, Git workflow enhancements, deterministic validation.

---

## 5. Alternative Distribution Methods

### 5.1 Private npm Packages

**Tools:** [npm private packages](https://docs.npmjs.com/about-private-packages/), [Verdaccio](https://www.verdaccio.org/), [AWS CodeArtifact](https://aws.amazon.com/blogs/devops/publishing-private-npm-packages-aws-codeartifact/), [ProGet](https://docs.inedo.com/docs/proget/feeds/npm/howto-npm-publish)

**How It Works:**
- Package your CLI tools as npm packages with scope `@your-org/package-name`
- Publish to npm registry (private packages) or self-hosted registry (Verdaccio, CodeArtifact)
- Users install via `npm install @your-org/package-name`
- Access control via npm tokens or IAM (for AWS)

**Recent Update:** [February 2026 guide on running Verdaccio in Docker](https://oneuptime.com/blog/post/2026-02-08-how-to-run-verdaccio-in-docker-private-npm-registry/view)

| Criterion | Rating | Notes |
|-----------|--------|-------|
| **Ease of Use** | ⭐⭐⭐⭐⭐ | npm is familiar to JavaScript developers, simple installation |
| **Privacy** | ⭐⭐⭐⭐⭐ | Scoped packages private by default, self-hosted options available |
| **Reusability** | ⭐⭐⭐⭐ | Standard npm ecosystem, works anywhere Node.js runs |
| **Claude Code Integration** | ⭐⭐⭐ | Can be invoked via Bash tool or MCP servers |

**Best For**: JavaScript/TypeScript CLI tools, teams already using npm, tools requiring Node.js ecosystem.

---

### 5.2 Private Pip Packages

**Tools:** Private PyPI servers, [DevPI](https://pypi.org/project/devpi/), AWS CodeArtifact, [JFrog Artifactory](https://jfrog.com/artifactory/)

**How It Works:**
- Package your Python tools as standard Python packages
- Publish to private PyPI server
- Users install via `pip install your-package --index-url https://your-pypi-server.com`
- Access control via authentication tokens

| Criterion | Rating | Notes |
|-----------|--------|-------|
| **Ease of Use** | ⭐⭐⭐⭐ | pip is familiar to Python developers |
| **Privacy** | ⭐⭐⭐⭐ | Private servers require VPN/authentication setup |
| **Reusability** | ⭐⭐⭐⭐⭐ | Standard Python ecosystem, portable |
| **Claude Code Integration** | ⭐⭐⭐ | Can be invoked via Bash tool or MCP servers |

**Best For**: Python CLI tools, data science/ML teams, Python-heavy organizations.

---

### 5.3 Git Submodules

**Documentation:** [Git Submodules Complete Guide 2026](https://devtoolbox.dedyn.io/blog/git-submodules-complete-guide)

**How It Works:**
- Create a Git repository for your shared code
- Add as submodule: `git submodule add https://github.com/your-org/shared-lib.git`
- Submodule points to specific commit of the library
- Users run `git submodule update --init --recursive`

**Trade-offs** (from [Philipp Stephan's PyCon talk](https://philippstephan.de/blog/posts/pycon22-talk/)):

**Pros:**
- Quick iteration on different versions
- IDE tooling works natively
- Dependency versions pinned replicably
- No need for private package infrastructure

**Cons:**
- Confusing and error-prone
- Requires extra CI/CD configuration (shallow clone doesn't initialize submodules)
- Not suitable for stable library archives

| Criterion | Rating | Notes |
|-----------|--------|-------|
| **Ease of Use** | ⭐⭐ | Steep learning curve, easy to make mistakes |
| **Privacy** | ⭐⭐⭐⭐⭐ | Uses existing Git authentication |
| **Reusability** | ⭐⭐⭐ | Tightly coupled to parent repo, version management complex |
| **Claude Code Integration** | ⭐⭐⭐⭐ | Files appear in project, Claude Code can read them directly |

**Best For**: Fast iteration on internal dependencies, teams that don't want to manage private package registries, monorepo-like setups.

---

### 5.4 Internal CLI Tools

**Distribution:** Internal package managers, shared network drives, container registries

**How It Works:**
- Build standalone CLI executables (e.g., via PyInstaller, Go compilation, Rust cargo)
- Distribute via internal download server or package manager
- Users install to PATH
- Invoke from Claude Code via Bash tool

| Criterion | Rating | Notes |
|-----------|--------|-------|
| **Ease of Use** | ⭐⭐⭐ | Depends on distribution mechanism |
| **Privacy** | ⭐⭐⭐⭐⭐ | Fully internal, no external dependencies |
| **Reusability** | ⭐⭐⭐⭐ | Portable if compiled for target OS |
| **Claude Code Integration** | ⭐⭐⭐⭐ | Can be invoked via Bash tool (must be in MCP allowlist) |

**Best For**: Organizations with existing internal tool distribution systems, teams building cross-language tools.

---

### 5.5 Docker-Based Distribution

**Resources:** [Distributing CLI Tools with Docker](https://spin.atomicobject.com/command-line-tools-docker/), [Dockerizing CLI Tools](https://blog.smallsec.ca/dockerizing-cli-tools/)

**How It Works:**
- Package CLI tool in Docker image
- Push to Docker registry (Docker Hub, private registry, AWS ECR)
- Users run: `docker run your-org/your-tool [args]`
- Can alias for convenience: `alias your-tool='docker run your-org/your-tool'`

**Benefits:**
- Perfect environment specification (libraries, dependencies, configuration versions)
- "If it works anywhere, it will work everywhere"
- Good for complex setup/installation processes
- Useful for tools requiring multiple languages or libraries

| Criterion | Rating | Notes |
|-----------|--------|-------|
| **Ease of Use** | ⭐⭐⭐ | Requires Docker knowledge, slightly slower startup |
| **Privacy** | ⭐⭐⭐⭐⭐ | Private registries widely available |
| **Reusability** | ⭐⭐⭐⭐⭐ | Highly portable, consistent across environments |
| **Claude Code Integration** | ⭐⭐⭐ | Can be invoked via Bash tool, but may have filesystem access limitations |

**Best For**: Tools with complex dependencies, ensuring environment consistency, teams already using Docker, tools requiring specific runtime environments.

---

## 6. Recommended Strategies by Use Case

### 6.1 For Development Workflows & Patterns

**Recommendation:** Claude Code Skills (Project)

**Approach:**
1. Create skills in `.claude/skills/` in your repository
2. Commit to version control
3. Skills automatically available to all team members who clone the repo
4. Use `CLAUDE.md` at repo root for project-specific instructions

**Example:**
```
your-repo/
├── .claude/
│   ├── skills/
│   │   ├── code-review/
│   │   │   └── SKILL.md
│   │   ├── commit-message/
│   │   │   └── SKILL.md
│   │   └── testing-strategy/
│   │       └── SKILL.md
│   └── hooks/
│       └── post-edit-format.json
├── CLAUDE.md
└── convention.md
```

### 6.2 For Organization-Wide Skills

**Recommendation:** Organization Skills API + Private Plugin Marketplace

**Approach:**
1. Use [Claude API Skills endpoint](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/enterprise) (`/v1/skills`) to provision skills workspace-wide
2. Create private plugin marketplace for governed distribution
3. Skills auto-update across all team members
4. Admins control which skills are available

### 6.3 For Executable Tools & Scripts

**Recommendation:** Private npm/pip Package + MCP Server

**Approach:**
1. Package your tools as npm/pip packages
2. Publish to private registry
3. Create MCP server that exposes tools to Claude Code
4. Users install package and configure MCP server in `~/.claude/settings.json`

**Example MCP Server:**
```python
# your_tools_mcp/server.py
from claude_agent_sdk import tool

@tool
def analyze_code(file_path: str) -> str:
    """Analyze code quality and security."""
    # Your tool implementation
    pass
```

### 6.4 For Complex Agent Workflows

**Recommendation:** Claude Agent SDK as Python Library

**Approach:**
1. Build agent workflow using Claude Agent SDK
2. Package as standard Python library with clear API
3. Publish to private PyPI or distribute via Git
4. Teams import and use in their automation scripts

**Example:**
```python
# your_agent_workflow/__init__.py
from claude_agent_sdk import ClaudeSDKClient

class CodeReviewAgent:
    def __init__(self, api_key: str):
        self.client = ClaudeSDKClient(api_key)

    async def review_pr(self, pr_url: str) -> dict:
        """Run automated PR review workflow."""
        # Workflow implementation
        pass
```

### 6.5 For Quality Enforcement & Validation

**Recommendation:** Claude Code Hooks

**Approach:**
1. Create hook configurations in `.claude/hooks/`
2. Commit to version control
3. Hooks automatically execute for all team members
4. Use PreToolUse for validation, PostToolUse for cleanup

**Example:**
```json
{
  "event": "PostToolUse",
  "matcher": "Edit(*.py)",
  "type": "command",
  "command": "ruff check --fix $FILE_PATH && ruff format $FILE_PATH"
}
```

---

## 7. Decision Matrix

Use this table to choose the right distribution method:

| Requirement | Recommended Approach | Alternative |
|-------------|---------------------|-------------|
| Share development patterns/instructions | Project Skills | Organization Skills API |
| Enforce code quality standards | Hooks + Project Skills | Pre-commit hooks |
| Distribute executable tools | Private npm/pip + MCP | Docker containers |
| Organization-wide policies | Organization Skills API | Private Plugin Marketplace |
| Complex automation pipelines | Agent SDK as library | CLI tools + Bash |
| Fast-changing internal dependencies | Git Submodules | Private packages with frequent releases |
| Environment-specific tools | Docker containers | Platform-specific packages |
| Multi-language tool ecosystem | Docker containers | Internal CLI + PATH |

---

## 8. Current State of Claude Code Ecosystem (Feb 2026)

### What's Available Now

✅ **Agent Skills Open Standard**: Launched Dec 18, 2025, widely adopted
✅ **Organization Skills Provisioning**: Available for Team/Enterprise plans
✅ **Private Plugin Marketplaces**: Fully supported with access control
✅ **Claude Agent SDK**: Python & TypeScript, actively maintained
✅ **MCP Tool Annotations**: Added Feb 13, 2026
✅ **Claude Opus 4.6**: Released Feb 5, 2026, improved agent capabilities
✅ **Hooks System**: Mature, with PreToolUse input modification since v2.0.10

### What's Limited or Missing

❌ **Individual Peer-to-Peer Skill Sharing**: Not available (must use organization provisioning or manual installation)
⚠️ **Git Workflow Hooks**: No dedicated PreCommit/PostCommit hooks (workarounds exist)
⚠️ **Hook Limitations**: PostToolUse cannot undo actions, PermissionRequest doesn't fire in non-interactive mode

### Community Activity

- **160,000+ agent skills** available via community marketplaces
- **Active GitHub ecosystem** with curated skill collections
- **Multiple tutorial series** from DataCamp, Eesel, and community bloggers
- **Integration with major AI platforms** (Microsoft, OpenAI tools)

---

## 9. Sources & References

### Official Documentation
- [Extend Claude with skills - Claude Code Docs](https://code.claude.com/docs/en/skills)
- [Agent Skills Specification](https://agentskills.io/specification)
- [Claude Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Automate workflows with hooks](https://code.claude.com/docs/en/hooks-guide)
- [Create and distribute a plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
- [Skills for enterprise - Claude API Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/enterprise)

### Technical Resources
- [GitHub - anthropics/skills](https://github.com/anthropics/skills)
- [GitHub - anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python)
- [GitHub - agentskills/agentskills](https://github.com/agentskills/agentskills)
- [claude-agent-sdk on PyPI](https://pypi.org/project/claude-agent-sdk/)

### Tutorials & Guides
- [Claude Code Has a Skills Marketplace Now — A Beginner-Friendly Walkthrough](https://medium.com/@markchen69/claude-code-has-a-skills-marketplace-now-a-beginner-friendly-walkthrough-8adeb67cdc89)
- [Claude Code Hooks: A Practical Guide to Workflow Automation | DataCamp](https://www.datacamp.com/tutorial/claude-code-hooks)
- [A complete guide to hooks in Claude Code](https://www.eesel.ai/blog/hooks-in-claude-code)
- [The Definitive Guide to the Claude Agent SDK](https://datapoetica.medium.com/the-definitive-guide-to-the-claude-agent-sdk-building-the-next-generation-of-ai-69fda0a0530f)
- [Build AI Agents with Claude Agent SDK and Microsoft Agent Framework](https://devblogs.microsoft.com/semantic-kernel/build-ai-agents-with-claude-agent-sdk-and-microsoft-agent-framework/)

### Community & Standards
- [Introducing Agent Skills | Claude Blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Agent Skills: Anthropic's Next Bid to Define AI Standards](https://thenewstack.io/agent-skills-anthropics-next-bid-to-define-ai-standards/)
- [SkillHub - Claude Skills & Agent Skills Marketplace](https://www.skillhub.club/)
- [SkillsMP: Agent Skills Marketplace](https://skillsmp.com/)

### Alternative Distribution
- [Creating and publishing private packages | npm](https://docs.npmjs.com/creating-and-publishing-private-packages/)
- [How to Run Verdaccio in Docker (Feb 2026)](https://oneuptime.com/blog/post/2026-02-08-how-to-run-verdaccio-in-docker-private-npm-registry/view)
- [Quitting pip: How we use git submodules](https://philippstephan.de/blog/posts/pycon22-talk/)
- [Distributing CLI Tools with Docker](https://spin.atomicobject.com/command-line-tools-docker/)
- [Publishing private npm packages with AWS CodeArtifact](https://aws.amazon.com/blogs/devops/publishing-private-npm-packages-aws-codeartifact/)

### GitHub Issues & Discussions
- [Feature Request: Add Hooks for Git Workflow Automation (#4834)](https://github.com/anthropics/claude-code/issues/4834)

---

## 10. Conclusion

The Claude Code ecosystem as of February 2026 offers robust options for internal tool distribution:

**For most teams**, the combination of:
1. **Project Skills** (in `.claude/skills/`) for development patterns
2. **Hooks** (in `.claude/hooks/`) for quality enforcement
3. **Private npm/pip packages** for executable tools
4. **Organization Skills API** for enterprise-wide distribution

...provides a comprehensive solution that balances ease of use, privacy, and Claude Code integration.

**For advanced use cases** requiring complex agent orchestration, the **Claude Agent SDK** packaged as a Python library offers the most flexibility, though at the cost of increased complexity.

The key insight is that these approaches are **complementary**, not mutually exclusive. Teams can mix and match based on specific needs, using Skills for instructions, Hooks for enforcement, and packages/SDK for executable logic.
