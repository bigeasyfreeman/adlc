# Ponytail Minimality Contract

Ponytail is an ADLC-owned minimality constraint, not a vendored plugin and not a prompt-bloat checklist.

## Contract Shape

Executable Build Brief tasks carry a settled `minimality_contract` with exactly two fields:

```json
{
  "rung": "reuse_existing | stdlib | native_platform | installed_dependency | minimum_code",
  "decision": "One line explaining the smallest acceptable behavior scope."
}
```

The ladder is:

1. does not need to exist
2. reuse existing code
3. use the standard library
4. use platform primitives
5. use an already installed dependency
6. write the minimum code

Reuse evidence lives in `reuse-analysis` output and may be referenced by task prose or evidence refs, but it is not duplicated inside `minimality_contract`.

## Precedence

`repo_conventions` and `module_plan` govern file and module structure. Ponytail governs behavior scope, dependency additions, and speculative abstraction.

A repo-convention-required directory module, coordinator, `types` file, pure/impure split, or architecture-test-first plan is not over-engineering. Minimality cannot skip or flag those structural files. If a task's minimality decision tries to override a required `module_plan`, `bin/adlc module-plan-check` blocks with `minimality_structural_precedence_violation`.

## Mechanical Gates

`bin/adlc ponytail-admit --build-brief <brief> --json` validates that executable tasks have the two-field settled contract.

When a final diff is available, pass it to the same gate:

```bash
bin/adlc ponytail-admit \
  --build-brief .adlc/build_brief.json \
  --diff-file /tmp/final.diff \
  --json
```

The diff gates are mechanical:

- Dependency manifest or lockfile additions block as `unapproved_dependency_diff` unless `--dependency-approval-ref <ref>` is supplied.
- Removals of input validation, error handling, security checks, or accessibility affordances block as `anatomy_removed_*` unless an explicit `--anatomy-waiver category:ref` or `--anatomy-waiver rule:ref` is supplied.

## Codegen

Minimality is decided once at decomposition time. Codegen context carries `minimality_contract` as a settled constraint. Coding agents must not re-deliberate the ladder on every turn.

## Scenario Canary

`bin/adlc ponytail-scenario-canary --json` runs local with/without scenarios. The no-contract variant must block readiness, the two-field variant must pass readiness, and emitted work items must preserve the settled `minimality_contract`.
