# ADLC

Agentic Development Lifecycle.

ADLC is a graph-driven framework for turning scoped work into reviewed code. The source tree contains agent configs, skill definitions, deterministic evaluators, and runtime adapter targets. `setup.sh` derives install counts from the repository so the shipped inventory stays truthful as the framework changes.

```
Build Loop:  PRD → Compound Preflight → Graph Research → Brief (Loop Contract + Implementation Interface + Productionization Gate) → Council → Scaffold → LDD → TDD → Code → Comprehension Gate → PR → Learning Capture → You
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
./setup.sh antigravity ~/my-project  # Antigravity
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

`setup.sh` also installs a target-repo wrapper at `.adlc/bin/adlc`. The wrapper
sets `ADLC_ROOT` back to this checkout and runs the deterministic ADLC CLI, so a
target repo can validate schemas, readiness, Loop Contracts, and MCP tool
metadata without copying the runtime source.

The shipped usage path is the runtime CLI plus installed agents/skills. Repo-local
goal prompts or decomposition scratch files are not required to install or run ADLC.

Runtime preflight:

```bash
python3 -m pip install -e .
bin/adlc health-check --json
bin/adlc ci --json
~/my-project/.adlc/bin/adlc health-check --json
```

## Pipeline

### Current Operating Model

ADLC now operates as an LLM-driven development system with deterministic control gates. The LLM still performs the judgment-heavy work: triage, research synthesis, planning, code generation, review, and repair. ADLC constrains those actions with schemas, verifier contracts, readiness checks, test-selection gates, workflow state, and explicit escalation rules.

The shipped framework layers are:

| Layer | What It Gives ADLC | How It Is Used |
|---|---|---|
| Compound engineering | Prior verified work, task refs, verifier refs, resume context, and graph status as compact context | `bin/adlc compound-context` before research |
| Scalable code primitives | Construct refs, paved-road reuse, intent contracts, production invariants, and verifiability | Build Brief task fields and Eval Council checks |
| Implementation Interface | Task-scoped contract for what a change reuses, consumes, emits, preserves, integrates with, and validates | Active when a task touches repo boundaries, schemas, emitters, providers, workflow state, CLI contracts, or reusable framework surfaces |
| Productionization Gate | Bounded production claim with Coverage State, evidence, rollback/observability/security posture, reliability risks, and No-Overclaim boundaries | Active when a task claims production support or production readiness |
| Slop Quality Gate | Output-side benchmark, threshold, eval cases, and failure action for generated-output surfaces | Active when a task changes prompt/model/agent/generated content behavior |
| Loop Contract | LLM action-loop contract: job, win condition, allowed tools, real feedback, required tests, progress, control channel, safe checkpoint, independent truth, escalation, and optional `budget_guard` evidence | Active when a task delegates decisions, tool use, test selection, retry/repair, escalation, or maturity claims to an LLM loop |

The current truthful maturity state is **assisted loop**. ADLC has a directed workflow, deterministic validators, retry caps, workflow state, compound context, readiness gates, test-strength checks, Loop Contract admission gates, and execution-backed required-test evidence when `loop-test-result` artifacts are supplied. A workflow only earns **self-autonomous** status when `bin/adlc loop-maturity-audit` scores it robustly, with no weak score on win condition rigor, non-gameable test selection, failure handling, or budget evidence. Missing, stale, warning, alert, or exhausted `budget_status` blocks `self_autonomous`; healthy local budget evidence is necessary but not sufficient. Tag-only Loop Contract coverage is intentionally capped below robust.

What is automatic today:

- schema validation for Build Briefs, workflow state, agent outputs, Loop Contracts, Loop Actions, and maturity reports
- readiness blocking through `emit-work-items --require-ready`
- generated-output slop gate checks when a generated-output surface is active
- implementation-interface and productionization overclaim checks
- Loop Contract test-selection, action-admission, and maturity-audit CLI/MCP tools
- deterministic `loop-budget-check` CLI/MCP budget guard for LLM-backed Loop Actions
- strict Loop Contract required-test proof through `docs/schemas/loop-test-result.schema.json` and `loop-test-selection --require-test-results`
- schema-backed work queue status, task claims, completion/block/escalation state, dirty-checks, file-overlap checks, and worktree prepare/status/cleanup dry-runs
- runtime preflight through `bin/adlc health-check --json`
- resume summaries for task fingerprints, loop progress, no-progress count, control events, safe checkpoints, and escalation context

What is still explicit:

- Loop Contracts are activated by task/workflow surface evidence; ADLC does not force them onto deterministic docs, lint, or build-validation work.
- LLM runtime invocation still goes through the selected adapter: Claude, Codex, Cursor, Antigravity, or Factory.
- Live process kill switches and provider-specific rollback are not claimed by default; state-level steer, abort, interrupt, escalate, safe checkpoint, and rollback notes are the current supported control model.
- Full self-autonomy is a per-workflow evidence claim, not the default framework claim.

### Build Loop

```
start → triage → compound_preflight (learning refs + resume context) → research (Graphify/Beads-aware) → plan ↔ plan_review → scaffold → gen_tests →
  context_assembly → code (fan-out) ↔ code_review (comprehension gate) ↔ fixer →
  [security if active] → qa → [test_strength if active] → [slop_gate if generated-output active] →
  pr_prep → [learning_capture if verified reusable learning exists] → engineer_review → done
```

Overlay gates are driven by the Build Brief `applicability_manifest` and task
surface evidence. Implementation Interface contracts and Productionization Gate
claims are optional Build Brief layers; they activate when repo integration or
production-ready claims are in scope. Loop Contracts activate when ADLC delegates
decisions, tool use, test selection, retry/repair, escalation, or maturity claims
to an LLM-driven loop. Inactive overlays are skipped or recorded as explicit
no-ops; they are not filler sections every task must satisfy.
`compound_preflight` also no-ops explicitly when `docs/solutions` or
`graphify-out` is missing, so new repos do not pay setup tax before research.

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
bin/adlc ci --json
bash tests/test_adlc_contracts.sh
bash tests/backtest/run_backtest.sh
ADLC_RUNTIME=codex ADLC_SMOKE_SETTINGS_CODEX=~/path/to/config.toml SMOKE=1 MODEL=gpt-5-codex bash tests/smoke/run_smoke.sh
```

Agent-native discovery and validation:

```bash
bin/adlc list-agents --json
bin/adlc list-phases --json
bin/adlc health-check --json
bin/adlc ci --json
bin/adlc validate-artifact --schema build-brief --input .adlc/build_brief.json --json
bin/adlc run --brief-id BRF-123 --workspace . --dry-run --json
bin/adlc run-phase triage --brief-id BRF-123 --workspace . --dry-run --json
bin/adlc run-phase context_assembly --build-brief .adlc/build_brief.json --workspace . --json
bin/adlc run-phase qa --workspace . --verifier 'pytest tests/test_task.py' --json
bin/adlc resume-workflow --workspace . --json
bin/adlc compound-context --workspace . --build-brief .adlc/build_brief.json --json
bin/adlc action-admit --tool-registry .adlc/tool_registry.json --tool Read --action read_file --phase research --brief-id BRF-123 --run-id ADLC-RUN-123 --session-id SESSION-123 --json
bin/adlc loop-test-selection --loop-contract docs/loop-contracts/task.json --test-plan .adlc/test_plan.json --json
bin/adlc loop-test-selection --loop-contract docs/loop-contracts/task.json --test-plan .adlc/test_plan.json --require-test-results .adlc/loop_test_result.json --json
bin/adlc loop-budget-check --token-budget .adlc/token_budget.json --estimated-input-tokens 2000 --expected-output-tokens 4000 --phase phase_5_codegen_context --skill codegen-context --json
bin/adlc loop-action-validate --loop-contract docs/loop-contracts/task.json --action .adlc/loop_action.json --state .adlc/workflow_state.json --json
bin/adlc loop-maturity-audit --loop-contract docs/loop-contracts/task.json --workflow WORKFLOW.dot --state .adlc/workflow_state.json --test-plan .adlc/test_plan.json --test-results .adlc/loop_test_result.json --token-budget .adlc/token_budget.json --json
bin/adlc emit-work-items --target linear --build-brief .adlc/build_brief.json --dry-run --json
bin/adlc sync-work-item --build-brief .adlc/build_brief.json --target linear --state .adlc/workflow_state.json --dry-run --json
bin/adlc queue-status --queue .adlc/work_queue.json --json
bin/adlc queue-claim --queue .adlc/work_queue.json --task-id TASK-123 --state .adlc/workflow_state.json --workspace . --dry-run --json
bin/adlc queue-complete --queue .adlc/work_queue.json --task-id TASK-123 --state .adlc/workflow_state.json --evidence .adlc/loop_test_result.json --dry-run --json
bin/adlc queue-block --queue .adlc/work_queue.json --task-id TASK-123 --reason file_collision --next-action 'split file ownership' --dry-run --json
bin/adlc queue-escalate --queue .adlc/work_queue.json --task-id TASK-123 --reason human_review_required --next-action 'review architecture boundary' --dry-run --json
bin/adlc worktree-prepare --queue .adlc/work_queue.json --task-id TASK-123 --workspace . --dry-run --json
bin/adlc worktree-status --queue .adlc/work_queue.json --workspace . --json
bin/adlc worktree-cleanup --queue .adlc/work_queue.json --task-id TASK-123 --workspace . --dry-run --json
bin/adlc mcp-tools --json
bin/adlc mcp-serve
```

Queue and worktree operations are dry-run first. Mutating queue state or creating/removing worktrees requires `--allow-mutation` plus a tool-registry admission path for `adlc-queue` or `adlc-worktree`. Claims fail closed when the checkout is dirty or when expected file, directory, or glob ownership overlaps an active `claimed` or `running` task.

Deterministic tool nodes emit schema-backed phase artifacts under `.adlc/outputs/` and workflow state records them in `phase_artifacts[]`. Dry-run tool-node calls produce `planned` artifacts without marking the phase complete. Mutating tool-node writes require `--allow-mutation` and `--tool-registry`.

Minimal Loop Contract flow:

```bash
bin/adlc validate-artifact --schema loop-contract --input docs/loop-contracts/task.json --json
bin/adlc loop-test-selection --loop-contract docs/loop-contracts/task.json --test-plan .adlc/test_plan.json --json
bin/adlc validate-artifact --schema loop-test-result --input .adlc/loop_test_result.json --json
bin/adlc loop-test-selection --loop-contract docs/loop-contracts/task.json --test-plan .adlc/test_plan.json --require-test-results .adlc/loop_test_result.json --json
bin/adlc validate-artifact --schema token-budget --input .adlc/token_budget.json --json
bin/adlc loop-budget-check --token-budget .adlc/token_budget.json --estimated-input-tokens 2000 --expected-output-tokens 4000 --phase phase_5_codegen_context --skill codegen-context --json
bin/adlc validate-artifact --schema loop-action --input .adlc/loop_action.json --json
bin/adlc loop-action-validate --loop-contract docs/loop-contracts/task.json --action .adlc/loop_action.json --state .adlc/workflow_state.json --token-budget .adlc/token_budget.json --json
bin/adlc loop-maturity-audit --loop-contract docs/loop-contracts/task.json --workflow WORKFLOW.dot --state .adlc/workflow_state.json --test-plan .adlc/test_plan.json --test-results .adlc/loop_test_result.json --action .adlc/loop_action.json --token-budget .adlc/token_budget.json --json
```

Public-repo hygiene is intentional:

- auth examples use placeholders only
- runtime credentials are read from env vars or local settings files, never committed
- smoke runs write ephemeral stage logs under `tests/smoke/artifacts/`; the tracked golden file is the summary report only

## Agents

| Agent | Job | Model | Skills |
|-------|-----|-------|--------|
| **triage** | Classify, route, or escalate | Sonnet | none |
| **researcher** | Graph-backed codebase analysis, learning refs, PRD cross-reference, dark-code risk notes | Opus | graph-research, codebase-research, paved-road-registry, dark-code-audit, grafana |
| **planner** | PRD + research into an applicability-aware Build Brief | Opus | graph-research, codegen-context, architecture, reuse-analysis, paved-road-registry, context-layers |
| **plan-reviewer** | 6-persona Eval Council with Gate 0 pre-checks | Opus | eval-council |
| **test-author** | Authors failing verifier tests from Brief | Sonnet | spec-to-tests, tdd-enforcement, qa-test-data |
| **coder** | Verifier-led execution per task class | Sonnet | tdd-enforcement, systematic-debugging |
| **code-reviewer** | Quality, correctness, and comprehension review | Opus | eval-council, graph-research, paved-road-registry, comprehension-gate |
| **fixer** | 4-phase root cause, then fix | Sonnet | systematic-debugging, fix-loop |
| **security-reviewer** | STRIDE + 5 OWASP domains + OWASP Top 10 | Opus | security-review + 5 domain skills |
| **pr-preparer** | Final PR package with DoD checklist and learning candidates | Sonnet | learning-capture |
| **PRD Agent** | Non-installable reference doc for structured discovery and repo-aware reuse/debt framing | Opus | prd-generation |
| **Build Brief Agent** | Non-installable reference doc for applicability-aware brief generation | Opus | codegen-context, architecture, reuse-analysis |

Markdown file. YAML frontmatter. Model, tools, skills, labels. Done.

## Skills

Skill definitions are injected into agents at startup. Runtime install counts are derived by `setup.sh` rather than hardcoded in docs.

**Core Engineering:**
`graph-research` (Graphify/Beads-aware evidence) · `codebase-research` · `paved-road-registry` (repo-local approved build paths) · `dark-code-audit` · `context-layers` · `comprehension-gate` · `eval-council` (6 personas + Gate 0) · `codegen-context` (zero-read assembly) · `tdd-enforcement` · `ldd-enforcement` (lint gate before TDD) · `systematic-debugging` · `architecture-pattern` · `qa-test-data` · `reuse-analysis` · `learning-capture` · `learning-refresh` · `definition-of-done` (22-check DoD) · `spec-to-tests` (failing-test authoring from Brief, with Loop Contract coverage tags and execution evidence when active)

**Security:**
`security-review` (STRIDE + OWASP Top 10) · `appsec-threat-model` · `llm-security` · `agentic-security` · `api-security` · `infra-security`

**Quality & Observability:**
`stop-slop` (generated-output contract + optional project eval loop) · `slop-judge` (rubric score + threshold) · `observability-contract` (structured logging mandate) · `feedback-loop` (case promotion + skill self-improvement)

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
| 13 | Comprehension Context (module manifests, behavioral contracts, decision logs) | When modules, interfaces, state, ownership, or dark-code hotspots are active |
| 14 | Graph Research Evidence (Graphify freshness, Beads task memory, direct verification) | Always when repo context is available |
| 15 | Open Items | Always |
| 16 | Implementation Interfaces (reuse, consumes, emits, invariants, integration points, validation gates) | When integration or reusable framework surfaces are active |
| 17 | Productionization Gates (Coverage State, Validation Evidence, No-Overclaim, rollback/observability/security posture) | When a task makes or changes a production support claim |
| 18 | Revision History (council finding IDs → changes) | Always |

Every task requires: files_to_create/modify, reference_impl, dependencies, `task_classification`, `verification_spec`, failure modes, and enough acceptance criteria to define the verifier contract. Tasks that touch integration boundaries should carry an `implementation_interface_contract`; tasks that claim `production_ready` must carry a `productionization_gate` with validation evidence and no-overclaim boundaries. Tasks that introduce or change LLM-driven loop behavior should carry a Loop Contract and the deterministic loop verifier commands that prove required tests, action admission, progress/control state, and maturity verdicts.

Loop Contracts are task/workflow control artifacts, not a required Build Brief section for every task. Emit them as referenced JSON artifacts through `work_item_metadata.loop_contract_path`, `loop_action_path`, and `loop_maturity_report_path` when an LLM-driven loop surface is active.

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
| Antigravity | `inherit` | `inherit` |
| Factory | `inherit` | `claude-opus-4-6` |

**Swap integrations.** Work-item emitters (`jira-ticket-creation`, `github-issue-creation`, `linear-ticket-creation`) and document emitters (`confluence-decomposition`, `notion-decomposition`) share the emitter contract in `docs/specs/emitter-contract.md` and are intended to run through locally installed MCP providers.

## Structure

```
adlc/
├── setup.sh               # One-command install
├── WORKFLOW.dot            # Pipeline graph
├── WORKFLOW.md             # Config
├── agents/                 # Source agent configs plus non-installable reference docs
├── skills/                 # Skill definitions + manifest.json
├── platform/               # CLAUDE.md, AGENTS.md, agents-antigravity.md
├── examples/               # Example PRD
├── docs/                   # build-briefs/, schemas/, specs/, tests/, adlc-v2-spec, tickets
├── docs/solutions/         # Schema-validated compound engineering learning store
├── tests/                  # contract checks, backtests, smoke harness
└── scripts/                # stable CLI entrypoint, adlc_runtime package, and validation utilities
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
- [`docs/specs/graph-research-and-comprehension.md`](docs/specs/graph-research-and-comprehension.md) — Graphify, Beads, context-layer, and comprehension-gate contract
- [`docs/specs/scalable-ai-code-primitives.md`](docs/specs/scalable-ai-code-primitives.md) — Graph-backed context, paved-road reuse, verifiability, and production invariant contract
- [`docs/specs/implementation-interfaces-and-productionization.md`](docs/specs/implementation-interfaces-and-productionization.md) — Implementation Interface, Productionization Gate, Coverage State, and No-Overclaim contract
- [`docs/specs/loop-system-maturity-audit.md`](docs/specs/loop-system-maturity-audit.md) — Loop Contract, LLM Action Envelope, non-gameable test selection, control channel, and maturity audit contract
- [`docs/specs/slop-eval-loop.md`](docs/specs/slop-eval-loop.md) — Output-side slop benchmark, threshold, regression, and case-promotion contract
- [`docs/specs/compound-engineering-learning-store.md`](docs/specs/compound-engineering-learning-store.md) — `docs/solutions` learning-entry schema, capture, refresh, and preflight contract
- [`docs/adlc-v2-tickets.md`](docs/adlc-v2-tickets.md) — 58-ticket implementation roadmap

## Acknowledgments

- [**Daniel Miessler**](https://github.com/danielmiessler) for providing a framework that everyone in the AI ecosystem has benefitted from. From prompting to learning to scaling and building systems, you have pushed this industry for the better.
- [**Pedram Amini**](https://github.com/pedramamini) for [Maestro](https://github.com/Maestro-AI/maestro) and the way it showed people what orchestrated AI agents could actually look like in practice. That work helped a lot of us see the path.
- [**Jonathan Haas**](https://github.com/haasonsaas) for being relentless about what is possible with AI, pushing me every day, and figuring out the right abstractions. You see the line through the fog as if you are the investor, the owner, the product manager, and the consumer.

## License

MIT. See [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
