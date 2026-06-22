# Control-Plane Drift Loop

`bin/adlc control-plane-drift-loop` is ADLC's first bounded dogfood loop. It is intentionally smaller than the full self-actioning meta-harness: one deterministic drift rule, one repair action, one verifier pass, and a mandatory human-review stop.

The first rule is schema-alias drift:

- inspect `docs/schemas/*.schema.json`
- inspect `scripts/adlc_runtime/metadata.py`
- detect schema files missing from `SCHEMA_ALIASES`
- generate a stable work-item sync payload for `adlc-control-plane-drift:schema_alias_missing`
- generate and validate a Loop Contract and Loop Action
- require `action-admit` before mutation
- repair only `scripts/adlc_runtime/metadata.py`
- rerun verifier commands
- write a schema-valid control-plane drift report
- stop at `engineer_review` for human review

## Command

```bash
bin/adlc control-plane-drift-loop \
  --workspace . \
  --verifier 'python3 -m py_compile scripts/adlc_runtime/metadata.py' \
  --dry-run \
  --json
```

Mutation requires:

```bash
bin/adlc control-plane-drift-loop \
  --workspace /path/to/adlc-worktree \
  --verifier 'python3 -m py_compile scripts/adlc_runtime/metadata.py' \
  --allow-mutation \
  --tool-registry .adlc/control_plane_tool_registry.json \
  --json
```

The repair workspace must be a clean git checkout. The command writes local run state and evidence under `.adlc/`, which is ignored by the repo.

## Artifacts

The loop writes:

- `.adlc/control_plane_drift_state.json`
- `.adlc/outputs/control_plane_drift_loop.json`
- `.adlc/outputs/control_plane_drift/work_item_sync.json`
- `.adlc/outputs/control_plane_drift/loop_contract.json`
- `.adlc/outputs/control_plane_drift/loop_action.json`
- bounded verifier stdout/stderr logs

The final report validates against `docs/schemas/control-plane-drift-report.schema.json`.

## Boundaries

This loop does not discover arbitrary tasks, schedule itself, open external tickets by default, auto-merge, or edit architecture. It proves that ADLC can use its own control-plane primitives to detect one class of framework drift, propose and validate a repair, apply it through a guarded mutation path, verify the result, and stop for review.
