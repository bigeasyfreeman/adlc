---
# ADLC Workflow Configuration
# This file defines agents, backends, routing, and concurrency for the DAG pipeline.

workflow: WORKFLOW.dot

backends:
  claude:
    command: "claude --model {{ model }} -p {{ prompt | shellquote }}"
    env:
      ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY}"
  codex:
    command: "codex --model {{ model }} --quiet --prompt {{ prompt | shellquote }}"
    env:
      OPENAI_API_KEY: "${OPENAI_API_KEY}"

default_backend: claude

concurrency:
  max_concurrent_agents: 8
  max_fan_out: 6

iteration_limits:
  plan_review: 3          # Eval Council max loops
  code_review: 3          # Code review max loops
  fixer: 2                # Fix attempts before escalate
  qa_retry: 2             # CI retry before escalate

labels:
  - lgtm                  # Approved, proceed to next node
  - revise                # Send back for revision
  - escalate              # Human intervention needed
  - blocked               # Cannot proceed, critical issue
  - pass                  # Deterministic gate passed
  - fail                  # Deterministic gate failed
  - proceed               # Triage approved
  - unclear               # Triage cannot classify
  - fixed                 # Fixer resolved the issue
  - stuck                 # Fixer cannot resolve
  - approve               # Engineer approved
---

# ADLC Pipeline Configuration

## Agents

Each agent is a thin config: model + prompt template + injected skills.
Agent prompts live in `agents/{name}.md`. Skills are synced into the workspace before execution.

### Node → Agent Mapping

| DAG Node | Agent | Backend | Model | Skills Injected |
|----------|-------|---------|-------|-----------------|
| `triage` | `agents/triage.md` | claude | claude-sonnet-4-6 | — |
| `research` | `agents/researcher.md` | claude | claude-opus-4-6 | codebase-research, grafana-observability |
| `plan` | `agents/planner.md` | claude | claude-opus-4-6 | codegen-context, architecture-pattern |
| `plan_review` | `agents/plan-reviewer.md` | claude | claude-opus-4-6 | eval-council |
| `scaffold` | *tool node* | — | — | architecture-pattern |
| `gen_tests` | *tool node* | — | — | qa-test-data, tdd-enforcement |
| `context_assembly` | *tool node* | — | — | codegen-context |
| `code` | `agents/coder.md` | claude | claude-sonnet-4-6 | tdd-enforcement, systematic-debugging |
| `code_review` | `agents/code-reviewer.md` | claude | claude-opus-4-6 | eval-council |
| `security` | `agents/security-reviewer.md` | claude | claude-opus-4-6 | appsec-threat-model, llm-security, agentic-security, api-security, infra-security |
| `qa` | *tool node* | — | — | — |
| `fixer` | `agents/fixer.md` | claude | claude-sonnet-4-6 | systematic-debugging |
| `pr_prep` | `agents/pr-preparer.md` | claude | claude-sonnet-4-6 | — |
| `engineer_review` | *human gate* | — | — | — |

### Tool Nodes (Deterministic — No LLM)

Tool nodes run shell commands. They are cheap, fast, and reliable.

```yaml
scaffold:
  command: |
    # Read architecture-pattern skill output, generate contracts and implementation guides
    mkdir -p ${WORKSPACE}/src/domain ${WORKSPACE}/src/adapters ${WORKSPACE}/src/ports
    # Scaffolding logic from architecture-pattern skill

gen_tests:
  command: |
    # Generate failing tests from G/W/T acceptance criteria
    # Uses qa-test-data skill output

context_assembly:
  command: |
    # Assemble per-task prompts with zero-read principle
    # Inlines: research, contracts/guides, tests, schemas, patterns

qa:
  command: |
    # Run linter + test suite
    ${TEST_COMMAND:-npm test}
    ${LINT_COMMAND:-npm run lint}
```

### Fan-Out Configuration

The `code` node fans out across tasks. Each task gets:
- Its own assembled context (from `context_assembly`)
- Its own workspace branch
- TDD enforcement: RED → GREEN → REFACTOR per G/W/T criterion

```yaml
code:
  fan_out_by: tasks              # Split by task tickets
  max_parallel: 6                # Concurrent coding agents
  fan_in: code_review            # Converge at code review
  success_criteria: all          # All tasks must succeed (vs "any")
```

## Workspace Isolation

Each pipeline run gets:
- Fresh repo clone or worktree
- Skills synced to `.claude/skills/` (digest-based, idempotent)
- `.adlc/` directory for pipeline state, artifacts, thread history
- Clean git state before each attempt

## Skill Injection

### Claude Code Native (Recommended)

Agent configs use Claude Code's native `skills:` frontmatter field. Skills listed in the frontmatter are injected into the agent's context at startup — no auto-discovery, no searching. The knowledge is there from the first turn.

```yaml
# agents/researcher.md
---
name: researcher
model: opus
skills:
  - codebase-research       # Injected at startup
  - grafana-observability    # Injected at startup
---
```

**Two patterns for skills + subagents:**

1. **Subagent preloads Skills** (what ADLC agents do) — The `skills:` field in agent frontmatter injects skill content directly. The agent is the actor; skills are its reference material.

2. **Skill delegates to Subagent** (`context: fork`) — For heavy skills that should run in isolation. Add `context: fork` and `agent: Explore` to a skill's frontmatter to spawn a subagent that runs the skill and returns only a summary.

### Manual Injection (Any Backend)

Skills are synced from `skills/` into the workspace before agent execution:

```
skills/{name}/SKILL.md  →  ${WORKSPACE}/.claude/skills/{name}/SKILL.md
                        →  ${WORKSPACE}/.codex/skills/{name}/SKILL.md
```

Sync is digest-based (SHA256). Only changed skills are copied.
Skills are excluded from git via `.git/info/exclude`.
