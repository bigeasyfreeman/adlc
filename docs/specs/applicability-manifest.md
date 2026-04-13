# Applicability Manifest Spec

## Goal
Carry one authoritative control-plane decision from triage into planning and brief generation so the pipeline can gate security, observability, compatibility, performance, and rollout work by actual task surface instead of by habit.

## Inputs
- Task text, PRD, or issue
- Repo evidence
- Triage classification output
- Research deliverable

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
      "trigger_fields": []
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
