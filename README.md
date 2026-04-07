# ADLC — Agentic Development Lifecycle

> Ship features with AI agents. From idea to pull request — one engineer review.

**9 agents. 22 skills. One DAG pipeline.**

```
Idea + Repo → Triage → Research → Plan ↔ Review → Code → QA → Security → PR → You ✅
```

ADLC is an open framework for orchestrating AI coding agents through a structured pipeline. Give it a feature description and a codebase — it researches your repo, writes a technical plan, generates code with TDD, runs security review across 5 OWASP domains, and delivers a single pull request for your review.

Works with **Claude Code**, **Codex (OpenAI)**, **Cursor**, **Antigravity (Google)**, **Factory**, or any CLI-based coding agent.

---

## Why ADLC?

Most AI coding workflows are either:
- **Too simple**: "Write me a function" → one-shot, no context, no tests
- **Too manual**: Copy-paste context between agents, manually orchestrate steps

ADLC fills the gap: a **structured, repeatable pipeline** that handles the full lifecycle — research, planning, coding, review, security, QA — with agents doing the work and you making the decisions.

**What makes it different:**

| Feature | How It Works |
|---------|-------------|
| **DAG pipeline** | Workflow defined as a visual graph (Graphviz DOT), not a monolithic prompt |
| **Label-based routing** | Agents emit `lgtm`/`revise`/`escalate` → edges route to the next step |
| **Fan-out parallelism** | Independent coding tasks execute simultaneously |
| **Deterministic + agentic** | Lint, test, scaffold nodes cost zero LLM tokens |
| **Bounded iteration** | Every review loop has a hard cap — no runaway agent cycles |
| **Injectable skills** | 22 markdown skill files encode domain expertise, injected per agent |
| **One human gate** | Machine gates (Eval Council, security, QA) run before you review |

Inspired by [Attractor](https://github.com/strongdm/attractor), [Stripe Minions](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents), and [Vajra](https://github.com/zamana-inc/vajra).

---

## Quick Start

### One-Command Setup

```bash
git clone https://github.com/bigeasyfreeman/adlc.git
cd adlc

# Install for your platform
./setup.sh claude ~/my-project       # Claude Code
./setup.sh codex ~/my-project        # Codex (OpenAI)
./setup.sh cursor ~/my-project       # Cursor
./setup.sh antigravity ~/my-project  # Antigravity (Google)
./setup.sh factory ~/my-project      # Factory
./setup.sh all ~/my-project          # All platforms
```

### What Gets Installed

| Platform | Skills Location | Agents Location | Instructions File |
|----------|----------------|-----------------|-------------------|
| **Claude Code** | `.claude/skills/` | `.claude/agents/` | `CLAUDE.md` |
| **Codex** | `.agents/skills/` | *(via AGENTS.md)* | `AGENTS.md` |
| **Cursor** | `.cursor/rules/*.mdc` | `.cursor/rules/*.mdc` | *(in rules)* |
| **Antigravity** | `.agent/skills/` | `agents.md` | *(in agents.md)* |
| **Factory** | `.factory/docs/` | `.factory/droids/` | `AGENTS.md` |

### Platform-Specific Usage

**Claude Code** — Agents are subagents with preloaded skills:
```bash
# Skills + agents auto-discovered. Just use them:
claude "Research this codebase for building notifications"  # → researcher agent
claude "Create a Build Brief from this PRD"                 # → planner agent
```

**Codex** — Skills in `.agents/skills/`, instructions in `AGENTS.md`:
```bash
codex "Analyze this repo and create a technical plan for notifications"
```

**Cursor** — Skills installed as `.mdc` rule files with semantic activation:
```
# In Cursor chat, skills activate automatically based on context
# Or reference directly: @adlc-codebase-research @adlc-eval-council
```

**Antigravity** — Skills in `.agent/skills/`, personas in `agents.md`:
```
# Agents defined with Goals/Traits/Constraints
# Skills activate via semantic description matching
```

**Factory** — Agents as droids, skills as approved docs:
```bash
# Droids available as subagent types
# Skills loaded from .factory/docs/
```

### Manual Setup (Any Platform)

If you prefer to install manually, just copy the skills you want:

```bash
# Copy all skills
cp -r skills/ /your/project/.claude/skills/   # or .agents/skills/, .agent/skills/, etc.

# Or copy individual skills
cp -r skills/codebase-research/ /your/project/.claude/skills/codebase-research/
cp -r skills/eval-council/ /your/project/.claude/skills/eval-council/
```

See [examples/](examples/) for a complete example PRD and walkthrough.

---

## Pipeline Architecture

The pipeline is defined in [`WORKFLOW.dot`](WORKFLOW.dot) — a Graphviz directed graph.

```
start → triage → research → plan ↔ plan_review → scaffold → gen_tests →
  context_assembly → code (fan-out) ↔ code_review ↔ fixer → security → qa →
  pr_prep → engineer_review → done
```

### Node Types

| Shape | Type | Example | LLM Cost |
|-------|------|---------|----------|
| Agent (blue) | LLM call with skills | Research, Plan, Code | Yes |
| Tool (dashed) | Shell command | Scaffold, Test, Lint | None |
| Fan-Out | Parallel execution | Code tasks | Yes (per task) |
| Human Gate | Your review | Engineer Review | None |
| Conditional | Route by classification | Triage | Minimal |

### Routing Labels

Agents emit structured labels. Edges match labels to route.

| Label | Meaning |
|-------|---------|
| `lgtm` | Approved — proceed to next node |
| `revise` | Send back with findings |
| `escalate` | Needs human judgment |
| `pass` / `fail` | Deterministic gate result |
| `fixed` / `stuck` | Fixer outcome |

### Iteration Limits

| Loop | Max | On Exhaustion |
|------|-----|---------------|
| Plan ↔ Review | 3 | Escalate |
| Code ↔ Review | 3 | Escalate |
| Fixer | 2 | Escalate |
| QA retry | 2 | Escalate |

Visualize the pipeline:
```bash
dot -Tpng WORKFLOW.dot -o pipeline.png
```

---

## Agents

9 thin configs. Each is ~100 lines: model + prompt + skills + output labels.

| Agent | Purpose | Model | Skills |
|-------|---------|-------|--------|
| **triage** | Classify input, route or escalate | Sonnet | — |
| **researcher** | Deep codebase analysis + PRD cross-reference | Opus | codebase-research, grafana |
| **planner** | PRD → Build Brief (spec/plan/tasks) | Opus | codegen-context, architecture |
| **plan-reviewer** | 6-persona Eval Council | Opus | eval-council |
| **coder** | TDD per task: RED → GREEN → REFACTOR | Sonnet | tdd-enforcement, debugging |
| **code-reviewer** | Code quality and correctness | Opus | eval-council |
| **fixer** | 4-phase root cause diagnosis | Sonnet | systematic-debugging |
| **security-reviewer** | 5 OWASP domain assessment | Opus | 5 security skills |
| **pr-preparer** | Assemble final PR package | Sonnet | — |

---

## Skills

22 injectable markdown files encoding domain expertise. Skills are the framework's knowledge layer — swap them, extend them, or write your own.

### Core Engineering
| Skill | What It Does |
|-------|-------------|
| `codebase-research` | Deep repo analysis → structured repo map (1,237 lines of expertise) |
| `eval-council` | 6-persona evaluation: Architect, Skeptic, Operator, Executioner, First Principles, Security Auditor |
| `codegen-context` | Per-task prompt assembly with zero-read principle (everything inlined) |
| `tdd-enforcement` | RED → GREEN → REFACTOR per acceptance criterion |
| `systematic-debugging` | 4-phase: Evidence → Hypotheses → Test → Fix |
| `architecture-pattern` | Port/adapter/domain scaffolding from repo conventions |
| `qa-test-data` | Test data generation from Given/When/Then criteria |

### Security (5 OWASP Domains)
| Skill | Coverage |
|-------|----------|
| `appsec-threat-model` | OWASP Top 10 (2021): A01–A10 |
| `llm-security` | OWASP LLM Top 10 (2025): LLM01–LLM10 |
| `agentic-security` | OWASP Agentic Security: ASI01–ASI10 |
| `api-security` | OWASP API Top 10 (2023): API1–API10 |
| `infra-security` | OWASP K8s Top 10 (2025): K01–K10 |

### Integrations (Optional)
| Skill | What It Does |
|-------|-------------|
| `jira-ticket-creation` | Generate JIRA tickets from task breakdown |
| `confluence-decomposition` | Create Confluence pages from Build Brief |
| `slack-orchestration` | Cross-phase workflow notifications |
| `grafana-observability` | Dashboard provisioning + traffic baseline validation |
| `ci-cd-pipeline` | GitHub Actions + Argo CD config generation |
| `incident-runbook` | Runbook + alert config from failure modes |

### Product (Optional — for PRD creation)
| Skill | What It Does |
|-------|-------------|
| `prd-generation` | PRD quality evaluation and completeness checking |
| `ux-flow-builder` | Mermaid flowcharts from user flows, catches dead ends |
| `figma-integration` | Design spec extraction, PRD ↔ Figma validation |
| `gong-customer-evidence` | Customer call transcript validation |

---

## Customization

### Write Your Own Skill

```markdown
# Skill: [Your Skill Name]

> One-line description

## Trigger
Which DAG nodes use this skill?

## Input
What data does it receive?

## Behavior
Step-by-step instructions.

## Output
What does it produce?

## Quality Gates
- [ ] Checklist item 1
- [ ] Checklist item 2
```

Add it to `skills/manifest.json` and the relevant agent's `skills` list.

### Modify the Pipeline

Edit `WORKFLOW.dot` to change the pipeline:

```bash
# Add a new node
vi WORKFLOW.dot

# Visualize
dot -Tpng WORKFLOW.dot -o pipeline.png

# Update config
vi WORKFLOW.md
```

**Common customizations:**
- **Skip security** for internal tools: remove the `security` node, route `code_review` → `qa`
- **Add a design review node**: insert between `plan_review` and `scaffold`
- **Bugfix pipeline**: `triage` → `research` → `code` → `qa` → `pr_prep` (skip planning)

### Use Different Models

Agent frontmatter uses platform-native model identifiers:

| Platform | Fast Model | Deep Reasoning Model |
|----------|-----------|---------------------|
| **Claude Code** | `model: sonnet` | `model: opus` |
| **Codex** | `model: o4-mini` | `model: o3` |
| **Antigravity** | `model: gemini-2.5-flash` | `model: gemini-2.5-pro` |
| **Factory** | `model: inherit` | `model: claude-opus-4-6` |
| **Cursor** | *(set in UI)* | *(set in UI)* |

Edit agent YAML frontmatter to change:
```yaml
---
model: sonnet    # Claude Code: sonnet (fast) or opus (deep)
# model: o3      # Codex: o3 (deep) or o4-mini (fast)
---
```

### Cross-Platform Compatibility

Agent configs use a universal frontmatter format that maps to each platform:

| Frontmatter Field | Claude Code | Codex | Factory | Antigravity | Cursor |
|-------------------|-------------|-------|---------|-------------|--------|
| `name` | Agent name | — | Droid name | — | — |
| `description` | Trigger text | Trigger text | UI description | Trigger text | `description:` |
| `model` | Model ID | Model ID | Model ID | Model ID | *(UI setting)* |
| `tools` | Tool list | — | Tool category | — | — |
| `skills` | Preloaded skills | — | — | — | — |
| `labels` | Output routing | — | — | — | — |

---

## File Structure

```
adlc/
├── setup.sh                  # One-command installer for any platform
├── WORKFLOW.dot               # Pipeline DAG (Graphviz)
├── WORKFLOW.md                # Configuration
├── README.md
├── CONTRIBUTING.md
├── LICENSE                    # MIT
├── agents/                    # 9 thin agent configs (universal format)
│   ├── triage.md
│   ├── researcher.md
│   ├── planner.md
│   ├── plan-reviewer.md
│   ├── coder.md
│   ├── code-reviewer.md
│   ├── fixer.md
│   ├── security-reviewer.md
│   └── pr-preparer.md
├── skills/                    # 22 injectable skills
│   ├── manifest.json
│   ├── codebase-research/
│   ├── eval-council/
│   ├── codegen-context/
│   └── ... (19 more)
├── platform/                  # Platform-specific instruction files
│   ├── CLAUDE.md              # Claude Code project instructions
│   ├── AGENTS.md              # Codex / Factory instructions
│   └── agents-antigravity.md  # Antigravity persona definitions
├── examples/
│   ├── README.md
│   └── example-prd.md
├── docs/
│   ├── archive/               # Original monolithic specs (reference)
│   ├── schemas/               # 12 JSON Schema contracts
│   ├── specs/                 # 15 runtime behavior specs
│   └── tests/                 # 7 test specifications
└── scripts/
    └── md2pdf.py
```

---

## Design Principles

1. **Graph, not prose.** The pipeline is a visual DAG, not instructions buried in a prompt.
2. **Thin agents, thick skills.** Agent configs are ~100 lines. Domain expertise lives in skills.
3. **Deterministic where possible.** Lint, test, and scaffold don't need an LLM.
4. **Labels drive routing.** `lgtm`/`revise`/`escalate` on edges, not in prompts.
5. **Fan-out by default.** Independent tasks run in parallel.
6. **Bounded iteration.** Every loop caps out. Escalation is cheaper than runaway agents.
7. **Zero-read principle.** Coding agents get everything inlined — no file searching.
8. **One human gate.** Machine gates handle structure; you handle judgment.
9. **Backend-agnostic.** Claude, Codex, Cursor — bring your own agent.
10. **Skills are composable.** Swap JIRA for Linear. Swap Confluence for Notion. The pipeline stays the same.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add skills, agents, and pipeline nodes.
