# Loop-System Maturity Audit

ADLC uses loop-system maturity to separate real autonomous loops from one-shot prompting. The target is not a non-LLM runner. The target is LLM-driven action with a deterministic control plane.

The LLM proposes the next action from end-user input, the Loop Contract, workflow state, real observations, and compact compound context. ADLC admits or rejects that action with deterministic checks: schema validity, allowed tools, required tests, progress, control state, safe checkpoints, and no-overclaim gates.

## Maturity Scale

- `0`: absent
- `1`: ad hoc
- `2`: present but gameable or fragile
- `3`: robust

Verdicts:

- `one_shot_in_disguise`: several dimensions score `0` or `1`.
- `assisted_loop`: mostly `2`, with bounded loop machinery but missing one or more robust autonomy controls.
- `self_autonomous`: mostly `3`, with no `0` or `1` on win condition rigor, test selection, or failure handling.

## Current ADLC Baseline

ADLC currently scores as `assisted_loop`. It has a directed workflow graph, labels, retry caps, verifier-first test generation, workflow state, test-strength audit, compound preflight, Loop Contract/action validators, execution-backed required-test result artifacts, and human gates. It still treats self-autonomy as a per-workflow evidence claim, not a default framework claim, and tag-only required-test plans are capped below robust.

## Seven Audit Dimensions

### Real loop

Check whether the system performs act -> observe -> decide -> repeat, can run more than once, and can recover from a bad step. A loop that cannot change course based on observations is one-shot prompting in disguise.

Evidence sources: workflow graph edges, labels, retry caps, phase history, action envelopes, observations, and repair/escalation routes.

### Win condition

Check whether done and correct is proven by deterministic code: schema validation, tests, invariant checks, and required evidence. The contract should specify the outcome or invariant, not a prescribed implementation path.

Evidence sources: `job_win_condition`, verifier commands, expected failure modes, schema checks, and post-change proof.

### Test selection

Check whether required tests cannot be gamed. A Loop Contract must declare:

- `mandatory_floor`: tests or gates that always run.
- `required_from_task_signals`: tests computed from task signals such as changed files, schemas, acceptance criteria, production invariants, and interface contracts.
- `additive_agent_tests`: model-selected tests that may add coverage but may never remove required tests.
- `coverage_tags`: machine-readable tags proving what each test covers.
- `loop-test-result`: executed command records proving each required test actually ran and passed.

If an agent could skip the test that catches its own bug, this dimension scores at most `1`. If required tests are only tag-covered without executed result evidence, this dimension is capped at `2`.

### Self-grading risk

Check whether verification uses independent or golden truth. Agent-authored tests can be useful, but they are circular when they are the only proof for agent-written code.

Evidence sources: independent verifier, golden fixtures, mutation results, external command output, or explicit circular-proof warnings.

### Feedback fidelity

Check whether the loop observes real results after every action: command output, test output, errors, changed artifacts, and state transitions. Acting on imagined results scores at most `1`.

Evidence sources: workflow history, stdout/stderr refs, test reports, action observations, and side-effect logs.

### Control channel

Check whether the loop has out-of-band control:

- `steer`: inject context and continue.
- `abort`: stop at a safe checkpoint.
- `interrupt`: defer until an idempotent boundary.
- `escalate`: stop with context for a human decision.

Live process kill-switch support is a separate claim. State-level control evidence is not live signal handling.

### Failure handling

Check whether failures are detected, classified, and routed to retry, repair, re-plan, escalate, or abort-safe. This must include progress signals, not only error signals, so ADLC catches loops that run confidently while getting nowhere.

Evidence sources: retry budgets, failure classes, no-progress counters, recent observations, escalation context, and repair route.

## Loop Brief

Every workflow that claims autonomous-loop behavior must fill these blanks:

1. **The job and win condition**: what is done, and how the loop proves it is correct.
2. **Allowed tools**: the specific actions the loop may take.
3. **Feedback after each step**: the real result fed back after every action.
4. **Stop and escalate rules**: max tries, no-progress threshold, high-stakes/high-uncertainty triggers, missing authority, or ambiguity.
5. **Tests**: mandatory floor, required tests from task signals, and additive-only agent tests.
6. **Safe state if it bails**: known-good state, rollback posture, and idempotent checkpoint.

## LLM Action Envelope

The LLM may choose the next action, but it must emit a structured action envelope. ADLC validates the envelope before execution. A valid action names the action type, selected tool, rationale, expected observation, preconditions, required tests it satisfies, checkpoint requirements, and rollback note.

The deterministic validator admits, rejects, repair-routes, or escalation-routes the action. The model's rationale is not sufficient evidence.

## No-Overclaim Rules

- Missing Loop Contract or action envelope downgrades autonomous claims to `assisted_loop`.
- Missing required tests or missing executed required-test result evidence blocks `self_autonomous`.
- A score of `0` or `1` on win condition, test selection, or failure handling blocks `self_autonomous`.
- Live kill-switch support is unsupported unless implemented and tested.
- External-provider rollback is unsupported unless provider-specific rollback exists.
- Compound learning capture may store only verified, redacted loop patterns with maturity-report evidence and stale conditions.
