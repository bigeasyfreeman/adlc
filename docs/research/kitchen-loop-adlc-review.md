# Kitchen Loop ADLC Review

Date: 2026-06-28

## Research Basis

- ArXiv abstract and HTML/PDF for `2603.25697v1`, "The Kitchen Loop: User-Spec-Driven Development for a Self-Evolving Codebase" by Yannick Roy.
- Local ADLC Graphify report refreshed on 2026-06-28 from commit `9c4432c7`.
- Local ADLC evidence reviewed:
  - `README.md`
  - `docs/research/loop-engineering-adlc-strategy-review.md`
  - `docs/build-briefs/loop-system-maturity-audit.json`
  - `docs/build-briefs/compound-engineering-adlc-implementation.json`
  - `docs/schemas/build-brief.schema.json`
  - `docs/schemas/applicability-manifest.schema.json`

The user supplied both the abstract and PDF links; they refer to the same arXiv v1 paper.

## Paper Summary

The paper argues that the binding constraint in AI-assisted software is no longer raw code generation. The hard parts are specifying what the product should do, proving it works at the real boundary, and preventing quality drift across long-running autonomous loops.

The useful primitives are:

| Paper primitive | Meaning | ADLC interpretation |
|---|---|---|
| Specification surface | Enumerable set of product capabilities and supported combinations | A schema-backed contract that declares what a feature or workflow claims to support |
| AaU1000 | LLM acts as a high-cadence synthetic power user across that surface | Scenario coverage planning, not task completion alone |
| Unbeatable tests | Ground-truth checks the code author cannot fake | Required verifier floor with independent oracle evidence |
| Regression oracle | Bounded answer to "is the system still working?" after each iteration | Build Brief and Loop Contract evidence consumed by CI, maturity audit, and drift gates |
| Drift control and pause gates | Trend monitoring that stops the loop when quality worsens | Deterministic report that emits `pass`, `pause`, or `escalate` without mutating by default |
| Discussion Manager | Structured multi-model debate for judgment-heavy decisions | An optional Eval Council extension, not the first implementation slice |

The paper's strongest operational distinction is coverage-exhaustion mode. Existing agent systems often turn an issue into a patch. Kitchen Loop starts from a product's declared surface and systematically explores scenarios until uncovered combinations and observed failures are exhausted or blocked.

## ADLC Fit

ADLC already has many of the control-plane pieces the paper treats as necessary:

- Build Briefs define task scope, verifier contracts, acceptance criteria, implementation interfaces, and productionization gates.
- Loop Contracts already bound LLM action loops with allowed tools, tests, progress, control, budget, and maturity evidence.
- `emit-work-items --require-ready`, `validate-artifact`, `loop-test-selection`, `loop-action-validate`, `loop-maturity-audit`, and `bin/adlc ci --json` provide deterministic gates.
- Eval Council, test-strength, slop gate, learning capture, Graphify research, and architecture memory provide maker-checker and durable-learning surfaces.

The paper should therefore be added as an optional ADLC coverage-exhaustion overlay, not as a new orchestrator. The first ADLC-native slice should make a workflow answer four questions before it claims Kitchen Loop style autonomy:

1. What is the enumerable specification surface?
2. Which scenario combinations must be exercised, and what coverage remains?
3. What oracle proves outcomes against independent ground truth?
4. Which drift metrics pause the loop before quality degrades?

## Recommended Additions

### 1. Specification Surface Contract

Add `docs/schemas/spec-surface.schema.json` and examples. This should represent product claims as enumerable dimensions, supported combinations, excluded states, and human-owned assumptions.

The schema should be intentionally modest:

- `surface_id`, `version`, `owner`
- `capability_claims[]`
- `dimensions[]`
- `supported_combinations[]`
- `blocked_combinations[]`
- `success_criteria[]`
- `out_of_scope[]`
- `oracle_refs[]`
- `human_assumption_refs[]`

This belongs beside Build Briefs and Loop Contracts. A Build Brief should reference a spec surface when a task claims coverage-exhaustion, broad product support, autonomous scenario generation, or production readiness across a combinatorial surface.

### 2. Scenario Coverage Plan

Add a provider-free scenario planning artifact, for example `docs/schemas/scenario-coverage-plan.schema.json`, plus a dry-run CLI command such as:

```bash
bin/adlc scenario-coverage-plan --spec-surface .adlc/spec_surface.json --build-brief .adlc/build_brief.json --json
```

The first implementation should not ask an LLM to invent infinite scenarios. It should validate and report:

- enumerated scenario candidates from declared dimensions
- tier assignment: foundation, composition, frontier
- coverage status: covered, missing, blocked, not_applicable
- required oracle per scenario
- human decision needed when success is subjective or the surface is not enumerable

### 3. UAT / Regression Oracle Contract

Add `docs/schemas/regression-oracle.schema.json` or extend Loop Contract references with an oracle contract. The important field is not "test command"; ADLC already has that. The important field is why the verifier is independent of the code author.

Minimum fields:

- `oracle_id`, `owner`, `oracle_type`
- `ground_truth_source`
- `execution_boundary`
- `state_delta_assertions[]`
- `anti_canaries[]`
- `environmental_failure_policy`
- `pre_merge_required`
- `post_merge_required`
- `coverage_limitations[]`

This should feed existing test-selection and loop-maturity evidence instead of creating another testing subsystem.

### 4. Drift Gate Report

Add `docs/schemas/drift-gate-report.schema.json` and a deterministic evaluator command, likely:

```bash
bin/adlc drift-gate-evaluate --oracle-report .adlc/oracle_report.json --history .adlc/drift_history.json --json
```

The output should be conservative:

- `status`: `pass`, `pause`, `escalate`
- regression delta
- quality trend delta
- starvation/no-work counters
- blocked-combination deltas
- latest oracle coverage
- required human action when the oracle cannot arbitrate

ADLC should not auto-merge or auto-dispatch based on this gate. It should emit a report and planned commands for the selected harness.

### 5. Eval Council / Discussion Manager Follow-Up

The paper's Discussion Manager is useful, but it should not be the first slice. ADLC already has Eval Council and code review surfaces. A later slice can add a debate-mode council only for Type 1 decisions:

- architecture choices
- "should we build this at all?"
- mutually exclusive product strategies
- cases where a kill-gate argument is required before proceeding

This should include anti-sycophancy rules, blind opening positions, issue register, capped rounds, and transcript preservation. It should not replace deterministic gates.

## What Not To Add

- Do not import Kitchen Loop wholesale or make it a required runtime dependency.
- Do not add auto-merge, auto-deploy, or production mutation.
- Do not treat LLM-authored tests as oracle evidence unless an independent ground-truth boundary exists.
- Do not claim self-autonomous support merely because a workflow has a scenario plan.
- Do not apply coverage-exhaustion to exploratory R&D, subjective UX taste, or domains without an observable oracle.

## Recommended First Slice

Build "Kitchen Loop Coverage Admission" as an ADLC-native capability:

1. Add spec-surface, scenario-coverage-plan, regression-oracle, and drift-gate schemas.
2. Add fixtures for a passing and failing coverage admission path.
3. Add read-only CLI/MCP metadata surfaces.
4. Wire the artifacts into Build Brief implementation-interface and productionization gates.
5. Add focused CLI and contract tests.
6. Validate with `bin/adlc ci --json` and refresh Graphify.

The companion Build Brief is `docs/build-briefs/kitchen-loop-coverage-admission.json`.

## No-Overclaim Boundary

This review supports a concrete ADLC implementation plan. It does not prove that ADLC already implements Kitchen Loop behavior.

Truthful current claim:

- ADLC already has strong lifecycle, schema, loop, verifier, queue, memory, and maturity primitives.
- Kitchen Loop adds a useful coverage-exhaustion overlay centered on enumerable spec surfaces and independent regression oracles.
- ADLC should first add admission contracts and deterministic validators, then consider scenario generation or debate orchestration after the evidence path is working.
