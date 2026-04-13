---
name: test-strength
description: Audits generated test strength on changed files using coverage diff and mutation kill rate after QA passes.
contract_version: 1.0.0
side_effect_profile: mutating
---

# Why This Exists

Passing tests are necessary but not sufficient. SWE-ABS-style test strength asks whether the generated verifier suite actually exercises the changed code and detects wrong behavior instead of merely replaying the happy path. This skill turns that question into a concrete audit before delivery.

## Trigger

Run at phase 4 after `qa` passes and before `slop_gate`. In repos where `slop_gate` is still implicit, run after `qa` and before the next delivery gate.

## Inputs

Use these inputs:

- changed files from `git diff`
- generated tests from `.adlc/test_plan.json`
- language-appropriate mutation config

Mutation tooling is optional at the repo level, but not optional for a passing audit. If the repo language is unsupported or the standard mutator is unavailable, emit `stuck` instead of silently passing.

## Supported Language Detection

Detect the dominant repo language from changed files and repo conventions:

- Python -> `mutmut`
- JavaScript or TypeScript -> `stryker`
- Rust -> `cargo-mutants`

If the changed files span multiple supported languages, audit the language that owns the generated tests in `.adlc/test_plan.json` and record the rationale in the report.

## Audit Workflow

1. Read `.adlc/test_plan.json` and collect the generated test paths plus their target acceptance criteria.
2. Compute changed executable lines from `git diff` for the files under audit.
3. Run the generated tests with coverage scoped to the changed files.
4. Calculate coverage diff on changed executable lines only.
5. Detect the repo language and the standard mutation tool for that language.
6. Run mutation analysis on the changed files only.
7. Write `.adlc/test_strength_report.json` with thresholds, per-file coverage, mutant counts, language detection rationale, and the verdict.

## Gates

### Coverage Diff

- Threshold: `>= 80%` of changed executable lines must be covered by the generated tests.
- Use the generated tests from `.adlc/test_plan.json` as the audit scope, not the whole suite.
- Coverage is measured per changed file and summarized across the changed-file set.

### Mutation Survival

- Threshold: `>= 60%` mutation kill rate on changed files.
- Use the language's standard mutator:
  - Python -> `mutmut`
  - JavaScript / TypeScript -> `stryker`
  - Rust -> `cargo-mutants`
- If the mutator is unsupported or unavailable, emit `stuck`.

## Output

Write `.adlc/test_strength_report.json`.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ADLC Test Strength Report",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "report_path",
    "language",
    "language_detection_rationale",
    "coverage_threshold",
    "mutation_threshold",
    "files",
    "mutants_generated",
    "mutants_killed",
    "kill_rate",
    "verdict"
  ],
  "properties": {
    "report_path": {
      "type": "string",
      "const": ".adlc/test_strength_report.json"
    },
    "language": {
      "type": "string",
      "enum": ["python", "javascript", "typescript", "rust", "unknown"]
    },
    "language_detection_rationale": {
      "type": "string",
      "minLength": 1
    },
    "coverage_threshold": {
      "type": "number",
      "const": 0.8
    },
    "mutation_threshold": {
      "type": "number",
      "const": 0.6
    },
    "files": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "path",
          "changed_executable_lines",
          "covered_changed_lines",
          "coverage_ratio"
        ],
        "properties": {
          "path": {
            "type": "string",
            "minLength": 1
          },
          "changed_executable_lines": {
            "type": "integer",
            "minimum": 0
          },
          "covered_changed_lines": {
            "type": "integer",
            "minimum": 0
          },
          "coverage_ratio": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          }
        }
      }
    },
    "mutants_generated": {
      "type": "integer",
      "minimum": 0
    },
    "mutants_killed": {
      "type": "integer",
      "minimum": 0
    },
    "kill_rate": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },
    "verdict": {
      "type": "string",
      "enum": ["pass", "weak", "stuck"]
    },
    "stuck_reason": {
      "type": "string"
    }
  }
}
```

## Failure Modes

- Coverage diff below `0.8` -> emit `weak`.
- Mutation kill rate below `0.6` -> emit `weak`.
- Unsupported repo language -> emit `stuck`.
- Standard mutator unavailable -> emit `stuck`.
- Missing or invalid `.adlc/test_plan.json` -> emit `stuck`.

Weak findings are for test strengthening, not for waving away. The current DAG routes `weak` into the repair loop; that loop must return through test authoring before the next audit, and the retry budget is capped at `test_strength_retry = 2`.

## Quality Gates

Before emitting `pass`, `weak`, or `stuck`, confirm:

1. `.adlc/test_strength_report.json` parses against the schema in this skill.
2. The report records `coverage_threshold` as `0.8` and `mutation_threshold` as `0.6`.
3. The report includes a non-empty `language_detection_rationale`.
4. No threshold is silently defaulted or omitted.

## Output Labels

- `pass`: both thresholds met
- `weak`: coverage or mutation strength below threshold
- `stuck`: no supported language, no available standard mutator, or invalid audit input
