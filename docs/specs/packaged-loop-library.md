# Packaged Loop Library

## Purpose

The packaged loop library makes ADLC loops reusable without jumping directly to full self-actioning orchestration. A packaged loop template is a machine-readable contract bundle that a harness can inspect, install, validate, and then run through existing ADLC primitives.

The library answers one question: "Which known loop should I install, and what gates must be true before it can run?"

It does not schedule jobs, poll trackers, dispatch agents, merge code, or choose work on its own. Those behaviors belong to the bounded meta-harness layer and remain gated by existing ADLC commands.

## Catalog

The canonical catalog is `docs/loop-library/catalog.json` and validates against `docs/schemas/loop-template-catalog.schema.json`.

Each template defines:

- task signals the loop may react to
- required skills and connectors
- required ADLC commands and schemas
- allowed tools and action types
- deterministic gates and human approval points
- mandatory and signal-derived required tests
- safe bail state, progress signal, control channel, independent truth, redaction posture, and budget guard
- queue seed tasks
- runbook and no-overclaim boundaries

The shipped catalog contains:

- `ci-triage`
- `pr-babysitter`
- `dependency-bump`
- `ticket-hygiene`
- `architecture-debt-discovery`
- `feedback-sweep`
- `skill-champion`

All shipped templates claim `assisted_loop`, not `self_autonomous`.

## Runtime Commands

List templates:

```bash
bin/adlc loop-library --json
```

Inspect one template and validate generated artifacts in memory:

```bash
bin/adlc loop-library --template-id ci-triage --json
```

Dry-run installation:

```bash
bin/adlc loop-template-install \
  --template-id ci-triage \
  --workspace . \
  --dry-run \
  --json
```

Write installation artifacts only after action admission:

```bash
bin/adlc loop-template-install \
  --template-id ci-triage \
  --workspace . \
  --allow-mutation \
  --tool-registry .adlc/loop_library_tool_registry.json \
  --json
```

The tool registry must admit tool `adlc-loop-library` action `install_loop_template` in phase `learning_capture` or the current workflow-state phase.

## Installed Artifacts

By default, installation targets `.adlc/loops/<template_id>/` and writes:

- `loop_contract.json`
- `tool_registry.json`
- `work_queue_seed.json`
- `token_budget.json`
- `README.md`
- `install_report.json`

The JSON artifacts validate against:

- `loop-contract`
- `tool-registry`
- `work-queue`
- `token-budget`
- `loop-template-install-report`

Existing artifacts that differ from generated content block installation unless `--force` is passed. This avoids silently replacing a locally customized loop contract.

## Harness Flow

1. Call `loop-library --json`.
2. Choose a template from task signal, category, connector availability, and gate fit.
3. Call `loop-library --template-id <id> --json` and inspect required skills, schemas, commands, gates, and approval points.
4. Run `loop-template-install --template-id <id> --dry-run --json`.
5. If the plan is acceptable, admit `adlc-loop-library:install_loop_template` through `action-admit`.
6. Run `loop-template-install --allow-mutation --tool-registry <registry>`.
7. Validate the installed Loop Contract, Tool Registry, Work Queue seed, and install report.
8. Use the installed seed with queue, worktree, sync, verifier, memory, and champion/holdout commands.
9. Stop at the template's human approval points.

## Non-Goals

The packaged loop library does not:

- pick tasks from a repo or ticket tracker
- rank task value, risk, or verifiability
- schedule unattended runs
- dispatch agents
- mutate external trackers directly
- open pull requests
- merge, deploy, or approve architecture changes

The packaged loop library is a reusable contract source for a harness. The bounded meta-harness planner is where ADLC ranks work candidates and returns the next executable command plan.
