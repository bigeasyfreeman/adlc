# Skill: Verification Discipline

> Enforces task-class-aware verification during execution. The source of truth is `verification_spec`, not a universal TDD ritual.

---

## Why This Exists

ADLC needs one discipline for all tasks, but not one verifier shape for all tasks. The right verifier depends on what changed:
- `feature` tasks need behavior-defining tests
- `bugfix` tasks need a reproducible failure first
- `build_validation` tasks need the exact failing build or test command
- `lint_cleanup` tasks need the exact failing lint, fmt, or static-analysis command

The goal is to prevent false greens without forcing fake behavioral tests onto maintenance work. Strong verification is task-class-specific.

---

## Trigger

This skill operates at execution time, when a task reaches a coding agent.

```yaml
triggers:
  - phase: 3
    event: task_dispatched_to_coding_agent
    action: verify `task_classification` and `verification_spec` are present
  - phase: 3
    event: verification_spec_missing_or_weak
    action: stop and request clarification
```

The upstream planner must provide:
- `task_classification`
- `verification_spec`
- `verifier_quality`
- any task-specific acceptance criteria or reproducer notes

If those fields are missing, the execution agent should not invent a ceremony. It should stop.

---

## Task Classes

### `feature`
- Use acceptance criteria as the verifier source.
- Prefer explicit test cases and edge cases.
- If pre-written tests exist, run them first and confirm they fail for the current code.
- If tests do not exist, write the smallest test that describes the intended behavior.

### `bugfix`
- Start from the observed failure.
- Use the smallest deterministic reproducer that fails for the right reason.
- Add or keep a regression guard after the fix.
- Do not invent broad feature tests when the bug is already described by a concrete failure.

### `build_validation`
- Use the exact failing build, compile, or test command as the primary verifier.
- The verifier should fail before the fix and pass after the fix.
- Do not add behavioral tests unless the build failure is caused by changed behavior.

### `lint_cleanup`
- Use the exact failing lint, fmt, or static-analysis command as the primary verifier.
- Keep behavior unchanged unless the lint fix necessarily changes code.
- Do not manufacture runtime tests to justify style or hygiene work.

### Fallback for `refactor` or `infra`
- Choose the verifier from the dominant change surface.
- If behavior changes, use `feature` or `bugfix` rules.
- If the task is purely mechanical, use `build_validation` or `lint_cleanup` rules.

---

## Verification Loop

The execution agent should follow this loop:

1. Record the primary verifier from `verification_spec`
2. Run the verifier in the current codebase
3. If it already passes, decide whether the task is already satisfied or the verifier is wrong
4. Make the smallest change that addresses the verified failure
5. Re-run the primary verifier until it passes
6. Run any secondary verifiers from `verification_spec`
7. Refactor only after the primary verifier passes

The point is not ceremony. The point is to bind implementation to a falsifiable signal that matches the task class.

---

## Verifier Quality

Every verifier must satisfy these rules:

- It matches the task class
- It is falsifiable before the change
- It is as close as possible to the real defect
- It is deterministic and low-noise
- It is minimal sufficient coverage, not ornamental coverage
- It provides regression value against the specific failure mode
- It does not pass for unrelated reasons

If a verifier passes too early, it is either the wrong verifier or the thing already exists.

---

## Integration With Codegen Context

The codegen-context skill should receive the `verification_spec` and convert it into the right execution prompt:

```markdown
## Verification Spec
- Task class: `[task_classification]`
- Primary verifier: `[type + command/test/reproducer]`
- Expected pre-change result: fail
- Expected post-change result: pass
- Secondary verifiers: `[optional list]`
- Scope note: `[why this verifier is sufficient]`

## Task-Class Instructions
- Feature: write or run the behavioral tests that define success
- Bugfix: reproduce the failure first, then fix it
- Build validation: use the exact failing build/test command
- Lint cleanup: use the exact failing lint/fmt/static-analysis command
```

The assembled context should not imply that every task must start with new behavioral tests.

---

## Violations And Enforcement

| Violation | Detection | Response |
|-----------|-----------|----------|
| No `verification_spec` provided | Missing upstream field | Stop and request clarification |
| Verifier does not match task class | `feature` task using only `cargo fmt --check`, or `lint_cleanup` task using invented tests | Reject the verifier |
| Verifier passes before the fix for the wrong reason | Current code already satisfies the check, or the check is too weak | Treat the verifier as invalid |
| Production code added without any verifier evidence | Diff shows code changes but no failing verifier or reproducer | Block completion |
| Weak verifier masks a false green | Task appears done but the failure mode is still present | Strengthen the verifier before approving |

---

## Quality Gates

- [ ] Every task has one primary verifier in `verification_spec`
- [ ] The verifier is task-class-aware
- [ ] The verifier fails before the fix for the right reason
- [ ] The verifier passes after the fix
- [ ] Secondary verifiers are only used when they add signal
- [ ] No universal RED/GREEN/REFACTOR wording is required in task output
- [ ] No task is forced into behavioral tests when the task class is maintenance

## Framework Hardening Addendum

- **Contract versioning:** `verification_spec` payloads should include `contract_version`
- **Schema validation:** Validate `task_classification` and verifier shape before execution
- **Budget controls:** Apply token pre-turn checks to any LLM-assisted verifier synthesis
- **Structured errors:** Emit deterministic failures such as `missing_verification_spec`, `invalid_task_classification`, `weak_verifier`, `non_deterministic_verifier`, and `verifier_mismatch`
