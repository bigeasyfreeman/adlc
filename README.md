# ADLC

[![CI](https://github.com/bigeasyfreeman/adlc/actions/workflows/ci.yml/badge.svg)](https://github.com/bigeasyfreeman/adlc/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Agentic Development Lifecycle.

ADLC is an agent control plane for AI-assisted engineering. It packages skills, agents, schemas, verifiers, queue/worktree primitives, loop templates, learning memory, and a bounded meta-harness planner so an LLM or external harness can turn repo, ticket, and signal input into reviewed work without relying on ad hoc prompt chains.

The shipped framework is intentionally evidence-bound: ADLC can propose, plan, queue, isolate, verify, synchronize, and learn from work, but mutation, merge, deploy, architecture decisions, and irreversible external actions stay behind deterministic gates and human approval.

```
Signal Loop: repo/ticket/signal → candidate ranking → loop template → queue/worktree → verifier → human review
Build Loop:  PRD → compound preflight → graph research → conventions → brief → council → scaffold → tests → code → QA → PR hygiene → PR
Fix Loop:    capture → confirm → investigate → conventions → fix → prove → council → PR hygiene → PR
Feedback:    human edits + maintainer PR comments → diff capture → pattern distill → skill, convention, vocabulary, or memory update
```

Claude Code and Codex have implemented runtime adapters; live conformance is
still pending. Cursor, Antigravity, and Factory adapters are experimental and
fail closed until their invocation surfaces are verified.
Current support claims and the evidence required to change them are recorded in
[`docs/evidence/provider-conformance/`](docs/evidence/provider-conformance/README.md).

## Why This Exists

AI coding stops scaling when the human remains the inner prompter. ADLC moves the leverage point to the control plane: what work is admissible, which loop should run, what context is allowed, which tools may act, how evidence is checked, where state is recorded, and when a human must decide.

ADLC is a directed graph plus a schema-backed CLI/MCP runtime. Agents emit labels (`lgtm`, `revise`, `escalate`). Edges route to the next step. Independent work can be queued and isolated in worktrees. Lint, test, scaffold, readiness, budget, and contract checks burn zero model tokens. Retry edges carry runtime-enforced caps in `WORKFLOW.dot`; `--max-phases` separately bounds each invocation.

The framework stays composable. Skills are injectable knowledge, agents are thin configs, contracts are Markdown plus JSON, and deterministic tool nodes fail closed before a harness can mutate state.

### Governing Philosophy

**Bitter Lesson Engineering:** Specify outcomes and constraints, never procedures. Invest in verification (tests, linters, security scans, councils), not guidance (step-by-step instructions).

**Bitter Pilled Engineering:** Every structural decision must be anti-fragile to smarter models. Gates test outcomes, not process. Quarterly audit: "What structure can we remove because models no longer need it?"

**Skills as Actions:** Skills are contextual behaviors, not static prompts. They activate by context, chain into sequences, and self-improve via feedback loops.

## Install

Build or install the Python package, then use its transactional lifecycle for
the supported generated bundle targets:

```bash
python3 -m pip install .
TARGET=/path/to/target-repo
adlc-skill install --provider claude --target "$TARGET"
adlc-skill doctor --provider claude --target "$TARGET"
adlc-skill update --provider claude --target "$TARGET"
adlc-skill rollback --provider claude --target "$TARGET"
adlc-skill uninstall --provider claude --target "$TARGET"
```

Use `--provider codex` for the Codex layout. Installs are manifest-owned,
digest-verified, collision-safe, and reversible. `link` is available for local
development. Passing install and doctor proves bundle integrity only; it does
not prove that Claude Code or Codex invoked or followed the skill. Generated
targets are currently limited to those two provider layouts.

`setup.sh` remains a dated compatibility wrapper during the 0.x beta window.
It preserves the previous multi-provider managed layout and emits migration
guidance. Use an absolute path or a shell variable:

```bash
TARGET=/path/to/target-repo
./setup.sh claude "$TARGET"
./setup.sh codex "$TARGET"
./setup.sh cursor "$TARGET"
./setup.sh all "$TARGET"
./setup.sh verify-claude "$TARGET"
```

The direct forms are `./setup.sh claude <target>`, `./setup.sh codex <target>`,
`./setup.sh cursor <target>`, and `./setup.sh all <target>`. Claude installs
ADLC-managed `SKILL.md` files under `<target>/.claude/skills/<skill>/SKILL.md`,
agents under `<target>/.claude/agents/`, `CLAUDE.md`, and
`<target>/.claude/WORKFLOW.dot`. Codex installs skills under
`<target>/.agents/skills/` plus `AGENTS.md`; Cursor installs `.mdc` rules.

Every install also writes `<target>/.adlc/bin/adlc`. That wrapper bakes
`ADLC_ROOT` to this ADLC checkout and execs `bin/adlc`, so schemas,
`skills/paved-road-registry/patterns.json`, the predicate library, and runtime
code stay source-backed. Deployed skills do not need copied non-SKILL assets.

Run `./setup.sh verify-claude "$TARGET"` after installation and after every merge
that touches `skills/`. It verifies managed Claude skill digests against this
checkout and ignores unmanaged local skills; redeploy with `./setup.sh claude
"$TARGET"` when it reports drift.

Runtime preflight:

```bash
bin/adlc health-check --json
bin/adlc ci --json
"$TARGET/.adlc/bin/adlc" health-check --json
```

Persisted workflows have separate inspection and mutation commands:

```bash
bin/adlc status --workspace "$TARGET" --json
bin/adlc resume --workspace "$TARGET" --json
bin/adlc resume --workspace "$TARGET" --approve intent_validation --json
bin/adlc resume --workspace "$TARGET" --approve engineer_review \
  --decision revise --reason "The evidence package is incomplete." --json
```

`status` is strictly read-only. Gate decisions are schema-validated approval
records under `.adlc/approvals/`; revise and rejected decisions require a human
rationale.

`WORKFLOW.md` is the deep reference for phase routing, enforced retry limits, tool-node
semantics, and approval points. The README keeps only the operator path.

## Prompt Your Harness To Do The Following

Copy this prompt into Claude Code, Codex, or another repo-aware harness after
installing ADLC:

```text
Use ADLC to drive <target>. Keep product code, product tests, and user-facing
target docs in the target repo; keep ADLC process artifacts out of the target
diff.

1. Extract target repo conventions first:
   bin/adlc repo-conventions --workspace <target> --json

   Carry the result into the Build Brief as top-level repo_conventions. Set
   repo_conventions.status=none_found only when CLAUDE.md, AGENTS.md,
   CONTRIBUTING.md, and nested convention files do not exist. If convention
   files exist, the honesty gate blocks a none_found claim or omitted rules.

2. Generate the Build Brief using build-feature Step 2. Each executable task
   carries these contracts:
   - repo_conventions from step 1.
   - module_plan with planned files, one-line responsibility per file, no "and"
     in responsibilities, pure/impure marking, and the architecture test to
     write first.
   - honesty_contract with explicit limitations and no-overclaim boundaries.
   - performance_envelope with scale, hot paths, benchmark requirement, and
     benchmark evidence when applicable.
   - task_sizing proving one task is one module, one coherent structured
     file-set (with module_plan when code structure requires it), or explicitly atomic cross-module work.
   - minimality_contract with exactly two fields: rung and decision. Decide it
     once. Repo conventions outrank minimality on file and module structure.
   - operator_surface only when evidence shows a wide solution space,
     taste/quality judgment, know-it-when-I-see-it approval, or medium/high
     blast radius. Omit it for deterministic docs, lint, or build-validation
     work with no operator decision surface.

3. Inventory contract surfaces and pass the clarity gate before finalizing
   the brief:
   bin/adlc contract-surface-inventory --workspace <target> --output <inventory> --json
   bin/adlc clarity-gate --build-brief <brief> --mode <interactive|headless> --json

   The brief must carry an epistemic ledger (every claim KNOWN with sources,
   ASSUMED with ratification, or UNKNOWN with a disposition) and a blindspot
   report whose items all map to ledger entries. The clarity gate blocks
   finalization on architecture-affecting unknowns, ask-user unknowns without
   a recorded human answer, predicate-free acceptance criteria, and
   proof-type criteria with no substance floor. In headless mode it blocks
   and emits a pending-questions artifact — answer the questions or
   explicitly delegate to the stated conservative default; the pipeline never
   self-answers.
   Pending questions are ranked with the same operator-surface volatility
   classifier used by the review packet, so schema/API/data-model questions
   surface before generic low-volatility unknowns.

4. Run operator-side overlays when the manifest or task surface activates
   them:
   bin/adlc operator-divergence-gate --build-brief <brief> --divergence-artifact <divergence> --json
   bin/adlc volatility-review --build-brief <brief> --output <volatility-review> --json
   bin/adlc teach-first-gate --build-brief <brief> --criteria-store <criteria-store> --teach-packet <teach-packet> --updated-store-output <criteria-store> --json

   Divergence requires an ordered options ladder, rejected-option reasons, and
   throwaway prototype refs for taste surfaces. Rejected reasons become
   user-ratified KNOWN ledger entries. Volatility review puts the most
   volatile decisions first while preserving the canonical Build Brief section
   order. Teach-first blocks surface approval until the operator has ratified
   criteria, then later runs cite the versioned criteria store instead of
   re-teaching. Inactive low-blast mechanical work reports `not_applicable`.

5. Validate and prove readiness before codegen:
   bin/adlc validate-artifact --schema build-brief --input <brief> --json
   bin/adlc emit-work-items --target linear --build-brief <brief> --workspace <target> --dry-run --require-ready --json

   validate-artifact blocks schema-invalid briefs. emit-work-items
   --require-ready blocks missing contracts, dishonest repo_conventions,
   split-required tasks, unready minimality, and other readiness issues. Fix
   until ready; never waive silently.

6. Assemble codegen context and write the architecture test first:
   bin/adlc run-phase context_assembly --brief-id <brief-id> --build-brief <brief> --workspace <target> --json

   Generate code only from the assembled context. For any task with a required
   module_plan, write and run the architecture test before production code.

7. Gate the result before opening a PR:
   bin/adlc convention-scan --workspace <target> --build-brief <brief> --json
   bin/adlc compatibility-evidence --build-brief <brief> --inventory <inventory> --json
   bin/adlc deviation-log-validate --input <deviations> --json
   bin/adlc ponytail-admit --build-brief <brief> --diff-file <final.diff> --json
   bin/adlc operator-comprehension-gate --build-brief <brief> --quiz <quiz> --diff-file <final.diff> --json
   bin/adlc pr-hygiene-scan --workspace <target> --build-brief <brief> --diff-file <final.diff> --title <title> --body <body> --base-branch main --default-branch main --json

   compatibility-evidence blocks tasks touching an inventoried contract
   surface unless the surface is named, carries verification predicates, and
   every evidence ref resolves to a real artifact. deviation-log-validate
   classifies every structural decision the brief did not specify: traceable
   to a ledger unknown, or a brief-generator defect that feeds the run
   report's defect count.

   convention-scan blocks target-convention violations and manual-review
   predicates that cannot be checked deterministically. ponytail-admit blocks
   missing two-field minimality contracts, unapproved dependency diffs, and
   removed validation/error/security/accessibility anatomy; see
   docs/specs/ponytail-minimality-contract.md for anatomy gate limits.
   Definition of Done blocks unsatisfied active contracts and verifier evidence.
   operator-comprehension-gate blocks medium/high blast-radius work until the
   operator passes a concrete quiz, records remediation after failure, or
   explicitly delegates comprehension to the engineer review.
   pr-hygiene-scan blocks process artifacts, local paths, banned vocabulary,
   removed gates, and undocumented stacked bases.

   Waivers are recorded, not skipped. PR hygiene waivers use rule:who:why.
   When another gate has a narrower flag format, put the same rule/who/why
   approval in the reason or reference field.

8. Audit completion honestly before presenting the work as done:
   bin/adlc minimalism-audit --build-brief <brief> --criterion-depth-report <depth> --json
   bin/adlc completion-audit --input <audit-plan> --workspace <target> --executor <executor-id> --auditor <auditor-id> --independence-evidence <independence.json> --json
   bin/adlc run-report --json  # aggregate clarity, deviation, compatibility, and harness evidence

   Every acceptance criterion declares a depth (minimal or robust) with a
   justification. The Minimalism Auditor checks each declaration against the
   predicate library (bin/adlc predicate-library) — declaring robust while
   shipping the cheapest satisfying implementation blocks approval. The
   completion audit re-verifies completion claims against actual repo state
   with an auditor that is not the executor, records what was verified versus
   taken on trust, and blocks PR prep on any contradicted claim. Independence
   evidence names distinct executor/auditor sessions and is hashed into the
   report; orchestration remains responsible for supplying truthful identities.
```

## Best Use / Anti-Patterns

- Treat the target repo as the standards source: conventions in, artifacts out.
- Store Build Briefs, council output, audits, validation summaries, and closeout
  packages in ADLC-side process artifact storage per
  `docs/specs/process-artifact-storage.md`; never add them to target diffs.
- Keep one task to one module plan, one coherent structured file-set (including
  non-code file sets), or one explicitly atomic cross-module change.
- Do not use file size, line count, or SLOC as split, design, or DoD criteria.
- Feed maintainer PR comments back through `bin/adlc feedback-conventions`; do
  not bake one-off review comments into hidden prompt lore.

## Pipeline

### Current Operating Model

ADLC now operates as an LLM-driven development system with deterministic control gates. The LLM still performs the judgment-heavy work: triage, research synthesis, planning, code generation, review, and repair. ADLC constrains those actions with schemas, verifier contracts, readiness checks, test-selection gates, workflow state, and explicit escalation rules.

The shipped framework layers are:

| Layer | What It Gives ADLC | How It Is Used |
|---|---|---|
| Compound engineering | Prior verified work, task refs, verifier refs, resume context, and graph status as compact context | `bin/adlc compound-context` before research |
| Learning and Architecture Memory | Evidence-backed learning refs, architecture decision memory, stale/overclaim checks, duplicate primitive checks, and champion/holdout promotion gates | `architecture-memory`, `memory-health`, and `champion-holdout` before reuse or prompt/skill promotion |
| Packaged Loop Library | Assisted-loop templates with required skills, connectors, ADLC commands, schemas, gates, approval points, generated Loop Contracts, Tool Registries, and Work Queue seeds | `loop-library` and `loop-template-install` before a harness runs a known loop |
| Self-Actioning Meta-Harness | Repo, ticket, and signal candidate ranking with packaged-loop selection, queue seed artifacts, tracker-sync payloads, planned ADLC commands, and explicit human gates | `meta-harness-plan` before a harness claims, dispatches, or mutates work |
| Scalable code primitives | Construct refs, paved-road reuse, intent contracts, production invariants, and verifiability | Build Brief task fields and Eval Council checks |
| Implementation Interface | Task-scoped contract for what a change reuses, consumes, emits, preserves, integrates with, and validates | Active when a task touches repo boundaries, schemas, emitters, providers, workflow state, CLI contracts, or reusable framework surfaces |
| Productionization Gate | Bounded production claim with Coverage State, evidence, rollback/observability/security posture, reliability risks, and No-Overclaim boundaries | Active when a task claims production support or production readiness |
| Honesty Contract | Per-feature statement of what the task does not do, limitations, unsafe claims, and required doc or artifact output fields such as `doc_honesty_section`, `no_overclaim`, and `limitations` | Required for executable tasks; pure internal work may declare `not_applicable` only with a no-external-claims reason |
| Performance Envelope | Per-task data-path contract for expected input scale, hot-path complexity, benchmark requirement, and benchmark evidence | Required for executable tasks; non-data-path work uses structured `not_applicable` with a meaningful reason |
| Task Sizing | Decomposition-time proof that each executable task is one module, one coherent module-plan file-set, or explicitly atomic cross-module work | Required for executable tasks; split-required work blocks emission and returns proposed splits |
| Slop Quality Gate | Output-side benchmark, threshold, eval cases, and failure action for generated-output surfaces | Active when a task changes prompt/model/agent/generated content behavior |
| Operator Surface Gates | Divergence options, volatility-first review ordering, teach-first judgment criteria, and operator comprehension proof | Active when `operator_surface` or task evidence shows wide solution space, taste/quality judgment, know-it-when-I-see-it approval, or medium/high blast radius |
| Loop Contract | LLM action-loop contract: job, win condition, allowed tools, real feedback, required tests, progress, control channel, safe checkpoint, independent truth, escalation, and optional `budget_guard` evidence | Active when a task delegates decisions, tool use, test selection, retry/repair, escalation, or maturity claims to an LLM loop |
| Target Repo Conventions | `repo_conventions`, product vocabulary, structural convention scans, explicit waivers, and PR hygiene checks | Extracted before Build Brief planning; consumed by context assembly, LDD, DoD, Eval Council, and PR closeout |
| Clarity Gate | Epistemic ledger (KNOWN/ASSUMED/UNKNOWN with sources and dispositions), blindspot report, interview loop with pending-questions artifacts, predicate-complete acceptance criteria, and substance floors on proof-type criteria | `clarity-gate` before brief finalization; ask-user unknowns block until a recorded human answer or signed accepted risk exists |
| Compatibility Evidence | Contract-surface inventory (policy-sourced over heuristic, confidence-tiered, with consumer discovery), per-surface verification predicates, and evidence refs that must dereference to real artifacts | `contract-surface-inventory` at research time; `compatibility-evidence` before PR |
| Honest Completion | Per-criterion depth declarations (minimal/robust), typed proof payload classes, deviation classification against the ledger, Minimalism Auditor checks against the versioned predicate library, and independent completion-claim re-verification | `deviation-log-validate`, `minimalism-audit`, `completion-audit`, and `run-report` before work is presented as done |

The current truthful maturity state is **assisted loop**. ADLC has a directed workflow, deterministic validators, runtime-enforced retry caps, an invocation bound, workflow state, compound context, readiness gates, test-strength checks, Loop Contract admission gates, and execution-backed required-test evidence when `loop-test-result` artifacts are supplied. A workflow only earns **self-autonomous** status when `bin/adlc loop-maturity-audit` scores it robustly, with no weak score on win condition rigor, non-gameable test selection, failure handling, or budget evidence. Missing, stale, warning, alert, or exhausted `budget_status` blocks `self_autonomous`; healthy local budget evidence is necessary but not sufficient. Tag-only Loop Contract coverage is intentionally capped below robust.

What is automatic today:

- schema validation for Build Briefs, workflow state, agent outputs, Loop Contracts, Loop Actions, and maturity reports
- readiness blocking through `emit-work-items --require-ready`
- generated-output slop gate checks when a generated-output surface is active
- implementation-interface and productionization overclaim checks
- Loop Contract test-selection, action-admission, and maturity-audit CLI/MCP tools
- deterministic `loop-budget-check` CLI/MCP budget guard for LLM-backed Loop Actions
- strict Loop Contract required-test proof through `docs/schemas/loop-test-result.schema.json` and `loop-test-selection --require-test-results`
- schema-backed work queue status, task claims, completion/block/escalation state, dirty-checks, file-overlap checks, and worktree prepare/status/cleanup dry-runs
- target-repo convention extraction, structural convention scans, and PR hygiene scans for pipeline artifacts, banned internal tokens, local paths, removed gates, and undocumented stacked bases
- right-sized Ponytail minimality admission through `bin/adlc ponytail-admit --build-brief <brief> --diff-file <final.diff> --json`, with executable tasks carrying only `rung` and one-line `decision`, dependency diffs requiring approval refs, and regex-based safety-anatomy removals requiring waivers; see `docs/specs/ponytail-minimality-contract.md` for exact limits and false-positive risk
- deterministic Ponytail scenario canaries through `bin/adlc ponytail-scenario-canary --json`, proving missing contracts block readiness and two-field contracts pass through emitted work items
- ADLC-side process artifact storage for Build Briefs, eval outputs, audits, validation summaries, and closeout packages keyed by target repo and task through `bin/adlc process-artifact-path`
- evidence-backed architecture memory writes, memory-health stale/overclaim/duplicate primitive checks, and champion/holdout promotion gates for prompt or skill changes
- packaged assisted-loop template inspection and install plans through `loop-library` and `loop-template-install`
- bounded self-actioning task selection and execution planning through `meta-harness-plan`
- runtime preflight through `bin/adlc health-check --json`
- resume summaries for task fingerprints, loop progress, no-progress count, control events, safe checkpoints, and escalation context
- clarity-gate blocking on missing epistemic ledgers, sourceless claims, unresolved architecture-affecting unknowns, ask-user unknowns without recorded human answers, empty blindspot reports, predicate-free acceptance criteria, and headless interview state with emitted pending-questions artifacts
- contract-surface inventory with policy-over-heuristic sourcing and confidence tiers, plus compatibility evidence that requires named surfaces, verification predicates, and evidence refs that resolve to real artifacts
- deviation-log validation classifying unspecified structural decisions as ledger-traceable or brief-generator defects, aggregated into the run report's defect count
- minimalism audit against the versioned predicate library (`bin/adlc predicate-library`) with rule-ID citations and robust-declared-but-cheapest-shipped contradictions blocking approval
- independent completion audit re-verifying completion claims against repository state, recording verified-versus-trusted splits, and blocking PR prep on contradicted claims
- operator-side divergence, volatility review, teach-first criteria, and comprehension gates through `operator-divergence-gate`, `volatility-review`, `teach-first-gate`, and `operator-comprehension-gate`; inactive low-blast mechanical work returns `not_applicable`
- non-Claude harness execution through `bin/adlc execution-adapter` with schema-backed adapter reports and dual-harness gate-outcome comparison

What is still explicit:

- Loop Contracts are activated by task/workflow surface evidence; ADLC does not force them onto deterministic docs, lint, or build-validation work.
- LLM runtime invocation still goes through the selected adapter: Claude, Codex, Cursor, Antigravity, or Factory.
- Live process kill switches and provider-specific rollback are not claimed by default; state-level steer, abort, interrupt, escalate, safe checkpoint, and rollback notes are the current supported control model.
- Full self-autonomy is a per-workflow evidence claim, not the default framework claim.

### Build Loop

```
start → triage → compound_preflight (learning refs + resume context) → research (Graphify/Beads-aware) → plan ↔ plan_review → scaffold → gen_tests →
  [operator_divergence if active] → [volatility_review if active] → [teach_first if active] →
  context_assembly → code (fan-out) ↔ code_review (comprehension gate) ↔ fixer →
  [security if active] → qa → [test_strength if active] → [slop_gate if generated-output active] →
  [operator_comprehension if medium/high operator blast radius] →
  pr_prep → [learning_capture if verified reusable learning exists] → engineer_review → done
```

Overlay gates are driven by the Build Brief `applicability_manifest` and task
surface evidence. Implementation Interface contracts and Productionization Gate
claims are optional Build Brief layers; they activate when repo integration or
production-ready claims are in scope. Loop Contracts activate when ADLC delegates
decisions, tool use, test selection, retry/repair, escalation, or maturity claims
to an LLM-driven loop. Operator-side gates activate from `operator_surface`,
change-surface volatility, task evidence, and blast-radius classification:
divergence handles option ladders and prototypes, volatility review orders the
review surface, teach-first stores ratified quality criteria, and operator
comprehension blocks medium/high blast work before engineer review. Inactive
overlays are skipped or recorded as explicit no-ops; they are not filler
sections every task must satisfy.
`compound_preflight` also no-ops explicitly when `docs/solutions` or
`graphify-out` is missing, so new repos do not pay setup tax before research.
Target-repo conventions are extracted before Build Brief decomposition,
inlined into codegen context, checked in LDD/DoD, audited by Eval Council, and
verified again during PR hygiene closeout.

### Fix Loop (parallel)

```
error_capture → confirm → investigate → conventions → fix → prove → light_council → pr_hygiene → pr
```

### Feedback Loop (nightly)

```
human_edits + maintainer_pr_comments → diff_capture → pattern_distill → skill_update + repo_conventions
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

Retry edges enforce their `max_retries` values from `WORKFLOW.dot` in persisted workflow state. Exhaustion stops with `stop_reason: cap_exhausted` and a named failure signature; `--max-phases` separately bounds each invocation.

## Verification

The repo ships with these verification layers:

- `tests/test_adlc_cli.sh` exercises the `bin/adlc` CLI surface end to end, including the clarity gate, contract-surface inventory, compatibility evidence, deviation validation, minimalism and completion audits, and the dual-harness feature-slice comparison.
- `tests/test_adlc_contracts.sh` checks prompt/schema/runtime wiring and the checked-in golden artifacts.
- `tests/test_drift_verification.sh` proves installed skill and agent digests fail closed when stale and pass after redeployment.
- `tests/test_public_hygiene.sh` blocks developer-local paths, credential-like values, malformed JSON, broken local Markdown links, and missing community files.
- `tests/backtest/run_backtest.sh` replays the deterministic evaluators against the benchmark fixture set and writes to a temporary report by default. Set `ADLC_BACKTEST_REPORT=/path/report.json` when a durable report is needed; the committed `tests/backtest/last_report.json` remains a reviewed golden snapshot.
- `tests/smoke/run_smoke.sh` runs the real staged agents through a tiny repo using the selected runtime adapter.
- `tests/acceptance/run_public_acceptance.sh` runs the provider-free public acceptance path: install ADLC into a realistic target repo, plan from repo/ticket signals, install a packaged loop, exercise queue/worktree gates, prove a verifier fails before a bounded repair and passes after it, complete the queue item, and dry-run tracker sync.
- `tests/acceptance/run_os12_acceptance.sh` is a provider-free gate proof on a controlled fixture: it extracts target conventions, validates a Build Brief with module_plan, honesty, performance, and task_sizing, assembles context, exercises generated code/tests, passes gates, and proves the flat-file, process-artifact, banned-token, and oversized-task negative controls fail at the named gates. The harness writes the fixture implementation itself, so it is not evidence of one-shot agent execution.

Typical verification flow:

```bash
bin/adlc ci --json
bash tests/acceptance/run_public_acceptance.sh
bash tests/acceptance/run_os12_acceptance.sh
bash tests/test_adlc_cli.sh
bash tests/test_adlc_contracts.sh
bash tests/test_drift_verification.sh
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
bin/adlc goal-prompt --build-brief .adlc/build_brief.json --task-id TASK-123 --output .adlc/goal-prompt.json --json
bin/adlc repo-conventions --workspace . --output .adlc/repo_conventions.json --json
bin/adlc convention-scan --workspace . --file src/lib.rs --json
bin/adlc pr-hygiene-scan --workspace . --build-brief .adlc/build_brief.json --base origin/main --base-branch feature --default-branch main --dependency PR-123 --json
bin/adlc run --brief-id BRF-123 --workspace . --dry-run --json
bin/adlc run-phase triage --brief-id BRF-123 --workspace . --dry-run --json
bin/adlc run-phase context_assembly --brief-id BRF-123 --build-brief .adlc/build_brief.json --workspace . --json
bin/adlc run-phase qa --workspace . --verifier 'pytest tests/test_task.py' --json
bin/adlc resume-workflow --workspace . --json
bin/adlc compound-context --workspace . --build-brief .adlc/build_brief.json --json
bin/adlc architecture-memory --input .adlc/architecture_decisions.json --workspace . --dry-run --json
bin/adlc memory-health --workspace . --changed-path scripts/adlc_runtime/cli.py --primitive-proposals .adlc/primitive_proposals.json --json
bin/adlc champion-holdout --input .adlc/champion_holdout.json --json
bin/adlc beads-status --workspace . --json
bin/adlc looper-status --workspace . --json
bin/adlc loop-design-validate --input .adlc/loops/task/loop_design.json --json
bin/adlc loop-contract-from-design --loop-design .adlc/loops/task/loop_design.json --output .adlc/loops/task/loop_contract.json --json
bin/adlc loop-library --json
bin/adlc loop-library --template-id ci-triage --json
bin/adlc loop-template-install --template-id ci-triage --workspace . --dry-run --json
bin/adlc meta-harness-plan --signals .adlc/signals.json --build-brief .adlc/build_brief.json --max-candidates 3 --json
bin/adlc control-plane-drift-loop --workspace . --verifier 'python3 -m py_compile scripts/adlc_runtime/metadata.py' --dry-run --json
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
bin/adlc contract-surface-inventory --workspace . --output .adlc/contract_inventory.json --json
bin/adlc clarity-gate --build-brief .adlc/build_brief.json --mode headless --json
bin/adlc compatibility-evidence --build-brief .adlc/build_brief.json --inventory .adlc/contract_inventory.json --json
bin/adlc deviation-log-validate --input .adlc/deviations.json --json
bin/adlc predicate-library --json
bin/adlc minimalism-audit --build-brief .adlc/build_brief.json --criterion-depth-report .adlc/criterion_depth.json --json
bin/adlc completion-audit --input .adlc/completion_audit_plan.json --workspace . --executor "$EXECUTOR_ID" --auditor "$AUDITOR_ID" --independence-evidence .adlc/completion_audit_independence.json --json
bin/adlc execution-adapter --provider codex --command 'codex exec --help' --workdir . --prompt-file .adlc/task_prompt.md --json
bin/adlc run-report --json
bin/adlc mcp-tools --json
bin/adlc mcp-serve
```

Queue and worktree operations are dry-run first. Mutating queue state or creating/removing worktrees requires `--allow-mutation` plus a tool-registry admission path for `adlc-queue` or `adlc-worktree`. Claims fail closed when the checkout is dirty or when expected file, directory, or glob ownership overlaps an active `claimed` or `running` task.

Deterministic tool nodes emit schema-backed phase artifacts under `.adlc/outputs/` and workflow state records them in `phase_artifacts[]`. Dry-run tool-node calls produce `planned` artifacts without marking the phase complete. Mutating tool-node writes require `--allow-mutation` and `--tool-registry`.

The first dogfood loop is `control-plane-drift-loop`. It detects schema-alias drift, creates a stable work-item sync payload, validates a proposed repair action, optionally applies the bounded `metadata.py` repair through action admission, reruns verifiers, and stops for human review.

Learning and architecture memory keeps ADLC's outer loop from compounding stale or overfit knowledge. `architecture-memory` records accepted architecture boundaries only from evidence-backed candidates and writes through action admission. `memory-health` audits `docs/solutions` and `docs/architecture/decisions` for stale refs, overclaim, and duplicate primitive proposals. `champion-holdout` promotes prompt or skill challengers only when holdout data beats the current champion by the configured margin and all must-pass rules pass.

The packaged loop library makes known assisted loops reusable by harnesses. `loop-library` lists or inspects templates such as `ci-triage`, `pr-babysitter`, `dependency-bump`, `ticket-hygiene`, `architecture-debt-discovery`, `feedback-sweep`, and `skill-champion`. `loop-template-install` dry-runs by default and, after `adlc-loop-library:install_loop_template` action admission, writes `.adlc/loops/<template_id>/loop_contract.json`, `tool_registry.json`, `work_queue_seed.json`, `token_budget.json`, `README.md`, and `install_report.json`. It does not schedule jobs, dispatch agents, choose work, merge code, or make architecture decisions; those remain outside the library contract.

Loop Design support makes Looper-style loop planning an admission artifact before execution. `looper-status` is read-only and optional. `loop-design-validate` checks a Looper-compatible Loop Design Contract for verifiers, judge criteria, stop/no-progress controls, mutation boundaries, and privacy posture. `loop-contract-from-design` converts a validated design into a schema-backed ADLC Loop Contract; it does not execute the loop, schedule agents, or mutate trackers.

The bounded self-actioning meta-harness planner lets ADLC decide candidate work without bypassing the control plane. `meta-harness-plan` reads repo, ticket, Build Brief, queue, and signal candidates; ranks them by value, risk, verifiability, repeatability, and urgency; chooses a packaged loop template; emits schema-backed Work Queue seed and Work Item Sync payloads; and returns the exact ADLC commands a harness should run next. It does not claim tasks, create worktrees, update trackers, dispatch agents, merge, deploy, or decide architecture. Those steps remain behind existing action-admitted commands and human approval gates.

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
- smoke runs write only ephemeral logs and reports under `tests/smoke/artifacts/`;
  the historical fixture under `tests/smoke/fixtures/` is regression data, not
  current provider-conformance evidence

## Agents

| Agent | Job | Model | Skills |
|-------|-----|-------|--------|
| **triage** | Classify, route, or escalate | Sonnet | none |
| **researcher** | Graph-backed codebase analysis, learning refs, PRD cross-reference, dark-code risk notes | Opus | graph-research, codebase-research, paved-road-registry, dark-code-audit, grafana |
| **planner** | PRD + research into an applicability-aware Build Brief | Opus | graph-research, codegen-context, architecture, reuse-analysis, paved-road-registry, context-layers |
| **plan-reviewer** | 3 core + 7 conditional-overlay Eval Council personas with Gate 0 pre-checks | Opus | eval-council |
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
`graph-research` (Graphify/Beads-aware evidence) · `codebase-research` · `paved-road-registry` (repo-local approved build paths) · `dark-code-audit` · `context-layers` · `comprehension-gate` (agent comprehension plus operator blast-radius quiz handoff) · `eval-council` (3 core + 7 conditional overlays + Gate 0) · `codegen-context` (zero-read assembly) · `tdd-enforcement` · `ldd-enforcement` (lint gate before TDD) · `systematic-debugging` · `architecture-pattern` · `qa-test-data` · `reuse-analysis` · `learning-capture` · `learning-refresh` · `definition-of-done` (applicability-aware core + overlay DoD) · `spec-to-tests` (failing-test authoring from Brief, with Loop Contract coverage tags and execution evidence when active)

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

Every task requires: files_to_create/modify, reference_impl, dependencies, `task_classification`, `verification_spec`, `module_plan` decision or registered structural pattern match, failure modes, and enough acceptance criteria to define the verifier contract. Executable tasks also require an `honesty_contract`; required contracts name what the feature does not do, known limitations, unsafe claims, output surfaces, and required output fields. Pure internal work may set `honesty_contract.applicability=not_applicable` only with a reason that explicitly says there are no external claims. Tasks that emit artifacts require `no_overclaim` and `limitations`; tasks that emit docs require `doc_honesty_section`. Executable tasks also require a `performance_envelope`; data-path tasks set `applicability=required` with expected input scale, hot paths, complexity bounds, and `benchmark_required`, plus a benchmark spec when true. Non-data-path tasks set `performance_envelope.applicability=not_applicable` with a meaningful reason; readiness uses the structured applicability value and does not parse magic words from the reason. Executable tasks also require a `minimality_contract` with exactly `rung` and one-line `decision`; reuse evidence belongs in reuse-analysis output, not the task contract. `repo_conventions` and `module_plan` govern file/module structure, while Ponytail governs behavior scope, dependency additions, and speculative abstraction. Tasks that create code modules or explicitly declare `module_plan` in their sizing basis must set `module_plan.applicability=required` with the planned file list, one-line responsibility per file, pure/impure marking, capabilities, and the architecture test that is written first; or cite an approved pattern such as `pattern:interralis:evidence-module?module_root=src/foo/bar` in `paved_road_refs` so `module-plan-check` generates the effective plan from `skills/paved-road-registry/patterns.json`. Behavior-only and coherent non-code file-set tasks may set `module_plan.applicability=not_applicable` with a reason. Readiness uses these structured fields rather than structural words in prose. Pattern departures require `module_plan.pattern_deviation_reason`. Executable tasks also require `task_sizing`: the change surface must be one module, one coherent file-set, or explicitly atomic cross-module work with an atomic-work reason. If the split decision says splitting is required, readiness blocks and surfaces the proposed split. Size, line count, and SLOC alone are not valid criteria. Run `bin/adlc paved-road-patterns --json`, `bin/adlc module-plan-check --build-brief <brief> --json`, and `bin/adlc ponytail-admit --build-brief <brief> --json` before codegen context assembly. Tasks that touch integration boundaries should carry an `implementation_interface_contract`; tasks that claim `production_ready` must carry a `productionization_gate` with validation evidence and no-overclaim boundaries. Tasks with wide solution space, taste/quality judgment, know-it-when-I-see-it approval, or medium/high blast radius should carry `operator_surface` plus refs such as `divergence_artifact_ref`, `operator_comprehension_quiz_ref`, and `judgment_criteria_refs`; keep the canonical 18-section order unchanged and store the supporting packets as process artifacts. Tasks that introduce or change LLM-driven loop behavior should carry a Loop Contract and the deterministic loop verifier commands that prove required tests, action admission, progress/control state, and maturity verdicts.

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
| Codex | `gpt-5` | `gpt-5-codex` |
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
├── docs/                   # build-briefs/, schemas/, specs/, tests/, archive/
├── docs/loop-library/      # Packaged assisted-loop templates for harness installation
├── docs/solutions/         # Schema-validated compound engineering learning store
├── tests/                  # contract checks, drift proof, backtests, smoke harness
└── scripts/                # stable CLI, production runtime adapters, adlc_runtime package, and validators
```

## Principles

1. **Graph, not prose.** DOT file you can see and edit. Not a 27K-token prompt.
2. **Thin agents, thick skills.** Agents are ~100 lines. Knowledge lives in skills.
3. **Deterministic where you can be.** Lint, test, scaffold. Zero tokens for predictable work.
4. **Labels on edges.** Routing logic lives in the graph, not in agent prompts.
5. **Fan-out by default.** Serial execution of independent work is a velocity bug.
6. **Cap every loop.** Runaway agents cost more than asking a human.
7. **Zero-read.** Coding agents get everything inlined. No searching. No guessing.
8. **Target repo conventions travel with the work.** Planning extracts them, codegen receives them, LDD/DoD scans them, and PR hygiene proves they did not leak ADLC artifacts.
9. **One human gate.** Machines catch structure. You catch judgment.
10. **Bring your own agent.** Claude, Codex, Cursor, Antigravity, Factory. Skills don't care.
11. **Composable.** Swap work-item or document emitters without changing the Build Brief task schema.
12. **Security baked in, not bolted on.** STRIDE and OWASP activate when the task touches a real security surface.
13. **BLE-compliant.** Specify outcomes, not procedures. Design for removal as models improve.

## Docs

- [`docs/specs/graph-research-and-comprehension.md`](docs/specs/graph-research-and-comprehension.md) — Graphify, Beads, context-layer, and comprehension-gate contract
- [`docs/specs/scalable-ai-code-primitives.md`](docs/specs/scalable-ai-code-primitives.md) — Graph-backed context, paved-road reuse, verifiability, and production invariant contract
- [`docs/specs/implementation-interfaces-and-productionization.md`](docs/specs/implementation-interfaces-and-productionization.md) — Implementation Interface, Productionization Gate, Coverage State, and No-Overclaim contract
- [`docs/design/runtime-decomposition-plan.md`](docs/design/runtime-decomposition-plan.md) — Approved-for-review boundary proposal and independently landable migration sequence for the runtime entrypoint; implementation remains human-gated
- [`docs/specs/loop-system-maturity-audit.md`](docs/specs/loop-system-maturity-audit.md) — Loop Contract, LLM Action Envelope, non-gameable test selection, control channel, and maturity audit contract
- [`docs/specs/slop-eval-loop.md`](docs/specs/slop-eval-loop.md) — Output-side slop benchmark, threshold, regression, and case-promotion contract
- [`docs/specs/compound-engineering-learning-store.md`](docs/specs/compound-engineering-learning-store.md) — `docs/solutions` learning-entry schema, capture, refresh, and preflight contract
- [`docs/specs/packaged-loop-library.md`](docs/specs/packaged-loop-library.md) — Packaged assisted-loop catalog, install artifacts, and action-admitted install flow
- [`docs/specs/self-actioning-meta-harness.md`](docs/specs/self-actioning-meta-harness.md) — Bounded candidate ranking, packaged-loop selection, queue seed, tracker-sync, and planned-command contract
- [`docs/archive/adlc-v2-specification.md`](docs/archive/adlc-v2-specification.md) and [`docs/archive/adlc-v2-tickets.md`](docs/archive/adlc-v2-tickets.md) — superseded v2 design history; retained for provenance, not current operator guidance
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — development setup, change expectations, and validation requirements
- [`SECURITY.md`](SECURITY.md) — private vulnerability reporting and support boundaries
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — community participation standards
- [`CHANGELOG.md`](CHANGELOG.md) — release-oriented change history

## Acknowledgments

- [**Daniel Miessler**](https://github.com/danielmiessler) for providing a framework that everyone in the AI ecosystem has benefitted from. From prompting to learning to scaling and building systems, you have pushed this industry for the better.
- [**Pedram Amini**](https://github.com/pedramamini) for [Maestro](https://github.com/Maestro-AI/maestro) and the way it showed people what orchestrated AI agents could actually look like in practice. That work helped a lot of us see the path.
- [**Jonathan Haas**](https://github.com/haasonsaas) for being relentless about what is possible with AI, pushing me every day, and figuring out the right abstractions. You see the line through the fog as if you are the investor, the owner, the product manager, and the consumer.

## License

MIT. See [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
