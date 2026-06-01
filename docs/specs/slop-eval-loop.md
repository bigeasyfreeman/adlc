# Slop Eval Loop

## Purpose

ADLC treats AI slop as an output-side quality-control problem. Better prompts,
larger models, and longer context can improve generation, but they do not prove
the output is good enough to ship. The missing primitive is a repeatable eval
loop that scores output against a benchmark, blocks regressions, and turns every
failure into a future test case.

This contract applies when a task creates or changes a generated-output
surface: prompt behavior, model selection, agent roles, content templates,
response shaping, product output, user-visible AI output, or output validators.
Ordinary code-only, docs-only, lint-only, and build-validation tasks do not
inherit this gate unless they also change one of those surfaces. The loop is:

1. Define what good output looks like.
2. Convert that standard into cases, metrics, and thresholds.
3. Score output before it ships.
4. Block or revise output below the line.
5. Sample real output after release when the surface is live.
6. Promote failures and human edits back into the eval case set.

## Benchmark Contract

A slop benchmark has three required pieces:

| Piece | Meaning | Examples |
|---|---|---|
| Eval cases | Representative inputs and the expected quality bar | Golden content, production logs, rejected council outputs, human edits, incidents |
| Metrics | How output becomes a number from 0 to 1 | Exact match, JSON validator, semantic judge, rubric score, test-strength score |
| Threshold | The line below which output does not ship | `0.70` for judgment outputs, existing `test-strength` thresholds for code |

The Build Brief task field is `slop_quality_gate`.

```json
{
  "applicability": "required",
  "reason": "Task changes generated user-visible agent output.",
  "mode": "agent_output",
  "threshold": 0.7,
  "metrics": [
    {
      "metric_type": "rubric_score",
      "validator_ref": "skills/slop-judge/SKILL.md"
    },
    {
      "metric_type": "schema_validity",
      "validator_ref": "docs/schemas/<output>.schema.json"
    }
  ],
  "eval_cases": [
    {
      "id": "SLOP-001",
      "source": "golden",
      "input": "Customer asks for refund status",
      "expected_quality": "Specific, policy-aware answer with no invented dates",
      "metric": "rubric_score",
      "threshold": 0.75
    }
  ],
  "baseline_score": 0.82,
  "regression_tolerance": 0.03,
  "failure_action": "block",
  "case_promotion_sources": ["human_edit", "council_rejection", "production_sample"]
}
```

If upstream material already includes `slop_quality_gate` for a task that does
not create or alter generated output, prompt behavior, model selection, agent
roles, content, or product responses, preserve it only as:

```json
{
  "applicability": "not_applicable",
  "reason": "Lint-only change with no generated-output surface."
}
```

## Where The Loop Runs

### 1. Pre-Ship Regression

Any prompt, model, agent-role, content-template, response-shaping, or product
output change must run against the saved eval cases before shipping. Compare the
new score with the baseline. A drop beyond `regression_tolerance` blocks unless
the Build Brief names a human approval checkpoint.

### 2. Delivery Guard

Before generated output reaches a user, customer, ticket, issue, PR, document,
or release, the relevant active gate runs:

- `bin/adlc slop-gate` for Build Brief slop-gate contract checks.
- `stop-slop` for project-configured deterministic code or prose slop checks.
- `slop-judge` for rubric-based judgment after deterministic checks clear.
- `test-strength` for code verification strength.
- Task-specific validators for product output shape, schemas, and invariants.

### 3. Post-Ship Sampling

Live generated-output systems need sampling. ADLC does not require a specific
cron, dashboard, or chat integration. It requires the contract: sample real
executions, score them with the same benchmark, and file a case-promotion event
when quality drops.

## Mode Rules

### Code

Code quality starts with deterministic gates. Placeholder code, missing wiring,
duplicate blocks, and missing tests remain hard failures. Code tasks also use the
existing `test-strength` thresholds:

- coverage diff score must be at least `0.8`
- mutation kill rate must be at least `0.6`
- material surviving mutants make the task `weak`

Code slop cases are promoted from reviewer findings, failed test-strength runs,
incident fixes, and repeated human edits.

### Content

Content uses a rubric, not only banned phrases. The default threshold is `0.70`.
The rubric must name concrete criteria such as specificity, actionability,
audience fit, and novelty. Vague rubrics such as "is this good" are invalid.

### Product And Agent Output

Product output uses the metric that matches the task:

- exact match for labels and routing decisions
- structural validator for JSON, schemas, and required fields
- semantic or rubric judge for open-ended responses
- invariant checks for identity, tenancy, data integrity, safety, and rollback

Product and agent output changes must include at least one eval case from a real
or realistic input, not only a happy-path example.

## Case Promotion

The eval suite improves only when failures become tests. The following events
create candidate eval cases before they become new skill rules:

- human edits that remove slop or correct wrong output
- council rejections
- runtime failures
- production samples below threshold
- incidents or support tickets caused by generated output
- analytics drops tied to generated output quality

Promotion record:

```json
{
  "source": "human_edit",
  "input": "string",
  "bad_output": "string",
  "corrected_output": "string",
  "expected_quality": "string",
  "metric": "rubric_score",
  "threshold": 0.7,
  "owner": "string"
}
```

Candidate cases need human or council approval before they become permanent
blocking gates. Once accepted, the case belongs in the benchmark, not only in a
prompt note.

## Non-Goals

- ADLC does not adopt Hermes-specific installation, channels, cron, or approval
  button mechanics.
- ADLC does not treat prompt tuning as sufficient proof.
- ADLC does not require slop benchmarks for trivial docs, lint-only cleanup, or
  build validation with no generated-output surface.
- ADLC does not let benchmarks become a large context file. Cases should be
  small, versioned, and tied to the task surface.

## Removal Criteria

This loop follows BPE discipline. Remove or lower a rule when it has not caught a
real issue for 30 days, contradicts a stronger deterministic gate, or exists only
to work around an outdated model limitation. Keep cases that represent business,
security, compliance, or user-trust failures even if they are rare.
