---
name: spec-to-tests
description: Authors failing tests and reproducers from Build Brief acceptance criteria plus verification_spec before coding starts.
contract_version: 1.0.0
side_effect_profile: mutating
---

# Why This Exists

Spec -> tests is the locking stage. The Build Brief names the contract; failing tests and reproducers turn that contract into a harness that blocks guesswork and anchors code to correctness. Coding should begin only after the verifier fails for the documented reason.

## Trigger

```yaml
phase: 3
event: context_assembly_pending
requires:
  - applicability_manifest
  - verification_spec
  - structured acceptance_criteria
```

This skill runs when `gen_tests` receives assembled Build Brief context for a task and must author the native failing verifier artifacts that the coder will inherit.

## Inputs

Use exactly these inputs:

- `task_classification`
- `verification_spec` (`primary_verifier`, `secondary_verifiers`, optional `target_files`, optional `expected_failure_mode`)
- per-task `acceptance_criteria`
- `files_to_create/modify`
- `reference_impl` path
- repo test conventions discovered at runtime

If any acceptance criterion arrives as an unstructured string with no normalized `id`, `given`, `when`, and `then`, do not invent structure. Emit `stuck`.

## Outputs

- Test files written under the repo's native test root and naming conventions
- `.adlc/test_plan.json` mapping `ac_id -> test_path -> expected_pre_change_failure_reason`
- `.adlc/pre_change_run.txt` capturing stdout from the pre-change run that proves the generated verifier fails for the documented reason

## Authoring Workflow

1. Read the task's `verification_spec`, `acceptance_criteria`, `files_to_create/modify`, and `reference_impl`.
2. Discover the repo's native test root, framework, helper layout, fixture style, and test naming conventions at runtime.
3. Normalize verifier scope against `verification_spec.target_files` when present.
4. Author the smallest failing tests or reproducers that make each acceptance criterion falsifiable before code changes.
5. Run the generated verifier set before editing production code.
6. Record the failing stdout in `.adlc/pre_change_run.txt`.
7. Emit `.adlc/test_plan.json` only after the self-check passes.

## Behavior by Task Class

### `feature`

- Translate every acceptance criterion into at least one named test that exercises the public behavior promised by the brief.
- Prefer tests at the narrowest stable seam already used by the repo: public API, service entrypoint, command handler, or component contract.
- Reuse existing fixtures, factories, and helper setup from the discovered test conventions before creating new data scaffolding.
- Make the pre-change failure expose the missing behavior directly in the assertion message, not via a broad "command failed" wrapper.

### `bugfix`

- Start from the observed failure path and encode the regression as the first failing test or reproducer.
- Keep the fixture or input payload as small as possible while still reproducing the bug.
- Assert both the corrected behavior and the absence of the prior broken result when that can be checked deterministically.
- Name the test after the defect condition so the future failure explains what regressed.

### `build_validation`

- Treat the failing build or test command as the primary verifier and add authored tests only when they sharpen the failure around the changed files.
- If a test is needed, bind it to the compile path, generated artifact, or contract that the command is failing on.
- Capture the exact command output that proves the repo still fails before the code change.
- Do not expand maintenance work into unrelated behavioral suites just to satisfy ceremony.

### `lint_cleanup`

- Use the exact lint, fmt, or static-analysis failure as the primary verifier and only author tests when the rule enforces a real code contract.
- Assert the concrete diagnostic, formatting delta, or emitted artifact that the lint rule guards.
- Keep authored reproducers scoped to the files and rules named in the brief.
- Avoid runtime behavior tests unless the lint issue changes executable output.

### `refactor`

- Add characterization tests at the public seams around the files being reorganized before moving code.
- Favor assertions that pin stable behavior, serialized output, or cross-module contracts over internal implementation details.
- When `target_files` is set, place or select tests whose paths intersect those files or the immediate native test peer paths that exercise them.
- Split large refactor coverage into multiple small tests so each acceptance criterion stays traceable.

### `infra`

- Author smoke tests or reproducers around startup scripts, CI glue, migrations, configuration rendering, or deployment entrypoints touched by the task.
- Assert exit codes, rendered config, artifact creation, or orchestrated command output instead of human inspection steps.
- Replace ambient environment assumptions with deterministic fixtures, temp directories, or mocked process inputs.
- Tie each test name to the operational invariant the infra change must preserve.

### `docs`

- Convert executable examples, CLI snippets, schema examples, or config fragments in scope into doctest-style verifiers or reproducers.
- Assert the documented command output, parse result, validation result, or sample render that the docs promise.
- Keep tests tied to the documented surface in `target_files` when those paths are provided.
- Reject prose-only completion when the brief still defines a deterministic verifier.

### `security`

- Author negative tests first: unauthorized access, malformed input, missing auth, unsafe output, or invariant-violation attempts.
- Assert the exact denial status, redaction behavior, audit event, or invariant hold that separates secure from insecure behavior.
- Use deterministic malicious payload fixtures; do not rely on live services or random fuzzing for the gating test.
- When `expected_failure_mode` is set, make the pre-change run show that specific vulnerable behavior or failure signature before coding starts.

## Quality Gates

Before emitting `done`, all of these must pass:

1. Every `acceptance_criteria` id has >=1 generated test.
2. Every test has at least one concrete assertion; no `assert true`, no empty bodies.
3. Pre-change run captured; failure reason matches `expected_failure_mode` when set.
4. Test file paths intersect `verification_spec.target_files` when `target_files` is set.
5. Generated tests pass stop-slop anti-stub patterns.
6. `test_plan.json` validates against the schema in this skill.

## Output Schema (`test_plan.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ADLC Spec-to-Tests Plan",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "brief_id",
    "task_id",
    "generated_tests",
    "pre_change_run_path",
    "verifier_target_intersection",
    "self_check"
  ],
  "properties": {
    "brief_id": {
      "type": "string",
      "minLength": 1
    },
    "task_id": {
      "type": "string",
      "minLength": 1
    },
    "generated_tests": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "ac_id",
          "test_path",
          "test_name",
          "expected_pre_change_failure_reason",
          "assertion_count"
        ],
        "properties": {
          "ac_id": {
            "type": "string",
            "pattern": "^AC-[A-Z0-9_-]+$"
          },
          "test_path": {
            "type": "string",
            "minLength": 1
          },
          "test_name": {
            "type": "string",
            "minLength": 1
          },
          "expected_pre_change_failure_reason": {
            "type": "string",
            "minLength": 1
          },
          "assertion_count": {
            "type": "integer",
            "minimum": 1
          }
        }
      }
    },
    "pre_change_run_path": {
      "type": "string",
      "const": ".adlc/pre_change_run.txt"
    },
    "verifier_target_intersection": {
      "type": "boolean"
    },
    "self_check": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "gate_1",
        "gate_2",
        "gate_3",
        "gate_4",
        "gate_5",
        "gate_6"
      ],
      "properties": {
        "gate_1": {
          "type": "string",
          "enum": ["pass", "fail"]
        },
        "gate_2": {
          "type": "string",
          "enum": ["pass", "fail"]
        },
        "gate_3": {
          "type": "string",
          "enum": ["pass", "fail"]
        },
        "gate_4": {
          "type": "string",
          "enum": ["pass", "fail"]
        },
        "gate_5": {
          "type": "string",
          "enum": ["pass", "fail"]
        },
        "gate_6": {
          "type": "string",
          "enum": ["pass", "fail"]
        }
      }
    }
  }
}
```

## Failure Modes

- Missing structured acceptance criteria -> emit `stuck`.
- Cannot make the authored verifier fail pre-change -> emit `stuck`.
- Verifier coverage against `target_files` cannot be confirmed -> emit `revise`.

## Anti-Slop

No TODO/FIXME/PLACEHOLDER. No stub functions. No commented-out code. Every function has a real implementation. Every import is used.

Banned in shipped code and generated tests:

- `TODO`, `FIXME`, `PLACEHOLDER`
- `todo!()`, `unimplemented!()`, `panic!("not implemented")`
- `NotImplementedError`, `pass`, empty placeholder bodies
- fake/mock placeholder logic in production code
- unwired entry points, dead handlers, unused providers, and unused config added "for later"
- `assert true`, empty `it()` or `test()` bodies, and snapshot-only tests with no concrete assertion

## Examples

### Feature Example

Input acceptance criterion:

```json
{
  "id": "AC-BALANCE-ZERO",
  "given": "a newly created account with no ledger entries",
  "when": "the account summary is requested",
  "then": "the summary returns balance_cents set to 0",
  "measurable_post_condition": "response.json.balance_cents == 0"
}
```

Output test body:

```python
def test_account_summary_returns_zero_balance_for_new_account(client, account_factory):
    account = account_factory(entries=[])

    response = client.get(f"/accounts/{account.id}/summary")

    assert response.status_code == 200
    assert response.json["balance_cents"] == 0
```

Expected pre-change failure reason:

```text
AssertionError: assert None == 0
```

### Bugfix Example

Input acceptance criterion:

```json
{
  "id": "AC-CSV-TRAILING-NEWLINE",
  "given": "a CSV export with one data row",
  "when": "the exporter serializes the file",
  "then": "the export ends with exactly one trailing newline"
}
```

Output test body:

```python
def test_export_csv_ends_with_exactly_one_trailing_newline(report_factory):
    report = report_factory(rows=[{"id": 1, "name": "Ada"}])

    output = export_csv(report)

    assert output.endswith("\n")
    assert not output.endswith("\n\n")
    assert output == "id,name\n1,Ada\n"
```

Expected pre-change failure reason:

```text
AssertionError: assert not True
```
