# Applicability Manifest Spec

## Goal
Carry one authoritative control-plane decision from triage into planning and brief generation so the pipeline can gate security, observability, compatibility, performance, and rollout work by actual task surface instead of by habit.

## Inputs
- Task text, PRD, or issue
- Repo evidence
- Triage classification output
- Research deliverable

## Confidence Policy

Route by `task_classification_confidence`:

- `task_classification_confidence >= 0.8` -> proceed
- `0.6 <= task_classification_confidence < 0.8` -> route back through research with `low_confidence`, then run `brief-clarity-judge`
- `task_classification_confidence < 0.6` -> emit `escalate`

Confidence routing is part of the control plane. Planning should not continue silently when the confidence falls below the escalation threshold.
In the middle band, the routing label remains `low_confidence`, but `brief-clarity-judge` decides whether the ambiguous task should proceed or escalate. That verdict is authoritative for downstream handling.

## Core Fields
- `task_classification`: `feature | bugfix | build_validation | lint_cleanup | refactor | infra | docs | security`
- `change_surface`: boolean flags for the surfaces the task actually touches
- `claim_provenance`: grounded claims with source refs
- `contamination`: unsupported, contradicted, or ambiguous claims that should not become scope
- `section_policy`: active/suppressed/not_applicable per brief section
- `verification_spec`: the exact verifier that must fail before the change and pass after it

## Change Surface
Set a flag only when repo evidence or the task text supports it.

- `new_attack_surface`
- `runtime_path_change`
- `service_boundary_change`
- `external_integration`
- `persistent_storage`
- `api_change`
- `data_format_change`
- `auth_change`
- `perf_sensitive`
- `user_facing_operation`

## Contamination Handling
Unsupported task text is not scope.

- `supported_claims` remain available for planning
- `unsupported_claims` are stripped or turned into clarification questions
- `contradicted_claims` block planning if they affect scope or correctness
- `needs_clarification` is the narrow set of claims that require a human answer
- `suspect_phrases` capture non-sequiturs or scope drift
- Stray comparison lines such as "this is not X with a new name" stay in contamination unless repo evidence or a documented prior failure makes them relevant scope

## Section Policy
Each policy entry describes one brief section.

- `active`: generate the section normally
- `suppressed`: omit substantive content and explain why
- `not_applicable`: the section does not apply to this task

Default guidance:
- `5_security_review` is active only when the task introduces attack surface, auth/data handling, or an external integration.
- `6_observability_slo` is active only when the task changes a runtime path or user-facing operation.
- `10_rollout` is active only when deployment, migration, or rollout mechanics matter.
- `12_skill_trigger_configuration` is active only when downstream skill activation changes meaningfully.
- Performance and compatibility concerns should be folded into the active sections only when the change surface warrants them.

### Section Activation Trigger Table

These triggers are the authoritative mapping consumed by the deterministic section_policy evaluator. Any change here must be mirrored in `tests/backtest/evaluators/section_policy.sh`.

| Section | Status When Active | Trigger Expression (over `change_surface` / task class) |
|---|---|---|
| `5_security_review` | `active` | `new_attack_surface OR auth_change OR external_integration` |
| `6_observability_slo` | `active` | `runtime_path_change OR user_facing_operation` |
| `10_rollout` | `active` | Task-class gated — activate only when `task_classification IN (infra, refactor)` AND rollout/migration mechanics are named in scope. Default `not_applicable` for all other classes. |
| `12_skill_trigger_configuration` | `active` | Activate only when the Build Brief explicitly adds, removes, or reconfigures skill triggers. Default `not_applicable`. |

All other sections default to `active` when the section is required by the Build Brief template, and to `suppressed` with a concrete reason when the change surface does not warrant them.

### Section Policy Override

After the deterministic section-policy pass, a short `section-policy-judge` pass may promote a suppressed or `not_applicable` section when manifest evidence says the section still matters.

- Overrides must cite manifest evidence, not generic caution.
- Overrides only promote sections; they do not suppress active sections.
- Every override entry must include `overridden_by: "section_policy_judge"`.

Build-validation and lint-cleanup tasks should usually suppress at least half the brief sections. That suppression must come from the manifest, not from ad hoc prose.

## Verification Spec
The verifier must be the closest deterministic signal to the actual failure.

- `test`: a named test or test case
- `command`: a build, lint, fmt, or CI command
- `reproducer`: a direct failing repro of the current issue

The chosen verifier must:
- fail before the fix
- pass after the fix
- be deterministic
- be specific enough to catch the real defect, not just ceremony

### Optional Fields

- `target_files`: which files the verifier exercises; enables the coverage intersection check for downstream failing-test authoring.
- `expected_failure_mode`: short string describing the reason the verifier should fail pre-change, for example `AssertionError: balance != 0` or `exit 1: cargo test failed`.

Verifier phrasing rules:
- `feature` tasks should phrase the verifier around intended behavior or contract edges. Prefer "failing tests for pre-execution event generation" over "tests showing the repo has no shell adapter."
- `bugfix`, `build_validation`, and `lint_cleanup` tasks should prefer the smallest direct reproducer or failing command for the observed defect.
- If a verifier only proves that current code lacks a future feature, it is usually the wrong verifier.

## Output Contract
```json
{
  "version": "1.0.0",
  "task_classification": "build_validation",
  "task_classification_confidence": 0.94,
  "change_surface": {
    "new_attack_surface": false,
    "runtime_path_change": false,
    "service_boundary_change": true,
    "external_integration": false,
    "persistent_storage": false,
    "api_change": false,
    "data_format_change": false,
    "auth_change": false,
    "perf_sensitive": false,
    "user_facing_operation": false
  },
  "claim_provenance": {
    "supported": [
      {
        "claim": "the repo fails cargo test",
        "source_ref": "issue text",
        "extracted_from": "task description"
      }
    ],
    "unsupported": [],
    "contradicted": []
  },
  "contamination": {
    "flags": ["unsupported_claim"],
    "supported_claims": ["the repo fails cargo test"],
    "unsupported_claims": ["this is a new feature"],
    "contradicted_claims": [],
    "needs_clarification": [],
    "suspect_phrases": ["non-sequitur wording"]
  },
  "section_policy": [
    {
      "section_name": "5_security_review",
      "status": "not_applicable",
      "reason": "No new attack surface or data handling change",
      "trigger_fields": [],
      "overridden_by": "section_policy_judge"
    }
  ],
  "verification_spec": {
    "primary_verifier": {
      "type": "command",
      "target": "cargo test",
      "expected_pre_change": "fail",
      "expected_post_change": "pass",
      "rationale": "This task is about restoring the broken validation path"
    },
    "secondary_verifiers": [],
    "must_fail_before_change": true,
    "must_be_deterministic": true,
    "scope_note": "Use the narrowest deterministic signal that matches the task class"
  }
}
```
