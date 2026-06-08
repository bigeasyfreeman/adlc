# ADLC Loop-System Maturity Productionization Goal Prompt

You are Codex working in the ADLC repository. Your task is to build ADLC's Loop-System Maturity layer against ADLC itself. This is framework work, not an application feature.

## Objective

Implement the Loop-System Maturity integration described by:

- `docs/build-briefs/loop-system-maturity-audit.json`

The target architecture is:

**LLM-driven action, deterministic control plane.**

The LLM proposes the next action from end-user input, the Loop Contract, workflow state, real observations, and compact compound context. ADLC then deterministically validates whether that proposed action is allowed, whether required tests or gates must run first, whether progress exists, and whether the loop should continue, steer, abort, repair, or escalate.

Do not turn this into a non-LLM deterministic runner. Do not add a parallel planner. Build this as an ADLC-native contract, schema, CLI, workflow-state, agent/skill, compound-learning, and validation layer.

## Required Preflight

1. Inspect the current branch and worktree. Preserve unrelated user changes. Do not delete, revert, or rewrite untracked prompt artifacts or `graphify-out/` unless the task explicitly requires it.
2. Read `docs/build-briefs/loop-system-maturity-audit.json` first. Treat it as the execution contract.
3. Validate the Build Brief before editing:

```bash
bin/adlc validate-artifact --schema build-brief --input docs/build-briefs/loop-system-maturity-audit.json --json
bin/adlc emit-work-items --target linear --build-brief docs/build-briefs/loop-system-maturity-audit.json --dry-run --require-ready --json
```

4. Read `graphify-out/GRAPH_REPORT.md` before broad source search. If it is missing or obviously stale, run `graphify update .` before relying on graph evidence.
5. Use `graphify query` for framework relationships before broad grep:

```bash
graphify query "How should Loop Contracts, LLM action envelopes, test selection, workflow state progress/control, loop maturity reports, and compound learning integrate into ADLC?" --budget 3000
```

6. Identify the existing ADLC primitives before editing:
   - `README.md`
   - `WORKFLOW.md`
   - `WORKFLOW.dot`
   - `scripts/adlc.py`
   - `docs/schemas/build-brief.schema.json`
   - `docs/schemas/workflow-state.schema.json`
   - `agents/planner.md`
   - `agents/test-author.md`
   - `agents/test-strength-auditor.md`
   - `skills/spec-to-tests/SKILL.md`
   - `skills/test-strength/SKILL.md`
   - `skills/codegen-context/SKILL.md`
   - `skills/eval-council/SKILL.md`
   - `skills/systematic-debugging/SKILL.md`
   - `docs/specs/compound-engineering-learning-store.md`

## Non-Negotiable Design Rule

ADLC applies the framework by letting the LLM act from the user's goal and live feedback, but every action must be admitted through deterministic constraints.

Build these responsibilities separately:

- **LLM responsibilities:** interpret the end-user goal, propose next action, explain rationale, incorporate real observations, decide whether to continue/repair/escalate within the allowed envelope.
- **Deterministic ADLC responsibilities:** validate schemas, enforce allowed tools, enforce mandatory test floors, compute required tests from task signals, preserve real feedback, detect no progress, distinguish steer from abort, require safe checkpoints, block unsupported self-autonomous claims, and emit evidence.
- **Human responsibilities:** set the rules of the game, approve unsafe/high-ambiguity escapes, and review final productionization evidence.

If the implementation collapses these roles into "the model says it is done", it fails the goal.

## Implementation Tasks

Follow the task order from the Build Brief. For each task:

1. Run the task's primary verifier before implementation and confirm it fails for the expected reason, unless the verifier already passes because prior work exists.
2. Implement the smallest ADLC-native slice that satisfies the task.
3. Run the task's primary verifier and relevant secondary verifiers.
4. Record any blocker with exact command output and the next rerun path.

### ADLC-LSMA-001: Define Loop-System Maturity as an ADLC spec

Create `docs/specs/loop-system-maturity-audit.md`.

The spec must preserve:

- the seven audit dimensions
- the 0-3 score scale
- the maturity verdicts
- the six Loop Brief blanks
- the LLM-driven action / deterministic control-plane split
- no-overclaim rules
- current ADLC maturity as Assisted loop until the evaluator proves otherwise

Primary verifier:

```bash
test -f docs/specs/loop-system-maturity-audit.md && rg -n "Real loop|Win condition|Test selection|Self-grading risk|Feedback fidelity|Control channel|Failure handling" docs/specs/loop-system-maturity-audit.md
```

### ADLC-LSMA-002: Add Loop Contract, action envelope, and maturity report schemas

Add schema-backed artifacts for:

- `docs/schemas/loop-contract.schema.json`
- `docs/schemas/loop-action.schema.json`
- `docs/schemas/loop-maturity-report.schema.json`

Add fixtures under `tests/fixtures/loop_maturity/`:

- valid assisted-loop contract
- valid loop action
- assisted-loop maturity report
- invalid missing test floor
- any additional fixtures needed for schema rejection

Wire schema aliases in `scripts/adlc.py` so `bin/adlc validate-artifact --schema loop-contract`, `--schema loop-action`, and `--schema loop-maturity-report` work.

Primary verifier:

```bash
bin/adlc validate-artifact --schema loop-maturity-report --input tests/fixtures/loop_maturity/assisted-loop-report.json --json
```

Secondary verifiers:

```bash
bin/adlc validate-artifact --schema loop-contract --input tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json --json
bin/adlc validate-artifact --schema loop-action --input tests/fixtures/loop_maturity/valid-loop-action.json --json
```

### ADLC-LSMA-003: Make test selection non-gameable

Implement the test-selection contract:

- mandatory floor that always runs
- required tests computed from task signals
- additive-only agent discretion
- self-describing coverage tags
- deterministic rejection when required tests are missing

This should extend the existing `spec-to-tests`, `test-author`, and `test-strength` path. Do not create a second independent test planner.

Expected CLI shape:

```bash
bin/adlc loop-test-selection --loop-contract tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json --test-plan tests/fixtures/loop_maturity/test-plan-complete-required.json --json
bin/adlc loop-test-selection --loop-contract tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json --test-plan tests/fixtures/loop_maturity/test-plan-missing-required.json --json
```

The complete fixture should pass. The missing-required fixture should fail with a concrete missing required-test reason.

Primary verifier from the Build Brief:

```bash
bin/adlc loop-test-selection --loop-contract tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json --test-plan tests/fixtures/loop_maturity/test-plan-missing-required.json --json
```

If the primary verifier returns nonzero for the negative fixture, that is acceptable only if the CLI output clearly proves the missing required test was caught and the positive fixture passes. Add shell tests that assert both paths.

### ADLC-LSMA-004: Add progress and control-channel workflow state

Extend workflow state for:

- `loop_progress`
- `no_progress_count`
- `control_events`
- `safe_checkpoint`
- `escalation_context`

The control model must distinguish:

- **steer:** inject context and continue
- **abort:** stop at a safe checkpoint
- **interrupt:** defer until a safe/idempotent boundary
- **escalate:** stop with context for a human decision

Do not claim live process kill-switch support unless you implement and test live signal handling. State-level control evidence is enough for this slice.

Primary verifier:

```bash
bin/adlc validate-artifact --schema workflow-state --input tests/fixtures/loop_maturity/workflow-state-control-progress.json --json
```

Also update `resume-workflow` output so progress/control summaries are visible in JSON.

### ADLC-LSMA-005: Add constrained LLM action and loop-maturity evaluator CLI

Implement:

- `bin/adlc loop-action-validate`
- `bin/adlc loop-maturity-audit`

`loop-action-validate` validates an LLM-proposed action before execution. It must check:

- action schema validity
- action type is known
- selected tool is allowed by the Loop Contract
- required preconditions are met
- mandatory tests/gates are not skipped
- current control state permits action
- safe checkpoint rules are honored
- rejected actions return concrete reasons
- escalate-routed actions include escalation context

`loop-maturity-audit` scores the seven dimensions from evidence. It must not trust the LLM's self-assessment. It may include LLM-generated rationale only when hard-gate outcomes and evidence refs are deterministic.

Primary verifier:

```bash
bin/adlc loop-action-validate --loop-contract tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json --action tests/fixtures/loop_maturity/valid-loop-action.json --state tests/fixtures/loop_maturity/workflow-state-control-progress.json --json
```

Additional required verifier:

```bash
bin/adlc loop-maturity-audit --loop-contract tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json --workflow WORKFLOW.dot --state tests/fixtures/loop_maturity/workflow-state-control-progress.json --test-plan tests/fixtures/loop_maturity/test-plan-complete-required.json --json
```

Add tests for:

- admitted action
- rejected action
- escalation-routed action
- assisted-loop report
- self-autonomous no-overclaim block when dimensions 2, 3, or 7 score 0-1

### ADLC-LSMA-006: Wire loop maturity into ADLC agents and compound learning

Update ADLC docs/prompts/skills so the new layer is actually used:

- `agents/planner.md`
- `skills/codegen-context/SKILL.md`
- `skills/eval-council/SKILL.md`
- `skills/systematic-debugging/SKILL.md`
- `docs/specs/compound-engineering-learning-store.md`
- any README/workflow docs needed for discoverability

Required behavior:

- Planner must require Loop Contract refs for autonomous-loop claims.
- Codegen context must pass compact `loop_contract`, `loop_action`, and `loop_maturity_report` refs, not full raw reports.
- Eval Council must block unsupported self-autonomous claims.
- Fixer/systematic-debugging must preserve progress/no-progress evidence.
- Compound learning must capture verified loop patterns only from maturity reports with verifier evidence and stale conditions.
- Emitters must preserve loop refs in normalized payloads if task metadata carries them.

Primary verifier:

```bash
rg -n "loop_contract|loop_action|loop_maturity_report|self-autonomous|assisted loop|no-overclaim" agents/planner.md skills/codegen-context/SKILL.md skills/eval-council/SKILL.md skills/systematic-debugging/SKILL.md docs/specs/compound-engineering-learning-store.md
```

### ADLC-LSMA-VAL: Validate loop-system maturity integration end to end

Run the full productionization validation suite.

Minimum required commands:

```bash
git diff --check
bin/adlc validate-artifact --schema build-brief --input docs/build-briefs/loop-system-maturity-audit.json --json
bin/adlc emit-work-items --target linear --build-brief docs/build-briefs/loop-system-maturity-audit.json --dry-run --require-ready --json
bin/adlc validate-artifact --schema loop-contract --input tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json --json
bin/adlc validate-artifact --schema loop-action --input tests/fixtures/loop_maturity/valid-loop-action.json --json
bin/adlc validate-artifact --schema loop-maturity-report --input tests/fixtures/loop_maturity/assisted-loop-report.json --json
bin/adlc loop-test-selection --loop-contract tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json --test-plan tests/fixtures/loop_maturity/test-plan-complete-required.json --json
bin/adlc loop-action-validate --loop-contract tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json --action tests/fixtures/loop_maturity/valid-loop-action.json --state tests/fixtures/loop_maturity/workflow-state-control-progress.json --json
bin/adlc loop-maturity-audit --loop-contract tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json --workflow WORKFLOW.dot --state tests/fixtures/loop_maturity/workflow-state-control-progress.json --test-plan tests/fixtures/loop_maturity/test-plan-complete-required.json --json
tests/test_adlc_contracts.sh
tests/test_adlc_cli.sh
```

Run smoke if the runtime adapter and local environment can support it:

```bash
tests/smoke/run_smoke.sh
```

If smoke cannot run because of missing runtime credentials, missing adapter, sandbox, or external environment, report the exact blocker and keep deterministic CLI/schema validation as the minimum gate.

Run Graphify after code/doc changes:

```bash
graphify update .
graphify query "How does ADLC integrate Loop Contracts, LLM action envelopes, non-gameable test selection, progress/control workflow state, maturity reports, and compound learning?" --budget 3000
```

## Productionization Gates

The implementation is not productionized until all applicable gates below are satisfied.

### Compatibility

- Existing Build Brief fixtures still validate.
- Existing workflow states still validate.
- Existing `emit-work-items` behavior still works when loop maturity refs are absent.
- New fields are optional unless a workflow explicitly claims autonomous-loop behavior.

### No-Overclaim

- ADLC must not claim global self-autonomous status.
- Self-autonomous status is per workflow or task and must be emitted only by `loop-maturity-audit`.
- A missing Loop Contract or action envelope downgrades an autonomous claim to assisted-loop status.
- Low score on win-condition rigor, non-gameable test selection, or failure handling blocks self-autonomous verdict.
- Live kill-switch support is unsupported unless separately implemented and tested.
- External-provider rollback is unsupported unless provider-specific rollback exists.

### Security And Privacy

- Loop feedback artifacts must avoid storing secrets.
- Command output in reports must be bounded or referenced by artifact path.
- Compound learning must capture distilled, redacted loop patterns, not raw logs.
- LLM-proposed actions must not execute outside the declared allowed tools.

### Reliability

- No-progress detection must use evidence, not only retry count.
- Control events must distinguish steer, abort, interrupt, and escalate.
- Escalation must include phase, failing verifier, recent observations, no-progress reason, and requested human decision.
- Side-effect logging must stay idempotent.

### Observability

Maturity reports must show:

- dimension scores
- evidence refs
- missing mechanisms
- action admission status
- required test-floor status
- progress/no-progress state
- control events
- safe checkpoint
- escalation context
- maturity verdict
- highest-leverage gap

## End State

At completion, ADLC should be able to:

1. Take an end-user goal and let the LLM propose the next loop action.
2. Validate that action against a Loop Contract before execution.
3. Force required tests and gates to run.
4. Feed real observations back into the next action decision.
5. Detect no-progress loops.
6. Distinguish steering from aborting.
7. Escalate with context.
8. Score loop maturity without trusting the model's self-assessment.
9. Capture verified loop patterns into compound engineering learning refs.
10. Emit ready work items and validation evidence without overclaiming production status.

## Final Response Requirements

Report:

- Changed files.
- Which LSMA tasks were completed.
- Exact validation commands and results.
- Current loop maturity verdict after implementation.
- Any unsupported states that remain.
- Whether smoke ran; if not, the exact blocker.
- Graphify update/query result.
- Any follow-up tasks needed before self-autonomous claims can be made.

Do not say the work is complete unless the validation commands above pass or a blocker is documented with the exact rerun path.
