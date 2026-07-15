# Advanced kernel and contributor CLI

This page preserves the low-level operator and contributor interfaces behind the public `/adlc` facade. They are deterministic control-plane tools, not the onboarding path.

## Canonical verification

```bash
bin/adlc health-check --json
bin/adlc ci --json
bash tests/acceptance/run_public_acceptance.sh
bash tests/acceptance/run_os12_acceptance.sh
```

The two acceptance scripts are provider-free gate proofs. They are not evidence of one-shot agent execution or live-provider behavior.

## State, admission, and work substrate

`bin/adlc action-admit` evaluates a proposed effect. Stateful execution uses `run --brief-id`, `run-phase triage`, `resume-workflow`, `status`, and `resume`. Work emission and isolation use `emit-work-items`, `queue-status`, `queue-claim`, and `worktree-prepare`; dirty-check and file-overlap checks prevent unsafe claims, and `adlc-queue`/`adlc-worktree` actions remain admitted effects.

## Build Brief closeout contracts

- **Module Plan:** `module_plan` and `module-plan-check` require responsibilities, purity, capabilities, and an architecture test before production code.
- **Honesty Contract:** `honesty_contract` requires `doc_honesty_section`, `no_overclaim`, and `limitations` on human-facing claims.
- **Performance Envelope:** `performance_envelope` names scale, hot paths, and `benchmark_required` evidence when applicable.
- **Task Sizing:** `task_sizing` records one coherent surface and a split decision instead of using line count.
- **Paved roads:** `paved-road-patterns` may resolve a registered exemplar such as `pattern:interralis:evidence-module`; departures record `pattern_deviation_reason`.
- **Target Repo Conventions:** extract `repo_conventions`, run `convention-scan`, then run `pr-hygiene-scan` before publication.

Internal `test-author` uses `spec-to-tests` for failing-test authoring from Brief evidence; these are internal roles, not peer public agents or skills.

## Compound engineering and learning

`compound-context` runs the Compound Preflight over `docs/solutions`; verified `learning_capture` proposals can feed later work. `architecture-memory`, `memory-health`, and `champion-holdout` prevent stale or duplicate primitive promotion.

## Packaged and designed loops

`loop-library` and `loop-template-install` expose packaged loops such as `ci-triage` and `skill-champion`. `looper-status`, `loop-design-validate`, and `loop-contract-from-design` admit a Looper-compatible Loop Design before execution. These commands do not schedule jobs or dispatch agents.

## Bounded automation

`meta-harness-plan` is the bounded self-actioning planner. It ranks candidates and emits plans; it does not claim tasks, dispatch agents, merge, deploy, or decide architecture. `control-plane-drift-loop` can detect schema-alias drift, admit a bounded repair, verify it, and stop for human review.

## Install compatibility details

`./setup.sh claude <target>` and `./setup.sh verify-claude <target>` remain the dated wrapper forms. Each target receives `<target>/.adlc/bin/adlc`; its `ADLC_ROOT` points to the source checkout. The [installation guide](../start/installation.md) is the current user path.

Harness authors must treat repo_conventions.status=none_found only when no convention documents exist. Waivers are recorded, not skipped. Put process artifacts under the [`process-artifact-storage.md` contract](https://github.com/bigeasyfreeman/adlc/blob/v0.1.0/docs/specs/process-artifact-storage.md), and feed durable maintainer rules through `feedback-conventions`.

`doc_honesty_section`: Low-level command availability proves an interface exists, not that a provider used it correctly.

`no_overclaim`: Provider-free acceptance and deterministic gates do not establish live-provider support.

`limitations`: Compatibility commands may change during 0.x with dated migration guidance.
