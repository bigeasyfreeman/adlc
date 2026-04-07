# ADLC — Agentic Development Lifecycle

> Ship features with AI agents. From idea to pull request — one engineer review.

**9 agents. 22 skills. One DAG pipeline.**

```
Idea + Repo → Triage → Research → Plan ↔ Review → Code → QA → Security → PR → You ✅
```

ADLC is an open framework for orchestrating AI coding agents through a structured pipeline. Give it a feature description and a codebase — it researches your repo, writes a technical plan, generates code with TDD, runs security review across 5 OWASP domains, and delivers a single pull request for your review.

Works with **Claude Code**, **Codex**, **Cursor**, or any CLI-based coding agent.

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

### Option 1: Use Individual Agents (Simplest)

Pick the agents you need. Each one works standalone.

```bash
# Research your codebase before building
claude --model claude-opus-4-6 -p "$(cat agents/researcher.md)" \
  "Analyze this repo for building a notifications feature. REPO: /path/to/repo"

# Generate a Build Brief from a PRD
claude --model claude-opus-4-6 -p "$(cat agents/planner.md)" \
  "PRD: $(cat my-prd.md) RESEARCH: [paste research output]"

# Review a Build Brief with the Eval Council
claude --model claude-opus-4-6 -p "$(cat agents/plan-reviewer.md)" \
  "BRIEF: [paste brief]"
```

### Option 2: Inject Skills into Your IDE Agent

Copy skills into your Claude Code or Codex project:

```bash
# Claude Code
cp -r skills/ /your/project/.claude/skills/

# Codex
cp -r skills/ /your/project/.codex/skills/
```

Now your coding agent has access to 22 specialized skills — codebase research, TDD enforcement, security review, debugging protocols, and more.

### Option 3: Run the Full Pipeline

```bash
# 1. Triage — classify the task
claude --model claude-sonnet-4-6 -p "$(cat agents/triage.md)" < my-prd.md

# 2. Research — deep codebase analysis
claude --model claude-opus-4-6 -p "$(cat agents/researcher.md)" \
  "PRD: $(cat my-prd.md) REPO: /path/to/repo"

# 3. Plan — generate Build Brief
claude --model claude-opus-4-6 -p "$(cat agents/planner.md)" \
  "PRD: $(cat my-prd.md) RESEARCH: [output from step 2]"

# 4. Review — Eval Council validates the plan
claude --model claude-opus-4-6 -p "$(cat agents/plan-reviewer.md)" \
  "BRIEF: [output from step 3]"

# 5. Code — execute tasks (fan out across tasks)
claude --model claude-sonnet-4-6 -p "$(cat agents/coder.md)" \
  "TASK: [each task from the brief]"

# 6. Review + Fix + Security + QA → PR
# Continue through the pipeline...
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

Edit agent YAML frontmatter:

```yaml
---
model: claude-sonnet-4-6    # Fast + cheap for coding
# model: claude-opus-4-6    # Deep reasoning for planning
# model: o3                  # OpenAI for Codex backend
---
```

### Use Different Backends

ADLC is backend-agnostic. Configure in `WORKFLOW.md`:

```yaml
backends:
  claude:
    command: "claude --model {{ model }} -p {{ prompt | shellquote }}"
  codex:
    command: "codex --model {{ model }} --quiet --prompt {{ prompt | shellquote }}"
  cursor:
    command: "cursor-cli --prompt {{ prompt | shellquote }}"
```

---

## File Structure

```
adlc/
├── WORKFLOW.dot              # Pipeline DAG (Graphviz)
├── WORKFLOW.md               # Configuration
├── README.md
├── CONTRIBUTING.md
├── LICENSE                   # MIT
├── agents/                   # 9 thin agent configs
│   ├── triage.md
│   ├── researcher.md
│   ├── planner.md
│   ├── plan-reviewer.md
│   ├── coder.md
│   ├── code-reviewer.md
│   ├── fixer.md
│   ├── security-reviewer.md
│   └── pr-preparer.md
├── skills/                   # 22 injectable skills
│   ├── manifest.json
│   ├── codebase-research/
│   ├── eval-council/
│   ├── codegen-context/
│   ├── tdd-enforcement/
│   ├── systematic-debugging/
│   └── ... (17 more)
├── examples/
│   ├── README.md
│   └── example-prd.md
├── docs/
│   ├── archive/              # Original monolithic specs (reference)
│   ├── schemas/              # 12 JSON Schema contracts
│   ├── specs/                # 15 runtime behavior specs
│   └── tests/                # 7 test specifications
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
