# Ponytail Minimality Contract

## Purpose

Ponytail becomes an ADLC-owned forcing function through `minimality_contract`, not just an optional agent plugin. The contract travels from decomposition to emitted tickets to codegen context and review. A coding agent inherits it as task scope.

## Build Brief Contract

Every Section 8 task carries `minimality_contract`.

Executable tasks require:

- `mode`: `lite`, `full`, or `ultra`; ADLC defaults to `full`.
- `rung`: `does_not_need_to_exist`, `reuse_existing`, `stdlib`, `native_platform`, `installed_dependency`, `one_liner`, or `minimum_code`.
- `decision`: why this is the smallest correct scoped work.
- `reuse_evidence`: repo, stdlib, platform, or installed dependency evidence checked before new code.
- `skipped`: avoided dependencies, abstractions, files, wrappers, or speculative future-proofing.
- `new_dependencies`: empty unless `dependency_approval_ref` is present.
- `new_abstractions`: empty unless `abstraction_approval_ref` is present.
- `minimum_check`: one runnable command and what it proves.
- `safety_preserved`: boundaries that minimality did not cut.

Non-executable `scope_lock_epic` and `decision_gate` tasks may use a compact `not_applicable` reason.

## Runtime Gates

`bin/adlc ponytail-admit --build-brief <path> --json` emits `ponytail-admission-report`.

`emit-work-items --require-ready` blocks:

- `missing_minimality_contract`
- `minimality_contract_not_applicable_on_executable`
- `missing_ponytail_reuse_evidence`
- `missing_ponytail_skipped_options`
- `unapproved_ponytail_new_dependency`
- `unapproved_ponytail_new_abstraction`
- `missing_ponytail_minimum_check`
- `missing_ponytail_safety_boundaries`

The normalized work-item payload preserves `minimality_contract`, so GitHub, Linear, JIRA, and harness tickets carry the same constraint the coding agent sees.

## Canary

`bin/adlc ponytail-scenario-canary --json` runs three local script tasks twice:

- without Ponytail: the script still works, but ADLC readiness blocks missing `minimality_contract`.
- with Ponytail: the script works, readiness is `ready`, and the emitted ticket inherits `minimality_contract`.

The canary writes only to a temp workspace, installs no dependencies, dispatches no agents, and calls no external model providers.
