---
name: specificity-judge
description: Score whether each task is specific enough for autonomous, one-shot, production-ready execution.
contract_version: 1.0.0
side_effect_profile: read_only
activation:
  mode: judgement
  consumes_manifest: true
  model_class: fast_judge
  cost_guard:
    max_tokens_per_call: 900
    expected_calls_per_run: 4
---

# Specificity Judge

Run this at Eval Council Gate 0 after schema validation succeeds.

## Inputs

For each task provide:

- `artifact_type`
- acceptance criteria list
- `decision_contract`
- `reference_impl`
- `files_to_modify`
- `files_to_create`
- `module_plan`
- `task_sizing`
- `tech_debt_boundaries`
- `compatibility_contract`
- `evidence_responsibilities`
- `definition_of_done`
- `dependencies`
- verifier target from `verification_spec.primary_verifier`
- verifier `target_files` and `expected_failure_mode`

## Output

```json
{
  "task_id": "TASK-001",
  "score": 0.74,
  "rationale": "The task names files and a verifier, but the acceptance criteria still leave rollback evidence implicit.",
  "failing_signals": ["missing_compatibility_contract", "ambiguous_user_path"]
}
```

## Thresholds

- `score >= 0.8` -> pass
- `0.6 <= score < 0.8` -> warn
- `score < 0.6` -> revise with `low_specificity`

## Rules

- Specificity means a cold-start coding agent can execute without guessing and can close the work with production-grade evidence.
- Penalize missing file scope, vague acceptance criteria, absent reference paths, missing `target_files`, missing `expected_failure_mode`, and verifier targets that do not pin the intended behavior.
- Fail implementation tasks that carry `decision_contract.status == unresolved` or `decision_contract.blocks_implementation == true`. Those must be decision gates, not executable tasks.
- Fail tasks whose dependencies are unresolved aliases instead of Build Brief artifact IDs or already-emitted target artifact IDs.
- Fail acceptance criteria that do not carry a checkable `verification_predicate` or `measurable_post_condition`; a criterion whose only check is that text, a file, or a JSON key exists is not specific.
- Fail proof, demonstration, slice, or end-to-end criteria that do not declare a substance floor and allowed payload class. A proof request must say whether product code/tests, compatibility evidence, documentation, or a process artifact can satisfy it.
- Load the predicate library from `docs/solutions/predicate-library.json` and apply each rule as an active checklist item. Violations should cite the matching `PRED-*` rule ID.
- Fail parent/child duplicate scope: a `scope_lock_epic` may lock context, but an implementation task must own the executable work. The same behavior should not be executable in both.
- Fail implementation tasks that do not say what existing primitive, schema, service, helper, or workflow they extend, unless they explicitly prove no existing primitive can absorb the change.
- Fail tasks missing `tech_debt_boundaries`, `compatibility_contract`, `evidence_responsibilities`, or `definition_of_done`; these are one-shot production readiness fields, not optional prose.
- Fail tasks that make a generic compatibility claim without naming touched contract surfaces, `verification_predicates`, and concrete `compatibility_evidence_refs`. "Backward compatible" is not specific unless the predicate and evidence path say how it will be proven.
- Fail executable tasks whose `module_plan` is missing or too vague for a cold-start coding agent to implement without inventing structure. A required plan must name the concrete files, one responsibility per file, pure/impure boundaries, capabilities, and the write-first architecture test.
- Fail executable tasks whose `task_sizing` is missing, marks `split_decision.required=true`, or declares multiple modules without either one coherent structured file-set or an `atomic_cross_module` reason. Require a module plan for code-module creation or when the sizing basis explicitly cites it; coherent non-code file sets may keep it not applicable. Oversized-but-atomic work can pass when the atomic reason explains why the work cannot split safely; file size, line count, or SLOC alone are never valid readiness criteria.
- Validation tasks must cover verifier execution, evidence capture, compatibility checks, and final readiness proof. Penalize decomposition sets that lack automatic validation tasks.
- Do not count checklist items mechanically. Judge whether the task is executable.
- If `fast_judge` is unavailable for the active runtime, emit `stuck` with reason `specificity_judge_unavailable`.

## Failing Signal Catalog

- `unresolved_type1_in_implementation`
- `missing_artifact_type`
- `parent_child_duplicate_scope`
- `unresolved_dependency_alias`
- `missing_reference_impl`
- `missing_target_files`
- `missing_expected_failure_mode`
- `missing_tech_debt_boundaries`
- `missing_compatibility_contract`
- `missing_compatibility_surface`
- `missing_compatibility_verification_predicates`
- `missing_compatibility_evidence_refs`
- `generic_compatibility_claim`
- `missing_evidence_responsibilities`
- `missing_definition_of_done`
- `missing_module_plan`
- `vague_module_plan`
- `missing_task_sizing`
- `task_split_required`
- `broad_change_surface`
- `size_only_split_or_pass`
- `missing_validation_task`
- `acceptance_criterion_missing_verification_predicate`
- `acceptance_criterion_presence_only_predicate`
- `proof_criterion_missing_substance_floor`
- `criterion_payload_class_mismatch`
- `predicate_library_violation`
- `ambiguous_user_path`
- `ambiguous_failure_mode`
