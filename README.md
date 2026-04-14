# ADLC

Agentic Development Lifecycle.

ADLC is a graph-driven framework for turning scoped work into reviewed code. The source tree contains agent configs, skill definitions, deterministic evaluators, and runtime adapter targets. `setup.sh` derives install counts from the repository so the shipped inventory stays truthful as the framework changes.

```
Build Loop:  PRD → Research → Brief → Council → Scaffold → LDD → TDD → Code → Council → PR → You
Fix Loop:    Capture → Confirm → Investigate → Fix → Prove → Council → PR
Feedback:    Human edits → Diff capture → Pattern distill → Skill update
```

Works with Claude Code, Codex, Cursor, Antigravity, and Factory.

## Why This Exists

Most AI coding is either "write me a function" or manually shuttling context between agents and praying they figure out the order. One is too dumb. The other is you doing the orchestration by hand, which defeats the point.

ADLC is a directed graph. Agents emit labels (`lgtm`, `revise`, `escalate`). Edges route to the next step. Independent tasks fan out in parallel. Lint, test, and scaffold/planning nodes burn zero tokens. Every review loop caps out so nothing spins forever.

The whole thing is markdown. Skills are injectable knowledge. Agents are thin configs. Swap any piece without touching the rest.

### Governing Philosophy

**Bitter Lesson Engineering:** Specify outcomes and constraints, never procedures. Invest in verification (tests, linters, security scans, councils), not guidance (step-by-step instructions).

**Bitter Pilled Engineering:** Every structural decision must be anti-fragile to smarter models. Gates test outcomes, not process. Quarterly audit: "What structure can we remove because models no longer need it?"

**Skills as Actions:** Skills are contextual behaviors, not static prompts. They activate by context, chain into sequences, and self-improve via feedback loops.

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

### Build Loop

```
start → triage → research → prd → plan ↔ plan_review → scaffold → gen_tests →
  ldd_gate → context_assembly → code (fan-out) ↔ code_review ↔ fixer →
  security → qa → test_strength → slop_gate → pr_prep → engineer_review → done
```

### Fix Loop (parallel)

```
error_capture → confirm → investigate → fix → prove → light_council → pr
```

### Feedback Loop (nightly)

```
human_edits → diff_capture → pattern_distill → skill_update
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
| `blocked` | Council blocked. Human decision required. |

Every loop caps. Plan review: 3. Code review: 3. Fixer: 2. QA: 2. Hit the wall and it comes to you.

## Verification

The repo ships with three verification layers:

- `tests/test_adlc_contracts.sh` checks prompt/schema/runtime wiring and the checked-in golden artifacts.
- `tests/backtest/run_backtest.sh` replays the deterministic evaluators against the benchmark fixture set.
- `tests/smoke/run_smoke.sh` runs the real staged agents through a tiny repo using the selected runtime adapter.

Typical verification flow:

```bash
bash tests/test_adlc_contracts.sh
bash tests/backtest/run_backtest.sh
ADLC_RUNTIME=codex ADLC_SMOKE_SETTINGS_CODEX=~/path/to/config.toml SMOKE=1 MODEL=gpt-5-codex bash tests/smoke/run_smoke.sh
```

Public-repo hygiene is intentional:

- auth examples use placeholders only
- runtime credentials are read from env vars or local settings files, never committed
- smoke runs write ephemeral stage logs under `tests/smoke/artifacts/`; the tracked golden file is the summary report only

## Agents

| Agent | Job | Model | Skills |
|-------|-----|-------|--------|
| **triage** | Classify, route, or escalate | Sonnet | none |
| **researcher** | Codebase analysis, PRD cross-reference | Opus | codebase-research, grafana |
| **planner** | PRD + research into an applicability-aware Build Brief | Opus | codegen-context, architecture, security-review |
| **plan-reviewer** | 6-persona Eval Council with Gate 0 pre-checks | Opus | eval-council |
| **test-author** | Authors failing verifier tests from Brief | Sonnet | spec-to-tests, tdd-enforcement, qa-test-data |
| **coder** | LDD then verifier-led execution per task class | Sonnet | tdd-enforcement, ldd-enforcement, debugging |
| **code-reviewer** | Quality, correctness, and security | Opus | eval-council, security-review |
| **fixer** | 4-phase root cause, then fix | Sonnet | systematic-debugging, fix-loop |
| **security-reviewer** | STRIDE + 5 OWASP domains + OWASP Top 10 | Opus | security-review + 5 domain skills |
| **pr-preparer** | Final PR package with DoD checklist | Sonnet | definition-of-done, stop-slop |
| **PRD Agent** | Structured discovery, 3-5 turns, extract-first | Opus | prd-generation |
| **Build Brief Agent** | Applicability-aware brief with core baseline and active overlays | Opus | codegen-context, architecture, security-review, reuse-analysis |

Markdown file. YAML frontmatter. Model, tools, skills, labels. Done.

## Skills

Skill definitions are injected into agents at startup. Runtime install counts are derived by `setup.sh` rather than hardcoded in docs.

**Core Engineering:**
`codebase-research` · `eval-council` (6 personas + Gate 0) · `codegen-context` (zero-read assembly) · `tdd-enforcement` · `ldd-enforcement` (lint gate before TDD) · `systematic-debugging` · `architecture-pattern` · `qa-test-data` · `reuse-analysis` · `definition-of-done` (22-check DoD) · `spec-to-tests` (failing-test authoring from Brief)

**Security:**
`security-review` (STRIDE + OWASP Top 10) · `appsec-threat-model` · `llm-security` · `agentic-security` · `api-security` · `infra-security`

**Quality & Observability:**
`stop-slop` (code + content dual-mode) · `observability-contract` (structured logging mandate) · `feedback-loop` (skill self-improvement)

**Lifecycle:**
`fix-loop` (autonomous error repair) · `fix-bug` (fix orchestration) · `build-feature` (build orchestration) · `ship-content` (content orchestration) · `execute-trade` (trade orchestration)

**Integrations (optional):**
`jira-ticket-creation` · `github-issue-creation` · `linear-ticket-creation` · `confluence-decomposition` · `notion-decomposition` · `slack-orchestration` · `grafana-observability` · `ci-cd-pipeline` · `incident-runbook`

**Product (optional):**
`prd-generation` · `ux-flow-builder` · `figma-integration` · `gong-customer-evidence`

## Build Brief Template (v2)

The Build Brief Agent produces a brief with an `applicability_manifest`, a core baseline, and only the overlays the task actually activates.

| # | Section | Required |
|---|---------|----------|
| 1 | Overview | Always |
| 2 | What Changes (capabilities + behavior changes) | Always |
| 3 | Architecture & Patterns (existing patterns + new components) | Always |
| 4 | Data Model Changes [C] | If project has persistent storage |
| 5 | API Changes [C] | If project has endpoints |
| 6 | Security Review (STRIDE + concern/mitigation table) | When the security overlay is active |
| 7 | Failure Modes (failure/impact/mitigation) | Always |
| 8 | SLOs & Performance (latency, error rate, performance budgets) | When observability or performance overlays are active |
| 9 | Task Breakdown (per-task: files, refs, deps, G/W/T, manual tests) | Always |
| 10 | Compatibility & Resilience (backwards, forward, availability, degradation) | When interface, integration, or rollout overlays are active |
| 11 | G/W/T Roll-Up (full test plan) | Always |
| 12 | Skill Handoffs | Always |
| 13 | Open Items | Always |
| 14 | Revision History (council finding IDs → changes) | Always |

Every task requires: files_to_create/modify, reference_impl, dependency_ids, `task_classification`, `verification_spec`, failure modes, and enough acceptance criteria to define the verifier contract.

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

**Swap integrations.** Work-item emitters (`jira-ticket-creation`, `github-issue-creation`, `linear-ticket-creation`) and document emitters (`confluence-decomposition`, `notion-decomposition`) share the emitter contract in `docs/specs/emitter-contract.md` and are intended to run through locally installed MCP providers.

## Structure

```
adlc/
├── setup.sh               # One-command install
├── WORKFLOW.dot            # Pipeline graph
├── WORKFLOW.md             # Config
├── agents/                 # Source agent configs (includes legacy pointers)
├── skills/                 # Skill definitions + manifest.json
├── platform/               # CLAUDE.md, AGENTS.md, agents-antigravity.md
├── examples/               # Example PRD
├── docs/                   # build-briefs/, schemas/, specs/, tests/, adlc-v2-spec, tickets
├── tests/                  # contract checks, backtests, smoke harness
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
10. **Composable.** Swap work-item or document emitters without changing the Build Brief task schema.
11. **Security baked in, not bolted on.** STRIDE and OWASP activate when the task touches a real security surface.
12. **BLE-compliant.** Specify outcomes, not procedures. Design for removal as models improve.

## Docs

- [`docs/adlc-v2-specification.md`](docs/adlc-v2-specification.md) — Full ADLC v2 spec (philosophy, pipeline, cross-cutting concerns)
- [`docs/adlc-v2-tickets.md`](docs/adlc-v2-tickets.md) — 58-ticket implementation roadmap

## Acknowledgments

- [**Daniel Miessler**](https://github.com/danielmiessler) for providing a framework that everyone in the AI ecosystem has benefitted from. From prompting to learning to scaling and building systems, you have pushed this industry for the better.
- [**Pedram Amini**](https://github.com/pedramamini) for [Maestro](https://github.com/Maestro-AI/maestro) and the way it showed people what orchestrated AI agents could actually look like in practice. That work helped a lot of us see the path.
- [**Jonathan Haas**](https://github.com/haasonsaas) for being relentless about what is possible with AI, pushing me every day, and figuring out the right abstractions. You see the line through the fog as if you are the investor, the owner, the product manager, and the consumer.

## License

MIT. See [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
