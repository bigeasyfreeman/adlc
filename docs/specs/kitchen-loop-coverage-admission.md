# Kitchen Loop Coverage Admission

Kitchen Loop Coverage Admission is an optional ADLC contract layer for workflows
that want to claim broad product coverage, coverage exhaustion, or autonomous
scenario evolution. It does not generate scenarios, run agents, mutate trackers,
merge code, deploy, or upgrade a workflow to `self_autonomous` on its own.

The layer is activated by explicit task evidence such as `kitchen-loop`,
`coverage-admission`, `coverage-exhaustion`, or these refs:

- `spec-surface:<path-or-id>`
- `scenario-coverage-plan:<path-or-id>`
- `regression-oracle:<path-or-id>`
- `drift-gate-report:<path-or-id>`

When activated, `bin/adlc emit-work-items --require-ready` requires all four ref
classes before the task is ready.

## Contracts

`spec-surface` declares the bounded product or framework surface. It must name
capability claims, dimensions, supported combinations, oracle refs, deterministic
success criteria, unsupported states, out-of-scope claims, and redaction posture.
Non-enumerable surfaces fail admission.

`scenario-coverage-plan` declares the bounded scenario set. It must set
`bounded=true`, cap `max_scenarios`, tie each scenario to an oracle, and record
covered, missing, blocked, and not-applicable counts. Missing runnable coverage
blocks the command.

`regression-oracle` declares independent truth. It must name the ground-truth
source, execution boundary, state-delta assertions, anti-canaries, environmental
failure policy, coverage limitations, and redaction posture. LLM self-assessment
is not independent truth.

`drift-gate-report` records whether more work can proceed. `pass` admits the next
step. `pause` and `escalate` fail closed until a human or higher-level controller
resolves the drift.

## Commands

```bash
bin/adlc validate-artifact --schema spec-surface --input tests/fixtures/kitchen_loop/valid-spec-surface.json --json
bin/adlc coverage-surface-validate --input tests/fixtures/kitchen_loop/valid-spec-surface.json --json
bin/adlc scenario-coverage-plan --input tests/fixtures/kitchen_loop/valid-scenario-coverage-plan.json --spec-surface tests/fixtures/kitchen_loop/valid-spec-surface.json --json
bin/adlc regression-oracle-validate --input tests/fixtures/kitchen_loop/valid-regression-oracle.json --json
bin/adlc drift-gate-evaluate --input tests/fixtures/kitchen_loop/valid-drift-gate-report.json --json
```

All commands are local and read-only. Future generators or schedulers must stay
behind the existing ADLC action-admission and human-gate surfaces.
