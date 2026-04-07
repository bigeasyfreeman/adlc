# ADLC

Agentic Development Lifecycle.

9 agents. 22 skills. One pipeline. You describe a feature, point it at a repo, and it does the rest: researches the codebase, writes a technical plan, generates code with TDD, runs security review across 5 OWASP domains, and hands you a single PR to review.

```
Idea + Repo → Triage → Research → Plan ↔ Review → Code → QA → Security → PR → You
```

Works with Claude Code, Codex, Cursor, Antigravity, and Factory.

## The Problem

AI coding right now is either "write me a function" (one-shot, no context, no tests) or manually copy-pasting context between agents and hoping they figure out the right order.

ADLC is the structured version. The pipeline is a directed graph. Agents emit labels (`lgtm`, `revise`, `escalate`) and edges route to the next step. Independent tasks fan out in parallel. Lint, test, and scaffold nodes burn zero LLM tokens. Every review loop has a hard cap so agents don't spin forever.

The whole thing is markdown files. Skills are injectable knowledge packets. Agents are thin configs (~100 lines each). You can swap any piece without touching the rest.

Built on patterns from [Attractor](https://github.com/strongdm/attractor), [Stripe Minions](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents), and [Vajra](https://github.com/zamana-inc/vajra).

## Setup

```bash
git clone https://github.com/bigeasyfreeman/adlc.git
cd adlc

./setup.sh claude ~/my-project       # Claude Code
./setup.sh codex ~/my-project        # Codex (OpenAI)
./setup.sh cursor ~/my-project       # Cursor
./setup.sh antigravity ~/my-project  # Antigravity (Google)
./setup.sh factory ~/my-project      # Factory
./setup.sh all ~/my-project          # All platforms
```

| Platform | Skills | Agents | Instructions |
|----------|--------|--------|-------------|
| Claude Code | `.claude/skills/` | `.claude/agents/` | `CLAUDE.md` |
| Codex | `.agents/skills/` | via `AGENTS.md` | `AGENTS.md` |
| Cursor | `.cursor/rules/*.mdc` | `.cursor/rules/*.mdc` | in rules |
| Antigravity | `.agent/skills/` | `agents.md` | in agents.md |
| Factory | `.factory/docs/` | `.factory/droids/` | `AGENTS.md` |

Or just copy the skills you want manually:
```bash
cp -r skills/codebase-research/ ~/my-project/.claude/skills/codebase-research/
```

## Pipeline

Defined in [`WORKFLOW.dot`](WORKFLOW.dot). Visualize it: `dot -Tpng WORKFLOW.dot -o pipeline.png`

```
start → triage → research → plan ↔ plan_review → scaffold → gen_tests →
  context_assembly → code (fan-out) ↔ code_review ↔ fixer → security → qa →
  pr_prep → engineer_review → done
```

**Agent nodes** (blue) are LLM calls with injected skills. **Tool nodes** (dashed) are shell commands that cost nothing. **Fan-out** runs coding tasks in parallel. **Human gate** is your review at the end.

Agents output structured labels. Edges match them:

| Label | What it means |
|-------|--------------|
| `lgtm` | Approved. Next node. |
| `revise` | Back to sender with findings. |
| `escalate` | Human needed. |
| `pass`/`fail` | Deterministic gate. |
| `fixed`/`stuck` | Fixer result. |

Every loop has a cap. Plan review: 3 rounds max. Code review: 3. Fixer: 2. QA: 2. Hit the cap and it escalates to you instead of spinning.

## Agents

| Agent | What it does | Model | Skills loaded |
|-------|-------------|-------|---------------|
| **triage** | Classifies the input, routes or escalates | Sonnet | none |
| **researcher** | Deep codebase analysis, PRD cross-reference | Opus | codebase-research, grafana |
| **planner** | PRD + research into Build Brief (spec/plan/tasks) | Opus | codegen-context, architecture |
| **plan-reviewer** | 6-persona Eval Council | Opus | eval-council |
| **coder** | TDD per task. RED, GREEN, REFACTOR. | Sonnet | tdd-enforcement, debugging |
| **code-reviewer** | Quality + correctness check | Opus | eval-council |
| **fixer** | 4-phase root cause diagnosis and repair | Sonnet | systematic-debugging |
| **security-reviewer** | 5 OWASP domain assessment | Opus | 5 security skills |
| **pr-preparer** | Assembles the final PR package | Sonnet | none |

Each agent is a markdown file with YAML frontmatter. Model, tools, preloaded skills, output labels. That's it.

## Skills

22 markdown files. Each one encodes a specific domain of expertise that gets injected into an agent's context at startup.

**Engineering:**
`codebase-research` (1,237 lines of repo analysis methodology) · `eval-council` (6 judge personas) · `codegen-context` (zero-read prompt assembly) · `tdd-enforcement` · `systematic-debugging` · `architecture-pattern` · `qa-test-data`

**Security (5 OWASP domains):**
`appsec-threat-model` (Top 10 2021) · `llm-security` (LLM Top 10 2025) · `agentic-security` (ASI Top 10) · `api-security` (API Top 10 2023) · `infra-security` (K8s Top 10 2025)

**Integrations (optional):**
`jira-ticket-creation` · `confluence-decomposition` · `slack-orchestration` · `grafana-observability` · `ci-cd-pipeline` · `incident-runbook`

**Product (optional):**
`prd-generation` · `ux-flow-builder` · `figma-integration` · `gong-customer-evidence`

## Customization

**Add a skill.** Create `skills/your-skill/SKILL.md`. Define trigger, input, behavior, output, quality gates. Add it to `manifest.json`.

**Change the pipeline.** Edit `WORKFLOW.dot`. Add nodes, remove nodes, rewire edges. Common variants:
- Skip security for internal tools: remove `security` node, route `code_review` straight to `qa`
- Bugfix pipeline: `triage → research → code → qa → pr_prep`
- Add design review: new node between `plan_review` and `scaffold`

**Switch models.** Edit agent frontmatter:

| Platform | Fast | Deep |
|----------|------|------|
| Claude Code | `sonnet` | `opus` |
| Codex | `o4-mini` | `o3` |
| Antigravity | `gemini-2.5-flash` | `gemini-2.5-pro` |
| Factory | `inherit` | `claude-opus-4-6` |

**Swap integrations.** Skills are composable. Replace `jira-ticket-creation` with a Linear skill. Replace `confluence-decomposition` with Notion. The pipeline doesn't care.

## File Structure

```
adlc/
├── setup.sh               # One-command install for any platform
├── WORKFLOW.dot            # Pipeline graph (Graphviz)
├── WORKFLOW.md             # Agent configs, backends, concurrency
├── agents/                 # 9 agent configs
├── skills/                 # 22 injectable skills
│   └── manifest.json       # Skill + agent registry
├── platform/               # Platform-specific instruction files
│   ├── CLAUDE.md
│   ├── AGENTS.md
│   └── agents-antigravity.md
├── examples/               # Example PRD + walkthrough
├── docs/
│   ├── archive/            # Original monolithic specs (reference)
│   ├── schemas/            # 12 JSON Schema contracts
│   ├── specs/              # 15 runtime behavior specs
│   └── tests/              # 7 test specifications
├── tests/                  # Setup script tests (80 assertions)
└── scripts/
    └── md2pdf.py
```

## Principles

1. **Graph, not prose.** The pipeline is a DOT file you can see, version, and edit. Not instructions buried in a 27K-token prompt.
2. **Thin agents, thick skills.** Agents are ~100 lines. The real knowledge lives in skills.
3. **Deterministic where you can be.** Lint, test, scaffold. Don't burn tokens on predictable work.
4. **Labels drive routing.** `lgtm`/`revise`/`escalate` on graph edges. Not prose inside a prompt.
5. **Fan-out by default.** Independent tasks run in parallel. Serial execution of independent work is a velocity bug.
6. **Cap every loop.** Runaway agents are more expensive than asking a human.
7. **Zero-read principle.** Coding agents get everything inlined. No searching, no guessing.
8. **One human gate.** Machine gates catch structure problems. You catch judgment calls.
9. **Bring your own agent.** Claude, Codex, Cursor, Antigravity, Factory. The skills don't care.
10. **Composable skills.** Swap JIRA for Linear. Swap Confluence for Notion. Pipeline stays the same.

## Acknowledgments

This framework wouldn't exist without the work and thinking of people who influenced it without knowing they did:

- [**Daniel Miessler**](https://github.com/danielmiessler) for PAI and the patterns behind structured agent evaluation, skill composition, and first-principles thinking tools that run through the Eval Council and skill architecture.
- [**Pedram Amini**](https://github.com/pedramamini) for showing what disciplined security engineering looks like when you actually build the systems, not just talk about them. The 5-domain OWASP security review chain exists because of that influence.
- [**Jonathan Haas**](https://github.com/haasonsaas) for relentlessly pushing what's possible with AI agents in practice and demonstrating that the right abstractions make complex systems simple. That philosophy is in every design decision here.

## License

MIT. See [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
