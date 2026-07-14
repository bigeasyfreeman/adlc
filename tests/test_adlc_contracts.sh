#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0
TOTAL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

assert() {
  local desc="$1"
  local condition="$2"
  TOTAL=$((TOTAL + 1))
  if eval "$condition"; then
    printf '  %bPASS%b %s\n' "$GREEN" "$NC" "$desc"
    PASS=$((PASS + 1))
  else
    printf '  %bFAIL%b %s\n' "$RED" "$NC" "$desc"
    FAIL=$((FAIL + 1))
  fi
}

assert_emit_preserves_scalable_primitives() {
  local tmp
  tmp="$(mktemp)"
  jq '
    (.sections."8_task_tickets"[0].construct_map_refs) = ["graph:construct:adlc-cli"] |
    (.sections."8_task_tickets"[0].paved_road_refs) = ["skill:paved-road-registry#adlc-cli"] |
    (.sections."8_task_tickets"[0].intent_contract_refs) = ["brief:intent:XIA-SOC-INDEX"] |
    (.sections."8_task_tickets"[0].production_invariant_coverage) = [
      {
        "invariant": "data_integrity",
        "status": "covered",
        "evidence": ["docs/schemas/build-brief.schema.json"]
      }
    ]
  ' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp"

  local status=0
  "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$tmp" --dry-run --json |
    jq -e '
      .artifacts[0].construct_map_refs[0] == "graph:construct:adlc-cli" and
      .artifacts[0].paved_road_refs[0] == "skill:paved-road-registry#adlc-cli" and
      .artifacts[0].intent_contract_refs[0] == "brief:intent:XIA-SOC-INDEX" and
      .artifacts[0].production_invariant_coverage[0].invariant == "data_integrity" and
      .artifacts[0].production_invariant_coverage[0].status == "covered"
    ' >/dev/null || status=$?

  rm -f "$tmp"
  return "$status"
}

assert_emit_preserves_task_fingerprints() {
  local tmp
  tmp="$(mktemp)"
  jq '
    (.sections."8_task_tickets"[0].stable_task_identity) = {
      "identity_key": "SMOKE_BUGFIX_AVERAGE:v1",
      "derived_from": ["task_id", "verification_spec.primary_verifier.target"],
      "stability_rule": "Keep task_id stable after first emission."
    } |
    (.sections."8_task_tickets"[0].resume_fingerprint) = {
      "input_hash": "hash-smoke",
      "status": "pending",
      "primary_verifier": "pytest tests/test_average.py",
      "pre_change_status": "failed_expected",
      "post_change_status": "not_run",
      "changed_files": [],
      "commit": null,
      "evidence": ["pre-change verifier expected to fail"]
    }
  ' "$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json" > "$tmp"

  local status=0
  "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$tmp" --dry-run --json |
    jq -e '
      .artifacts[0].stable_task_identity.identity_key == "SMOKE_BUGFIX_AVERAGE:v1" and
      .artifacts[0].resume_fingerprint.input_hash == "hash-smoke" and
      .artifacts[0].resume_fingerprint.status == "pending"
    ' >/dev/null || status=$?

  rm -f "$tmp"
  return "$status"
}

assert_workflow_state_accepts_task_fingerprints() {
  local tmp
  tmp="$(mktemp)"
  cat > "$tmp" <<'JSON'
{"brief_id":"SMOKE","session_id":"adlc-test","phase":"compound_preflight","status":"planned","step":"ready","started_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z","resume_count":0,"checkpoint":{"workspace":"/tmp","history":[]},"side_effects":[],"task_fingerprints":[{"task_id":"SMOKE-001","input_hash":"abc123","status":"skipped_already_satisfied","primary_verifier":"pytest tests/test_smoke.py","pre_change_status":"not_applicable","post_change_status":"passed","changed_files":[],"commit":null,"evidence":["existing verifier passed"]}]}
JSON
  local status=0
  "$ROOT/bin/adlc" validate-artifact --schema workflow-state --input "$tmp" --json |
    jq -e '.valid == true' >/dev/null || status=$?
  rm -f "$tmp"
  return "$status"
}

assert_workflow_state_accepts_interface_and_productionization_status() {
  local tmp
  tmp="$(mktemp)"
  cat > "$tmp" <<'JSON'
{"brief_id":"SMOKE","session_id":"adlc-test","phase":"pr_prep","status":"planned","step":"ready","started_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z","resume_count":0,"checkpoint":{"workspace":"/tmp","history":[]},"side_effects":[],"interface_contract_status":[{"contract_id":"iface:smoke","task_id":"SMOKE-001","status":"ready","evidence":["schema validated"],"updated_at":"2026-01-01T00:00:00Z"}],"productionization_status":[{"gate_id":"prod:smoke","task_id":"SMOKE-001","coverage_state":"production_ready","status":"ready","evidence":["readiness passed"],"updated_at":"2026-01-01T00:00:00Z"}]}
JSON
  local status=0
  "$ROOT/bin/adlc" validate-artifact --schema workflow-state --input "$tmp" --json |
    jq -e '.valid == true' >/dev/null || status=$?
  rm -f "$tmp"
  return "$status"
}

assert_workflow_state_accepts_loop_progress_control() {
  "$ROOT/bin/adlc" validate-artifact --schema workflow-state --input "$ROOT/tests/fixtures/loop_maturity/workflow-state-control-progress.json" --json |
    jq -e '.valid == true and (.errors | length) == 0' >/dev/null
}

assert_workflow_state_accepts_run_identity_side_effects() {
  local tmp
  tmp="$(mktemp)"
  cat > "$tmp" <<'JSON'
{"brief_id":"SMOKE","run_id":"adlc-run-contract","session_id":"adlc-contract","phase":"pr_prep","status":"planned","step":"ready","started_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z","resume_count":1,"attempt":2,"last_resumed_at":"2026-01-01T00:01:00Z","checkpoint":{"workspace":"/tmp","history":[]},"side_effects":[{"idempotency_key":"SMOKE:linear:SMOKE-001:upsert","brief_id":"SMOKE","run_id":"adlc-run-contract","session_id":"adlc-contract","tool_name":"linear-work-item-emitter","operation":"upsert_artifact","status":"completed","artifact_id":"LIN-1","artifact_ref":"linear://LIN-1","timestamp":"2026-01-01T00:02:00Z"}]}
JSON
  local status=0
  "$ROOT/bin/adlc" validate-artifact --schema workflow-state --input "$tmp" --json |
    jq -e '.valid == true and (.errors | length) == 0' >/dev/null || status=$?
  rm -f "$tmp"
  return "$status"
}

assert_permission_audit_trail_accepts_run_identity() {
  local tmp
  tmp="$(mktemp)"
  cat > "$tmp" <<'JSON'
{"session_id":"adlc-contract","brief_id":"SMOKE","run_id":"adlc-run-contract","entries":[{"decision_id":"decision-1","tool_name":"Write","action":"edit_file","tier":"requires_approval","decision":"denied","reason":"permission_requires_human_approval","decided_by":"policy","timestamp":"2026-01-01T00:00:00Z","session_id":"adlc-contract","brief_id":"SMOKE","run_id":"adlc-run-contract","stop_reason":"permission_denied"}],"denial_summary":{"count":1,"patterns":["permission_requires_human_approval"]}}
JSON
  local status=0
  "$ROOT/bin/adlc" validate-artifact --schema permission-audit-trail --input "$tmp" --json |
    jq -e '.valid == true and (.errors | length) == 0' >/dev/null || status=$?
  rm -f "$tmp"
  return "$status"
}

assert_workflow_state_accepts_work_item_links() {
  local tmp
  tmp="$(mktemp)"
  cat > "$tmp" <<'JSON'
{"brief_id":"SMOKE","run_id":"adlc-run-contract","session_id":"adlc-contract","phase":"pr_prep","status":"planned","step":"ready","started_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z","resume_count":1,"attempt":2,"checkpoint":{"workspace":"/tmp","history":[]},"side_effects":[{"idempotency_key":"SMOKE:linear:SMOKE-001:upsert:sync:sync-update-001","brief_id":"SMOKE","run_id":"adlc-run-contract","session_id":"adlc-contract","tool_name":"linear-work-item-sync","operation":"append_work_item_status","status":"completed","artifact_id":"LIN-1","artifact_ref":"linear://LIN-1","timestamp":"2026-01-01T00:02:00Z"}],"work_item_links":[{"target":"linear","external_id":"SMOKE:linear:SMOKE-001:upsert","idempotency_key":"SMOKE:linear:SMOKE-001:upsert","brief_id":"SMOKE","run_id":"adlc-run-contract","session_id":"adlc-contract","build_brief_id":"SMOKE","task_id":"SMOKE-001","artifact_id":"LIN-1","artifact_ref":"linear://LIN-1","title":"Smoke task","operation":"append","status":"appended","last_sync_idempotency_key":"SMOKE:linear:SMOKE-001:upsert:sync:sync-update-001","status_update":{"status":"blocked","phase":"qa","next_action":"rerun verifier","evidence_refs":["pytest tests/test_smoke.py"]},"evidence_refs":["pytest tests/test_smoke.py"],"updated_at":"2026-01-01T00:02:00Z"}]}
JSON
  local status=0
  "$ROOT/bin/adlc" validate-artifact --schema workflow-state --input "$tmp" --json |
    jq -e '.valid == true and (.errors | length) == 0' >/dev/null || status=$?
  rm -f "$tmp"
  return "$status"
}

assert_workflow_state_accepts_queue_and_worktree_refs() {
  local tmp
  tmp="$(mktemp)"
  cat > "$tmp" <<'JSON'
{"brief_id":"SMOKE","run_id":"adlc-run-contract","session_id":"adlc-contract","phase":"code","status":"planned","step":"ready","started_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z","resume_count":1,"attempt":2,"checkpoint":{"workspace":"/tmp","history":[]},"side_effects":[{"idempotency_key":"SMOKE:adlc-queue:SMOKE-001:claim_task:abc123","brief_id":"SMOKE","run_id":"adlc-run-contract","session_id":"adlc-contract","tool_name":"adlc-queue","operation":"claim_task","status":"completed","artifact_id":"SMOKE-001","artifact_ref":"tests/fixtures/work_queue/valid-queue.json","timestamp":"2026-01-01T00:02:00Z"}],"queue_claims":[{"queue_id":"queue:smoke","queue_ref":"tests/fixtures/work_queue/valid-queue.json","task_id":"SMOKE-001","claim_id":"claim:smoke","agent_id":"codex","brief_id":"SMOKE","run_id":"adlc-run-contract","session_id":"adlc-contract","status":"claimed","expected_paths":[{"path":"scripts/adlc_runtime/cli.py","kind":"file","reason":"test"}],"worktree_ref":"/tmp/worktrees/smoke","updated_at":"2026-01-01T00:02:00Z"}],"worktree_refs":[{"queue_id":"queue:smoke","queue_ref":"tests/fixtures/work_queue/valid-queue.json","task_id":"SMOKE-001","branch":"adlc/smoke-001","path":"/tmp/worktrees/smoke","base_ref":"HEAD","status":"active","dirty":false,"cleanup_eligible":false,"updated_at":"2026-01-01T00:02:00Z"}]}
JSON
  local status=0
  "$ROOT/bin/adlc" validate-artifact --schema workflow-state --input "$tmp" --json |
    jq -e '.valid == true and (.errors | length) == 0' >/dev/null || status=$?
  rm -f "$tmp"
  return "$status"
}

assert_workflow_state_covers_workflow_nodes() {
  python3 - "$ROOT" <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
schema = json.loads((root / "docs/schemas/workflow-state.schema.json").read_text())
allowed = set(schema["properties"]["phase"]["enum"])
nodes = set()
node_re = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+\[")
for line in (root / "WORKFLOW.dot").read_text().splitlines():
    match = node_re.match(line)
    if not match:
        continue
    node = match.group(1)
    if node in {"graph", "node", "edge"} or node.startswith("l_"):
        continue
    nodes.add(node)
missing = sorted(nodes - allowed)
if missing:
    print("workflow-state phase enum missing: " + ", ".join(missing))
    sys.exit(1)
PY
}

assert_build_brief_1_1_requires_narrative_contract() {
  local tmp result status
  tmp="$(mktemp)"
  result="$(mktemp)"
  jq '.version = "1.1.0"' "$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json" > "$tmp"
  status=0
  if "$ROOT/bin/adlc" validate-artifact --schema build-brief --input "$tmp" --json > "$result" 2>/dev/null; then
    status=1
  else
    jq -e '.valid == false and any(.errors[]; contains("narrative_contract"))' "$result" >/dev/null || status=$?
  fi
  rm -f "$tmp" "$result"
  return "$status"
}

write_module_plan_valid_brief() {
  local output="$1"
  local fixture_dir="$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc"
  local fixture_file="build_brief.json"
  jq '
    (.sections."8_task_tickets"[0].title) = "Split scoreboard module persistence" |
    (.sections."8_task_tickets"[0].objective) = "Split scoreboard module persistence boundary." |
    (.sections."8_task_tickets"[0].files_to_create) = ["src/scoreboard/persist.py"] |
    (.sections."8_task_tickets"[0].module_plan) = {
      "applicability": "required",
      "reason": "Task creates a persistence module for scoreboard storage.",
      "files": [
        {
          "path": "src/scoreboard.py",
          "responsibility": "Score submissions",
          "purity": "pure",
          "capabilities": ["compute"]
        },
        {
          "path": "src/scoreboard/persist.py",
          "responsibility": "Persist score records",
          "purity": "impure",
          "capabilities": ["fs"]
        }
      ],
      "architecture_test": {
        "test_path": "tests/test_scoreboard_architecture.py",
        "command": "pytest tests/test_scoreboard_architecture.py",
        "assertions": [
          "scoreboard persistence lives in src/scoreboard/persist.py",
          "pure scoreboard module has no filesystem capability"
        ],
        "write_first": true
      }
    } |
    (.sections."8_task_tickets"[0].task_sizing) = {
      "applicability": "required",
      "reason": "Structural persistence split is one coherent module_plan file-set.",
      "basis": ["module_plan", "coherent_file_set"],
      "change_surface": {
        "surface_kind": "coherent_file_set",
        "primary_module": "src/scoreboard",
        "touched_modules": ["src/scoreboard"],
        "touched_files": ["src/scoreboard.py", "src/scoreboard/persist.py", "tests/test_scoreboard_architecture.py"],
        "coherence": "The source files and architecture test are the planned scoreboard persistence module split."
      },
      "split_decision": {
        "required": false,
        "rationale": "The required module_plan describes one coherent file-set."
      }
    } |
    (.sections."8_task_tickets"[1].module_plan) = {
      "applicability": "not_applicable",
      "reason": "Existing behavior bugfix changes only current files."
    } |
    (.sections."8_task_tickets"[2].module_plan) = {
      "applicability": "not_applicable",
      "reason": "Validation task only and creates no module structure."
    }
  ' "$fixture_dir/$fixture_file" > "$output"
}

assert_build_brief_accepts_valid_module_plan() {
  local tmp status
  tmp="$(mktemp)"
  write_module_plan_valid_brief "$tmp"
  status=0
  "$ROOT/bin/adlc" validate-artifact --schema build-brief --input "$tmp" --json |
    jq -e '.valid == true and (.errors | length) == 0' >/dev/null || status=$?
  rm -f "$tmp"
  return "$status"
}

assert_build_brief_rejects_module_plan_and_responsibility() {
  local tmp invalid result status
  tmp="$(mktemp)"
  invalid="$(mktemp)"
  result="$(mktemp)"
  write_module_plan_valid_brief "$tmp"
  jq '(.sections."8_task_tickets"[0].module_plan.files[0].responsibility) = "Read and write records"' "$tmp" > "$invalid"
  status=0
  if "$ROOT/bin/adlc" validate-artifact --schema build-brief --input "$invalid" --json > "$result" 2>/dev/null; then
    status=1
  else
    jq -e '.valid == false' "$result" >/dev/null || status=$?
  fi
  rm -f "$tmp" "$invalid" "$result"
  return "$status"
}

assert_build_brief_rejects_module_plan_pure_side_effects() {
  local tmp invalid result status
  tmp="$(mktemp)"
  invalid="$(mktemp)"
  result="$(mktemp)"
  write_module_plan_valid_brief "$tmp"
  jq '(.sections."8_task_tickets"[0].module_plan.files[0].capabilities) = ["compute", "fs"]' "$tmp" > "$invalid"
  status=0
  if "$ROOT/bin/adlc" validate-artifact --schema build-brief --input "$invalid" --json > "$result" 2>/dev/null; then
    status=1
  else
    jq -e '.valid == false' "$result" >/dev/null || status=$?
  fi
  rm -f "$tmp" "$invalid" "$result"
  return "$status"
}

assert_build_brief_rejects_module_plan_catch_all_path() {
  local tmp invalid result status
  tmp="$(mktemp)"
  invalid="$(mktemp)"
  result="$(mktemp)"
  write_module_plan_valid_brief "$tmp"
  jq '(.sections."8_task_tickets"[0].module_plan.files[0].path) = "src/helpers.py"' "$tmp" > "$invalid"
  status=0
  if "$ROOT/bin/adlc" validate-artifact --schema build-brief --input "$invalid" --json > "$result" 2>/dev/null; then
    status=1
  else
    jq -e '.valid == false' "$result" >/dev/null || status=$?
  fi
  rm -f "$tmp" "$invalid" "$result"
  return "$status"
}

assert_build_brief_rejects_module_plan_misc_responsibility() {
  local tmp invalid result status
  tmp="$(mktemp)"
  invalid="$(mktemp)"
  result="$(mktemp)"
  write_module_plan_valid_brief "$tmp"
  jq '(.sections."8_task_tickets"[0].module_plan.files[0].responsibility) = "Miscellaneous helpers"' "$tmp" > "$invalid"
  status=0
  if "$ROOT/bin/adlc" validate-artifact --schema build-brief --input "$invalid" --json > "$result" 2>/dev/null; then
    status=1
  else
    jq -e '.valid == false' "$result" >/dev/null || status=$?
  fi
  rm -f "$tmp" "$invalid" "$result"
  return "$status"
}

assert_emit_preserves_slop_quality_gate() {
  local tmp
  tmp="$(mktemp)"
  jq '
    (.sections."8_task_tickets"[0].slop_quality_gate) = {
      "applicability": "required",
      "reason": "Task changes generated agent output.",
      "mode": "agent_output",
      "threshold": 0.7,
      "metrics": ["rubric_score", "schema_validity"],
      "eval_cases": [
        {
          "id": "SLOP-001",
          "source": "golden",
          "input": "User asks for a deployment plan",
          "expected_quality": "Specific, executable plan with verifier and rollback",
          "metric": "rubric_score",
          "threshold": 0.7
        }
      ],
      "baseline_score": 0.82,
      "regression_tolerance": 0.03,
      "failure_action": "block",
      "case_promotion_sources": ["human_edit", "council_rejection", "production_sample"]
    }
  ' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp"

  local status=0
  "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$tmp" --dry-run --json |
    jq -e '
      .artifacts[0].slop_quality_gate.applicability == "required" and
      .artifacts[0].slop_quality_gate.mode == "agent_output" and
      .artifacts[0].slop_quality_gate.threshold == 0.7 and
      .artifacts[0].slop_quality_gate.metrics[0] == "rubric_score" and
      .artifacts[0].slop_quality_gate.eval_cases[0].source == "golden" and
      .artifacts[0].slop_quality_gate.failure_action == "block" and
      .artifacts[0].slop_quality_gate.case_promotion_sources[1] == "council_rejection"
    ' >/dev/null || status=$?

  rm -f "$tmp"
  return "$status"
}

assert_emit_preserves_loop_contract_refs() {
  local tmp
  tmp="$(mktemp)"
  jq '
    (.sections."8_task_tickets"[0].work_item_metadata.loop_contract_path) = "tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json" |
    (.sections."8_task_tickets"[0].work_item_metadata.loop_action_path) = "tests/fixtures/loop_maturity/valid-loop-action.json" |
    (.sections."8_task_tickets"[0].work_item_metadata.loop_maturity_report_path) = "tests/fixtures/loop_maturity/assisted-loop-report.json"
  ' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp"

  local status=0
  "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$tmp" --dry-run --json |
    jq -e '
      .artifacts[0].loop_contract_path == "tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json" and
      .artifacts[0].loop_action_path == "tests/fixtures/loop_maturity/valid-loop-action.json" and
      .artifacts[0].loop_maturity_report_path == "tests/fixtures/loop_maturity/assisted-loop-report.json"
    ' >/dev/null || status=$?

  rm -f "$tmp"
  return "$status"
}

assert_emit_preserves_implementation_and_productionization_contracts() {
  local tmp
  tmp="$(mktemp)"
  jq '
    (.sections."8_task_tickets"[0].implementation_interface_contract) = {
      "id": "iface:xia-adlc-ready",
      "capability": "ADLC readiness payload",
      "reuse": ["scripts/adlc.py normalized_work_item_payload"],
      "consumes": ["Build Brief task fields"],
      "emits": ["normalized work-item artifact"],
      "minimum_fields": [
        {"name":"task_id","kind":"string","constraint":"stable non-empty task ID"}
      ],
      "invariants": ["optional fields are omitted when absent"],
      "integration_points": ["bin/adlc emit-work-items"],
      "validation_gates": ["tests/test_adlc_contracts.sh"],
      "failure_semantics": ["schema or readiness failure blocks mutation"],
      "privacy_redaction": "No secrets are emitted."
    } |
    (.sections."8_task_tickets"[0].productionization_gate) = {
      "id": "prod:xia-adlc-ready",
      "claim": "Normalized ADLC work-item payload is production ready for local dry-run emission.",
      "coverage_state": "production_ready",
      "operational_readiness": {
        "owner": "ADLC",
        "rollback_path": "Revert the schema and CLI patch.",
        "runbook_refs": ["docs/specs/emitter-contract.md"]
      },
      "security_privacy": {
        "redaction_posture": "Payload contains task metadata only and no secrets."
      },
      "reliability_failure_modes": ["Schema mismatch blocks before external mutation."],
      "validation_evidence": ["tests/test_adlc_contracts.sh"],
      "no_overclaim": ["This does not prove external provider mutation."]
    }
  ' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp"

  local status=0
  "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$tmp" --dry-run --require-ready --json |
    jq -e '
      .readiness_report.status == "ready" and
      .artifacts[0].implementation_interface_contract.id == "iface:xia-adlc-ready" and
      .artifacts[0].implementation_interface_contract.consumes[0] == "Build Brief task fields" and
      .artifacts[0].productionization_gate.coverage_state == "production_ready" and
      .artifacts[0].productionization_gate.no_overclaim[0] == "This does not prove external provider mutation."
    ' >/dev/null || status=$?

  rm -f "$tmp"
  return "$status"
}

assert_emit_preserves_honesty_contracts() {
  "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$ROOT/docs/build-briefs/xia-adlc-remediation.json" --dry-run --require-ready --json |
    jq -e '
      .readiness_report.status == "ready" and
      any(.artifacts[]; .id == "XIA-SOC-INDEX" and .honesty_contract.applicability == "required" and (.honesty_contract.required_output_fields | index("doc_honesty_section")) != null) and
      any(.artifacts[]; .id == "XIA-ADLC-READY" and .honesty_contract.applicability == "required" and (.honesty_contract.output_surfaces | index("artifact")) != null and (.no_overclaim[0] | contains("provider mutation")) and (.limitations[0] | contains("local schema"))) and
      any(.artifacts[]; .id == "XIA-VAL-SPLIT" and .honesty_contract.applicability == "not_applicable" and (.honesty_contract.reason | contains("no external claims")))
    ' >/dev/null
}

assert_emit_preserves_performance_envelopes() {
  "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$ROOT/docs/build-briefs/xia-adlc-remediation.json" --dry-run --require-ready --json |
    jq -e '
      .readiness_report.status == "ready" and
      any(.artifacts[]; .id == "XIA-ADLC-READY" and .performance_envelope.applicability == "required" and .performance_envelope.hot_paths[0].complexity == "O(n)") and
      any(.artifacts[]; .id == "XIA-VAL-SPLIT" and .performance_envelope.applicability == "not_applicable" and (.performance_envelope.reason | contains("no data path")))
    ' >/dev/null &&
  "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json" --dry-run --require-ready --json |
    jq -e '
      .readiness_report.status == "ready" and
      any(.artifacts[]; .id == "SMOKE_FEATURE_SCOREBOARD" and .performance_envelope.applicability == "required" and .benchmark_required == true and (.benchmark_command | contains("tests/test_scoreboard_performance.py")))
    ' >/dev/null
}

assert_emit_preserves_task_sizing() {
  "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$ROOT/docs/build-briefs/xia-adlc-remediation.json" --dry-run --require-ready --json |
    jq -e '
      .readiness_report.status == "ready" and
      any(.artifacts[]; .id == "XIA-ADLC-READY" and .task_sizing.change_surface.surface_kind == "atomic_cross_module" and (.task_sizing.atomic_work_reason | contains("atomically"))) and
      any(.artifacts[]; .id == "XIA-VAL-SPLIT" and .task_sizing.applicability == "not_applicable")
    ' >/dev/null &&
  "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json" --dry-run --require-ready --json |
    jq -e '
      .readiness_report.status == "ready" and
      any(.artifacts[]; .id == "SMOKE_BUGFIX_AVERAGE" and .task_sizing.change_surface.surface_kind == "single_module" and .module_plan.applicability == "not_applicable")
    ' >/dev/null
}

assert_overclaimed_production_ready_blocks_readiness() {
  local tmp
  tmp="$(mktemp)"
  jq '
    (.sections."8_task_tickets"[0].productionization_gate) = {
      "id": "prod:overclaim",
      "claim": "This task is production ready.",
      "coverage_state": "production_ready",
      "operational_readiness": {
        "owner": "ADLC",
        "rollback_path": "Revert the patch.",
        "runbook_refs": ["docs/specs/emitter-contract.md"]
      },
      "security_privacy": {
        "redaction_posture": "No secrets."
      },
      "reliability_failure_modes": [],
      "validation_evidence": [],
      "no_overclaim": []
    }
  ' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp"

  local status=0
  if ! "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$tmp" --dry-run --json >"$tmp.result" 2>/dev/null; then
    status=1
  else
    jq -e 'any(.readiness_report.issues[]; .rule == "overclaimed_production_ready")' "$tmp.result" >/dev/null || status=$?
    if "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$tmp" --dry-run --require-ready --json >/dev/null 2>&1; then
      status=1
    fi
  fi
  rm -f "$tmp" "$tmp.result"
  return "$status"
}

assert_emit_omits_absent_slop_quality_gate() {
  "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$ROOT/docs/build-briefs/xia-adlc-remediation.json" --dry-run --json |
    jq -e 'all(.artifacts[]; has("slop_quality_gate") | not)' >/dev/null
}

assert_generated_output_missing_slop_gate_blocks_readiness() {
  local tmp
  tmp="$(mktemp)"
  jq '
    (.sections."8_task_tickets"[0].generated_output_surface) = {
      "active": true,
      "reason": "Task changes generated agent output.",
      "modes": ["agent_output"]
    }
  ' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp"

  local status=0
  if "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$tmp" --dry-run --require-ready --json >/dev/null 2>&1; then
    status=1
  fi
  rm -f "$tmp"
  return "$status"
}

assert_generated_output_valid_slop_gate_passes_readiness() {
  local tmp
  tmp="$(mktemp)"
  jq '
    (.sections."8_task_tickets"[0].generated_output_surface) = {
      "active": true,
      "reason": "Task changes generated agent output.",
      "modes": ["agent_output"]
    } |
    (.sections."8_task_tickets"[0].slop_quality_gate) = {
      "applicability": "required",
      "reason": "Task changes generated agent output.",
      "mode": "agent_output",
      "threshold": 0.7,
      "metrics": [
        {
          "metric_type": "rubric_score",
          "validator_ref": "skills/slop-judge/SKILL.md"
        }
      ],
      "eval_cases": [
        {
          "id": "SLOP-001",
          "source": "golden",
          "input": "User asks for a deployment plan",
          "expected_quality": "Specific, executable plan with verifier and rollback",
          "metric": "rubric_score",
          "threshold": 0.7
        }
      ],
      "baseline_score": 0.82,
      "regression_tolerance": 0.03,
      "failure_action": "block",
      "case_promotion_sources": ["human_edit", "council_rejection", "production_sample"]
    }
  ' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp"

  local status=0
  "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$tmp" --dry-run --require-ready --json |
    jq -e '.readiness_report.status == "ready" and .artifacts[0].slop_quality_gate.applicability == "required"' >/dev/null || status=$?
  rm -f "$tmp"
  return "$status"
}

assert_generated_output_string_metric_blocks_readiness() {
  local tmp
  tmp="$(mktemp)"
  jq '
    (.sections."8_task_tickets"[0].generated_output_surface) = {
      "active": true,
      "reason": "Task changes generated agent output.",
      "modes": ["agent_output"]
    } |
    (.sections."8_task_tickets"[0].slop_quality_gate) = {
      "applicability": "required",
      "reason": "Task changes generated agent output.",
      "mode": "agent_output",
      "threshold": 0.7,
      "metrics": ["rubric_score"],
      "eval_cases": [
        {
          "id": "SLOP-001",
          "source": "golden",
          "input": "User asks for a deployment plan",
          "expected_quality": "Specific, executable plan with verifier and rollback",
          "metric": "rubric_score",
          "threshold": 0.7
        }
      ],
      "failure_action": "block"
    }
  ' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp"

  local status=0
  if "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$tmp" --dry-run --require-ready --json >/dev/null 2>&1; then
    status=1
  fi
  rm -f "$tmp"
  return "$status"
}

assert_code_only_without_slop_gate_passes_readiness() {
  "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$ROOT/docs/build-briefs/xia-adlc-remediation.json" --dry-run --require-ready --json |
    jq -e '.readiness_report.status == "ready" and all(.artifacts[]; has("slop_quality_gate") | not)' >/dev/null
}

assert_compact_not_applicable_contracts_pass_readiness() {
  local tmp
  tmp="$(mktemp)"
  jq '
    (.sections."8_task_tickets"[0].anti_slop_rules) = {
      "applicability": "not_applicable",
      "reason": "Build-validation contract change with no generated output."
    } |
    (.sections."8_task_tickets"[0].tech_debt_boundaries) = {
      "applicability": "not_applicable",
      "reason": "No debt boundary for this validation-only task."
    } |
    (.sections."8_task_tickets"[0].compatibility_contract) = {
      "applicability": "not_applicable",
      "reason": "No compatibility surface changes."
    }
  ' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp"

  local status=0
  "$ROOT/bin/adlc" emit-work-items --target linear --build-brief "$tmp" --dry-run --require-ready --json |
    jq -e '.readiness_report.status == "ready"' >/dev/null || status=$?
  rm -f "$tmp"
  return "$status"
}

assert_slop_gate_cli_blocks_missing_generated_gate() {
  local tmp
  tmp="$(mktemp)"
  jq '
    (.sections."8_task_tickets"[0].generated_output_surface) = {
      "active": true,
      "reason": "Task changes generated agent output.",
      "modes": ["agent_output"]
    }
  ' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp"

  local status=0
  if "$ROOT/bin/adlc" slop-gate --build-brief "$tmp" --json >/dev/null 2>&1; then
    status=1
  fi
  rm -f "$tmp"
  return "$status"
}

echo "ADLC Contract Checks"
echo "Root: $ROOT"
echo ""

echo "--- JSON ---"
assert "product contract is complete and legacy surfaces are mapped" "python3 '$ROOT/tests/check_product_contract.py' '$ROOT/PRODUCT.md' '$ROOT/docs/STYLE.md' '$ROOT/docs/migration/legacy-surface-ledger.json' >/dev/null"
assert "applicability-manifest schema parses" "jq empty '$ROOT/docs/schemas/applicability-manifest.schema.json' >/dev/null 2>&1"
assert "build-brief schema parses" "jq empty '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null 2>&1"
assert "learning-entry schema parses" "jq empty '$ROOT/docs/schemas/learning-entry.schema.json' >/dev/null 2>&1"
assert "workflow-state schema parses" "jq empty '$ROOT/docs/schemas/workflow-state.schema.json' >/dev/null 2>&1"
assert "loop-system schemas parse" "jq empty '$ROOT/docs/schemas/loop-contract.schema.json' '$ROOT/docs/schemas/loop-action.schema.json' '$ROOT/docs/schemas/loop-test-result.schema.json' '$ROOT/docs/schemas/loop-maturity-report.schema.json' '$ROOT/docs/schemas/token-budget.schema.json' >/dev/null 2>&1"
assert "control-plane schemas parse" "jq empty '$ROOT/docs/schemas/tool-registry.schema.json' '$ROOT/docs/schemas/permission-audit-trail.schema.json' >/dev/null 2>&1"
assert "learning and architecture memory schemas parse" "jq empty '$ROOT/docs/schemas/architecture-memory-report.schema.json' '$ROOT/docs/schemas/memory-health-report.schema.json' '$ROOT/docs/schemas/champion-holdout-report.schema.json' >/dev/null 2>&1"
assert "skills manifest parses" "jq empty '$ROOT/skills/manifest.json' >/dev/null 2>&1"
assert "applicability issue set parses" "jq empty '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null 2>&1"
assert "artifact contract case set parses" "jq empty '$ROOT/tests/fixtures/adlc-artifact-contract-cases.json' >/dev/null 2>&1"
assert "implementation interface productionization example parses" "jq empty '$ROOT/docs/build-briefs/implementation-interfaces-productionization-example.json' >/dev/null 2>&1"
assert "loop-system maturity fixtures parse" "jq empty '$ROOT'/tests/fixtures/loop_maturity/*.json >/dev/null 2>&1"

echo ""
echo "--- Build Brief Contract ---"
assert "build brief requires applicability_manifest" "jq -e '.required | index(\"applicability_manifest\")' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "build brief requires product vocabulary" "jq -e '(.required | index(\"product_vocabulary\")) and .properties.product_vocabulary[\"\$ref\"] == \"#/definitions/product_vocabulary\"' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "build brief requires adlc_mode" "jq -e '. as \$s | (\$s.required | index(\"adlc_mode\")) and (\$s.properties.adlc_mode.enum == [\"prd_only\", \"decompose_only\", \"prd_and_decompose\"])' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "build brief requires enterprise_readiness_contract" "jq -e '. as \$s | (\$s.required | index(\"enterprise_readiness_contract\")) and (\$s.definitions.enterprise_readiness_contract.required | index(\"production_grade_target\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "build brief requires repo conventions" "jq -e '(.required | index(\"repo_conventions\")) and (.definitions.repo_conventions.properties.status.enum | index(\"extracted\")) and (.definitions.repo_conventions.properties.status.enum | index(\"files_present_but_no_normative_rules\")) and (.definitions.repo_conventions.properties.status.enum | index(\"none_found\")) and .definitions.repo_conventions.properties.explicit_empty_marker.const == \"no_conventions_found\"' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "build brief repo conventions support recorded waivers" "jq -e '.definitions.repo_conventions.properties.waivers.items.required == [\"rule\", \"reason\"]' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "build brief repo conventions support extractor fidelity metadata" "jq -e '.definitions.repo_conventions.properties.rules.items.properties.line.minimum == 1 and .definitions.repo_conventions.properties.rules.items.properties.line_start.minimum == 1 and .definitions.repo_conventions.properties.rules.items.properties.line_end.minimum == 1 and .definitions.repo_conventions.properties.removed_ci_gates.items.type == \"string\" and .definitions.repo_conventions.properties.warnings.items.required == [\"rule\", \"message\", \"source_path\"]' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "build brief allows 1.0 briefs without narrative contract" "'$ROOT/bin/adlc' validate-artifact --schema build-brief --input '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "build brief requires narrative contract at 1.1" "assert_build_brief_1_1_requires_narrative_contract"
assert "build brief allows prd_only without forced tickets" "jq -e '.properties.sections.properties.\"8_task_tickets\".minItems == 0' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "decomposition modes require task tickets and validation task references" "jq -e '.allOf[] | select(.if.properties.adlc_mode.enum == [\"decompose_only\", \"prd_and_decompose\"]) | .then.properties.sections.properties.\"8_task_tickets\".minItems == 1 and .then.properties.enterprise_readiness_contract.properties.validation_tasks.minItems == 1' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema requires task_classification" "jq -e '.definitions.task.required | index(\"task_classification\")' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema requires artifact taxonomy and decision contract" "jq -e '. as \$s | (\$s.definitions.task.required | index(\"artifact_type\")) and (\$s.definitions.task.properties.artifact_type.enum | index(\"decision_gate\")) and (\$s.definitions.task.required | index(\"decision_contract\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema requires enterprise execution contracts" "jq -e '. as \$s | (\$s.definitions.task.required | index(\"tech_debt_boundaries\")) and (\$s.definitions.task.required | index(\"compatibility_contract\")) and (\$s.definitions.task.required | index(\"evidence_responsibilities\")) and (\$s.definitions.task.required | index(\"definition_of_done\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema requires verification_spec" "jq -e '.definitions.task.required | index(\"verification_spec\")' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "verifier schema requires target files and expected failure mode" "jq -e '.definitions.verifier.required as \$r | (\$r | index(\"target_files\")) and (\$r | index(\"expected_failure_mode\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema preserves scalable AI code primitive refs" "jq -e '.definitions.task.properties.construct_map_refs.type == \"array\" and .definitions.task.properties.paved_road_refs.type == \"array\" and .definitions.task.properties.intent_contract_refs.type == \"array\" and (.definitions.task.properties.production_invariant_coverage.items.properties.status.enum | index(\"requires_human_judgment\")) and (.definitions.task.properties.production_invariant_coverage.items.properties.invariant.enum | index(\"idempotency\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema supports stable identity and resume fingerprints" "jq -e '.definitions.task.properties.stable_task_identity[\"\$ref\"] == \"#/definitions/stable_task_identity\" and .definitions.task.properties.resume_fingerprint[\"\$ref\"] == \"#/definitions/resume_fingerprint\" and (.definitions.resume_fingerprint.properties.status.enum | index(\"skipped_already_satisfied\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema supports slop quality gates" "jq -e '.definitions.task.properties.slop_quality_gate[\"\$ref\"] == \"#/definitions/slop_quality_gate\" and (.definitions.slop_quality_gate.properties.applicability.enum | index(\"required\")) and (.definitions.slop_quality_gate.properties.mode.enum | index(\"agent_output\")) and (.definitions.slop_quality_gate.properties.failure_action.enum | index(\"human_approval\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "build brief schema supports product vocabulary firewall" "jq -e '.definitions.product_vocabulary.required == [\"status\", \"mappings\", \"banned_tokens\"] and (.definitions.product_vocabulary.properties.status.enum | index(\"defined\")) and (.definitions.product_vocabulary.properties.status.enum | index(\"none_declared\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema supports explicit generated-output surfaces" "jq -e '.definitions.task.properties.generated_output_surface[\"\$ref\"] == \"#/definitions/generated_output_surface\" and (.definitions.generated_output_surface.required | index(\"active\")) and (.definitions.generated_output_surface.required | index(\"reason\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema supports implementation interface and productionization gates" "jq -e '.definitions.task.properties.implementation_interface_contract[\"\$ref\"] == \"#/definitions/implementation_interface_contract\" and .definitions.task.properties.productionization_gate[\"\$ref\"] == \"#/definitions/productionization_gate\" and (.properties.sections.properties | has(\"16_implementation_interfaces\")) and (.properties.sections.properties | has(\"17_productionization_gates\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "build brief schema supports clarity ledger and blindspot sections" "jq -e '.properties.epistemic_ledger[\"\$ref\"] == \"#/definitions/epistemic_ledger\" and .properties.sections.properties.\"18_blindspot_report\".oneOf[0][\"\$ref\"] == \"#/definitions/blindspot_report\" and .properties.sections.properties.\"19_clarity_interview\".oneOf[0][\"\$ref\"] == \"#/definitions/pending_questions\" and .properties.pending_questions_ref.type == \"string\"' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "compatibility contract supports verified surface predicates" "jq -e '.definitions.compatibility_contract.oneOf[0].properties.surfaces.type == \"array\" and .definitions.compatibility_contract.oneOf[0].properties.verification_predicates.items.required == [\"surface\", \"predicate\"] and .definitions.compatibility_contract.oneOf[0].properties.deprecation_record_ref.type == \"string\"' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "clarity gate schemas are registered" "'$ROOT/bin/adlc' health-check --json | jq -e '.status == \"pass\"' >/dev/null && PYTHONPATH='$ROOT/scripts' python3 -c 'from adlc_runtime.metadata import SCHEMA_ALIASES; required={\"epistemic-ledger\",\"blindspot-report\",\"pending-questions\",\"clarity-gate-report\",\"contract-surface-inventory\",\"compatibility-evidence-report\",\"execution-adapter-report\"}; assert required <= set(SCHEMA_ALIASES)'"
assert "pending questions schema records provenance" "jq -e '.properties.questions.items.properties.source.enum == [\"authored\", \"generated\"] and .properties.questions.items.properties.machine_generated.type == \"boolean\"' '$ROOT/docs/schemas/pending-questions.schema.json' >/dev/null"
assert "contract surface inventory schema records confidence and discovery" "jq -e '(.properties.summary.required | index(\"low_confidence\")) and (.properties.surfaces.items.required | index(\"source\")) and (.properties.surfaces.items.required | index(\"confidence\")) and (.properties.surfaces.items.required | index(\"consumer_discovery\")) and .properties.surfaces.items.properties.blocking.type == \"boolean\" and .properties.surfaces.items.properties.consumer_discovery.properties.status.enum == [\"attempted\", \"not_attempted\", \"unknown\"]' '$ROOT/docs/schemas/contract-surface-inventory.schema.json' >/dev/null"
assert "run report schema and command are registered" "PYTHONPATH='$ROOT/scripts' python3 -c 'from adlc_runtime.metadata import SCHEMA_ALIASES, COMMAND_METADATA; assert SCHEMA_ALIASES[\"run-report\"].endswith(\"run-report.schema.json\"); assert COMMAND_METADATA[\"run-report\"][\"mcp_name\"] == \"adlc_run_report\"' && '$ROOT/bin/adlc' mcp-tools --json | jq -e 'any(.tools[]; .name == \"adlc_run_report\")' >/dev/null"
assert "meta compensation schemas and commands are registered" "PYTHONPATH='$ROOT/scripts' python3 -c 'from adlc_runtime.metadata import SCHEMA_ALIASES, COMMAND_METADATA; required={\"predicate-library\",\"criterion-depth-report\",\"minimalism-audit-report\",\"completion-audit-report\",\"completion-audit-independence\"}; assert required <= set(SCHEMA_ALIASES); assert COMMAND_METADATA[\"predicate-library\"][\"mcp_name\"] == \"adlc_predicate_library\"; assert COMMAND_METADATA[\"minimalism-audit\"][\"mcp_name\"] == \"adlc_minimalism_audit\"; assert COMMAND_METADATA[\"completion-audit\"][\"mcp_name\"] == \"adlc_completion_audit\"' && '$ROOT/bin/adlc' mcp-tools --json | jq -e 'any(.tools[]; .name == \"adlc_predicate_library\") and any(.tools[]; .name == \"adlc_minimalism_audit\") and any(.tools[]; .name == \"adlc_completion_audit\" and (.inputSchema.required | index(\"executor\")) and (.inputSchema.required | index(\"auditor\")) and (.inputSchema.required | index(\"independence_evidence\")))' >/dev/null"
assert "completion audit independence fixture is schema-valid" "'$ROOT/bin/adlc' validate-artifact --schema completion-audit-independence --input '$ROOT/tests/fixtures/completion_audit/independence.json' --json | jq -e '.valid == true' >/dev/null"
assert "completion audit report schema carries structured independence evidence" "jq -e '(.properties | has(\"executor\")) and (.properties | has(\"independence\")) and (.properties.independence.required | index(\"evidence_sha256\")) and .properties.independence.properties.basis.enum == [\"separate_agent\",\"separate_session\",\"external_reviewer\"]' '$ROOT/docs/schemas/completion-audit-report.schema.json' >/dev/null"
assert "build brief criteria support predicate floors and payload classes" "jq -e '.definitions.task.properties.acceptance_criteria.items.oneOf[] | select(.type==\"object\") | .properties.verification_predicate.minLength == 1 and .properties.substance_floor.minLength == 1 and (.properties.allowed_payload_classes.items.enum | index(\"product-change\")) and (.properties.allowed_payload_classes.items.enum | index(\"process-artifact\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "predicate library seeds five audit patterns" "'$ROOT/bin/adlc' validate-artifact --schema predicate-library --input '$ROOT/docs/solutions/predicate-library.json' --json | jq -e '.valid == true' >/dev/null && jq -e '([.rules[].id] | index(\"PRED-PRESENCE-ONLY-VALIDATION\") and index(\"PRED-SCHEMA-VALID-EMPTY\") and index(\"PRED-STATIC-TEMPLATE-CONTENT\") and index(\"PRED-PROCESS-ARTIFACT-PROOF\") and index(\"PRED-UNRESOLVABLE-EVIDENCE-REF\"))' '$ROOT/docs/solutions/predicate-library.json' >/dev/null"
assert "eval council and manifest include Minimalism Auditor" "rg -q 'Minimalism Auditor|minimalism-audit|predicate-library' '$ROOT/skills/eval-council/SKILL.md' && jq -e '.skills[] | select(.name==\"eval-council\") | (.activation.overlay_personas | index(\"minimalism_auditor\")) != null and (.activation.overlay_triggers.minimalism_auditor | index(\"completed implementation_task\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "specificity and feedback skills load predicate library rules" "rg -q 'predicate library|PRED-\\*|verification_predicate|substance floor' '$ROOT/skills/specificity-judge/SKILL.md' && rg -q 'completion-audit|predicate-library|feedback_findings' '$ROOT/skills/feedback-loop/SKILL.md' && rg -q 'predicate-library rule ID|honesty-contract violation' '$ROOT/skills/learning-capture/SKILL.md'"
assert "task schema supports honesty contracts" "jq -e '.definitions.task.properties.honesty_contract[\"\$ref\"] == \"#/definitions/honesty_contract\" and .definitions.honesty_contract.required == [\"applicability\", \"reason\"] and (.definitions.honesty_contract.properties.applicability.enum | index(\"required\")) and (.definitions.honesty_contract.properties.applicability.enum | index(\"not_applicable\")) and (.definitions.honesty_contract.properties.output_surfaces.items.enum | index(\"artifact\")) and (.definitions.honesty_contract.properties.required_output_fields.items.enum | index(\"doc_honesty_section\")) and (.definitions.honesty_contract.properties.required_output_fields.items.enum | index(\"no_overclaim\")) and (.definitions.honesty_contract.properties.required_output_fields.items.enum | index(\"limitations\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema supports performance envelopes" "jq -e '.definitions.task.properties.performance_envelope[\"\$ref\"] == \"#/definitions/performance_envelope\" and (.definitions.performance_envelope.required | index(\"applicability\")) and (.definitions.performance_envelope.required | index(\"reason\")) and (.definitions.performance_envelope.properties.applicability.enum | index(\"required\")) and (.definitions.performance_envelope.properties.applicability.enum | index(\"not_applicable\")) and .definitions.performance_envelope.properties.expected_input_scale.items.required == [\"name\", \"expected\", \"unit\"] and .definitions.performance_envelope.properties.hot_paths.items.required == [\"operation\", \"complexity\", \"rationale\"] and .definitions.performance_envelope.properties.benchmark_required.type == \"boolean\" and (.definitions.performance_envelope.properties.benchmark_spec.required | index(\"command\")) and (.definitions.performance_envelope.allOf[] | select(.if.properties.applicability.const == \"required\") | (.then.required | index(\"expected_input_scale\")) and (.then.required | index(\"hot_paths\")) and (.then.required | index(\"benchmark_required\")))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema supports task sizing" "jq -e '.definitions.task.properties.task_sizing[\"\$ref\"] == \"#/definitions/task_sizing\" and .definitions.task_sizing.required == [\"applicability\", \"reason\"] and (.definitions.task_sizing.properties.applicability.enum | index(\"required\")) and (.definitions.task_sizing.properties.applicability.enum | index(\"not_applicable\")) and (.definitions.task_sizing.properties.change_surface.properties.surface_kind.enum | index(\"atomic_cross_module\")) and (.definitions.task_sizing.properties.basis.items.enum | index(\"module_plan\")) and (.definitions.task_sizing.allOf[] | select(.if.properties.applicability.const == \"required\") | (.then.required | index(\"basis\")) and (.then.required | index(\"change_surface\")) and (.then.required | index(\"split_decision\")))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema supports module plans" "jq -e '.definitions.task.properties.module_plan[\"\$ref\"] == \"#/definitions/module_plan\" and .definitions.module_plan.required == [\"applicability\", \"reason\"] and (.definitions.module_plan.properties.applicability.enum | index(\"required\")) and (.definitions.module_plan.properties.applicability.enum | index(\"not_applicable\")) and (.definitions.module_plan.allOf[] | select(.if.properties.applicability.const == \"required\") | (.then.required | index(\"files\")) and (.then.required | index(\"architecture_test\")))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "module plan file schema forbids catch-all names pure side effects and conjunction responsibilities" "jq -e '.definitions.module_plan_file.required == [\"path\",\"responsibility\",\"purity\",\"capabilities\"] and .definitions.module_plan_file.properties.capabilities.minItems == 1 and (.definitions.module_plan_file.properties.capabilities.items.enum | index(\"fs\")) and (.definitions.module_plan_architecture_test.required | index(\"write_first\")) and .definitions.module_plan_architecture_test.properties.write_first.const == true' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "module plans support paved-road pattern provenance and deviations" "jq -e '.definitions.module_plan.properties.pattern_id.type == \"string\" and .definitions.module_plan.properties.pattern_ref[\"\$ref\"] == \"#/definitions/module_plan_pattern_ref\" and .definitions.module_plan.properties.pattern_deviation_reason.type == \"string\" and .definitions.module_plan_pattern_ref.properties.exemplar_commit.pattern == \"^[0-9a-f]{40}$\"' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "paved-road pattern registry schema and first entry are valid" "'$ROOT/bin/adlc' validate-artifact --schema paved-road-pattern-registry --input '$ROOT/skills/paved-road-registry/patterns.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null && jq -e '.patterns[0].id == \"interralis:evidence-module\" and .patterns[0].exemplar.repo == \"github.com/interralis/interralis\" and .patterns[0].exemplar.path == \"src/observability/ingestion/harness_sources\" and .patterns[0].exemplar.commit == \"acad66428a1b5c872a5796cb779787f7d39403a3\" and any(.patterns[0].module_plan_template.files[]; .role == \"collect\" and .purity == \"impure\") and any(.patterns[0].module_plan_template.files[]; .role == \"privacy\" and .purity == \"pure\") and .patterns[0].module_plan_template.architecture_test.write_first == true' '$ROOT/skills/paved-road-registry/patterns.json' >/dev/null"
assert "build brief accepts valid module plan" "assert_build_brief_accepts_valid_module_plan"
assert "build brief rejects module plan responsibility using and" "assert_build_brief_rejects_module_plan_and_responsibility"
assert "build brief rejects pure module plan side effects" "assert_build_brief_rejects_module_plan_pure_side_effects"
assert "build brief rejects catch-all module plan file names" "assert_build_brief_rejects_module_plan_catch_all_path"
assert "build brief rejects miscellaneous module responsibilities" "assert_build_brief_rejects_module_plan_misc_responsibility"
assert "task metadata supports loop contract refs" "jq -e '.definitions.task.properties.work_item_metadata.properties.loop_contract_path.type == \"string\" and .definitions.task.properties.work_item_metadata.properties.loop_action_path.type == \"string\" and .definitions.task.properties.work_item_metadata.properties.loop_maturity_report_path.type == \"string\"' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "implementation interface schema captures interface contract shape" "jq -e '.definitions.implementation_interface_contract.oneOf[0].required as \$r | (\$r | index(\"reuse\")) and (\$r | index(\"consumes\")) and (\$r | index(\"emits\")) and (\$r | index(\"minimum_fields\")) and (\$r | index(\"invariants\")) and (\$r | index(\"integration_points\")) and (\$r | index(\"validation_gates\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "productionization gate schema supports coverage state and no-overclaim" "jq -e '(.definitions.productionization_gate.oneOf[0].properties.coverage_state.enum | index(\"production_ready\")) and (.definitions.productionization_gate.oneOf[0].properties.coverage_state.enum | index(\"monitor_only\")) and (.definitions.productionization_gate.oneOf[0].required | index(\"no_overclaim\")) and (.definitions.productionization_gate.oneOf[0].properties.operational_readiness.properties | has(\"rollback_path\")) and (.definitions.productionization_gate.oneOf[0].properties.security_privacy.properties | has(\"redaction_posture\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "slop quality metrics can reference validators" "jq -e '.definitions.slop_quality_gate.properties.metrics.items.oneOf[] | select(.type==\"object\") | (.required | index(\"metric_type\")) and (.required | index(\"validator_ref\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema allows compact not-applicable safety contracts" "jq -e 'any(.definitions.task.properties.anti_slop_rules.oneOf[]; .\"\$ref\"==\"#/definitions/not_applicable_reason\") and any(.definitions.tech_debt_boundaries.oneOf[]; .\"\$ref\"==\"#/definitions/not_applicable_reason\") and any(.definitions.compatibility_contract.oneOf[]; .\"\$ref\"==\"#/definitions/not_applicable_reason\")' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "required slop quality gates require threshold metrics and eval cases" "jq -e '.definitions.slop_quality_gate.allOf[] | select(.if.properties.applicability.const == \"required\") | (.then.required | index(\"threshold\")) and (.then.required | index(\"metrics\")) and (.then.required | index(\"eval_cases\")) and (.then.required | index(\"failure_action\"))' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "enterprise readiness contract can carry scalable primitive rollups" "jq -e '.definitions.enterprise_readiness_contract.properties.construct_map_refs.type == \"array\" and .definitions.enterprise_readiness_contract.properties.paved_road_refs.type == \"array\" and .definitions.enterprise_readiness_contract.properties.production_invariant_coverage.type == \"array\"' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "enterprise readiness contract can carry interface and productionization refs" "jq -e '.definitions.enterprise_readiness_contract.properties.implementation_interface_refs.type == \"array\" and .definitions.enterprise_readiness_contract.properties.productionization_gate_refs.type == \"array\"' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "implementation tasks cannot carry unresolved Type 1 decisions" "jq -e '.definitions.task.allOf[] | select(.if.properties.artifact_type.const==\"implementation_task\") | (.then.properties.decision_contract.properties.status.enum | index(\"unresolved\") | not) and .then.properties.decision_contract.properties.blocks_implementation.const == false' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "scope-lock epics cannot carry file-change instructions" "jq -e '.definitions.task.allOf[] | select(.if.properties.artifact_type.const==\"scope_lock_epic\") | .then.properties.files_to_modify.maxItems == 0 and .then.properties.files_to_create.maxItems == 0' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "decision gates enforce Type 1 blocking semantics" "jq -e '.definitions.task.allOf[] | select(.if.properties.artifact_type.const==\"decision_gate\") | .then.properties.bpe_classification.const == \"type_1\" and .then.properties.decision_contract.properties.type1_decision.const == true and .then.properties.decision_contract.properties.status.const == \"unresolved\" and .then.properties.decision_contract.properties.blocks_implementation.const == true' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "validation tasks map to build validation and do not block implementation" "jq -e '.definitions.task.allOf[] | select(.if.properties.artifact_type.const==\"validation_task\") | .then.properties.task_classification.const == \"build_validation\" and .then.properties.decision_contract.properties.blocks_implementation.const == false' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema keeps failure_modes required" "jq -e '.definitions.task.required | index(\"failure_modes\")' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "change surface includes service_boundary_change" "jq -e '.properties.change_surface.required | index(\"service_boundary_change\")' '$ROOT/docs/schemas/applicability-manifest.schema.json' >/dev/null"
assert "applicability manifest supports implementation and productionization sections" "jq -e '(.properties.section_policy.items.properties.section_name.enum | index(\"16_implementation_interfaces\")) and (.properties.section_policy.items.properties.section_name.enum | index(\"17_productionization_gates\"))' '$ROOT/docs/schemas/applicability-manifest.schema.json' >/dev/null"
assert "workflow-state supports compound phases and task fingerprints" "jq -e '(.properties.phase.enum | index(\"compound_preflight\")) and (.properties.phase.enum | index(\"intent_validation\")) and (.properties.phase.enum | index(\"learning_capture\")) and .properties.task_fingerprints.items.properties.input_hash.type == \"string\"' '$ROOT/docs/schemas/workflow-state.schema.json' >/dev/null"
assert "workflow-state phase enum covers WORKFLOW.dot nodes" "assert_workflow_state_covers_workflow_nodes"
assert "workflow-state supports durable run identity" "jq -e '.properties.run_id.type == \"string\" and .properties.attempt.minimum == 1 and .properties.last_resumed_at.format == \"date-time\" and .properties.side_effects.items.properties.run_id.type == \"string\" and .properties.side_effects.items.properties.session_id.type == \"string\" and .properties.side_effects.items.properties.brief_id.type == \"string\"' '$ROOT/docs/schemas/workflow-state.schema.json' >/dev/null"
assert "workflow-state supports work item links" "jq -e '.properties.work_item_links.items.properties.external_id.type == \"string\" and (.properties.work_item_links.items.properties.operation.enum | index(\"append\")) and (.properties.work_item_links.items.properties.status.enum | index(\"appended\")) and .properties.work_item_links.items.properties.last_sync_idempotency_key.type == \"string\"' '$ROOT/docs/schemas/workflow-state.schema.json' >/dev/null"
assert "work-item sync schema requires stable identity and update evidence" "jq -e '.required == [\"contract_version\",\"target\",\"work_item\",\"run_identity\",\"status_update\"] and (.properties.work_item.required | index(\"external_id\")) and (.properties.work_item.required | index(\"idempotency_key\")) and (.properties.run_identity.required | index(\"run_id\")) and (.properties.run_identity.required | index(\"session_id\")) and (.properties.status_update.required | index(\"evidence_refs\")) and (.properties.status_update.required | index(\"next_action\"))' '$ROOT/docs/schemas/work-item-sync.schema.json' >/dev/null"
assert "work-queue schema supports claim lifecycle and path ownership" "jq -e '(.properties.tasks.items[\"\$ref\"] == \"#/definitions/task\") and (.definitions.task.properties.status.enum | index(\"queued\")) and (.definitions.task.properties.status.enum | index(\"claimed\")) and (.definitions.task.properties.status.enum | index(\"running\")) and (.definitions.task.properties.status.enum | index(\"blocked\")) and (.definitions.task.properties.status.enum | index(\"done\")) and (.definitions.task.properties.status.enum | index(\"escalated\")) and (.definitions.task.required | index(\"expected_paths\")) and (.definitions.path_owner.properties.kind.enum | index(\"glob\")) and (.definitions.claim.required | index(\"claim_id\")) and (.definitions.worktree.properties.status.enum | index(\"cleanup_blocked\"))' '$ROOT/docs/schemas/work-queue.schema.json' >/dev/null"
assert "work-queue schema supports benchmark evidence" "jq -e '.definitions.task.properties.benchmark_required.type == \"boolean\" and .definitions.task.properties.benchmark_refs.type == \"array\" and .definitions.task.properties.benchmark_refs.items.type == \"string\"' '$ROOT/docs/schemas/work-queue.schema.json' >/dev/null"
assert "workflow-state supports queue claims and worktree refs" "jq -e '(.properties.queue_claims.items.properties.status.enum | index(\"claimed\")) and (.properties.queue_claims.items.properties.status.enum | index(\"released\")) and .properties.queue_claims.items.properties.expected_paths.items.properties.kind.enum[2] == \"glob\" and (.properties.worktree_refs.items.properties.status.enum | index(\"active\")) and (.properties.worktree_refs.items.properties.status.enum | index(\"cleaned\")) and .properties.worktree_refs.items.properties.cleanup_eligible.type == \"boolean\"' '$ROOT/docs/schemas/workflow-state.schema.json' >/dev/null"
assert "workflow-state supports executable phase artifacts" "jq -e '.properties.phase_artifacts.items.properties.artifact_ref.type == \"string\" and (.properties.phase_artifacts.items.properties.status.enum | index(\"planned\")) and (.properties.phase_artifacts.items.properties.status.enum | index(\"pass\")) and (.properties.phase_artifacts.items.properties.status.enum | index(\"blocked\"))' '$ROOT/docs/schemas/workflow-state.schema.json' >/dev/null"
assert "workflow-state supports loop progress and control channel" "jq -e '.properties.loop_progress.properties.last_progress_signal.type == \"string\" and (.properties.control_events.items.properties.event_type.enum | index(\"steer\")) and (.properties.control_events.items.properties.event_type.enum | index(\"abort\")) and .properties.safe_checkpoint.properties.idempotent.type == \"boolean\" and .properties.escalation_context.properties.no_progress_after.type == \"integer\"' '$ROOT/docs/schemas/workflow-state.schema.json' >/dev/null"
assert "loop schemas support budget guard evidence" "jq -e '.properties.budget_guard[\"\$ref\"] == \"#/definitions/budget_guard\" and (.definitions.budget_guard.required | index(\"token_budget_ref\")) and (.definitions.budget_guard.required | index(\"hard_stop_behavior\"))' '$ROOT/docs/schemas/loop-contract.schema.json' >/dev/null && jq -e '.properties.budget_estimate.required | index(\"projected_total_tokens\")' '$ROOT/docs/schemas/loop-action.schema.json' >/dev/null && jq -e '.properties.budget_status[\"\$ref\"] == \"#/definitions/budget_status\" and (.definitions.budget_status.properties.status.enum | index(\"missing\")) and (.definitions.budget_status.properties.status.enum | index(\"stale\"))' '$ROOT/docs/schemas/loop-maturity-report.schema.json' >/dev/null"
assert "workflow-state supports loop budget status" "jq -e '(.properties.budget_status.properties.status.enum | index(\"healthy\")) and (.properties.budget_status.properties.decision.enum | index(\"wrap_up\")) and (.properties.budget_status.properties.stop_reason.enum | index(\"budget_exhausted\"))' '$ROOT/docs/schemas/workflow-state.schema.json' >/dev/null"
assert "token-budget schema supports stale status" "jq -e '.properties.status.enum | index(\"stale\")' '$ROOT/docs/schemas/token-budget.schema.json' >/dev/null"
assert "tool registry supports workflow DAG and legacy phases" "jq -e '(.definitions.phase.enum | index(\"research\")) and (.definitions.phase.enum | index(\"code\")) and (.definitions.phase.enum | index(\"pr_prep\")) and (.definitions.phase.enum | index(\"phase_9_codegen_execution\"))' '$ROOT/docs/schemas/tool-registry.schema.json' >/dev/null"
assert "permission audit trail supports escalation runtime evidence" "jq -e '(.properties.entries.items.properties.decision.enum | index(\"escalated\")) and .properties.entries.items.properties.phase.type == \"string\" and (.properties.entries.items.properties.side_effect_profile.enum | index(\"mutating\")) and .properties.entries.items.properties.policy_ref.type == \"string\"' '$ROOT/docs/schemas/permission-audit-trail.schema.json' >/dev/null"
assert "permission audit trail supports run identity and stop reasons" "jq -e '.properties.run_id.type == \"string\" and .properties.entries.items.properties.run_id.type == \"string\" and .properties.entries.items.properties.stop_reason.type == \"string\"' '$ROOT/docs/schemas/permission-audit-trail.schema.json' >/dev/null"
assert "session-state schema supports run identity on permission decisions" "jq -e '.properties.run_id.type == \"string\" and .properties.permission_decisions.items.properties.run_id.type == \"string\" and .properties.permission_decisions.items.properties.session_id.type == \"string\" and .properties.permission_decisions.items.properties.brief_id.type == \"string\"' '$ROOT/docs/schemas/session-state.schema.json' >/dev/null"
assert "test-author output supports loop coverage and result refs" "jq -e '.properties.generated_tests.items.properties.coverage_tags.type == \"array\" and .properties.generated_tests.items.properties.covers_required_tests.type == \"array\" and .properties.generated_tests.items.properties.execution_evidence_refs.type == \"array\" and .properties.test_result_refs.type == \"array\"' '$ROOT/docs/schemas/test-author-output.schema.json' >/dev/null"
assert "workflow-state validates task fingerprints" "assert_workflow_state_accepts_task_fingerprints"
assert "workflow-state validates interface and productionization statuses" "assert_workflow_state_accepts_interface_and_productionization_status"
assert "workflow-state validates loop progress and control fixture" "assert_workflow_state_accepts_loop_progress_control"
assert "workflow-state validates run identity side effects" "assert_workflow_state_accepts_run_identity_side_effects"
assert "workflow-state validates work item links" "assert_workflow_state_accepts_work_item_links"
assert "workflow-state validates queue claims and worktree refs" "assert_workflow_state_accepts_queue_and_worktree_refs"
assert "permission audit trail validates run identity evidence" "assert_permission_audit_trail_accepts_run_identity"

echo ""
echo "--- Artifact Contract Cases ---"
assert "artifact contract evaluator exists and is executable" "[ -x '$ROOT/tests/artifact_contract/evaluate.sh' ]"
assert "artifact contract cases cover decision, duplicate scope, validation, and emitters" "jq -e '[.cases[].id] | all([\"ART-002-unresolved-type1-in-implementation\", \"ART-003-duplicate-parent-child-scope\", \"ART-004-validation-task-missing\", \"ART-005-emitter-drops-taxonomy\"][]; index(.))' '$ROOT/tests/fixtures/adlc-artifact-contract-cases.json' >/dev/null"
assert "artifact contract evaluator passes" "'$ROOT/tests/artifact_contract/evaluate.sh' >/dev/null 2>&1"

echo ""
echo "--- Prompt Contracts ---"
assert "scalable AI code primitives spec exists" "[ -f '$ROOT/docs/specs/scalable-ai-code-primitives.md' ] && rg -q 'Graph-Backed Construct Map|Agent Paved-Road Registry|Verifiability Gate|Production Invariant Coverage' '$ROOT/docs/specs/scalable-ai-code-primitives.md'"
assert "slop eval loop spec exists" "[ -f '$ROOT/docs/specs/slop-eval-loop.md' ] && rg -q 'Benchmark Contract|Pre-Ship Regression|Delivery Guard|Post-Ship Sampling|Case Promotion' '$ROOT/docs/specs/slop-eval-loop.md'"
assert "loop-system maturity spec exists" "[ -f '$ROOT/docs/specs/loop-system-maturity-audit.md' ] && rg -q 'Loop Contract|LLM Action Envelope|mandatory_floor|additive_agent_tests|self_autonomous' '$ROOT/docs/specs/loop-system-maturity-audit.md'"
assert "loop-system maturity spec documents budget guard no-overclaim" "rg -q 'budget_guard|budget_status|budget_exhausted|budget_stale|self_autonomous' '$ROOT/docs/specs/loop-system-maturity-audit.md'"
assert "agent-native and emitter specs document work item sync" "rg -q 'sync-work-item|work_item_links|work-item state synchronization' '$ROOT/docs/specs/agent-native-interface.md' && rg -q 'Work-Item State Sync Contract|sync-work-item|action-admission' '$ROOT/docs/specs/emitter-contract.md' && rg -q 'sync-work-item|work_item_links|side_effects' '$ROOT/docs/specs/work-item-reconciliation.md'"
assert "agent-native docs document work queue and worktree substrate" "rg -q 'queue-status|queue-claim|worktree-prepare|dirty-check|file-overlap|adlc-queue|adlc-worktree' '$ROOT/docs/specs/agent-native-interface.md' && rg -q 'queue-status|queue-claim|worktree-prepare|file-overlap' '$ROOT/README.md'"
assert "token and pre-turn specs document loop budget guards" "rg -q 'budget_guard|budget_status|self_autonomous' '$ROOT/docs/specs/token-budgets.md' && rg -q 'loop-budget-check|budget_exhausted|budget_status|self_autonomous' '$ROOT/docs/specs/pre-turn-check.md'"
assert "compound learning store spec and template exist" "[ -f '$ROOT/docs/specs/compound-engineering-learning-store.md' ] && [ -f '$ROOT/docs/solutions/README.md' ] && [ -f '$ROOT/docs/solutions/_template.md' ] && rg -q 'docs/solutions|learning_refs|learning_capture|learning_refresh|redaction' '$ROOT/docs/specs/compound-engineering-learning-store.md'"
assert "compound learning store captures loop maturity reports" "rg -q 'loop_contract_path|loop_maturity_report_path|maturity_verdict' '$ROOT/docs/specs/compound-engineering-learning-store.md'"
assert "compound learning store captures loop budget status" "rg -q 'budget_status|budget_guard|stale.*budget' '$ROOT/docs/specs/compound-engineering-learning-store.md'"
assert "learning-entry validator exists and accepts valid fixtures" "[ -x '$ROOT/scripts/validate_learning_entry.py' ] && '$ROOT/scripts/validate_learning_entry.py' '$ROOT/tests/fixtures/learning-entry-bug.md' >/dev/null && '$ROOT/scripts/validate_learning_entry.py' '$ROOT/tests/fixtures/learning-entry-knowledge.md' >/dev/null"
assert "learning-entry validator rejects malformed fixtures" "if '$ROOT/scripts/validate_learning_entry.py' '$ROOT/tests/fixtures/learning-entry-invalid.md' >/dev/null 2>&1; then false; else true; fi"
assert "triage emits task classification" "rg -q 'task_classification' '$ROOT/agents/triage.md'"
assert "PRD agent captures reuse and tech debt boundaries" "rg -q 'reuse|tech debt|existing system, component, or workflow|existing services, components, or patterns|blocking tech debt' '$ROOT/agents/PM-PRD-AGENT.md'"
assert "PRD evaluator checks reuse and tech debt readiness" "rg -q 'missing reuse boundary|missing debt risk|Repo-Aware Reuse & Debt Framing|reuse/debt boundaries' '$ROOT/skills/prd-generation/SKILL.md'"
assert "codebase research evidence-gates debt findings" "rg -q 'Debt Evidence And Calibration|path:line|false_positives_considered|Do not aim for a finding count' '$ROOT/skills/codebase-research/SKILL.md'"
assert "codebase research emits scalable primitive evidence" "rg -q 'Scalable AI Code Primitive Research|construct_map|paved_road_evidence|load_bearing_invariants' '$ROOT/skills/codebase-research/SKILL.md'"
assert "graph research skill defines Graphify and Beads roles" "rg -q 'Graphify.*research substrate|Beads.*work graph|compatibility_evidence|dark_code_hotspots' '$ROOT/skills/graph-research/SKILL.md'"
assert "graph research skill captures construct maps and paved roads" "rg -q 'Construct Map Rules|construct_map|paved_road_refs|validation surfaces' '$ROOT/skills/graph-research/SKILL.md'"
assert "paved-road registry skill defines evidence-backed build paths" "rg -q 'paved_road_candidates|no_paved_road_found|allowed_departure|do_not_reimplement' '$ROOT/skills/paved-road-registry/SKILL.md'"
assert "paved-road registry documents structural patterns and approval" "rg -q 'patterns.json|interralis:evidence-module|module-plan-check|pattern_deviation_reason|human approval' '$ROOT/skills/paved-road-registry/SKILL.md'"
assert "dark-code audit skill captures structural and velocity risk" "rg -q 'Structural Dark Code|Velocity Dark Code|insufficient data to assess|comprehension infrastructure' '$ROOT/skills/dark-code-audit/SKILL.md'"
assert "context-layers skill defines all three artifacts" "rg -q 'Module Manifest|Behavioral Contracts|Decision Log|Reasoning unknown' '$ROOT/skills/context-layers/SKILL.md'"
assert "comprehension-gate skill defines blocking verdicts" "rg -q 'Comprehension Verdict|CLEAR|REVIEW REQUIRED|HOLD|Passing tests' '$ROOT/skills/comprehension-gate/SKILL.md'"
assert "researcher emits calibrated debt findings" "rg -q 'architecture mental model|false positives considered|debt_calibration|Unsupported or low-confidence debt claims' '$ROOT/agents/researcher.md'"
assert "researcher emits graph and dark-code evidence" "rg -q 'graph_research_evidence|compatibility_evidence|dark_code_risk|Graphify before broad raw search|Beads only as task-memory' '$ROOT/agents/researcher.md'"
assert "researcher emits construct maps and paved-road evidence" "rg -q 'construct_map|paved_road_evidence|load_bearing_invariants|no_paved_road_found' '$ROOT/agents/researcher.md'"
assert "researcher emits implementation interface and blocked production claims" "rg -q 'implementation_interface_candidates|blocked_production_claims|Implementation Interface Evidence' '$ROOT/agents/researcher.md'"
assert "researcher consumes compound learning refs" "rg -q 'compound_context|learning_refs|docs/solutions|no_op_reasons' '$ROOT/agents/researcher.md'"
assert "planner references applicability manifest" "rg -q 'applicability_manifest' '$ROOT/agents/planner.md'"
assert "planner supports ADLC PRD and decomposition modes" "rg -q 'prd_only.*decompose_only.*prd_and_decompose|decompose_only.*prd_and_decompose' '$ROOT/agents/planner.md'"
assert "planner requires graph-backed compatibility and context layers" "rg -q 'Graph-Backed Compatibility And Comprehension|context-layer artifact|MODULE_MANIFEST|Graphify identifies a dark-code hotspot' '$ROOT/agents/planner.md'"
assert "planner enforces behavior-first task wording" "rg -q 'concrete user or system behavior|intended behavior' '$ROOT/agents/planner.md'"
assert "planner treats reuse and tech debt as planning inputs" "rg -q 'reuse_opportunities|tech_debt|Reuse And Tech-Debt Discipline' '$ROOT/agents/planner.md'"
assert "planner requires reference implementations and debt prerequisite handling" "rg -q 'reference_impl|prerequisite task|reimplementing cited helpers|existing pattern cannot absorb the change' '$ROOT/agents/planner.md'"
assert "planner keeps unsupported debt out of scope" "rg -q 'Unsupported debt claims|must not become tasks|Do not recommend rewrites|path:line' '$ROOT/agents/planner.md'"
assert "planner consumes learning refs and preserves task identity" "rg -q 'learning_refs|docs/solutions|stable_task_identity|resume_fingerprint|Do not renumber tasks' '$ROOT/agents/planner.md'"
assert "planner defines artifact taxonomy and automatic validation tasks" "rg -q 'scope_lock_epic|decision_gate|implementation_task|validation_task' '$ROOT/agents/planner.md' && rg -q 'Generate validation tasks automatically' '$ROOT/agents/planner.md'"
assert "planner blocks unresolved Type 1 implementation" "rg -q 'unresolved Type 1.*decision_gate|decision_gate.*unresolved Type 1' '$ROOT/agents/planner.md'"
assert "planner emits scalable AI code primitive evidence" "rg -q 'Scalable AI Code Primitives|construct_map|paved_road_refs|production_invariant_coverage|Verifiability gate' '$ROOT/agents/planner.md'"
assert "planner emits implementation interface and productionization gates" "rg -q 'Implementation Interface And Productionization Gates|implementation_interface_contract|productionization_gate|missing_productionization_gate|production_ready' '$ROOT/agents/planner.md'"
assert "planner emits loop contracts for LLM-driven action gates" "rg -q 'Loop Contract And LLM Action Gates|loop_contract_path|loop_action_path|loop_maturity_report_path|loop-maturity-audit' '$ROOT/agents/planner.md'"
assert "planner emits slop quality gates for generated outputs" "rg -q 'Slop Quality Gate|slop_quality_gate|case_promotion_sources|generated-output surface' '$ROOT/agents/planner.md'"
assert "planner omits slop quality gates when not applicable" "rg -q 'omit .*slop_quality_gate|Do not add the gate as ceremony' '$ROOT/agents/planner.md'"
assert "planner emits repo conventions" "rg -q 'repo-conventions' '$ROOT/agents/planner.md' && rg -q 'repo_conventions' '$ROOT/agents/planner.md' && rg -q 'no_conventions_found' '$ROOT/agents/planner.md'"
assert "planner emits product vocabulary firewall" "rg -q 'Product Vocabulary' '$ROOT/agents/planner.md' && rg -q 'product_vocabulary' '$ROOT/agents/planner.md' && rg -q 'banned_tokens' '$ROOT/agents/planner.md' && rg -q 'none_declared' '$ROOT/agents/planner.md' && rg -q 'Product vocabulary' '$ROOT/agents/ADLC-BUILD-BRIEF-AGENT.md' && rg -q 'codenames' '$ROOT/agents/ADLC-BUILD-BRIEF-AGENT.md' && rg -q 'ticket IDs' '$ROOT/agents/ADLC-BUILD-BRIEF-AGENT.md'"
assert "planner and Build Brief agent emit module plan decisions" "rg -q 'module_plan' '$ROOT/agents/planner.md' && rg -q 'write_first=true' '$ROOT/agents/planner.md' && rg -q 'Module Plan' '$ROOT/agents/ADLC-BUILD-BRIEF-AGENT.md'"
assert "planner and Build Brief agent support pattern-generated module plans" "rg -q 'pattern:interralis:evidence-module.*module_root|pattern_deviation_reason|module-plan-check.*generates the plan' '$ROOT/agents/planner.md' && rg -q 'registered structural paved-road pattern|pattern_deviation_reason' '$ROOT/agents/ADLC-BUILD-BRIEF-AGENT.md'"
assert "code reviewer runs comprehension gate" "rg -q 'Comprehension Gate|comprehension_artifact|REVIEW REQUIRED|HOLD' '$ROOT/agents/code-reviewer.md'"
assert "code reviewer checks scalable AI code primitives" "rg -q 'Scalable code primitives|construct-map refs|paved-road refs|production invariant coverage' '$ROOT/agents/code-reviewer.md'"
assert "code reviewer checks implementation interface and productionization gates" "rg -q 'missing_implementation_interface_contract|missing_productionization_gate|overclaimed_production_ready|production_claim_overreach' '$ROOT/agents/code-reviewer.md'"
assert "code reviewer checks slop quality gates" "rg -q 'Slop quality gate|missing_slop_quality_gate|slop score.*below threshold|missing_slop_case_promotion' '$ROOT/agents/code-reviewer.md'"
assert "code reviewer checks repo conventions" "rg -q 'Target repo conventions' '$ROOT/agents/code-reviewer.md' && rg -q 'missing_repo_convention_evidence' '$ROOT/agents/code-reviewer.md' && rg -q 'silent_convention_waiver' '$ROOT/agents/code-reviewer.md'"
assert "coder uses verification_spec" "rg -q 'verification_spec' '$ROOT/agents/coder.md'"
assert "verification discipline is task-class-aware" "rg -q 'build_validation|lint_cleanup' '$ROOT/skills/tdd-enforcement/SKILL.md'"
assert "codegen context consumes verification_spec" "rg -q 'verification_spec' '$ROOT/skills/codegen-context/SKILL.md'"
assert "codegen context inlines scalable AI code primitives" "rg -q 'missing_scalable_code_primitives|Scalable AI Code Primitives|construct_map_refs|paved_road_refs|production_invariant_coverage' '$ROOT/skills/codegen-context/SKILL.md'"
assert "codegen context inlines implementation interface and productionization gates" "rg -q 'missing_implementation_interface_contract|missing_productionization_gate|overclaimed_production_ready|Implementation Interface|Productionization Gate' '$ROOT/skills/codegen-context/SKILL.md'"
assert "codegen context inlines loop contracts and action gates" "rg -q 'missing_loop_contract|Loop Contract|loop-test-selection|loop-action-validate|loop-maturity-audit' '$ROOT/skills/codegen-context/SKILL.md'"
assert "codegen context inlines slop quality gates" "rg -q 'missing_slop_quality_gate|Slop Quality Gate|slop_quality_gate|case-promotion sources' '$ROOT/skills/codegen-context/SKILL.md'"
assert "codegen context inlines module plans and architecture-test-first instructions" "rg -q 'missing_module_plan|module_plan|architecture_test.write_first|architecture_test.test_path|Do not create support/helpers/util/common' '$ROOT/skills/codegen-context/SKILL.md'"
assert "codegen context inlines pattern-generated module plans and exemplars" "rg -q 'module_plan_source=pattern|pattern_deviation_reason|exemplar structure|skills/paved-road-registry/patterns.json' '$ROOT/skills/codegen-context/SKILL.md'"
assert "codegen context enforces product vocabulary" "rg -q 'product_vocabulary' '$ROOT/skills/codegen-context/SKILL.md' && rg -q 'banned_tokens' '$ROOT/skills/codegen-context/SKILL.md' && rg -q 'missing_product_vocabulary' '$ROOT/skills/codegen-context/SKILL.md' && rg -q 'schema/version strings' '$ROOT/skills/codegen-context/SKILL.md' && rg -q 'pr-hygiene-scan' '$ROOT/skills/codegen-context/SKILL.md'"
assert "build and fix loops require PR hygiene" "rg -q 'pr-hygiene-scan' '$ROOT/skills/build-feature/SKILL.md' && rg -q 'Diff contract' '$ROOT/skills/build-feature/SKILL.md' && rg -q 'Base policy' '$ROOT/skills/build-feature/SKILL.md' && rg -q 'Language contract' '$ROOT/skills/build-feature/SKILL.md' && rg -q 'pr-hygiene-scan' '$ROOT/skills/fix-bug/SKILL.md' && rg -q 'product_vocabulary' '$ROOT/skills/fix-bug/SKILL.md' && rg -q 'base branch' '$ROOT/skills/fix-bug/SKILL.md'"
assert "process artifact storage contract is documented and discoverable" "[ -f '$ROOT/docs/specs/process-artifact-storage.md' ] && rg -q 'ADLC Process Artifact Storage|target_repo_key|task_key|process-artifact-path' '$ROOT/docs/specs/process-artifact-storage.md' && '$ROOT/bin/adlc' process-artifact-path --target-repo owner/repo --task TASK-1 --artifact-type build-brief --json | jq -e '.target_repo_key == \"owner--repo\" and .task_key == \"task-1\" and .artifact_type == \"build-brief\"' >/dev/null"
assert "process artifact storage is wired into process-writing skills" "rg -q 'process-artifact-path|process artifact storage' '$ROOT/skills/build-feature/SKILL.md' && rg -q 'process-artifact-path|process artifact storage' '$ROOT/skills/fix-bug/SKILL.md' && rg -q 'process-artifact-path' '$ROOT/skills/eval-council/SKILL.md' && rg -q 'process-artifact-path' '$ROOT/skills/test-strength/SKILL.md' && rg -q 'process-artifact-path' '$ROOT/skills/dark-code-audit/SKILL.md' && rg -q 'process-artifact-path' '$ROOT/skills/learning-capture/SKILL.md' && rg -q 'process-artifact-path' '$ROOT/agents/pr-preparer.md' && rg -q 'process-artifact-path' '$ROOT/agents/ADLC-BUILD-BRIEF-AGENT.md'"
assert "codegen context consumes compact learning refs" "rg -q 'compound_context|learning_refs|Full solution-note bodies|Prior Learnings' '$ROOT/skills/codegen-context/SKILL.md'"
assert "codegen context carries repo conventions" "rg -q 'missing_repo_conventions|repo_conventions|no_conventions_found|Repo Conventions' '$ROOT/skills/codegen-context/SKILL.md'"
assert "codegen context carries honesty contracts" "rg -q 'missing_honesty_contract|Honesty Contract|doc_honesty_section|no_overclaim.*limitations' '$ROOT/skills/codegen-context/SKILL.md'"
assert "codegen context carries performance envelopes" "rg -q 'missing_performance_envelope|Performance Envelope|queue-complete --benchmark' '$ROOT/skills/codegen-context/SKILL.md'"
assert "codegen context carries task sizing" "rg -q 'missing_task_sizing|Task Sizing|split_decision.required|atomic_cross_module' '$ROOT/skills/codegen-context/SKILL.md'"
assert "spec-to-tests enforces module plan architecture tests first" "rg -q 'module_plan.architecture_test|before production code|forbidden catch-all names|pure/impure markings' '$ROOT/skills/spec-to-tests/SKILL.md'"
assert "spec-to-tests covers pattern-generated architecture tests" "rg -q 'module_plan_source=pattern|registered paved-road pattern|pattern_deviation_reason' '$ROOT/skills/spec-to-tests/SKILL.md'"
assert "docs document module plan closeout" "rg -q 'module_plan|module-plan-check' '$ROOT/README.md' && rg -q 'module_plan|module-plan-check' '$ROOT/WORKFLOW.md'"
assert "docs document honesty contract closeout" "rg -q 'Honesty Contract|honesty_contract|doc_honesty_section|no_overclaim.*limitations' '$ROOT/README.md' && rg -q 'honesty_contract' '$ROOT/WORKFLOW.md'"
assert "docs document performance envelope closeout" "rg -q 'Performance Envelope|performance_envelope|benchmark_required' '$ROOT/README.md' && rg -q 'performance_envelope' '$ROOT/WORKFLOW.md'"
assert "docs document task sizing closeout" "rg -q 'Task Sizing|task_sizing|split decision' '$ROOT/README.md' && rg -q 'task_sizing' '$ROOT/WORKFLOW.md'"
assert "docs document paved-road pattern preflight" "rg -q 'paved-road-patterns|pattern:interralis:evidence-module|pattern_deviation_reason' '$ROOT/README.md' && rg -q 'paved-road-patterns|registered pattern exemplars' '$ROOT/WORKFLOW.md'"
assert "docs document target repo convention closeout" "rg -Fq 'Target Repo Conventions' '$ROOT/CONTRIBUTING.md' && rg -Fq 'repo_conventions' '$ROOT/CONTRIBUTING.md' && rg -Fq 'pr-hygiene-scan' '$ROOT/CONTRIBUTING.md' && rg -Fq 'repo_conventions' '$ROOT/WORKFLOW.md' && rg -Fq 'convention-scan' '$ROOT/WORKFLOW.md' && rg -Fq 'pr-hygiene-scan' '$ROOT/WORKFLOW.md' && rg -Fq 'Target Repo Conventions' '$ROOT/README.md' && rg -Fq 'convention-scan' '$ROOT/README.md' && rg -Fq 'pr-hygiene-scan' '$ROOT/README.md' && rg -Fq 'Step 2: Build Brief + repo conventions' '$ROOT/skills/build-feature/SKILL.md' && rg -Fq '6a: LDD gate + structural convention scan' '$ROOT/skills/build-feature/SKILL.md' && rg -Fq 'Step 9: Stop Slop + PR hygiene scan' '$ROOT/skills/build-feature/SKILL.md'"
assert "README documents install wrapper and harness prompt" "rg -Fq './setup.sh claude <target>' '$ROOT/README.md' && rg -Fq './setup.sh verify-claude' '$ROOT/README.md' && rg -Fq '<target>/.adlc/bin/adlc' '$ROOT/README.md' && rg -Fq 'ADLC_ROOT' '$ROOT/README.md' && rg -Fq 'Prompt Your Harness To Do The Following' '$ROOT/README.md' && rg -Fq 'repo_conventions.status=none_found only when' '$ROOT/README.md' && rg -Fq 'Waivers are recorded, not skipped' '$ROOT/README.md' && rg -Fq 'process-artifact-storage.md' '$ROOT/README.md' && rg -Fq 'feedback-conventions' '$ROOT/README.md'"
assert "reuse analysis checks docs solutions learning refs" "rg -q 'docs/solutions|compound_context.learning_refs|Learning Store Prior Art|no_op_reasons' '$ROOT/skills/reuse-analysis/SKILL.md'"
assert "DoD uses core baseline and overlays" "rg -q 'core baseline|overlay' '$ROOT/skills/definition-of-done/SKILL.md'"
assert "DoD checks honesty contract" "rg -q 'Honesty contract satisfied|honesty_contract_satisfied|no external claims' '$ROOT/skills/definition-of-done/SKILL.md'"
assert "DoD checks performance envelope" "rg -q 'Performance envelope satisfied|performance_envelope_satisfied|benchmark_required' '$ROOT/skills/definition-of-done/SKILL.md'"
assert "DoD checks task sizing" "rg -q 'Task sizing satisfied|task_sizing_satisfied|split-required tasks' '$ROOT/skills/definition-of-done/SKILL.md'"
assert "DoD checks compatibility evidence predicates" "rg -q 'Compatibility evidence satisfied|compatibility_evidence_satisfied|verification predicate|contract-surface-inventory' '$ROOT/skills/definition-of-done/SKILL.md'"
assert "DoD requires convention scan without size gates" "rg -q 'convention-scan' '$ROOT/skills/definition-of-done/SKILL.md' && rg -q 'Repo convention waivers explicit' '$ROOT/skills/definition-of-done/SKILL.md' && rg -q 'File size, line count, and SLOC are not valid DoD criteria' '$ROOT/skills/definition-of-done/SKILL.md'"
assert "LDD runs convention scan without size gates" "rg -q 'Repo Convention Structural Scan' '$ROOT/skills/ldd-enforcement/SKILL.md' && rg -q 'convention-scan' '$ROOT/skills/ldd-enforcement/SKILL.md' && rg -q 'file size.*line count' '$ROOT/skills/ldd-enforcement/SKILL.md'"
assert "architecture pattern enforces recursive convention decomposition" "rg -q 'Apply Target Repo Conventions First' '$ROOT/skills/architecture-pattern/SKILL.md' && rg -q 'Recursive rule' '$ROOT/skills/architecture-pattern/SKILL.md' && rg -q 'responsibility' '$ROOT/skills/architecture-pattern/SKILL.md' && rg -q 'architecture tests' '$ROOT/skills/architecture-pattern/SKILL.md' && rg -q 'Catch-all' '$ROOT/skills/architecture-pattern/SKILL.md' && rg -q 'file size or line count' '$ROOT/skills/architecture-pattern/SKILL.md'"
assert "eval council checks applicability manifest" "rg -q 'applicability_manifest' '$ROOT/skills/eval-council/SKILL.md'"
assert "eval council gates scalable AI code primitives" "rg -q 'Scalable AI Code Primitive Checks|unverifiable_delegation|paved_road_refs|production_invariant_coverage' '$ROOT/skills/eval-council/SKILL.md'"
assert "eval council gates implementation interface and productionization claims" "rg -q 'Implementation Interface And Productionization Gate Checks|missing_implementation_interface_contract|missing_productionization_gate|overclaimed_production_ready' '$ROOT/skills/eval-council/SKILL.md'"
assert "eval council gates loop maturity claims" "rg -q 'Loop System Maturity Checks|missing_loop_contract|missing_required_loop_tests|loop_action_not_admitted|self_autonomy_overclaim' '$ROOT/skills/eval-council/SKILL.md'"
assert "eval council gates slop quality benchmarks" "rg -q 'Slop Quality Gate Checks|missing_slop_quality_gate|missing_slop_eval_cases|slop_regression|slop_score_below_threshold' '$ROOT/skills/eval-council/SKILL.md'"
assert "eval council includes clarity auditor" "rg -q 'Clarity Auditor|epistemic_ledger|blindspot report|ask-user unknown|fabricated certainty' '$ROOT/skills/eval-council/SKILL.md'"
assert "build-feature ingests repo conventions" "rg -q 'repo-conventions|repo_conventions|no_conventions_found' '$ROOT/skills/build-feature/SKILL.md'"
assert "build-feature runs clarity gate and interview loop" "rg -q 'epistemic ledger|blindspot pass|clarity-gate|pending questions|ask-user' '$ROOT/skills/build-feature/SKILL.md'"
assert "codebase and graph research require blindspot contract inventory" "rg -q 'blindspot|contract-surface inventory|adjacent systems|domain vocabulary' '$ROOT/skills/codebase-research/SKILL.md' && rg -q 'contract-surface inventory|compatibility_evidence_refs|published surface' '$ROOT/skills/graph-research/SKILL.md'"
assert "clarity and specificity judges enforce ledger and compatibility evidence" "rg -q 'epistemic_ledger|pending questions|ask-user' '$ROOT/skills/brief-clarity-judge/SKILL.md' && rg -q 'verification_predicates|compatibility_evidence_refs|generic compatibility' '$ROOT/skills/specificity-judge/SKILL.md'"
assert "feedback and learning capture consume deviation defects" "rg -q 'brief-generator defect|deviation log|ledger-absent' '$ROOT/skills/feedback-loop/SKILL.md' && rg -q 'brief-generator defect|epistemic ledger|ledger-absent' '$ROOT/skills/learning-capture/SKILL.md'"
assert "PR preparer surfaces epistemic honesty outside target diff" "rg -q 'Knowns|Ratified Assumptions|Remaining Unknowns|accepted-risk|target repo diff' '$ROOT/agents/pr-preparer.md'"
assert "Build Brief Agent extracts repo conventions" "rg -q 'repo-conventions|repo_conventions|no_conventions_found' '$ROOT/agents/ADLC-BUILD-BRIEF-AGENT.md'"
assert "Build Brief Agent emits honesty contracts" "rg -q 'honesty_contract|does_not_do|unsafe claims|no external claims' '$ROOT/agents/ADLC-BUILD-BRIEF-AGENT.md'"
assert "planner emits honesty contracts" "rg -q 'Honesty contract|honesty_contract|no external claims|doc_honesty_section|no_overclaim.*limitations' '$ROOT/agents/planner.md'"
assert "Build Brief Agent emits performance envelopes" "rg -q 'Performance Envelope|performance_envelope|benchmark_required' '$ROOT/agents/ADLC-BUILD-BRIEF-AGENT.md'"
assert "planner emits performance envelopes" "rg -q 'Performance envelope|performance_envelope|benchmark_required' '$ROOT/agents/planner.md'"
assert "Build Brief Agent emits task sizing" "rg -q 'Task Sizing|task_sizing|atomic_cross_module|split_decision' '$ROOT/agents/ADLC-BUILD-BRIEF-AGENT.md'"
assert "planner emits task sizing" "rg -q 'Task sizing|task_sizing|atomic_cross_module|split_decision' '$ROOT/agents/planner.md'"
assert "eval council includes convention auditor" "rg -q 'Convention Auditor' '$ROOT/skills/eval-council/SKILL.md' && rg -q 'repo_conventions.status == extracted' '$ROOT/skills/eval-council/SKILL.md' && rg -q 'file and line ranges' '$ROOT/skills/eval-council/SKILL.md'"
assert "fix loop uses primary verifier wording" "rg -q 'primary verifier' '$ROOT/skills/fix-loop/SKILL.md'"
assert "shared emitter contract covers supported targets and local MCP providers" "rg -q 'GitHub|Linear|Notion|Work-item emitter|Document emitter|locally installed MCP provider|capability_bindings' '$ROOT/docs/specs/emitter-contract.md'"
assert "shared emitter contract preserves reuse and tech debt context" "rg -q 'reference_impl|reuse|tech-debt|deferred-cleanup|do not reimplement' '$ROOT/docs/specs/emitter-contract.md'"
assert "shared emitter contract preserves artifact taxonomy and enterprise readiness" "rg -q 'artifact_type|decision_contract|enterprise_readiness_contract|validation_task|unresolved_dependency_alias' '$ROOT/docs/specs/emitter-contract.md'"
assert "shared emitter contract preserves scalable AI code primitives" "rg -q 'construct_map_refs|paved_road_refs|intent_contract_refs|production_invariant_coverage' '$ROOT/docs/specs/emitter-contract.md'"
assert "shared emitter contract preserves implementation interface and productionization gates" "rg -q 'implementation_interface_contract|productionization_gate|Coverage State|No-Overclaim|overclaimed_production_ready' '$ROOT/docs/specs/emitter-contract.md'"
assert "shared emitter contract preserves loop contract refs" "rg -q 'loop_contract_path|loop_action_path|loop_maturity_report_path|Loop action checks' '$ROOT/docs/specs/emitter-contract.md'"
assert "shared emitter contract preserves slop quality gates" "rg -q 'slop_quality_gate|case-promotion sources|generated-output behavior' '$ROOT/docs/specs/emitter-contract.md'"
assert "shared emitter contract preserves honesty contracts" "rg -q 'honesty_contract|no_overclaim|limitations|doc_honesty_section|missing_honesty_contract' '$ROOT/docs/specs/emitter-contract.md'"
assert "shared emitter contract preserves performance envelopes" "rg -q 'performance_envelope|benchmark_results|missing_performance_envelope|missing_benchmark_evidence' '$ROOT/docs/specs/emitter-contract.md'"
assert "shared emitter contract preserves task sizing" "rg -q 'task_sizing|missing_task_sizing|task_sizing_split_required|Task sizing checks' '$ROOT/docs/specs/emitter-contract.md'"
assert "JIRA ticket creation preserves verification contract" "rg -q 'contract_version|Verification Contract|task_classification|verification_spec' '$ROOT/skills/jira-ticket-creation/SKILL.md'"
assert "Confluence decomposition respects applicability manifest" "rg -q 'contract_version|applicability_manifest|active Build Brief sections' '$ROOT/skills/confluence-decomposition/SKILL.md'"
assert "GitHub issue creation preserves verification contract" "rg -q 'contract_version|Verification Contract|task_classification|verification_spec' '$ROOT/skills/github-issue-creation/SKILL.md'"
assert "Linear ticket creation preserves verification contract" "rg -q 'contract_version|Verification Contract|task_classification|verification_spec' '$ROOT/skills/linear-ticket-creation/SKILL.md'"
assert "Linear ticket creation preserves artifact taxonomy and enterprise readiness" "rg -q 'artifact_type|Decision Contract|Compatibility Contract|Evidence Responsibilities|Definition of Done|enterprise readiness contract' '$ROOT/skills/linear-ticket-creation/SKILL.md'"
assert "work item emitters preserve scalable AI code primitives" "rg -q 'Scalable AI Code Primitives|Construct map refs|Paved-road refs|Production invariant coverage' '$ROOT/skills/jira-ticket-creation/SKILL.md' && rg -q 'Scalable AI Code Primitives|Construct map refs|Paved-road refs|Production invariant coverage' '$ROOT/skills/github-issue-creation/SKILL.md' && rg -q 'Scalable AI Code Primitives|Construct map refs|Paved-road refs|Production invariant coverage' '$ROOT/skills/linear-ticket-creation/SKILL.md'"
assert "work item emitters preserve implementation interface and productionization gates" "rg -q 'Implementation Interface Contract|Productionization Gate|Coverage State|No-Overclaim' '$ROOT/skills/jira-ticket-creation/SKILL.md' && rg -q 'Implementation Interface Contract|Productionization Gate|Coverage State|No-Overclaim' '$ROOT/skills/github-issue-creation/SKILL.md' && rg -q 'Implementation Interface Contract|Productionization Gate|Coverage State|No-Overclaim' '$ROOT/skills/linear-ticket-creation/SKILL.md'"
assert "work item emitters preserve loop contract refs" "rg -q 'Loop Contract refs|loop_contract_path|loop_action_path|loop_maturity_report_path' '$ROOT/skills/jira-ticket-creation/SKILL.md' && rg -q 'Loop Contract refs|loop_contract_path|loop_action_path|loop_maturity_report_path' '$ROOT/skills/github-issue-creation/SKILL.md' && rg -q 'Loop Contract refs|loop_contract_path|loop_action_path|loop_maturity_report_path' '$ROOT/skills/linear-ticket-creation/SKILL.md'"
assert "work item emitters preserve slop quality gates" "rg -q 'Slop Quality Gate|slop_quality_gate|Case promotion sources' '$ROOT/skills/jira-ticket-creation/SKILL.md' && rg -q 'Slop Quality Gate|slop_quality_gate|Case promotion sources' '$ROOT/skills/github-issue-creation/SKILL.md' && rg -q 'Slop Quality Gate|slop_quality_gate|Case promotion sources' '$ROOT/skills/linear-ticket-creation/SKILL.md'"
assert "work item emitters preserve honesty contracts" "rg -q 'Honesty Contract|honesty_contract|No-Overclaim' '$ROOT/skills/jira-ticket-creation/SKILL.md' && rg -q 'Honesty Contract|honesty_contract|No-Overclaim' '$ROOT/skills/github-issue-creation/SKILL.md' && rg -q 'Honesty Contract|honesty_contract|No-Overclaim' '$ROOT/skills/linear-ticket-creation/SKILL.md'"
assert "work item emitters preserve performance envelopes" "rg -q 'Performance Envelope|performance_envelope|Benchmark results' '$ROOT/skills/jira-ticket-creation/SKILL.md' && rg -q 'Performance Envelope|performance_envelope|Benchmark results' '$ROOT/skills/github-issue-creation/SKILL.md' && rg -q 'Performance Envelope|performance_envelope|Benchmark results' '$ROOT/skills/linear-ticket-creation/SKILL.md'"
assert "work item emitters preserve task sizing" "rg -q 'task_sizing' '$ROOT/skills/jira-ticket-creation/SKILL.md' && rg -q 'task_sizing' '$ROOT/skills/github-issue-creation/SKILL.md' && rg -q 'task_sizing' '$ROOT/skills/linear-ticket-creation/SKILL.md'"
assert "emit-work-items preserves scalable AI code primitive refs" "assert_emit_preserves_scalable_primitives"
assert "emit-work-items preserves task fingerprints" "assert_emit_preserves_task_fingerprints"
assert "emit-work-items preserves implementation interface and productionization contracts" "assert_emit_preserves_implementation_and_productionization_contracts"
assert "emit-work-items preserves honesty contracts" "assert_emit_preserves_honesty_contracts"
assert "emit-work-items preserves performance envelopes" "assert_emit_preserves_performance_envelopes"
assert "emit-work-items preserves task sizing" "assert_emit_preserves_task_sizing"
assert "emit-work-items preserves loop contract refs" "assert_emit_preserves_loop_contract_refs"
assert "emit-work-items preserves slop quality gates" "assert_emit_preserves_slop_quality_gate"
assert "implementation interface productionization example is ready" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/docs/build-briefs/implementation-interfaces-productionization-example.json' --dry-run --require-ready --json | jq -e '.readiness_report.status == \"ready\" and .artifacts[0].implementation_interface_contract.id == \"iface:adlc-iip-example\" and .artifacts[0].productionization_gate.coverage_state == \"production_ready\"' >/dev/null"
assert "emit-work-items omits absent slop quality gates" "assert_emit_omits_absent_slop_quality_gate"
assert "generated-output work without slop gate blocks readiness" "assert_generated_output_missing_slop_gate_blocks_readiness"
assert "generated-output work with valid slop gate passes readiness" "assert_generated_output_valid_slop_gate_passes_readiness"
assert "generated-output string metric without validator blocks readiness" "assert_generated_output_string_metric_blocks_readiness"
assert "code-only work without slop gate passes readiness" "assert_code_only_without_slop_gate_passes_readiness"
assert "overclaimed production_ready blocks readiness" "assert_overclaimed_production_ready_blocks_readiness"
assert "compact not-applicable safety contracts pass readiness" "assert_compact_not_applicable_contracts_pass_readiness"
assert "slop-gate CLI blocks missing generated-output gate" "assert_slop_gate_cli_blocks_missing_generated_gate"
assert "Notion decomposition respects applicability manifest" "rg -q 'contract_version|applicability_manifest|active Build Brief sections' '$ROOT/skills/notion-decomposition/SKILL.md'"
assert "JIRA ticket creation preserves reuse and tech debt context" "rg -q 'Reference implementation|Reuse / Existing Patterns|Tech Debt / Cleanup Boundaries' '$ROOT/skills/jira-ticket-creation/SKILL.md'"
assert "GitHub issue creation preserves reuse and tech debt context" "rg -q 'Reference implementation|Reuse / Existing Patterns|Tech Debt / Cleanup Boundaries' '$ROOT/skills/github-issue-creation/SKILL.md'"
assert "Linear ticket creation preserves reuse and tech debt context" "rg -q 'Reference implementation|Reuse / Existing Patterns|Tech Debt / Cleanup Boundaries' '$ROOT/skills/linear-ticket-creation/SKILL.md'"
assert "specificity judge checks one-shot production readiness" "rg -q 'one-shot.*production-ready|unresolved_type1_in_implementation|missing_compatibility_contract|missing_validation_task|missing_task_sizing|broad_change_surface|size_only_split_or_pass' '$ROOT/skills/specificity-judge/SKILL.md'"
assert "Confluence decomposition preserves reuse and tech debt context" "rg -q 'reference implementations|tech-debt|reuse/reference-implementation guidance|debt-prerequisite sequencing' '$ROOT/skills/confluence-decomposition/SKILL.md'"
assert "Notion decomposition preserves reuse and tech debt context" "rg -q 'reference implementations|tech-debt|reuse guidance|debt-prerequisite sequencing' '$ROOT/skills/notion-decomposition/SKILL.md'"
assert "GitHub issue creation requires local MCP provider bindings" "rg -q 'locally installed MCP provider|capability_bindings' '$ROOT/skills/github-issue-creation/SKILL.md'"
assert "Linear ticket creation requires local MCP provider bindings" "rg -q 'locally installed MCP provider|capability_bindings' '$ROOT/skills/linear-ticket-creation/SKILL.md'"
assert "Notion decomposition requires local MCP provider bindings" "rg -q 'locally installed MCP provider|capability_bindings' '$ROOT/skills/notion-decomposition/SKILL.md'"

echo ""
echo "--- Activation Metadata ---"
assert "paved-road registry has activation metadata" "jq -e '.skills[] | select(.name==\"paved-road-registry\") | .activation.consumes_manifest == true and (.dag_nodes | index(\"research\")) != null and (.dag_nodes | index(\"plan\")) != null and (.dag_nodes | index(\"context_assembly\")) != null and (.dag_nodes | index(\"code_review\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "security-review has activation metadata" "jq -e '.skills[] | select(.name==\"security-review\") | .activation.consumes_manifest == true' '$ROOT/skills/manifest.json' >/dev/null"
assert "observability-contract has activation metadata" "jq -e '.skills[] | select(.name==\"observability-contract\") | .activation.mode == \"overlay\"' '$ROOT/skills/manifest.json' >/dev/null"
assert "definition-of-done declares core checks" "jq -e '.skills[] | select(.name==\"definition-of-done\") | (.activation.core_checks | length) > 0' '$ROOT/skills/manifest.json' >/dev/null"
assert "definition-of-done manifest includes honesty core check" "jq -e '.skills[] | select(.name==\"definition-of-done\") | (.activation.core_checks | index(\"29\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "definition-of-done manifest includes performance core check" "jq -e '.skills[] | select(.name==\"definition-of-done\") | (.activation.core_checks | index(\"30\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "definition-of-done manifest includes task sizing core check" "jq -e '.skills[] | select(.name==\"definition-of-done\") | (.activation.core_checks | index(\"31\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "build-feature consumes manifest" "jq -e '.skills[] | select(.name==\"build-feature\") | .activation.consumes_manifest == true' '$ROOT/skills/manifest.json' >/dev/null"
assert "build-feature activates paved-road registry" "jq -e '.skills[] | select(.name==\"build-feature\") | (.activation.activates | index(\"paved-road-registry\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "eval-council manifest registers convention auditor" "jq -e '.skills[] | select(.name==\"eval-council\") | (.activation.overlay_personas | index(\"convention_auditor\")) != null and (.activation.overlay_triggers.convention_auditor | index(\"repo_conventions.status=extracted\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "github issue creation is registered for pr_prep" "jq -e '.skills[] | select(.name==\"github-issue-creation\") | .side_effect_profile == \"mutating\" and (.dag_nodes | index(\"pr_prep\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "linear ticket creation is registered for pr_prep" "jq -e '.skills[] | select(.name==\"linear-ticket-creation\") | .side_effect_profile == \"mutating\" and (.dag_nodes | index(\"pr_prep\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "notion decomposition is registered for pr_prep" "jq -e '.skills[] | select(.name==\"notion-decomposition\") | .side_effect_profile == \"mutating\" and (.dag_nodes | index(\"pr_prep\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "learning capture is registered for closeout" "jq -e '.skills[] | select(.name==\"learning-capture\") | .side_effect_profile == \"mutating\" and .activation.mode == \"conditional_closeout\" and (.dag_nodes | index(\"learning_capture\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "learning refresh is scoped maintenance only" "jq -e '.skills[] | select(.name==\"learning-refresh\") | .side_effect_profile == \"mutating\" and .activation.mode == \"scoped_maintenance\" and (.dag_nodes | length) == 0' '$ROOT/skills/manifest.json' >/dev/null"
assert "pr-preparer is wired to learning capture and non-skippable PR gates" "jq -e '.agents[] | select(.name==\"pr-preparer\") | (.skills | index(\"learning-capture\")) != null' '$ROOT/skills/manifest.json' >/dev/null && rg -q 'learning_candidates|redaction_status|stale_conditions' '$ROOT/agents/pr-preparer.md' && rg -q 'pr-hygiene-scan|base/default|PR-123' '$ROOT/agents/pr-preparer.md' && rg -q 'non-skippable|banned-token input|--waiver rule:who:why|stacked_base_check' '$ROOT/agents/pr-preparer.md'"

echo ""
echo "--- gen_tests Authoring ---"
assert "spec-to-tests skill file exists" "[ -f '$ROOT/skills/spec-to-tests/SKILL.md' ]"
assert "test-author agent file exists" "[ -f '$ROOT/agents/test-author.md' ]"
assert "spec-to-tests consumes manifest" "jq -e '.skills[] | select(.name==\"spec-to-tests\") | .activation.consumes_manifest == true' '$ROOT/skills/manifest.json' >/dev/null"
assert "test-author agent maps to gen_tests" "jq -e '.agents[] | select(.name==\"test-author\") | .dag_node == \"gen_tests\"' '$ROOT/skills/manifest.json' >/dev/null"
assert "test-author agent declares done stuck revise labels" "jq -e '.agents[] | select(.name==\"test-author\") | (.labels | index(\"done\")) != null and (.labels | index(\"stuck\")) != null and (.labels | index(\"revise\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "WORKFLOW.dot promotes gen_tests to agent styling" "rg -q 'gen_tests \\[shape=box, label=\"Generate Verifiers\\\\nAuthor Failing Tests / Reproducers\", style=filled, fillcolor=\"#e6f3ff\"\\]' '$ROOT/WORKFLOW.dot'"
assert "WORKFLOW.dot no longer marks gen_tests as dashed" "! rg -q 'gen_tests .*dashed' '$ROOT/WORKFLOW.dot'"
assert "WORKFLOW.md table includes test-author row" "rg -q 'agents/test-author\\.md.*spec-to-tests, tdd-enforcement, qa-test-data' '$ROOT/WORKFLOW.md'"
assert "WORKFLOW.md removes gen_tests tool block" "! rg -q '^gen_tests:' '$ROOT/WORKFLOW.md'"
assert "coder consumes test_plan.json" "rg -q 'test_plan\\.json|test_plan_missing|generated_tests' '$ROOT/agents/coder.md'"
assert "test author emits loop coverage tags" "rg -q 'loop_contract_path|coverage_tags|covers_required_tests|loop-test-selection' '$ROOT/agents/test-author.md'"
assert "README lists spec-to-tests in core engineering" "rg -q 'spec-to-tests.*failing-test authoring from Brief' '$ROOT/README.md'"
assert "README lists test-author agent" "rg -q '\\| \\*\\*test-author\\*\\* \\| Authors failing verifier tests from Brief \\| Sonnet \\| spec-to-tests, tdd-enforcement, qa-test-data \\|' '$ROOT/README.md'"
assert "applicability-manifest verifier includes target_files and expected_failure_mode" "jq -e '.definitions.verifier.properties.target_files.type == \"array\" and .definitions.verifier.properties.expected_failure_mode.type == \"string\"' '$ROOT/docs/schemas/applicability-manifest.schema.json' >/dev/null"
assert "build-brief verifier mirrors target_files and expected_failure_mode" "jq -e '.definitions.verifier.properties.target_files.type == \"array\" and .definitions.verifier.properties.expected_failure_mode.type == \"string\"' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "build-brief keeps string acceptance criteria for backward compatibility" "jq -e '.definitions.task.properties.acceptance_criteria.items.oneOf[] | select(.type==\"string\") | .minLength == 1' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "build-brief accepts structured acceptance criteria objects" "jq -e '.definitions.task.properties.acceptance_criteria.items.oneOf[] | select(.type==\"object\") | .properties.id.pattern == \"^AC-[A-Z0-9_-]+$\"' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "applicability manifest spec documents optional verifier fields" "rg -q 'Optional Fields|target_files|expected_failure_mode' '$ROOT/docs/specs/applicability-manifest.md'"
assert "spec-to-tests skill declares all six quality gates" "rg -q 'acceptance_criteria.*>=1 generated test' '$ROOT/skills/spec-to-tests/SKILL.md' && rg -q 'Every test has at least one concrete assertion' '$ROOT/skills/spec-to-tests/SKILL.md' && rg -q 'Pre-change run captured; failure reason matches .*expected_failure_mode' '$ROOT/skills/spec-to-tests/SKILL.md' && rg -q 'Test file paths intersect .*verification_spec\\.target_files' '$ROOT/skills/spec-to-tests/SKILL.md' && rg -q 'Generated tests pass stop-slop anti-stub patterns' '$ROOT/skills/spec-to-tests/SKILL.md' && rg -q 'test_plan\\.json.*validates against the schema in this skill' '$ROOT/skills/spec-to-tests/SKILL.md'"
assert "spec-to-tests enforces additive loop test selection" "rg -q 'mandatory_floor|required_from_task_signals|additive only|coverage_tags|covers_required_tests|loop-test-selection' '$ROOT/skills/spec-to-tests/SKILL.md'"

echo ""
echo "--- Post-Fix-0 Hardening ---"
assert "codegen-context declares AC normalization" "rg -q 'Normalize Acceptance Criteria|objective-derived|AC-\\{task_id\\}-\\{n\\}' '$ROOT/skills/codegen-context/SKILL.md'"
assert "planner defaults to structured acceptance criteria" "rg -q 'structured acceptance criteria by default|measurable_post_condition' '$ROOT/agents/planner.md'"
assert "planner records legacy_ac and low-confidence escalate policy" "rg -q 'legacy_ac|task_classification_confidence < 0.6|human override' '$ROOT/agents/planner.md'"
assert "JIRA skill handles mixed acceptance criteria shapes" "rg -q 'Mixed Acceptance Criteria Shapes|\\.then|measurable_post_condition' '$ROOT/skills/jira-ticket-creation/SKILL.md'"
assert "Confluence skill handles mixed acceptance criteria shapes" "rg -q 'Mixed Acceptance Criteria Shapes|\\.then|measurable_post_condition' '$ROOT/skills/confluence-decomposition/SKILL.md'"
assert "DoD skill handles mixed acceptance criteria shapes" "rg -q 'Mixed Acceptance Criteria Shapes|\\.then|measurable_post_condition' '$ROOT/skills/definition-of-done/SKILL.md'"
assert "workflow binding contract exists and marks gen_tests as an agent node" "rg -q 'Bounded Directed Workflow Binding Contract|WORKFLOW\\.md|gen_tests is an agent node' '$ROOT/docs/specs/dag-binding.md'"
assert "triage implements confidence bands" "rg -q 'Confidence Bands|low_confidence|confidence_band|0.6 <= confidence < 0.8|< 0.6' '$ROOT/agents/triage.md'"
assert "applicability manifest spec documents confidence policy" "rg -q 'Confidence Policy|low_confidence|task_classification_confidence < 0.6' '$ROOT/docs/specs/applicability-manifest.md'"
assert "CASE-006 exists with escalate label and 0.55 confidence" "jq -e '.cases[] | select(.id==\"CASE-006\" and .expected_label==\"escalate\" and .expected_manifest.task_classification_confidence == 0.55)' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "CASE-007 exists with low_confidence label and 0.72 confidence" "jq -e '.cases[] | select(.id==\"CASE-007\" and .expected_label==\"low_confidence\" and .expected_manifest.task_classification_confidence == 0.72)' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "eval-council declares verifier scope intersection check" "rg -q 'Verifier Scope Intersection|verifier_no_coverage|target_files' '$ROOT/skills/eval-council/SKILL.md'"
assert "plan-reviewer output references verifier scope intersection" "rg -q 'verifier_scope_intersection|verifier_no_coverage' '$ROOT/agents/plan-reviewer.md'"
assert "test-strength skill exists with coverage and mutation thresholds" "[ -f '$ROOT/skills/test-strength/SKILL.md' ] && rg -q '0.8|0.6|mutmut|stryker|cargo-mutants|test_strength_report' '$ROOT/skills/test-strength/SKILL.md'"
assert "test-strength agent exists and maps to test_strength" "[ -f '$ROOT/agents/test-strength-auditor.md' ] && jq -e '.agents[] | select(.name==\"test-strength-auditor\") | .dag_node == \"test_strength\"' '$ROOT/skills/manifest.json' >/dev/null"
assert "WORKFLOW.dot includes conditional test_strength node and weak edge" "rg -q 'test_strength \\[shape=box, label=\"Test Strength\\\\nConditional Audit\", style=filled, fillcolor=\"#e6f3ff\"\\]' '$ROOT/WORKFLOW.dot' && rg -q 'qa -> test_strength.*test-strength active' '$ROOT/WORKFLOW.dot' && rg -q 'test_strength -> fixer.*label=\"weak\"' '$ROOT/WORKFLOW.dot'"
assert "WORKFLOW.dot routes test_strength pass to slop_gate conditionally" "rg -q 'test_strength -> slop_gate.*slop active' '$ROOT/WORKFLOW.dot' && rg -q 'test_strength -> pr_prep.*slop inactive' '$ROOT/WORKFLOW.dot'"
assert "workflow registers test_strength and caps weak retries" "rg -q 'agents/test-strength-auditor\\.md.*test-strength' '$ROOT/WORKFLOW.md' && rg -q 'test_strength -> fixer.*label=\"weak\".*max_retries=2' '$ROOT/WORKFLOW.dot'"
assert "WORKFLOW.md binds executable slop_gate command" "rg -q '^slop_gate:' '$ROOT/WORKFLOW.md' && rg -q 'run-phase slop_gate' '$ROOT/WORKFLOW.md' && '$ROOT/bin/adlc' run-phase slop_gate --brief-id CONTRACT-SLOP --workspace \"\$(mktemp -d)\" --build-brief '$ROOT/docs/build-briefs/xia-adlc-remediation.json' --json >/dev/null"
assert "manifest registers test-strength skill with consumes_manifest" "jq -e '.skills[] | select(.name==\"test-strength\") | .activation.consumes_manifest == true and (.activation.produces | index(\"test_strength_report\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "manifest registers triage low_confidence and planner escalate labels" "jq -e '.agents[] | select(.name==\"triage\") | (.labels | index(\"low_confidence\")) != null' '$ROOT/skills/manifest.json' >/dev/null && jq -e '.agents[] | select(.name==\"planner\") | (.labels | index(\"escalate\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "manifest registers graph research and comprehension skills" "jq -e '.skills[] | select(.name==\"graph-research\") | (.dag_nodes | index(\"research\")) != null and (.dag_nodes | index(\"code_review\")) != null' '$ROOT/skills/manifest.json' >/dev/null && jq -e '.skills[] | select(.name==\"comprehension-gate\") | (.dag_nodes | index(\"code_review\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "manifest wires researcher planner and code reviewer to new skills" "jq -e '(.agents[] | select(.name==\"researcher\") | (.skills | index(\"graph-research\")) != null and (.skills | index(\"dark-code-audit\")) != null and (.skills | index(\"paved-road-registry\")) != null) and (.agents[] | select(.name==\"planner\") | (.skills | index(\"context-layers\")) != null and (.skills | index(\"paved-road-registry\")) != null) and (.agents[] | select(.name==\"code-reviewer\") | (.skills | index(\"comprehension-gate\")) != null and (.skills | index(\"paved-road-registry\")) != null)' '$ROOT/skills/manifest.json' >/dev/null"

echo ""
echo "--- LLM vs Deterministic Rebalance ---"
assert "llm-vs-deterministic spec exists" "[ -f '$ROOT/docs/specs/llm-vs-deterministic.md' ]"
assert "llm-vs-deterministic spec has at least 10 node rows" "awk '/^## Node Map$/{in_table=1; next} /^## Judge Inventory$/{in_table=0} in_table && /^\\|/{count++} END {exit !(count>=12)}' '$ROOT/docs/specs/llm-vs-deterministic.md'"
assert "llm-vs-deterministic spec lists per-judge cost guards" "rg -q 'Brief clarity|Specificity|Verifier semantic|Slop|Section policy|Mutant materiality' '$ROOT/docs/specs/llm-vs-deterministic.md' && rg -q '700 max tokens / call|900 max tokens / call|650 max tokens / call|750 max tokens / call|1400 max tokens / call' '$ROOT/docs/specs/llm-vs-deterministic.md'"
assert "all six judge skill files exist" "for f in '$ROOT/skills/brief-clarity-judge/SKILL.md' '$ROOT/skills/specificity-judge/SKILL.md' '$ROOT/skills/verifier-semantic-judge/SKILL.md' '$ROOT/skills/mutant-materiality-judge/SKILL.md' '$ROOT/skills/slop-judge/SKILL.md' '$ROOT/skills/section-policy-judge/SKILL.md'; do [ -f \"\$f\" ] || exit 1; done"
assert "judge skill frontmatter declares activation metadata" "for f in '$ROOT/skills/brief-clarity-judge/SKILL.md' '$ROOT/skills/specificity-judge/SKILL.md' '$ROOT/skills/verifier-semantic-judge/SKILL.md' '$ROOT/skills/mutant-materiality-judge/SKILL.md' '$ROOT/skills/slop-judge/SKILL.md' '$ROOT/skills/section-policy-judge/SKILL.md'; do rg -q '^activation:' \"\$f\" && rg -q 'model_class:' \"\$f\" && rg -q 'cost_guard:' \"\$f\" || exit 1; done"
assert "brief-clarity-judge registered with fast_judge metadata" "jq -e '.skills[] | select(.name==\"brief-clarity-judge\") | .activation.mode == \"judgement\" and .activation.model_class == \"fast_judge\" and .activation.cost_guard.max_tokens_per_call == 700' '$ROOT/skills/manifest.json' >/dev/null"
assert "specificity-judge registered with fast_judge metadata" "jq -e '.skills[] | select(.name==\"specificity-judge\") | .activation.mode == \"judgement\" and .activation.model_class == \"fast_judge\" and .activation.cost_guard.expected_calls_per_run == 4' '$ROOT/skills/manifest.json' >/dev/null"
assert "verifier-semantic-judge registered with fast_judge metadata" "jq -e '.skills[] | select(.name==\"verifier-semantic-judge\") | .activation.mode == \"judgement\" and .activation.model_class == \"fast_judge\" and .activation.cost_guard.max_tokens_per_call == 650' '$ROOT/skills/manifest.json' >/dev/null"
assert "mutant-materiality-judge registered with deep_judge metadata" "jq -e '.skills[] | select(.name==\"mutant-materiality-judge\") | .activation.mode == \"judgement\" and .activation.model_class == \"deep_judge\" and .activation.cost_guard.max_tokens_per_call == 1400' '$ROOT/skills/manifest.json' >/dev/null"
assert "slop-judge registered with fast_judge metadata" "jq -e '.skills[] | select(.name==\"slop-judge\") | .activation.mode == \"judgement\" and .activation.model_class == \"fast_judge\" and .activation.cost_guard.expected_calls_per_run == 3' '$ROOT/skills/manifest.json' >/dev/null"
assert "section-policy-judge registered with fast_judge metadata" "jq -e '.skills[] | select(.name==\"section-policy-judge\") | .activation.mode == \"judgement\" and .activation.model_class == \"fast_judge\" and .activation.cost_guard.expected_calls_per_run == 2' '$ROOT/skills/manifest.json' >/dev/null"
assert "every judge skill declares a cost guard" "jq -e 'all(.skills[] | select(.name==\"brief-clarity-judge\" or .name==\"specificity-judge\" or .name==\"verifier-semantic-judge\" or .name==\"mutant-materiality-judge\" or .name==\"slop-judge\" or .name==\"section-policy-judge\"); (.activation.cost_guard.max_tokens_per_call > 0) and (.activation.cost_guard.expected_calls_per_run >= 1))' '$ROOT/skills/manifest.json' >/dev/null"
assert "every modeled agent carries default fast_judge and deep_judge slots per runtime" "jq -e 'all(.agents[]; ((has(\"runtime_model_map\") | not) or ([.runtime_model_map.claude.default, .runtime_model_map.claude.fast_judge, .runtime_model_map.claude.deep_judge, .runtime_model_map.codex.default, .runtime_model_map.codex.fast_judge, .runtime_model_map.codex.deep_judge, .runtime_model_map.cursor.default, .runtime_model_map.cursor.fast_judge, .runtime_model_map.cursor.deep_judge, .runtime_model_map.antigravity.default, .runtime_model_map.antigravity.fast_judge, .runtime_model_map.antigravity.deep_judge, .runtime_model_map.factory.default, .runtime_model_map.factory.fast_judge, .runtime_model_map.factory.deep_judge] | all(type == \"string\"))))' '$ROOT/skills/manifest.json' >/dev/null"
assert "eval-council Gate 0 delegates presence checks to JSON schema" "rg -q 'Presence checks.*JSON schema validation|task_classification.*, change_surface.*, applicability_manifest.*, and verification_spec.*JSON schema validation' '$ROOT/skills/eval-council/SKILL.md'"
assert "eval-council Gate 0 references specificity-judge" "rg -q 'specificity-judge|low_specificity|specificity_judge_unavailable' '$ROOT/skills/eval-council/SKILL.md'"
assert "eval-council Gate 0 references verifier-semantic-judge" "rg -q 'verifier-semantic-judge|semantic change' '$ROOT/skills/eval-council/SKILL.md'"
assert "planner and Eval Council enforce loop budget no-overclaim" "rg -q 'budget_guard|budget_status|loop-budget-check|budget_exhausted|self_autonomous' '$ROOT/agents/planner.md' && rg -q 'budget_guard|budget_status|loop-budget-check|budget_exhausted|self_autonomous' '$ROOT/skills/eval-council/SKILL.md'"
assert "codegen context and LLM security pass compact budget refs" "rg -q 'budget_guard|budget_status|loop-budget-check|billing account IDs' '$ROOT/skills/codegen-context/SKILL.md' && rg -q 'budget_guard|budget_status|loop-budget-check|budget_exhausted' '$ROOT/skills/llm-security/SKILL.md'"
assert "agent native interface exposes loop budget command" "rg -q 'loop-budget-check|loop_budget_check|budget_status|budget_exhausted' '$ROOT/docs/specs/agent-native-interface.md'"
assert "plan-reviewer supports stuck and low_specificity outputs" "rg -q 'labels: \\[lgtm, revise, blocked, stuck\\]' '$ROOT/agents/plan-reviewer.md' && rg -q 'low_specificity|specificity_judge_unavailable' '$ROOT/agents/plan-reviewer.md'"
assert "plan-reviewer exposes convention auditor" "rg -q 'Convention Auditor' '$ROOT/agents/plan-reviewer.md' && rg -q 'repo_conventions.status == extracted' '$ROOT/agents/plan-reviewer.md'"
assert "council verdict schema supports schema validation and specificity status fields" "jq -e '((.properties.verdict.properties.gate_0.required | index(\"schema_validation\")) != null) and ((.properties.verdict.properties.gate_0.required | index(\"specificity\")) != null)' '$ROOT/docs/schemas/council-verdict-output.schema.json' >/dev/null"
assert "council verdict schema uses rationale and failing_signals for specificity findings" "jq -e '((.properties.specificity_findings.items.required | index(\"rationale\")) != null) and ((.properties.specificity_findings.items.required | index(\"failing_signals\")) != null)' '$ROOT/docs/schemas/council-verdict-output.schema.json' >/dev/null"
assert "council verdict schemas support convention auditor" "jq -e '(.properties.verdict.properties.applicability_manifest.properties.overlay_personas.items.enum | index(\"convention_auditor\")) and (.properties.verdict.properties.personas.items.properties.name.enum | index(\"convention_auditor\"))' '$ROOT/docs/schemas/council-verdict-output.schema.json' >/dev/null && jq -e '(.properties.personas.items.properties.name.enum | index(\"convention_auditor\"))' '$ROOT/docs/schemas/eval-council-verdict.schema.json' >/dev/null"
assert "build-brief schema requires files_to_modify files_to_create and reference_impl" "jq -e '((.definitions.task.required | index(\"files_to_modify\")) != null) and ((.definitions.task.required | index(\"files_to_create\")) != null) and ((.definitions.task.required | index(\"reference_impl\")) != null)' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "coder uses deterministic expected_failure_mode matching before LLM" "rg -q 'substring match|regex match|Levenshtein distance.*20%' '$ROOT/agents/coder.md'"
assert "test-strength-auditor is a wrapper with only materiality judge handoff" "rg -q 'tool-invocation wrapper|mutant-materiality-judge' '$ROOT/agents/test-strength-auditor.md'"
assert "test-strength skill marks material surviving mutants as weak" "rg -q 'material.*surviving mutant.*weak' '$ROOT/skills/test-strength/SKILL.md'"
assert "DoD tags checks as automatable or judgement" "awk -F'|' '(\$2 ~ /^[[:space:]]*[0-9]+[[:space:]]*$/) && (\$4 ~ /automatable/ || \$4 ~ /judgement/) {count++} END {exit !(count>=22)}' '$ROOT/skills/definition-of-done/SKILL.md'"
assert "stop-slop content mode routes through slop-judge with schema" "rg -q 'slop-judge|Slop Judge Input|Slop Judge Output' '$ROOT/skills/stop-slop/SKILL.md'"
assert "stop-slop defines output eval loop" "rg -q 'Output Eval Loop|slop_quality_gate|Pre-ship regression|case_promotion_sources' '$ROOT/skills/stop-slop/SKILL.md'"
assert "slop-judge returns numeric scores and candidate cases" "rg -q 'criterion_scores|regression_delta|new_eval_case_candidate|missing_benchmark' '$ROOT/skills/slop-judge/SKILL.md'"
assert "feedback loop promotes slop failures into eval cases" "rg -q 'Eval Case Promotion|candidate eval cases|slop_removal|new_eval_case_candidate' '$ROOT/skills/feedback-loop/SKILL.md'"
assert "feedback loop ingests maintainer PR comments" "rg -q 'Maintainer PR Comment Intake' '$ROOT/skills/feedback-loop/SKILL.md' && rg -q 'gh pr view' '$ROOT/skills/feedback-loop/SKILL.md' && rg -q 'target_repo_convention' '$ROOT/skills/feedback-loop/SKILL.md' && rg -q 'repo_conventions.rules' '$ROOT/skills/feedback-loop/SKILL.md' && rg -q 'skill_file_rule_changes' '$ROOT/skills/feedback-loop/SKILL.md'"
assert "feedback loop documents interralis review comment fixture" "rg -q 'Interralis PR #225 And #226' '$ROOT/skills/feedback-loop/SKILL.md' && rg -q 'interralis#225' '$ROOT/skills/feedback-loop/SKILL.md' && rg -q 'interralis#226' '$ROOT/skills/feedback-loop/SKILL.md' && rg -q 'one responsibility' '$ROOT/skills/feedback-loop/SKILL.md' && rg -q 'recursive directory module' '$ROOT/skills/feedback-loop/SKILL.md' && rg -q 'pure core logic' '$ROOT/skills/feedback-loop/SKILL.md' && rg -q 'file size as a gate' '$ROOT/skills/feedback-loop/SKILL.md'"
assert "systematic debugging records loop progress and no-progress signals" "rg -q 'loop_progress|no_progress_count|control_events|safe_checkpoint|escalation_context' '$ROOT/skills/systematic-debugging/SKILL.md'"
assert "manifest registers stop-slop slop quality outputs" "jq -e '.skills[] | select(.name==\"stop-slop\") | .activation.consumes_manifest == true and (.activation.produces | index(\"slop_quality_report\")) != null and (.activation.produces | index(\"slop_eval_case_candidates\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "manifest registers slop-judge score outputs" "jq -e '.skills[] | select(.name==\"slop-judge\") | .contract_version == \"2.0.0\" and (.activation.produces | index(\"slop_quality_score\")) != null and (.activation.produces | index(\"slop_eval_case_candidates\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "triage extracts signal features and low_confidence judge output" "rg -q 'Deterministic Feature Extraction|signal_features|low_confidence_judge' '$ROOT/agents/triage.md'"
assert "triage schema requires signal_features" "jq -e '((.required | index(\"signal_features\")) != null) and ((.properties.signal_features.required | index(\"reproducer_present\")) != null)' '$ROOT/docs/schemas/triage-output.schema.json' >/dev/null"
assert "applicability manifest spec documents section-policy override" "rg -q 'Section Policy Override|overridden_by: \"section_policy_judge\"' '$ROOT/docs/specs/applicability-manifest.md'"
assert "applicability manifest schema supports overridden_by" "jq -e '.properties.section_policy.items.properties.overridden_by.enum[0] == \"section_policy_judge\"' '$ROOT/docs/schemas/applicability-manifest.schema.json' >/dev/null"
assert "CASE-011 through CASE-018 exist with judge_calls" "jq -e '[.cases[] | select((.id | test(\"^CASE-01[1-8]$\")) and ((.expected_stage_outputs.judge_calls | length) == 6)) | .id] | unique | length == 8' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "judge_invocation evaluator exists and is executable" "[ -x '$ROOT/tests/backtest/evaluators/judge_invocation.sh' ]"
assert "run_backtest invokes judge_invocation evaluator" "rg -q 'judge_invocation' '$ROOT/tests/backtest/run_backtest.sh'"
assert "run_backtest serializes judge decisions into the report" "rg -q 'judge_decisions' '$ROOT/tests/backtest/run_backtest.sh'"
assert "smoke specificity fixture and assertion exist" "[ -f '$ROOT/tests/smoke/fixtures/feature_vague/.adlc/build_brief.json' ] && [ -x '$ROOT/tests/smoke/assertions/assert_specificity.sh' ] && [ -x '$ROOT/tests/smoke/stages/run_specificity.sh' ]"
assert "run_smoke includes the specificity stage" "rg -q 'run_stage_with_fixture .*specificity|artifacts/specificity\\.json' '$ROOT/tests/smoke/run_smoke.sh'"

echo ""
echo "--- Production Readiness Probe ---"
assert "codebase research gates production readiness probe by change surface" "rg -q 'Production Readiness Antipattern Probe' '$ROOT/skills/codebase-research/SKILL.md' && rg -q 'runtime_path_change.*service_boundary_change.*external_integration.*persistent_storage.*api_change.*perf_sensitive.*user_facing_operation' '$ROOT/skills/codebase-research/SKILL.md'"
assert "production readiness probe requires evidence before findings" "rg -q 'Do not create a finding unless all five are present' '$ROOT/skills/codebase-research/SKILL.md' && rg -q 'Do not turn this catalog into scope by default' '$ROOT/skills/codebase-research/SKILL.md'"
assert "production readiness probe output carries priority and verifier path" "rg -q 'production_readiness_probe' '$ROOT/skills/codebase-research/SKILL.md' && rg -q 'must_fix_for_v1 \\| monitor \\| fix_in_v2 \\| not_applicable' '$ROOT/skills/codebase-research/SKILL.md' && rg -q 'verification_path' '$ROOT/skills/codebase-research/SKILL.md'"
assert "build brief consumes production readiness probe without making generic scope" "rg -q 'Production readiness scoping rule' '$ROOT/agents/ADLC-BUILD-BRIEF-AGENT.md' && rg -q 'must_fix_for_v1.*failure-mode mitigations and tasks' '$ROOT/agents/ADLC-BUILD-BRIEF-AGENT.md' && rg -q 'not_applicable.*do not become scope' '$ROOT/agents/ADLC-BUILD-BRIEF-AGENT.md'"
assert "codegen context limits production readiness work to assigned findings" "rg -q 'evidence-backed production readiness probe findings assigned to this task' '$ROOT/skills/codegen-context/SKILL.md' && rg -q 'Do not ask the coding agent to implement unrelated catalog items' '$ROOT/skills/codegen-context/SKILL.md'"

echo ""
echo "--- Backtest Integrity ---"
assert "backtest runner exists and is executable" "[ -x '$ROOT/tests/backtest/run_backtest.sh' ]"
assert "triage evaluator exists and is executable" "[ -x '$ROOT/tests/backtest/evaluators/triage.sh' ]"
assert "section policy evaluator exists and is executable" "[ -x '$ROOT/tests/backtest/evaluators/section_policy.sh' ]"
assert "verifier scope evaluator exists and is executable" "[ -x '$ROOT/tests/backtest/evaluators/verifier_scope.sh' ]"
assert "DoD overlays evaluator exists and is executable" "[ -x '$ROOT/tests/backtest/evaluators/dod_overlays.sh' ]"
assert "council personas evaluator exists and is executable" "[ -x '$ROOT/tests/backtest/evaluators/council_personas.sh' ]"
assert "test strength evaluator exists and is executable" "[ -x '$ROOT/tests/backtest/evaluators/test_strength.sh' ]"
assert "judge invocation evaluator exists and is executable" "[ -x '$ROOT/tests/backtest/evaluators/judge_invocation.sh' ]"
assert "every fixture case declares expected_stage_outputs and rationale" "jq -e 'all(.cases[]; has(\"expected_stage_outputs\") and has(\"expected_rationale\"))' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "CASE-008 expects verifier scope revise" "jq -e '.cases[] | select(.id==\"CASE-008\") | .expected_stage_outputs.verifier_scope.verdict == \"revise\" and .expected_stage_outputs.verifier_scope.reason == \"verifier_no_coverage\"' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "CASE-009 expects weak test strength" "jq -e '.cases[] | select(.id==\"CASE-009\") | .expected_stage_outputs.test_strength.verdict == \"weak\" and .expected_stage_outputs.test_strength.coverage == 0.82 and .expected_stage_outputs.test_strength.mutation_kill_rate == 0.45' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "CASE-010 expects passing test strength" "jq -e '.cases[] | select(.id==\"CASE-010\") | .expected_stage_outputs.test_strength.verdict == \"pass\" and .expected_stage_outputs.test_strength.coverage == 0.85 and .expected_stage_outputs.test_strength.mutation_kill_rate == 0.7' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
backtest_report="$(mktemp)"
assert "backtest runner exits 0 without mutating the golden report" "ADLC_BACKTEST_REPORT='$backtest_report' '$ROOT/tests/backtest/run_backtest.sh' >/dev/null 2>&1"
assert "backtest report parses" "jq empty '$backtest_report' >/dev/null 2>&1"
assert "backtest report covers every fixture case" "[ \"\$(jq -r '.cases | length' '$backtest_report')\" -eq \"\$(jq -r '.cases | length' '$ROOT/tests/fixtures/applicability-issue-set.json')\" ]"
assert "backtest report records judge decisions per case" "jq -e 'all(.cases[]; (.judge_decisions | type) == \"array\" and (.judge_decisions | length) == 6)' '$backtest_report' >/dev/null"
assert "backtest report records zero failures" "jq -e '.failed == 0 and .passed == .total' '$backtest_report' >/dev/null"
assert "backtest total entries cover the seven-stage matrix" "[ \"\$(jq -r '.total' '$backtest_report')\" -eq \"\$(jq -r '.cases | length * 7' '$ROOT/tests/fixtures/applicability-issue-set.json')\" ]"
rm -f "$backtest_report"

echo ""
echo "--- Smoke Harness Integrity ---"
assert "smoke runner exists and is executable" "[ -x '$ROOT/tests/smoke/run_smoke.sh' ]"
assert "smoke build brief parses" "jq empty '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' >/dev/null 2>&1"
assert "smoke applicability manifest parses and satisfies required schema fields" "jq -e '.version == \"1.0.0\" and .task_classification == \"feature\" and .task_classification_confidence == 0.92 and (.change_surface.runtime_path_change == true) and (.change_surface.user_facing_operation == true) and (.verification_spec.primary_verifier.target_files[0] == \"src/scoreboard.py\")' '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/applicability_manifest.json' >/dev/null"
assert "smoke expected directory has five JSON files and they parse" "[ \"\$(find '$ROOT/tests/smoke/fixtures/feature_bugfix/expected' -maxdepth 1 -name '*.json' | wc -l | tr -d ' ')\" -eq 5 ] && jq empty '$ROOT/tests/smoke/fixtures/feature_bugfix/expected/'*.json >/dev/null 2>&1"
assert "every smoke stage script is executable" "! find '$ROOT/tests/smoke/stages' -maxdepth 1 -name '*.sh' ! -perm -111 | grep -q ."
assert "every smoke assertion script is executable" "! find '$ROOT/tests/smoke/assertions' -maxdepth 1 -name '*.sh' ! -perm -111 | grep -q ."
assert "smoke stages README exists" "[ -f '$ROOT/tests/smoke/stages/README.md' ]"
assert "smoke artifacts path is gitignored" "rg -q 'tests/smoke/artifacts/\\*|tests/smoke/artifacts/' '$ROOT/.gitignore'"
assert "run_smoke without SMOKE=1 exits non-zero with explanatory message" "tmp=\$(mktemp); if '$ROOT/tests/smoke/run_smoke.sh' >\"\$tmp\" 2>&1; then ok=1; else ok=0; fi; if [ \"\$ok\" -ne 0 ]; then rm -f \"\$tmp\"; false; else rg -q 'SMOKE=1' \"\$tmp\"; status=\$?; rm -f \"\$tmp\"; [ \"\$status\" -eq 0 ]; fi"
assert "run_smoke without SMOKE=1 does not mention claude invocation" "tmp=\$(mktemp); '$ROOT/tests/smoke/run_smoke.sh' >\"\$tmp\" 2>&1 || true; if rg -q 'claude --|\\bclaude\\b' \"\$tmp\"; then rm -f \"\$tmp\"; false; else rm -f \"\$tmp\"; true; fi"

echo ""
echo "--- Smoke Invocation Hardening ---"
assert "_invoke helper exists and is executable" "[ -x '$ROOT/tests/smoke/stages/_invoke.sh' ]"
assert "_validate helper exists and is executable" "[ -x '$ROOT/tests/smoke/stages/_validate.sh' ]"
assert "specificity smoke stage and assertion exist" "[ -x '$ROOT/tests/smoke/stages/run_specificity.sh' ] && [ -x '$ROOT/tests/smoke/assertions/assert_specificity.sh' ]"
assert "triage agent has output contract section" "rg -q '^## Output Contract$' '$ROOT/agents/triage.md'"
assert "test-author agent has output contract section" "rg -q '^## Output Contract$' '$ROOT/agents/test-author.md'"
assert "coder agent has output contract section" "rg -q '^## Output Contract$' '$ROOT/agents/coder.md'"
assert "test-strength agent has output contract section" "rg -q '^## Output Contract$' '$ROOT/agents/test-strength-auditor.md'"
assert "plan-reviewer agent has output contract section" "rg -q '^## Output Contract$' '$ROOT/agents/plan-reviewer.md'"
assert "all five smoke output schemas parse" "jq empty '$ROOT/docs/schemas/triage-output.schema.json' '$ROOT/docs/schemas/test-author-output.schema.json' '$ROOT/docs/schemas/coder-output.schema.json' '$ROOT/docs/schemas/test-strength-output.schema.json' '$ROOT/docs/schemas/council-verdict-output.schema.json' >/dev/null 2>&1"
assert "human approval and security review schemas parse" "jq empty '$ROOT/docs/schemas/approval-record.schema.json' '$ROOT/docs/schemas/security-review-output.schema.json' >/dev/null 2>&1"
assert "provider conformance evidence is schema-backed and tested" "jq empty '$ROOT/docs/schemas/provider-conformance-report.schema.json' >/dev/null 2>&1 && PYTHONPATH='$ROOT/scripts' python3 '$ROOT/tests/test_provider_conformance_schema.py'"
assert "smoke report records source runtime adapter and fixture identity" "rg -q 'source_tree_clean' '$ROOT/tests/smoke/run_smoke.sh' && rg -q 'adapter_sha256' '$ROOT/tests/smoke/run_smoke.sh' && rg -q 'fixture_sha256' '$ROOT/tests/smoke/run_smoke.sh' && rg -q 'provider-conformance-report' '$ROOT/tests/smoke/run_smoke.sh'"
assert "workflow state supports approval records and retry counters" "jq -e '.properties.approval_records.items[\"\$ref\"] == \"approval-record.schema.json\" and .properties.edge_counters.items.properties.failure_signature.minLength == 1' '$ROOT/docs/schemas/workflow-state.schema.json' >/dev/null"
assert "atomic persistence failure modes preserve the previous file" "PYTHONPATH='$ROOT/scripts' python3 '$ROOT/tests/test_atomic_write.py' >/dev/null"
assert "all five smoke output schemas declare required arrays with at least three entries" "jq -e '(.required | type) == \"array\" and (.required | length) >= 3' '$ROOT/docs/schemas/triage-output.schema.json' >/dev/null && jq -e '(.required | type) == \"array\" and (.required | length) >= 3' '$ROOT/docs/schemas/test-author-output.schema.json' >/dev/null && jq -e '(.required | type) == \"array\" and (.required | length) >= 3' '$ROOT/docs/schemas/coder-output.schema.json' >/dev/null && jq -e '(.required | type) == \"array\" and (.required | length) >= 3' '$ROOT/docs/schemas/test-strength-output.schema.json' >/dev/null && jq -e '(.required | type) == \"array\" and (.required | length) >= 3' '$ROOT/docs/schemas/council-verdict-output.schema.json' >/dev/null"
assert "stage scripts source _invoke helper" "for f in '$ROOT/tests/smoke/stages/run_triage.sh' '$ROOT/tests/smoke/stages/run_spec_to_tests.sh' '$ROOT/tests/smoke/stages/run_coder.sh' '$ROOT/tests/smoke/stages/run_test_strength.sh' '$ROOT/tests/smoke/stages/run_council.sh'; do rg -q '_invoke\\.sh' \"\$f\" || exit 1; done"
assert "specificity stage sources _invoke helper" "rg -q '_invoke\\.sh' '$ROOT/tests/smoke/stages/run_specificity.sh'"
assert "_invoke helper is a runtime dispatcher without inline CLI flags" "bad_runtime=\"gemi\"\"ni\"; ! rg -q \"claude --|codex exec|--system-prompt|--bare|--json-schema|--output-schema|command -v (claude|codex|cursor|\${bad_runtime}|antigravity|factory)\" '$ROOT/tests/smoke/stages/_invoke.sh'"
assert "stage scripts pass explicit tool grants into invoke_agent" "rg -q -- '--tools \"\"' '$ROOT/tests/smoke/stages/run_triage.sh' && rg -q -- '--tools \"Read,Write,Bash\"' '$ROOT/tests/smoke/stages/run_spec_to_tests.sh' && rg -q -- '--tools \"Read,Write,Edit,Bash,Glob,Grep\"' '$ROOT/tests/smoke/stages/run_coder.sh' && rg -q -- '--tools \"Read,Bash\"' '$ROOT/tests/smoke/stages/run_test_strength.sh' && rg -q -- '--tools \"\"' '$ROOT/tests/smoke/stages/run_council.sh' && rg -q -- '--tools \"\"' '$ROOT/tests/smoke/stages/run_specificity.sh'"
assert "triage stage makes workspace read-only before invocation" "rg -q 'chmod -R a-w ' '$ROOT/tests/smoke/stages/run_triage.sh' && rg -q 'workspace_dir' '$ROOT/tests/smoke/stages/run_triage.sh'"
assert "council stage makes workspace read-only before invocation" "rg -q 'chmod -R a-w ' '$ROOT/tests/smoke/stages/run_council.sh' && rg -q 'workspace_dir' '$ROOT/tests/smoke/stages/run_council.sh'"
assert "run_smoke recreates a fresh workspace copy at the start of each stage" "rg -q 'prepare_workspace ' '$ROOT/tests/smoke/run_smoke.sh' && rg -q 'cp -R ' '$ROOT/tests/smoke/run_smoke.sh' && rg -q 'source_dir' '$ROOT/tests/smoke/run_smoke.sh' && rg -q 'WORKSPACE_DIR' '$ROOT/tests/smoke/run_smoke.sh'"
assert "live smoke report path is absent and ignored" "[ ! -e '$ROOT/tests/smoke/artifacts/smoke_report.json' ] && git -C '$ROOT' check-ignore --no-index -q 'tests/smoke/artifacts/smoke_report.json'"
assert "historical smoke fixture is explicitly non-conformance evidence" "jq -e '.evidence_status == \"historical_fixture_not_current_conformance\" and .runtime == \"codex\" and .overall == \"pass\"' '$ROOT/tests/smoke/fixtures/historical-codex-smoke-report.json' >/dev/null 2>&1"

echo ""
echo "--- Runtime-Agnostic Smoke Dispatch ---"
assert "fixer agent is wired with bounded diagnose repair and proof phases" "rg -qi 'root cause' '$ROOT/agents/fixer.md' && rg -qi 'prove|verif' '$ROOT/agents/fixer.md' && jq -e 'any(.agents[]; .name == \"fixer\" and .dag_node == \"fixer\")' '$ROOT/skills/manifest.json' >/dev/null"
assert "Eval Council persona docs match manifest core-overlay counts" "jq -e '(.skills[] | select(.name == \"eval-council\") | .activation | (.core_personas | length) == 3 and (.overlay_personas | length) == 7)' '$ROOT/skills/manifest.json' >/dev/null && rg -q '3 core \\+ 7 conditional-overlay' '$ROOT/README.md' '$ROOT/platform/CLAUDE.md'"
assert "drift-maintenance is declared in the skill manifest" "jq -e 'any(.skills[]; .name == \"drift-maintenance\" and .path == \"skills/drift-maintenance/SKILL.md\" and .contract_version == \"1.0.0\" and .side_effect_profile == \"read_only\")' '$ROOT/skills/manifest.json' >/dev/null"
assert "security workflow ownership is explicit" "rg -q 'security.*workflow node is owned by.*security-reviewer' '$ROOT/docs/specs/dag-binding.md'"
assert "_invoke dispatcher sources runtime adapters" "rg -Fq 'adapters/\${runtime}.sh' '$ROOT/tests/smoke/stages/_invoke.sh' && rg -Fq 'source \"\$adapter_path\"' '$ROOT/tests/smoke/stages/_invoke.sh'"
assert "all production adapters exist and are executable" "for f in '$ROOT/scripts/adlc_runtime/adapters/claude.sh' '$ROOT/scripts/adlc_runtime/adapters/codex.sh' '$ROOT/scripts/adlc_runtime/adapters/cursor.sh' '$ROOT/scripts/adlc_runtime/adapters/antigravity.sh' '$ROOT/scripts/adlc_runtime/adapters/factory.sh'; do [ -x \"\$f\" ] || exit 1; done"
assert "all adapter headers declare runtime metadata markers" "for f in '$ROOT/scripts/adlc_runtime/adapters/claude.sh' '$ROOT/scripts/adlc_runtime/adapters/codex.sh' '$ROOT/scripts/adlc_runtime/adapters/cursor.sh' '$ROOT/scripts/adlc_runtime/adapters/antigravity.sh' '$ROOT/scripts/adlc_runtime/adapters/factory.sh'; do rg -q '^# Runtime:' \"\$f\" && rg -q '^# Minimum CLI Version:' \"\$f\" && rg -q '^# Auth Env Vars:' \"\$f\" && rg -q '^# Flag Mapping:' \"\$f\" && rg -q '^# Known Limitations:' \"\$f\" || exit 1; done"
assert "unsupported runtime fails with a clear message" "tmp=\$(mktemp); if env -i PATH='/usr/bin:/bin' ADLC_RUNTIME='unsupported' /bin/bash -c 'source \"\$1\"; preflight' bash '$ROOT/tests/smoke/stages/_invoke.sh' >\"\$tmp\" 2>&1; then status=0; else status=\$?; fi; ok=0; if [ \"\$status\" -ne 0 ] && rg -q 'unsupported runtime' \"\$tmp\"; then ok=1; fi; rm -f \"\$tmp\"; [ \"\$ok\" -eq 1 ]"
assert "keyed adapters preflight without auth exits 65" "for runtime in claude codex cursor factory; do if env -i PATH='/usr/bin:/bin' /bin/bash '$ROOT/scripts/adlc_runtime/adapters/'\"\$runtime\"'.sh' preflight >/dev/null 2>&1; then exit 1; else [ \"\$?\" -eq 65 ] || exit 1; fi; done"
assert "antigravity preflight uses native session and no provider key" "tmp=\$(mktemp); if env -i PATH='/usr/bin:/bin' /bin/bash '$ROOT/scripts/adlc_runtime/adapters/antigravity.sh' preflight >\"\$tmp\" 2>&1; then status=0; else status=\$?; fi; ok=0; if [ \"\$status\" -eq 77 ] && rg -q 'does not use provider API keys' \"\$tmp\"; then ok=1; fi; rm -f \"\$tmp\"; [ \"\$ok\" -eq 1 ]"
assert "adapter dispatch test exists and is executable" "[ -x '$ROOT/tests/smoke/adapters/test_dispatch.sh' ]"
assert "adapter dispatch test passes" "'$ROOT/tests/smoke/adapters/test_dispatch.sh' >/dev/null 2>&1"
assert "agent-native CLI test exists and passes" "[ -x '$ROOT/tests/test_adlc_cli.sh' ] && '$ROOT/tests/test_adlc_cli.sh' >/dev/null 2>&1"
assert "WORKFLOW.md names machine-readable truth and is not configuration" "rg -q 'WORKFLOW\\.dot' '$ROOT/WORKFLOW.md' && rg -q 'skills/manifest\\.json' '$ROOT/WORKFLOW.md' && rg -q 'machine-readable sources' '$ROOT/WORKFLOW.md' && rg -q 'not parsed as configuration' '$ROOT/WORKFLOW.md' && ! head -1 '$ROOT/WORKFLOW.md' | rg -q '^---$'"
assert "dag binding routes all five runtimes through production adapters" "rg -q 'scripts/adlc_runtime/adapters/.*single source of truth' '$ROOT/docs/specs/dag-binding.md' && for runtime in claude codex cursor antigravity factory; do [ -x '$ROOT/scripts/adlc_runtime/adapters/'\"\$runtime\"'.sh' ] || exit 1; done"
assert "dag binding references production adapters as invocation source of truth" "rg -q 'scripts/adlc_runtime/adapters/' '$ROOT/docs/specs/dag-binding.md' && rg -q 'selected adapter.*source of truth' '$ROOT/docs/specs/dag-binding.md'"
assert "smoke README documents all five runtime commands" "rg -q 'ADLC_RUNTIME=claude' '$ROOT/tests/smoke/README.md' && rg -q 'ADLC_RUNTIME=codex' '$ROOT/tests/smoke/README.md' && rg -q 'ADLC_RUNTIME=antigravity' '$ROOT/tests/smoke/README.md' && rg -q 'ADLC_RUNTIME=cursor' '$ROOT/tests/smoke/README.md' && rg -q 'ADLC_RUNTIME=factory' '$ROOT/tests/smoke/README.md'"
assert "antigravity runtime does not advertise provider API keys" "bad_pattern=\"GEM\"\"INI\"\"_API_KEY|GOO\"\"GLE\"\"_API_KEY|gemi\"\"ni\"; ! rg -q \"\$bad_pattern\" '$ROOT/WORKFLOW.md' '$ROOT/tests/smoke/README.md' '$ROOT/scripts/adlc_runtime/adapters/antigravity.sh' '$ROOT/skills/manifest.json' '$ROOT/README.md'"
assert "run_smoke uses adapter preflight and ADLC_RUNTIME" "rg -Fq 'ADLC_RUNTIME:-claude' '$ROOT/tests/smoke/run_smoke.sh' && rg -Fq 'AUTH_PATH=\"\$(preflight)\"' '$ROOT/tests/smoke/run_smoke.sh'"
assert "manifest carries runtime_model_map on every modeled agent" "jq -e 'all(.agents[]; (has(\"model\") | not) or ((.runtime_model_map | type) == \"object\" and (.runtime_model_map | has(\"claude\")) and (.runtime_model_map | has(\"codex\")) and (.runtime_model_map | has(\"cursor\")) and (.runtime_model_map | has(\"antigravity\")) and (.runtime_model_map | has(\"factory\"))))' '$ROOT/skills/manifest.json' >/dev/null"

echo ""
echo "--- Agent-Native Interface ---"
assert "agent-native interface spec exists" "[ -f '$ROOT/docs/specs/agent-native-interface.md' ]"
assert "agent-native interface names machine-readable anchors" "rg -q 'skills/manifest\\.json|WORKFLOW\\.dot|docs/schemas/|scripts/adlc_runtime/adapters/|emitter-contract' '$ROOT/docs/specs/agent-native-interface.md'"
assert "agent-native interface documents quick hook contract" "rg -q 'Quick Hook Contract|ADLC_RUNTIME|validate.*schema|local MCP provider' '$ROOT/docs/specs/agent-native-interface.md'"
assert "agent-native interface documents workflow runner and emitter hooks" "rg -q 'adlc run|run-phase|resume-workflow|emit-work-items|allow_mutation|provider_command' '$ROOT/docs/specs/agent-native-interface.md'"
assert "agent-native interface documents executable tool nodes" "rg -q 'Executable Tool-Node Contract|phase_artifacts|tool-node-result|context_assembly|learning_capture' '$ROOT/docs/specs/agent-native-interface.md'"
assert "agent-native interface documents control-plane dogfood loop" "rg -q 'control-plane-drift-loop|control_plane_drift_loop|dogfood loop|human review' '$ROOT/docs/specs/agent-native-interface.md'"
assert "agent-native interface documents learning and architecture memory" "rg -q 'architecture-memory|memory-health|champion-holdout|adlc_architecture_memory|adlc_memory_health|adlc_champion_holdout' '$ROOT/docs/specs/agent-native-interface.md'"
assert "agent-native interface documents packaged loop library" "rg -q 'loop-library|loop-template-install|adlc_loop_library|adlc_loop_template_install|packaged assisted-loop templates' '$ROOT/docs/specs/agent-native-interface.md'"
assert "agent-native interface documents self-actioning meta harness" "rg -q 'meta-harness-plan|adlc_meta_harness_plan|self-actioning|dispatch' '$ROOT/docs/specs/agent-native-interface.md'"
assert "workflow-state schema supports DAG node phases" "jq -e '.properties.phase.enum | index(\"start\") and index(\"triage\") and index(\"research\") and index(\"engineer_review\") and index(\"done\")' '$ROOT/docs/schemas/workflow-state.schema.json' >/dev/null"
assert "Ponytail schemas parse" "jq empty '$ROOT/docs/schemas/ponytail-admission-report.schema.json' '$ROOT/docs/schemas/ponytail-scenario-canary-report.schema.json' >/dev/null 2>&1"
assert "Build Brief schema minimality contract has only rung and decision" "jq -e '.definitions.minimality_contract.required == [\"rung\", \"decision\"] and (.definitions.minimality_contract.properties | keys | sort) == [\"decision\", \"rung\"] and .definitions.minimality_contract.additionalProperties == false' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "Build Brief schema omits removed Ponytail contract fields" "! rg -q 'reuse_evidence|minimum_check|new_dependencies|new_abstractions|abstraction_approval_ref|dependency_approval_ref' '$ROOT/docs/schemas/build-brief.schema.json' '$ROOT/docs/schemas/ponytail-admission-report.schema.json' '$ROOT/docs/schemas/ponytail-scenario-canary-report.schema.json'"
assert "Ponytail spec documents precedence and codegen settled constraint" "rg -q 'repo_conventions.*module_plan.*govern file and module structure|Minimality is decided once at decomposition time|must not re-deliberate the ladder' '$ROOT/docs/specs/ponytail-minimality-contract.md'"
assert "Ponytail spec documents anatomy gate limitations" "rg -Fq 'regex-backed diff scanner' '$ROOT/docs/specs/ponytail-minimality-contract.md' && rg -Fq 'removed lines' '$ROOT/docs/specs/ponytail-minimality-contract.md' && rg -Fq 'can miss removed safeguards' '$ROOT/docs/specs/ponytail-minimality-contract.md' && rg -Fq 'false-positive' '$ROOT/docs/specs/ponytail-minimality-contract.md' && rg -Fq 'over-engineering minimalist persona' '$ROOT/docs/specs/ponytail-minimality-contract.md'"
assert "Eval Council includes over-engineering minimalist persona" "rg -q 'over-engineering minimalist|Ponytail Over-Engineering Checks|REVISION_REQUIRED.*rung' '$ROOT/skills/eval-council/SKILL.md' && jq -e '.skills[] | select(.name == \"eval-council\") | (.activation.overlay_personas | index(\"over_engineering_minimalist\")) != null and (.activation.overlay_triggers.over_engineering_minimalist | index(\"artifact_type=implementation_task\")) != null' '$ROOT/skills/manifest.json' >/dev/null"
assert "Eval Council schemas accept over-engineering minimalist persona" "jq -e '.. | arrays | select(index(\"over_engineering_minimalist\")) | length > 0' '$ROOT/docs/schemas/council-verdict-output.schema.json' >/dev/null && jq -e '.. | arrays | select(index(\"over_engineering_minimalist\")) | length > 0' '$ROOT/docs/schemas/eval-council-verdict.schema.json' >/dev/null"
assert "agent and ticket skills use only right-sized minimality contract wording" "! rg -q 'reuse_evidence|minimum_check|new_dependencies|new_abstractions|abstraction_approval_ref|dependency_approval_ref' '$ROOT/agents/coder.md' '$ROOT/agents/planner.md' '$ROOT/agents/code-reviewer.md' '$ROOT/skills/codegen-context/SKILL.md' '$ROOT/skills/definition-of-done/SKILL.md' '$ROOT/skills/github-issue-creation/SKILL.md' '$ROOT/skills/jira-ticket-creation/SKILL.md' '$ROOT/skills/linear-ticket-creation/SKILL.md'"
assert "README lists Ponytail admission and scenario canary commands" "rg -q 'ponytail-admit|ponytail-scenario-canary|minimality_contract.*rung.*decision' '$ROOT/README.md'"
assert "runtime schema aliases include Ponytail reports" "PYTHONPATH='$ROOT/scripts' python3 -c 'from adlc_runtime.metadata import SCHEMA_ALIASES; assert SCHEMA_ALIASES[\"ponytail-admission-report\"].endswith(\"ponytail-admission-report.schema.json\"); assert SCHEMA_ALIASES[\"ponytail-scenario-canary-report\"].endswith(\"ponytail-scenario-canary-report.schema.json\")'"
assert "runtime command metadata includes Ponytail commands" "PYTHONPATH='$ROOT/scripts' python3 -c 'from adlc_runtime.metadata import COMMAND_METADATA; assert COMMAND_METADATA[\"ponytail-admit\"][\"mcp_name\"] == \"adlc_ponytail_admit\"; assert COMMAND_METADATA[\"ponytail-scenario-canary\"][\"mcp_name\"] == \"adlc_ponytail_scenario_canary\"'"
assert "runtime schema aliases include control-plane memory loop-library and meta-harness schemas" "PYTHONPATH='$ROOT/scripts' python3 -c 'from adlc_runtime.metadata import SCHEMA_ALIASES; assert SCHEMA_ALIASES[\"tool-registry\"].endswith(\"tool-registry.schema.json\"); assert SCHEMA_ALIASES[\"permission-audit-trail\"].endswith(\"permission-audit-trail.schema.json\"); assert SCHEMA_ALIASES[\"tool-node-result\"].endswith(\"tool-node-result.schema.json\"); assert SCHEMA_ALIASES[\"control-plane-drift-report\"].endswith(\"control-plane-drift-report.schema.json\"); assert SCHEMA_ALIASES[\"architecture-memory-report\"].endswith(\"architecture-memory-report.schema.json\"); assert SCHEMA_ALIASES[\"memory-health-report\"].endswith(\"memory-health-report.schema.json\"); assert SCHEMA_ALIASES[\"beads-status-report\"].endswith(\"beads-status-report.schema.json\"); assert SCHEMA_ALIASES[\"looper-status-report\"].endswith(\"looper-status-report.schema.json\"); assert SCHEMA_ALIASES[\"loop-design\"].endswith(\"loop-design.schema.json\"); assert SCHEMA_ALIASES[\"loop-design-validation-report\"].endswith(\"loop-design-validation-report.schema.json\"); assert SCHEMA_ALIASES[\"champion-holdout-report\"].endswith(\"champion-holdout-report.schema.json\"); assert SCHEMA_ALIASES[\"loop-template-catalog\"].endswith(\"loop-template-catalog.schema.json\"); assert SCHEMA_ALIASES[\"loop-template-install-report\"].endswith(\"loop-template-install-report.schema.json\"); assert SCHEMA_ALIASES[\"meta-harness-plan-report\"].endswith(\"meta-harness-plan-report.schema.json\")'"
assert "runtime command metadata includes action admission dogfood memory loop-library and meta-harness commands" "PYTHONPATH='$ROOT/scripts' python3 -c 'from adlc_runtime.metadata import COMMAND_METADATA; assert COMMAND_METADATA[\"action-admit\"][\"mcp_name\"] == \"adlc_action_admit\"; assert COMMAND_METADATA[\"control-plane-drift-loop\"][\"mcp_name\"] == \"adlc_control_plane_drift_loop\"; assert COMMAND_METADATA[\"architecture-memory\"][\"mcp_name\"] == \"adlc_architecture_memory\"; assert COMMAND_METADATA[\"memory-health\"][\"mcp_name\"] == \"adlc_memory_health\"; assert COMMAND_METADATA[\"beads-status\"][\"mcp_name\"] == \"adlc_beads_status\"; assert COMMAND_METADATA[\"looper-status\"][\"mcp_name\"] == \"adlc_looper_status\"; assert COMMAND_METADATA[\"loop-design-validate\"][\"mcp_name\"] == \"adlc_loop_design_validate\"; assert COMMAND_METADATA[\"loop-contract-from-design\"][\"mcp_name\"] == \"adlc_loop_contract_from_design\"; assert COMMAND_METADATA[\"champion-holdout\"][\"mcp_name\"] == \"adlc_champion_holdout\"; assert COMMAND_METADATA[\"loop-library\"][\"mcp_name\"] == \"adlc_loop_library\"; assert COMMAND_METADATA[\"loop-template-install\"][\"mcp_name\"] == \"adlc_loop_template_install\"; assert COMMAND_METADATA[\"meta-harness-plan\"][\"mcp_name\"] == \"adlc_meta_harness_plan\"'"
assert "runtime command metadata includes convention commands" "PYTHONPATH='$ROOT/scripts' python3 -c 'from adlc_runtime.metadata import COMMAND_METADATA; assert COMMAND_METADATA[\"repo-conventions\"][\"mcp_name\"] == \"adlc_repo_conventions\"; assert COMMAND_METADATA[\"convention-scan\"][\"mcp_name\"] == \"adlc_convention_scan\"'"
assert "runtime command metadata includes PR hygiene scan" "PYTHONPATH='$ROOT/scripts' python3 -c 'from adlc_runtime.metadata import COMMAND_METADATA; assert COMMAND_METADATA[\"pr-hygiene-scan\"][\"mcp_name\"] == \"adlc_pr_hygiene_scan\"'"
assert "runtime command metadata includes process artifact path" "PYTHONPATH='$ROOT/scripts' python3 -c 'from adlc_runtime.metadata import COMMAND_METADATA; assert COMMAND_METADATA[\"process-artifact-path\"][\"mcp_name\"] == \"adlc_process_artifact_path\"'"
assert "mcp-tools exposes optional beads status preflight" "'$ROOT/bin/adlc' mcp-tools --json | jq -e 'any(.tools[]; .name == \"adlc_beads_status\")' >/dev/null"
assert "mcp-tools exposes PR hygiene scan" "'$ROOT/bin/adlc' mcp-tools --json | jq -e 'any(.tools[]; .name == \"adlc_pr_hygiene_scan\" and .inputSchema.properties.waiver.type == \"array\")' >/dev/null"
assert "mcp-tools exposes process artifact path helper" "'$ROOT/bin/adlc' mcp-tools --json | jq -e 'any(.tools[]; .name == \"adlc_process_artifact_path\" and .inputSchema.properties.artifact_type.enum[0] == \"build-brief\")' >/dev/null"
assert "mcp-tools exposes looper loop design commands" "'$ROOT/bin/adlc' mcp-tools --json | jq -e 'any(.tools[]; .name == \"adlc_looper_status\") and any(.tools[]; .name == \"adlc_loop_design_validate\") and any(.tools[]; .name == \"adlc_loop_contract_from_design\")' >/dev/null"
assert "runtime CI includes public and OS-12 acceptance suites" "PYTHONPATH='$ROOT/scripts' python3 -c 'from adlc_runtime.cli import CI_SUITES, DEFAULT_CI_SUITE_ORDER; assert \"acceptance\" in CI_SUITES; assert \"acceptance\" in DEFAULT_CI_SUITE_ORDER; assert \"os12-acceptance\" in CI_SUITES; assert \"os12-acceptance\" in DEFAULT_CI_SUITE_ORDER'"
assert "README lists canonical ADLC CI command" "rg -q 'bin/adlc ci --json' '$ROOT/README.md'"
assert "README truthfully labels public and OS-12 gate harnesses" "rg -q 'tests/acceptance/run_public_acceptance.sh|provider-free public acceptance' '$ROOT/README.md' && rg -q 'tests/acceptance/run_os12_acceptance.sh|provider-free gate proof' '$ROOT/README.md' && rg -q 'not evidence of one-shot agent execution' '$ROOT/README.md'"
assert "README lists action admission command" "rg -q 'bin/adlc action-admit' '$ROOT/README.md'"
assert "README lists stateful ADLC CLI commands" "rg -q 'run --brief-id|run-phase triage|resume-workflow|emit-work-items' '$ROOT/README.md'"
assert "README lists compound workflow commands" "rg -q 'Compound Preflight|learning_capture|compound-context|docs/solutions' '$ROOT/README.md'"
assert "README lists control-plane dogfood loop" "rg -q 'control-plane-drift-loop|schema-alias drift|human review' '$ROOT/README.md'"
assert "README lists learning and architecture memory commands" "rg -q 'architecture-memory|memory-health|champion-holdout|duplicate primitive' '$ROOT/README.md'"
assert "README lists packaged loop library commands" "rg -q 'loop-library|loop-template-install|ci-triage|skill-champion|packaged loop library' '$ROOT/README.md'"
assert "README lists self-actioning meta-harness command" "rg -q 'meta-harness-plan|Self-Actioning Meta-Harness|bounded self-actioning|dispatch agents' '$ROOT/README.md'"
assert "README lists Looper loop design commands" "rg -q 'looper-status|loop-design-validate|loop-contract-from-design|Loop Design' '$ROOT/README.md'"
assert "loop maturity spec documents Loop Design admission" "rg -q 'Loop Design Admission|loop-design-validate|loop-contract-from-design|Looper-compatible' '$ROOT/docs/specs/loop-system-maturity-audit.md'"
assert "WORKFLOW.dot routes compound preflight before research" "rg -q 'triage -> compound_preflight.*label=\"proceed\"' '$ROOT/WORKFLOW.dot' && rg -q 'compound_preflight -> research.*label=\"proceed\"' '$ROOT/WORKFLOW.dot'"
assert "WORKFLOW.dot routes learning capture before engineer review" "rg -q 'pr_prep -> learning_capture' '$ROOT/WORKFLOW.dot' && rg -q 'learning_capture -> engineer_review.*label=\"pass\"' '$ROOT/WORKFLOW.dot'"
assert "WORKFLOW.md binds executable tool-node run-phase commands" "rg -q 'run-phase compound_preflight|run-phase scaffold|run-phase context_assembly|run-phase qa|run-phase slop_gate|run-phase learning_capture' '$ROOT/WORKFLOW.md'"
assert "executable tool-node spec documents artifacts and fail-closed behavior" "rg -q 'Executable Tool Nodes|tool-node-result|phase_artifacts|missing_verifier_command|missing_tool_binding|action_not_admitted' '$ROOT/docs/specs/executable-tool-nodes.md'"
assert "control-plane drift loop spec documents dogfood repair gates" "rg -q 'Control-Plane Drift Loop|schema-alias drift|action-admit|human review|control-plane drift report' '$ROOT/docs/specs/control-plane-drift-loop.md'"
assert "learning architecture memory spec documents memory gates" "rg -q 'Learning And Architecture Memory|architecture-memory|memory-health|champion-holdout|duplicate primitive|working_set_only_improvement' '$ROOT/docs/specs/learning-architecture-memory.md'"
assert "packaged loop library spec documents install gates" "rg -q 'Packaged Loop Library|loop-template-install|adlc-loop-library|ci-triage|bounded meta-harness' '$ROOT/docs/specs/packaged-loop-library.md'"
assert "self-actioning meta-harness spec documents planning gates" "rg -q 'Self-Actioning Meta-Harness|meta-harness-plan|Work Queue seed|Work Item Sync|dispatch agents|bounded control plane' '$ROOT/docs/specs/self-actioning-meta-harness.md'"
assert "loop template catalog contains seven assisted loop templates" "jq -e '.templates | length == 7 and all(.[]; .autonomy_claim == \"assisted_loop\") and any(.[]; .template_id == \"architecture-debt-discovery\")' '$ROOT/docs/loop-library/catalog.json' >/dev/null"
assert "loop template catalog validates against schema" "'$ROOT/bin/adlc' validate-artifact --schema loop-template-catalog --input '$ROOT/docs/loop-library/catalog.json' --json | jq -e '.valid == true' >/dev/null"
assert "agent-native interface documents compound context" "rg -q 'compound-context|docs/solutions|task-level fingerprints|compound_context' '$ROOT/docs/specs/agent-native-interface.md'"
assert "agent-native interface documents loop MCP commands" "rg -q 'action-admit|loop-test-selection|loop-action-validate|loop-maturity-audit|loop_action_validate|loop_maturity_audit|control_plane_drift_loop|adlc_loop_library' '$ROOT/docs/specs/agent-native-interface.md'"
assert "mcp-tools exposes control-plane dogfood loop" "'$ROOT/bin/adlc' mcp-tools --json | jq -e 'any(.tools[]; .name == \"adlc_control_plane_drift_loop\")' >/dev/null"
assert "mcp-tools exposes learning architecture memory commands" "'$ROOT/bin/adlc' mcp-tools --json | jq -e 'any(.tools[]; .name == \"adlc_architecture_memory\") and any(.tools[]; .name == \"adlc_memory_health\") and any(.tools[]; .name == \"adlc_champion_holdout\")' >/dev/null"
assert "mcp-tools exposes packaged loop library commands" "'$ROOT/bin/adlc' mcp-tools --json | jq -e 'any(.tools[]; .name == \"adlc_loop_library\") and any(.tools[]; .name == \"adlc_loop_template_install\")' >/dev/null"
assert "mcp-tools exposes self-actioning meta-harness planner" "'$ROOT/bin/adlc' mcp-tools --json | jq -e 'any(.tools[]; .name == \"adlc_meta_harness_plan\")' >/dev/null"
assert "mcp-tools exposes convention commands" "'$ROOT/bin/adlc' mcp-tools --json | jq -e 'any(.tools[]; .name == \"adlc_repo_conventions\") and any(.tools[]; .name == \"adlc_convention_scan\" and .inputSchema.properties.build_brief.type == \"string\") and any(.tools[]; .name == \"adlc_feedback_conventions\" and .inputSchema.properties.repo.type == \"string\" and .inputSchema.properties.pr.items.type == \"string\")' >/dev/null"
assert "tool pools bind enforcement to action admission" "rg -q 'action-admit|permission audit trail' '$ROOT/docs/specs/tool-pools.md'"

echo ""
echo "--- Work-Item Reconciliation ---"
assert "work-item reconciliation contract exists" "[ -f '$ROOT/docs/specs/work-item-reconciliation.md' ]"
assert "work-item reconciliation requires read-only audit before mutation" "rg -q 'read-only estate audit' '$ROOT/docs/specs/work-item-reconciliation.md' && rg -q 'Mutate the tracker only after explicit approval' '$ROOT/docs/specs/work-item-reconciliation.md' && rg -q 'proposed_mutations.*empty' '$ROOT/docs/specs/work-item-reconciliation.md'"
assert "work-item reconciliation stays product-neutral" "rg -q 'product-neutral' '$ROOT/docs/specs/work-item-reconciliation.md' && rg -q 'must not embed.*ticket IDs' '$ROOT/docs/specs/work-item-reconciliation.md' && rg -q 'Generic ADLC skills' '$ROOT/docs/specs/work-item-reconciliation.md'"
assert "emitter contract references product-neutral reconciliation" "rg -q 'work-item-reconciliation' '$ROOT/docs/specs/emitter-contract.md' && rg -q 'Generic emitter skills must not embed product-specific tracker IDs' '$ROOT/docs/specs/emitter-contract.md'"

echo ""
echo "--- Socraticode Indexing Contract ---"
assert "Socraticode indexing contract exists" "[ -f '$ROOT/docs/specs/socraticode-indexing.md' ]"
assert "Socraticode contract locks coverage threshold and source set" "rg -q 'coverage = indexed_contract_files / eligible_contract_files|>= 95%|eligible contract files' '$ROOT/docs/specs/socraticode-indexing.md'"
assert "Socraticode contract names required MCP operations" "rg -q 'codebase_index|codebase_status|codebase_search|codebase_symbols|codebase_symbol|codebase_graph_stats' '$ROOT/docs/specs/socraticode-indexing.md'"
assert "Socraticode contract protects local snapshots from validation mutation" "rg -q 'codedb\\.snapshot|must not be edited|Snapshot contamination' '$ROOT/docs/specs/socraticode-indexing.md'"
assert "Socraticode contract proves ADLC readiness symbols resolve" "rg -q 'compute_readiness_report|normalized_work_item_payload|emit_work_items_payload|linear-ticket-creation|agent-native-interface' '$ROOT/docs/specs/socraticode-indexing.md'"

echo ""
echo "--- Truthfulness ---"
assert "setup script does not hardcode 22 skills" "! rg -q '22 skills' '$ROOT/setup.sh'"
assert "platform CLAUDE doc does not hardcode 22 skills" "! rg -q '22 skills' '$ROOT/platform/CLAUDE.md'"
assert "platform AGENTS doc does not hardcode 22 skills" "! rg -q '22 injectable skills|22 skills' '$ROOT/platform/AGENTS.md'"
assert "setup test does not expect 22 skills" "! rg -q \"'22'|22 skills\" '$ROOT/tests/test_setup.sh'"
assert "README avoids stale headline inventory claim" "! rg -q '^11 agents\\. 34 skills\\.' '$ROOT/README.md'"
assert "platform CLAUDE doc avoids RED/GREEN/REFACTOR" "! rg -q 'RED/GREEN/REFACTOR' '$ROOT/platform/CLAUDE.md'"
assert "agents antigravity doc avoids RED/GREEN/REFACTOR" "! rg -q 'RED/GREEN/REFACTOR' '$ROOT/platform/agents-antigravity.md'"
assert "workflow diagram uses verifier-led wording" "rg -q 'Verifier-led execution|Author Failing Tests / Reproducers|Tests / Reproducers / Failing Commands' '$ROOT/WORKFLOW.dot'"
assert "idempotency keys cover GitHub" "rg -q 'GitHub Issue Creation' '$ROOT/docs/specs/idempotency-keys.md'"
assert "idempotency keys cover Linear" "rg -q 'Linear Ticket Creation' '$ROOT/docs/specs/idempotency-keys.md'"
assert "idempotency keys cover Notion" "rg -q 'Notion Decomposition' '$ROOT/docs/specs/idempotency-keys.md'"

echo ""
echo "--- Issue Benchmark ---"
assert "issue set contains eighteen benchmark cases" "jq -e '.cases | length == 18' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "issue set covers build_validation" "jq -e '.cases[] | select(.expected_manifest.task_classification==\"build_validation\")' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "issue set covers lint_cleanup" "jq -e '.cases[] | select(.expected_manifest.task_classification==\"lint_cleanup\")' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "issue set covers bugfix" "jq -e '.cases[] | select(.expected_manifest.task_classification==\"bugfix\")' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "issue set covers feature" "jq -e '.cases[] | select(.expected_manifest.task_classification==\"feature\")' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "issue set covers security-sensitive work" "jq -e '.cases[] | select(.expected_manifest.task_classification==\"security\")' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "build validation suppresses security and observability" "jq -e '.cases[] | select(.id==\"CASE-001\") | (.expected_manifest.section_policy | any(.section_name==\"5_security_review\" and .status==\"suppressed\")) and (.expected_manifest.section_policy | any(.section_name==\"6_observability_slo\" and .status==\"suppressed\"))' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "lint cleanup uses command verifier" "jq -e '.cases[] | select(.id==\"CASE-002\") | .expected_manifest.verification_spec.primary_verifier.type == \"command\"' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "bugfix case flags contamination" "jq -e '.cases[] | select(.id==\"CASE-003\") | (.expected_manifest.contamination.flags | index(\"unsupported_claim\")) != null' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "security feature activates security review" "jq -e '.cases[] | select(.id==\"CASE-005\") | (.expected_manifest.section_policy | any(.section_name==\"5_security_review\" and .status==\"active\"))' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "issue set covers convention auditor routing" "jq -e '.cases[] | select(.id==\"CASE-008\") | .expected_manifest.repo_conventions.status == \"extracted\" and (.expected_stage_outputs.council_personas.overlays | index(\"convention_auditor\")) != null' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"

echo ""
echo "═══════════════════════════════════════"
printf 'Results: %b%s passed%b, %b%s failed%b, %s total\n' "$GREEN" "$PASS" "$NC" "$RED" "$FAIL" "$NC" "$TOTAL"
echo "═══════════════════════════════════════"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
