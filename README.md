# ADLC

Agentic Development Lifecycle.

9 agents. 22 skills. One pipeline. Describe a feature, point it at a repo, get back a PR. It researches the codebase, writes a technical plan, generates code with TDD, runs security across 5 OWASP domains, and hands you one pull request.

```
Idea + Repo → Triage → Research → Plan ↔ Review → Code → QA → Security → PR → You
```

Works with Claude Code, Codex, Cursor, Antigravity, and Factory.

## Why This Exists

Most AI coding is either "write me a function" or manually shuttling context between agents and praying they figure out the order. One is too dumb. The other is you doing the orchestration by hand, which defeats the point.

ADLC is a directed graph. Agents emit labels (`lgtm`, `revise`, `escalate`). Edges route to the next step. Independent tasks fan out in parallel. Lint, test, and scaffold nodes burn zero tokens. Every review loop caps out so nothing spins forever.

The whole thing is markdown. Skills are injectable knowledge. Agents are thin configs. Swap any piece without touching the rest.

Patterns borrowed from [Attractor](https://github.com/strongdm/attractor), [Stripe Minions](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents), and [Vajra](https://github.com/zamana-inc/vajra).

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

Or copy what you need by hand:
```bash
cp -r skills/codebase-research/ ~/my-project/.claude/skills/codebase-research/
```

## Pipeline

Defined in [`WORKFLOW.dot`](WORKFLOW.dot). Render it: `dot -Tpng WORKFLOW.dot -o pipeline.png`

```
start → triage → research → plan ↔ plan_review → scaffold → gen_tests →
  context_assembly → code (fan-out) ↔ code_review ↔ fixer → security → qa →
  pr_prep → engineer_review → done
```

Agent nodes are LLM calls with injected skills. Tool nodes are shell commands. Zero tokens. Fan-out runs coding tasks in parallel. Human gate is you at the end.

Labels drive routing:

| Label | Meaning |
|-------|---------|
| `lgtm` | Approved. Next. |
| `revise` | Back with findings. |
| `escalate` | Human needed. |
| `pass`/`fail` | Deterministic. |
| `fixed`/`stuck` | Fixer result. |

Every loop caps. Plan review: 3. Code review: 3. Fixer: 2. QA: 2. Hit the wall and it comes to you.

## Agents

| Agent | Job | Model | Skills |
|-------|-----|-------|--------|
| **triage** | Classify, route, or escalate | Sonnet | none |
| **researcher** | Codebase analysis, PRD cross-reference | Opus | codebase-research, grafana |
| **planner** | PRD + research into Build Brief | Opus | codegen-context, architecture |
| **plan-reviewer** | 6-persona Eval Council | Opus | eval-council |
| **coder** | TDD per task. RED. GREEN. REFACTOR. | Sonnet | tdd-enforcement, debugging |
| **code-reviewer** | Quality and correctness | Opus | eval-council |
| **fixer** | 4-phase root cause, then fix | Sonnet | systematic-debugging |
| **security-reviewer** | 5 OWASP domains | Opus | 5 security skills |
| **pr-preparer** | Final PR package | Sonnet | none |

Markdown file. YAML frontmatter. Model, tools, skills, labels. Done.

## Skills

22 markdown files. Domain expertise injected into agents at startup.

**Engineering:**
`codebase-research` (1,237 lines) · `eval-council` (6 judge personas) · `codegen-context` (zero-read prompt assembly) · `tdd-enforcement` · `systematic-debugging` · `architecture-pattern` · `qa-test-data`

**Security (5 OWASP domains):**
`appsec-threat-model` (Top 10 2021) · `llm-security` (LLM Top 10 2025) · `agentic-security` (ASI Top 10) · `api-security` (API Top 10 2023) · `infra-security` (K8s Top 10 2025)

**Integrations (optional):**
`jira-ticket-creation` · `confluence-decomposition` · `slack-orchestration` · `grafana-observability` · `ci-cd-pipeline` · `incident-runbook`

**Product (optional):**
`prd-generation` · `ux-flow-builder` · `figma-integration` · `gong-customer-evidence`

## Customization

**Add a skill.** `skills/your-skill/SKILL.md`. Trigger, input, behavior, output, quality gates. Add to `manifest.json`.

**Change the pipeline.** Edit `WORKFLOW.dot`. Add nodes, kill nodes, rewire edges.
- Internal tools: cut the `security` node, route `code_review` straight to `qa`
- Bugfix mode: `triage → research → code → qa → pr_prep`
- Design review: new node between `plan_review` and `scaffold`

**Switch models:**

| Platform | Fast | Deep |
|----------|------|------|
| Claude Code | `sonnet` | `opus` |
| Codex | `o4-mini` | `o3` |
| Antigravity | `gemini-2.5-flash` | `gemini-2.5-pro` |
| Factory | `inherit` | `claude-opus-4-6` |

**Swap integrations.** Replace `jira-ticket-creation` with Linear. Replace `confluence-decomposition` with Notion. Pipeline doesn't care.

## Structure

```
adlc/
├── setup.sh               # One-command install
├── WORKFLOW.dot            # Pipeline graph
├── WORKFLOW.md             # Config
├── agents/                 # 9 agents
├── skills/                 # 22 skills + manifest.json
├── platform/               # CLAUDE.md, AGENTS.md, agents-antigravity.md
├── examples/               # Example PRD
├── docs/                   # schemas/, specs/, tests/, archive/
├── tests/                  # 80 assertions
└── scripts/                # md2pdf.py
```

## Principles

1. **Graph, not prose.** DOT file you can see and edit. Not a 27K-token prompt.
2. **Thin agents, thick skills.** Agents are ~100 lines. Knowledge lives in skills.
3. **Deterministic where you can be.** Lint, test, scaffold. Zero tokens for predictable work.
4. **Labels on edges.** Routing logic lives in the graph, not in agent prompts.
5. **Fan-out by default.** Serial execution of independent work is a velocity bug.
6. **Cap every loop.** Runaway agents cost more than asking a human.
7. **Zero-read.** Coding agents get everything inlined. No searching. No guessing.
8. **One human gate.** Machines catch structure. You catch judgment.
9. **Bring your own agent.** Claude, Codex, Cursor, Antigravity, Factory. Skills don't care.
10. **Composable.** Swap JIRA for Linear. Swap Confluence for Notion. Same pipeline.

## Acknowledgments

- [**Daniel Miessler**](https://github.com/danielmiessler) for providing a framework that everyone in the AI ecosystem has benefitted from. From prompting to learning to scaling and building systems, you have pushed this industry for the better.
- [**Pedram Amini**](https://github.com/pedramamini) for [Maestro](https://github.com/Maestro-AI/maestro) and the way it showed people what orchestrated AI agents could actually look like in practice. That work helped a lot of us see the path.
- [**Jonathan Haas**](https://github.com/haasonsaas) for being relentless about what is possible with AI, pushing me every day, and figuring out the right abstractions. You see the line through the fog as if you are the investor, the owner, the product manager, and the consumer.

## License

MIT. See [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
