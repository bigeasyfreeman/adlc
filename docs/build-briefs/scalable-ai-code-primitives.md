# Scalable AI Code Primitives Build Brief

## ADLC Mode

`prd_and_decompose`

## Production Target

Teach ADLC to preserve production-grade engineering quality while AI increases code throughput by making five primitives first-class in planning, review, and codegen context:

1. graph-backed construct maps
2. intent contracts
3. agent paved-road registry
4. verifiability gates
5. production quality, compatibility, and failsafe invariants

The outcome is not a broad organization ecology audit. The outcome is a code-scaling contract that keeps monoliths and large codebases consistent, understandable, and safe to evolve.

## Source Research

- Google I/O "Software engineering at the tipping point": extract shared fate, systems thinking, validation pressure, and intellectual control as engineering constraints, not as Google-specific operating-model mandates.
- Google I/O "Build core skills to thrive as an AI-era developer": extract shift-left intent, specs and skill files as source of truth, verified high-quality code, trace-driven learning, and delegate tasks, not judgment.
- Karpathy "From vibe coding to agentic engineering": extract Software 3.0 context bundles, verifiability as the delegation boundary, agentic engineering as preserving the quality bar, and understanding as non-delegable.
- ADLC graph research: current insertion points are `agents/researcher.md`, `agents/planner.md`, `skills/eval-council/SKILL.md`, `docs/specs/graph-research-and-comprehension.md`, `docs/schemas/build-brief.schema.json`, and `skills/manifest.json`.

## Scope Lock

In scope:

- Add a concise spec defining the scalable AI code primitives and their lifecycle binding.
- Add a new `paved-road-registry` skill that lets ADLC discover and maintain approved build patterns for agents.
- Extend graph research expectations from repository topology to construct relationship maps: modules, interfaces, schemas, config/env, persistence paths, tests, and dependency edges.
- Extend planner expectations so every relevant Build Brief captures intent, construct-map evidence, paved-road choices, verifiability, production invariants, and compatibility/failsafe behavior.
- Extend Eval Council checks so agent-ready work can be blocked for missing paved-road evidence, missing deterministic verifier, missing load-bearing invariant coverage, or vague production-quality claims.
- Add schema fields only where needed to preserve these contracts across Build Briefs and emitted work items.
- Add deterministic tests for schema acceptance, manifest/setup inventory, and contract text wiring.

Out of scope:

- Full socio-technical software ecology mapping of teams, incentives, culture, or org design.
- Token economics, model budget enforcement, or load-bearing token-engine runtime controls.
- Company productivity metrics, T-shaped developer training, hiring process design, or psychological safety programs.
- A separate release/rollback framework. Rollout, downgrade, and failsafe behavior stay inside compatibility and production-quality contracts.
- Enforcing one repository topology such as monorepo or trunk-based development.
- Replacing existing Graphify/Beads responsibilities.

## Existing Primitives Reused

- `graph-research` remains the codebase and corpus map.
- `codebase-research` remains the broad repo research skill.
- `reuse-analysis` remains the duplicate/pattern avoidance skill.
- `context-layers` remains the durable module/interface/decision comprehension record.
- `comprehension-gate` remains the post-change understanding gate.
- `eval-council` remains the adversarial review gate.
- `build-brief.schema.json` remains the canonical Build Brief contract.
- `tests/test_adlc_contracts.sh` and `tests/test_setup.sh` remain the deterministic regression gates.

## Proposed Architecture

### Primitive 1: Graph-Backed Construct Map

ADLC should require graph-backed context in addition to raw code access. Research output should name:

- constructs: modules, packages, services, CLIs, schemas, configs, env vars, migrations, queues/events, persistence paths, public APIs, internal interfaces
- relationships: imports, callers, consumers, producers, stored artifacts, generated artifacts, tests, ownership/context artifacts when available
- reuse paths: existing implementations or patterns the agent should extend
- blast radius: reverse dependencies and compatibility-sensitive paths
- validation surfaces: deterministic tests, integration paths, schemas, contract checks, smoke/backtest targets

This belongs in `docs/specs/graph-research-and-comprehension.md`, `agents/researcher.md`, and `agents/planner.md`.

### Primitive 2: Intent Contract

ADLC should treat the Build Brief as the structured intent file, not a prose plan. For codegen, every task should preserve:

- what behavior changes
- why the behavior matters
- constraints and non-goals
- tradeoffs and rejected alternatives when relevant
- edge cases
- load-bearing assumptions
- verifier or eval

This belongs in `agents/planner.md`, `docs/schemas/build-brief.schema.json`, and Eval Council Gate 0 specificity checks.

### Primitive 3: Agent Paved-Road Registry

ADLC should have a registry of approved build paths that agents must prefer:

- framework and library choices
- module layout conventions
- API and CLI patterns
- schema, migration, and persistence patterns
- auth, identity, tenancy, idempotency, retry, and error-handling patterns
- logging, metrics, and observability conventions
- test and eval patterns
- deployment/runtime conventions
- reference implementations

Agents may leave the paved road only when the Build Brief records direct evidence and a reviewer-verifiable rationale.

This should be a new skill at `skills/paved-road-registry/SKILL.md`, registered in `skills/manifest.json`, used by `agents/researcher.md` and `agents/planner.md`, and checked by `skills/eval-council/SKILL.md`.

### Primitive 4: Verifiability Gate

Autonomous execution should be bounded by verifiability. Every implementation task should identify:

- primary verifier
- expected failure before the change when applicable
- deterministic or judgment-based classification
- target files or target behavior
- validation surface touched by the graph-backed construct map
- fallback human judgment point when the output cannot be deterministically verified

This builds on the existing `verification_spec` and should be strengthened in planner and Eval Council wording before any schema expansion.

### Primitive 5: Production Quality, Compatibility, And Failsafe Invariants

ADLC should preserve the production-quality bar by requiring explicit invariants for risky work:

- identity and account binding
- auth/authz and secret handling
- tenancy and data isolation
- money movement or financial state
- PII and sensitive data handling
- ordering, concurrency, idempotency, retries, and dedupe
- persistence, migrations, and rollback/downgrade
- dependency failure behavior
- observability required to know whether the behavior works

This belongs in the task `compatibility_contract`, `failure_modes`, `definition_of_done`, and a new or extended production-quality section in the Build Brief schema.

## Implementation Tasks

| Task ID | Artifact Type | Objective | Dependencies | Parallel | Verification |
|---|---|---|---|---|---|
| ADLC-SCALE-001 | implementation_task | Add `docs/specs/scalable-ai-code-primitives.md` defining the five primitives, lifecycle binding, removal criteria, and non-goals. | none | yes | `rg -n "Scalable AI Code Primitives|Graph-Backed Construct Map|Agent Paved-Road Registry" docs/specs` |
| ADLC-SCALE-002 | implementation_task | Add `skills/paved-road-registry/SKILL.md` with discovery, registry format, evidence rules, output contract, and guardrails for leaving the paved road. | ADLC-SCALE-001 | yes | `test -f skills/paved-road-registry/SKILL.md` and manifest/setup tests |
| ADLC-SCALE-003 | implementation_task | Register `paved-road-registry` in `skills/manifest.json` and setup/install expectations so downstream platforms receive the skill. | ADLC-SCALE-002 | no | `bash tests/test_setup.sh` and `bash tests/test_adlc_contracts.sh` |
| ADLC-SCALE-004 | implementation_task | Update `agents/researcher.md` to emit graph-backed construct maps and paved-road candidates as first-class research output. | ADLC-SCALE-001, ADLC-SCALE-002 | yes | Contract grep plus `bash tests/test_adlc_contracts.sh` |
| ADLC-SCALE-005 | implementation_task | Update `agents/planner.md` to convert construct-map evidence, intent contract, paved-road choices, verifiability, production invariants, and compatibility/failsafe proof into Build Brief tasks. | ADLC-SCALE-001, ADLC-SCALE-002 | yes | Contract grep plus `bash tests/test_adlc_contracts.sh` |
| ADLC-SCALE-006 | implementation_task | Update `docs/specs/graph-research-and-comprehension.md` so Graphify evidence covers construct relationships and validation surfaces, not only topology and compatibility paths. | ADLC-SCALE-001 | yes | `rg -n "construct map|validation surfaces|paved-road" docs/specs/graph-research-and-comprehension.md` |
| ADLC-SCALE-007 | implementation_task | Extend `docs/schemas/build-brief.schema.json` with backwards-compatible optional fields for construct-map refs, paved-road refs, intent contract refs, and production invariant coverage. | ADLC-SCALE-004, ADLC-SCALE-005 | no | `bin/adlc validate-artifact --schema build-brief --input docs/build-briefs/xia-adlc-remediation.json --json` and `bash tests/test_adlc_contracts.sh` |
| ADLC-SCALE-008 | implementation_task | Update `skills/eval-council/SKILL.md` so Gate 0 / personas flag missing paved-road evidence, unverifiable delegation, unsupported production-quality claims, and missing invariant coverage. | ADLC-SCALE-005, ADLC-SCALE-007 | no | `bash tests/backtest/run_backtest.sh` if available; otherwise `bash tests/test_adlc_contracts.sh` |
| ADLC-SCALE-009 | validation_task | Add or update deterministic tests/fixtures so the new optional schema fields, skill registration, and contract text are protected without making legacy briefs invalid. | ADLC-SCALE-003, ADLC-SCALE-007, ADLC-SCALE-008 | no | `bash tests/test_adlc_contracts.sh`; `bash tests/test_setup.sh`; `git diff --check` |
| ADLC-SCALE-010 | validation_task | Run Graphify post-change and capture whether the new primitive spec connects to planner, researcher, Eval Council, and Build Brief schema. | ADLC-SCALE-009 | no | `graphify update .`; `graphify query "How do scalable AI code primitives connect to planner, researcher, Eval Council, and Build Brief schema?"` |

## Agent-Ready Task Details

### ADLC-SCALE-001: Define Scalable AI Code Primitives Spec

**Files to create:** `docs/specs/scalable-ai-code-primitives.md`

**Reference implementation:** `docs/specs/graph-research-and-comprehension.md`

**Acceptance criteria:**

- Given the spec is opened, when a planner reads it, then it can distinguish the five core primitives from explicitly out-of-scope org-governance concepts.
- Given a task touches code generation, when the spec is applied, then it identifies which primitive gates are required and which are not applicable.
- Given future models improve, when removal criteria are reviewed, then redundant ceremony can be removed without losing production-quality guarantees.

**Failure modes:**

- The spec recreates broad software-ecology mapping instead of code construct and engineering contract mapping.
- The spec mandates Google-specific practices such as monorepo/trunk-based development.
- The spec adds unbounded ceremony without removal criteria.

### ADLC-SCALE-002: Add Paved-Road Registry Skill

**Files to create:** `skills/paved-road-registry/SKILL.md`

**Reference implementation:** `skills/reuse-analysis/SKILL.md`, `skills/codebase-research/SKILL.md`

**Acceptance criteria:**

- Given a repo with existing patterns, when the skill runs, then it outputs approved patterns, reference implementations, evidence paths, and gaps.
- Given no paved road exists for a capability, when the skill reports, then it records `no_paved_road_found` instead of inventing a pattern.
- Given a proposed task leaves an approved pattern, when the planner consumes the skill output, then the task requires direct evidence and rationale.

**Failure modes:**

- The registry becomes a static preference list not grounded in repository evidence.
- The skill blocks legitimate new abstractions even when existing patterns cannot absorb the change.

### ADLC-SCALE-003: Register Paved-Road Registry

**Files to modify:** `skills/manifest.json`, setup/install tests as needed

**Reference implementation:** existing skill manifest entries for `reuse-analysis`, `context-layers`, and `graph-research`

**Acceptance criteria:**

- Given setup runs for each supported platform, when installed skills are inspected, then `paved-road-registry` is included where core engineering skills are installed.
- Given `bin/adlc list-agents --json` runs, when planner/researcher skills are inspected, then any new skill assignment is visible.

**Failure modes:**

- The skill exists in the repo but is not shipped by setup.
- The manifest claims a skill path that setup cannot install.

### ADLC-SCALE-004: Extend Researcher Output

**Files to modify:** `agents/researcher.md`

**Reference implementation:** current `Graph Research Evidence` and `reuse_opportunities` output blocks

**Acceptance criteria:**

- Given a PRD and repo path, when researcher runs, then the output includes `construct_map`, `paved_road_candidates`, `validation_surfaces`, and `load_bearing_invariants` where evidence supports them.
- Given evidence is missing, when researcher reports, then gaps are explicit and do not become tasks.

**Failure modes:**

- Researcher proposes solutions instead of reporting constructs, relationships, and evidence.
- Researcher treats Graphify output as proof for Type 1 decisions without direct verification.

### ADLC-SCALE-005: Extend Planner Output

**Files to modify:** `agents/planner.md`

**Reference implementation:** current graph-backed compatibility, context-layer, reuse, and tech-debt sections

**Acceptance criteria:**

- Given research includes construct-map and paved-road evidence, when planner emits tasks, then tasks cite the construct evidence and selected paved road.
- Given a task cannot be deterministically verified, when planner emits it, then it either creates a human-judgment checkpoint or blocks delegation.
- Given a task touches identity, auth, tenancy, persistence, money, PII, ordering, retries, or migration, when planner emits it, then load-bearing invariants are explicit in failure modes, compatibility, and DoD.

**Failure modes:**

- Planner adds generic production-quality prose that no verifier can check.
- Planner lets agents leave paved roads without rationale.

### ADLC-SCALE-006: Extend Graph Research Contract

**Files to modify:** `docs/specs/graph-research-and-comprehension.md`

**Reference implementation:** existing Graph Research Evidence and Compatibility Evidence sections

**Acceptance criteria:**

- Given graph research evidence is recorded, when a Build Brief references it, then it can include construct relationships, validation surfaces, and paved-road references.
- Given Graphify is unavailable or stale, when planning continues, then confidence is lowered and validation tasks cover the gap.

**Failure modes:**

- The contract confuses Graphify with work-item source of truth.
- The contract implies graph-derived claims are enough for irreversible decisions.

### ADLC-SCALE-007: Extend Build Brief Schema

**Files to modify:** `docs/schemas/build-brief.schema.json`

**Reference implementation:** existing optional `comprehension_context_refs`, `compatibility_evidence_refs`, and `dark_code_hotspots` task fields

**Acceptance criteria:**

- Given existing checked-in Build Brief fixtures, when schema validation runs, then legacy artifacts remain valid.
- Given a new scalable-code task, when schema validation runs, then optional fields can preserve construct-map refs, paved-road refs, intent refs, and production invariant coverage.
- Given emitted work items are generated, when `emit-work-items` runs, then relevant new fields are preserved if present or intentionally omitted if absent.

**Failure modes:**

- Required fields break legacy Build Briefs.
- New fields are too loosely named to be useful to downstream emitters.

### ADLC-SCALE-008: Extend Eval Council Gates

**Files to modify:** `skills/eval-council/SKILL.md`, deterministic backtest evaluator docs/tests if required

**Reference implementation:** current Gate 0 specificity and comprehension gate checks

**Acceptance criteria:**

- Given a Build Brief claims production-grade output without verifiers or invariants, when Eval Council reviews, then it returns `revise`.
- Given a task leaves a paved road without evidence, when Architect or Executioner reviews, then it is a major finding.
- Given a task delegates unverifiable judgment to agents, when First Principles or Skeptic reviews, then it is blocked or escalated.

**Failure modes:**

- Council turns these primitives into broad philosophical critique instead of file/task-specific findings.
- Council requires paved-road evidence for trivial docs or lint-only changes.

### ADLC-SCALE-009: Deterministic Validation

**Files to modify:** `tests/test_adlc_contracts.sh`, `tests/test_setup.sh`, fixtures as needed

**Reference implementation:** existing checks for graph research, comprehension gate, schema fixtures, and skill install inventory

**Acceptance criteria:**

- Given the new skill exists, when setup tests run, then platform install inventory remains truthful.
- Given schema optional fields are added, when contract tests run, then existing fixtures pass and at least one fixture exercises the new fields.
- Given contract text changes, when contract tests run, then critical phrases are protected from accidental removal.

**Failure modes:**

- Tests assert exact counts that are not derived from manifest/setup reality.
- Tests validate only file existence but not contract semantics.

### ADLC-SCALE-010: Post-Change Graph Review

**Files to modify:** none unless graph output is committed by project policy

**Reference implementation:** `docs/specs/graph-research-and-comprehension.md`

**Acceptance criteria:**

- Given implementation is complete, when `graphify update .` runs, then graph freshness matches HEAD.
- Given the graph is queried, when asking how scalable AI code primitives connect to planner/researcher/council/schema, then those relationships are discoverable.

**Failure modes:**

- Graphify is skipped after code changes.
- Graph-derived relationships are not directly verified before final claims.

## Compatibility Contract

Backward compatibility: all existing Build Briefs, schema fixtures, setup flows, CLI commands, and work-item emitters must remain valid. New schema fields should be optional for this slice.

Forward compatibility: the primitives should leave room for future runtime enforcement, but this slice should only define contracts, skills, planner/researcher/council behavior, and deterministic tests.

Migration or rollout: additive documentation, skill, schema, and prompt-contract changes only. No migration is required.

Rollback or downgrade: revert the added spec, skill, prompt-contract changes, schema optional fields, and tests. Existing ADLC behavior should continue because no runtime workflow phase is removed or renamed.

## Definition of Done

- `docs/specs/scalable-ai-code-primitives.md` exists and defines the five primitives plus non-goals.
- `skills/paved-road-registry/SKILL.md` exists and is registered in `skills/manifest.json`.
- Researcher and planner explicitly consume construct maps, paved-road evidence, verifiability, and production invariants.
- Eval Council flags missing paved-road evidence, unverifiable delegation, unsupported production-quality claims, and missing invariant coverage.
- Build Brief schema preserves optional primitive evidence without breaking existing fixtures.
- `bash tests/test_adlc_contracts.sh` passes.
- `bash tests/test_setup.sh` passes.
- `git diff --check` passes.
- `graphify update .` runs after implementation and graph freshness is recorded.

## Open Questions

- Should paved-road registry data live only in generated research output, or should ADLC also define a conventional repo file such as `.adlc/paved-roads.json` for projects that want a durable local registry?
- Should production invariants be a top-level Build Brief field, a task-level field, or both?
- Should verifiability classification be added to `verification_spec`, or is existing `must_be_deterministic` enough if planner/council wording is strengthened?
- Should `paved-road-registry` be a core skill installed by default, or an optional skill activated only when repo context exists?
