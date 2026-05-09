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

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
mkdir -p "$tmp_dir/workflow" "$tmp_dir/emitter"

echo "ADLC CLI Tests"
echo "Root: $ROOT"
echo ""

echo "--- Discovery ---"
assert "CLI wrapper exists and is executable" "[ -x '$ROOT/bin/adlc' ]"
assert "list-agents emits JSON with planner" "'$ROOT/bin/adlc' list-agents --json | jq -e '.count >= 11 and any(.agents[]; .name == \"planner\" and .dag_node == \"plan\")' >/dev/null"
assert "list-phases emits workflow nodes and edges" "'$ROOT/bin/adlc' list-phases --json | jq -e '.count >= 15 and any(.nodes[]; .id == \"plan\" and .type == \"agent\") and any(.edges[]; .from == \"plan\" and .to == \"plan_review\")' >/dev/null"
assert "list-phases emits readable text" "'$ROOT/bin/adlc' list-phases | rg -q '^plan[[:space:]]+agent[[:space:]]+planner'"

echo ""
echo "--- Schema Validation ---"
assert "validate-artifact accepts smoke build brief" "'$ROOT/bin/adlc' validate-artifact --schema build-brief --input '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
jq 'del(.adlc_mode)' "$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json" > "$tmp_dir/invalid-build-brief.json"
assert "validate-artifact rejects missing required field" "if '$ROOT/bin/adlc' validate-artifact --schema build-brief --input '$tmp_dir/invalid-build-brief.json' --json >'$tmp_dir/invalid-result.json' 2>/dev/null; then false; else jq -e '.valid == false and any(.errors[]; contains(\"adlc_mode\"))' '$tmp_dir/invalid-result.json' >/dev/null; fi"

echo ""
echo "--- Workflow Runner ---"
assert "run dry-run creates workflow state and advances start to triage" "'$ROOT/bin/adlc' run --brief-id CLI-WF --workspace '$tmp_dir/workflow' --dry-run --json | jq -e '.state.brief_id == \"CLI-WF\" and .state.phase == \"triage\" and .state.status == \"planned\" and (.state.checkpoint.history | length) == 1' >/dev/null"
assert "run-phase dry-run advances triage to research" "'$ROOT/bin/adlc' run-phase --workspace '$tmp_dir/workflow' --dry-run --json | jq -e '.state.phase == \"research\" and .state.status == \"planned\" and (.state.checkpoint.history[-1].phase == \"triage\")' >/dev/null"
assert "resume-workflow increments resume count and reports next action" "'$ROOT/bin/adlc' resume-workflow --workspace '$tmp_dir/workflow' --json | jq -e '.state.resume_count == 1 and .next_action.phase == \"research\" and .next_action.runnable == true' >/dev/null"
assert "workflow state validates against schema" "'$ROOT/bin/adlc' validate-artifact --schema workflow-state --input '$tmp_dir/workflow/.adlc/workflow_state.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"

echo ""
echo "--- Work-Item Emitters ---"
provider="$tmp_dir/provider.sh"
cat > "$provider" <<'SH'
#!/usr/bin/env bash
jq '{status:"completed", artifact_count:(.artifacts | length), artifacts:(.artifacts | map({idempotency_key, artifact_id: ("LIN-" + .id), artifact_ref: ("linear://LIN-" + .id)}))}'
SH
chmod +x "$provider"
partial_provider="$tmp_dir/partial-provider.sh"
cat > "$partial_provider" <<'SH'
#!/usr/bin/env bash
jq '{status:"completed", artifacts:(.artifacts | map(if .id == "SMOKE_FEATURE_SCOREBOARD" then {idempotency_key, status:"failed", error:"boom"} else {idempotency_key, status:"completed", artifact_id: ("LIN-" + .id), artifact_ref: ("linear://LIN-" + .id)} end))}'
SH
chmod +x "$partial_provider"
failed_provider="$tmp_dir/failed-provider.sh"
cat > "$failed_provider" <<'SH'
#!/usr/bin/env bash
jq '{status:"failed", artifacts:(.artifacts | map(if .id == "SMOKE_FEATURE_SCOREBOARD" then {idempotency_key, status:"failed", error:"boom"} else {idempotency_key, status:"completed", artifact_id: ("LIN-" + .id), artifact_ref: ("linear://LIN-" + .id)} end))}'
SH
chmod +x "$failed_provider"
assert "emit-work-items dry-run preserves ADLC task contracts" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --dry-run --json | jq -e '.dry_run == true and (.artifacts | length) >= 2 and all(.artifacts[]; (.artifact_type | length) > 0 and (.decision_contract | type) == \"object\" and (.verification_spec | type) == \"object\" and (.idempotency_key | contains(\":linear:\")))' >/dev/null"
assert "emit-work-items dry-run readiness report is ready" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --dry-run --json | jq -e '.readiness_report.status == \"ready\" and .readiness_report.totals.tasks >= 3' >/dev/null"
assert "emit-work-items preserves work_item_metadata in normalized artifacts" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --dry-run --json | jq -e 'any(.artifacts[]; .area == \"backend\" and .phase_label == \"coding\" and .target_project == \"smoke\" and (.labels | index(\"smoke\")) >= 0 and (.external_refs | index(\"EXT-1\")) >= 0)' >/dev/null"
printf '%s\n' '{"coding":"smoke"}' > "$tmp_dir/phase-project-map.json"
assert "emit-work-items phase-project map accepts matching metadata" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --dry-run --require-ready --phase-project-map '$tmp_dir/phase-project-map.json' --json | jq -e '.readiness_report.status == \"ready\"' >/dev/null"
assert "emit-work-items phase-project map blocks mismatched metadata" "if '$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --dry-run --require-ready --phase-project-map '{\"coding\":\"not-smoke\"}' --json >'$tmp_dir/invalid-phase-map.json' 2>/dev/null; then false; else true; fi"
jq '.enterprise_readiness_contract.validation_tasks = ["SMOKE_BUGFIX_AVERAGE"]' "$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json" > "$tmp_dir/invalid-brief.json"
assert "emit-work-items --require-ready fails on invalid validation task reference" "if '$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/invalid-brief.json' --dry-run --require-ready --json >'$tmp_dir/invalid-ready.json' 2>/dev/null; then false; else true; fi"
jq '.sections."8_task_tickets"[1].dependencies = ["GOV-ALIAS"]' "$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json" > "$tmp_dir/alias-brief.json"
guard_provider="$tmp_dir/guard-provider.sh"
cat > "$guard_provider" <<SH
#!/usr/bin/env bash
touch "$tmp_dir/provider-called"
printf '{"status":"completed"}\n'
SH
chmod +x "$guard_provider"
assert "emit-work-items readiness blocks unresolved aliases before provider mutation" "if '$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/alias-brief.json' --workspace '$tmp_dir/emitter' --allow-mutation --provider-command '$guard_provider' --require-ready --json >'$tmp_dir/alias-result.json' 2>/dev/null; then false; else [ ! -f '$tmp_dir/provider-called' ]; fi"
mkdir -p "$tmp_dir/external-state/.adlc"
cat > "$tmp_dir/external-state/.adlc/workflow_state.json" <<'JSON'
{"brief_id":"SMOKE-BRIEF-FEATURE-BUGFIX","session_id":"adlc-test","phase":"pr_prep","status":"planned","step":"ready","started_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z","resume_count":0,"checkpoint":{"workspace":"/tmp","history":[]},"side_effects":[{"idempotency_key":"SMOKE-BRIEF-FEATURE-BUGFIX:linear:EXT-DONE:upsert","tool_name":"linear-work-item-emitter","operation":"upsert_artifact","status":"completed","artifact_id":"EXT-DONE","artifact_ref":"linear://EXT-DONE","timestamp":"2026-01-01T00:00:00Z"}]}
JSON
jq '.sections."8_task_tickets"[1].dependencies = ["EXT-DONE"]' "$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json" > "$tmp_dir/external-dep-brief.json"
assert "emit-work-items resolves dependencies to terminal emitted artifact ids" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/external-dep-brief.json' --workspace '$tmp_dir/external-state' --dry-run --require-ready --json | jq -e '.readiness_report.status == \"ready\" and any(.dependency_links[]; .from == \"EXT-DONE\" and .to == \"SMOKE_FEATURE_SCOREBOARD\" and .type == \"blocks\")' >/dev/null"
mkdir -p "$tmp_dir/unrelated-state/.adlc"
cat > "$tmp_dir/unrelated-state/.adlc/workflow_state.json" <<'JSON'
{"brief_id":"SMOKE-BRIEF-FEATURE-BUGFIX","session_id":"adlc-test","phase":"pr_prep","status":"planned","step":"ready","started_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z","resume_count":0,"checkpoint":{"workspace":"/tmp","history":[]},"side_effects":[{"idempotency_key":"OTHER-BRIEF:linear:THING:upsert","tool_name":"linear-work-item-emitter","operation":"upsert_artifact","status":"completed","artifact_id":"WRONG_BRIEF","artifact_ref":"linear://WRONG_BRIEF","timestamp":"2026-01-01T00:00:00Z"},{"idempotency_key":"SMOKE-BRIEF-FEATURE-BUGFIX:linear:THING:upsert","tool_name":"github-work-item-emitter","operation":"upsert_artifact","status":"completed","artifact_id":"WRONG_TOOL","artifact_ref":"linear://WRONG_TOOL","timestamp":"2026-01-01T00:00:00Z"},{"idempotency_key":"SMOKE-BRIEF-FEATURE-BUGFIX:linear:THING:upsert","tool_name":"linear-work-item-emitter","operation":"delete_artifact","status":"completed","artifact_id":"WRONG_OP","artifact_ref":"linear://WRONG_OP","timestamp":"2026-01-01T00:00:00Z"}]}
JSON
assert "emit-work-items ignores unrelated terminal side effects for dependency readiness" "for alias in WRONG_BRIEF WRONG_TOOL WRONG_OP; do jq --arg alias \"\$alias\" '.sections.\"8_task_tickets\"[1].dependencies = [\$alias]' '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' > '$tmp_dir/unrelated-dep.json'; if '$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/unrelated-dep.json' --workspace '$tmp_dir/unrelated-state' --dry-run --require-ready --json >'$tmp_dir/unrelated-result.json' 2>/dev/null; then exit 1; fi; done"
assert "XIA remediation decomposition emits ready Linear work items" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/docs/build-briefs/xia-adlc-remediation.json' --dry-run --require-ready --phase-project-map '{\"phase:m2\":\"M2: Hosted Foundation\",\"phase:m4\":\"M4: Policy Graduation\"}' --json | jq -e '.readiness_report.status == \"ready\" and (.artifacts | length) == 6' >/dev/null"
assert "emit-work-items preserves decision gates and validation tasks as first-class artifacts" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/docs/build-briefs/xia-adlc-remediation.json' --dry-run --require-ready --phase-project-map '{\"phase:m2\":\"M2: Hosted Foundation\",\"phase:m4\":\"M4: Policy Graduation\"}' --json | jq -e '. as \$root | any(.artifacts[]; .id == \"XIA-DEC-BLOCK\" and .artifact_type == \"decision_gate\" and .blocks_implementation == true and .decision_contract.status == \"unresolved\") and any(.dependency_links[]; .from == \"XIA-DEC-BLOCK\" and .to == \"XIA-ADLC-READY\" and .type == \"blocks\") and (.enterprise_readiness_contract.validation_tasks as \$tasks | all(\$tasks[]; . as \$id | any(\$root.artifacts[]; .id == \$id and .artifact_type == \"validation_task\" and .executable == true)))' >/dev/null"
assert "emit-work-items mutation uses provider hook and records side effects" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --workspace '$tmp_dir/emitter' --allow-mutation --provider-command '$provider' --json | jq -e '.dry_run == false and .provider_result.artifact_count == (.artifacts | length) and (.state.side_effects | length) >= (.artifacts | length)' >/dev/null"
assert "emit-work-items mutation records provider-returned target metadata" "jq -e 'any(.side_effects[]; .idempotency_key == \"SMOKE-BRIEF-FEATURE-BUGFIX:linear:SMOKE_BUGFIX_AVERAGE:upsert\" and .artifact_id == \"LIN-SMOKE_BUGFIX_AVERAGE\" and .artifact_ref == \"linear://LIN-SMOKE_BUGFIX_AVERAGE\")' '$tmp_dir/emitter/.adlc/workflow_state.json' >/dev/null"
jq '.sections."8_task_tickets"[1].dependencies = ["LIN-SMOKE_BUGFIX_AVERAGE"]' "$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json" > "$tmp_dir/provider-dep-brief.json"
assert "emit-work-items resolves dependencies to provider-returned target artifact ids" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/provider-dep-brief.json' --workspace '$tmp_dir/emitter' --dry-run --require-ready --json | jq -e '.readiness_report.status == \"ready\" and any(.dependency_links[]; .from == \"LIN-SMOKE_BUGFIX_AVERAGE\" and .to == \"SMOKE_FEATURE_SCOREBOARD\" and .type == \"blocks\")' >/dev/null"
assert "emit-work-items surfaces per-artifact provider failures" "if '$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --workspace '$tmp_dir/partial-emitter' --allow-mutation --provider-command '$partial_provider' --json >'$tmp_dir/partial-result.json' 2>/dev/null; then false; else jq -e '.provider_result.status == \"failed\" and .provider_result.stop_reason == \"external_mutation_partial\" and any(.state.side_effects[]; .idempotency_key == \"SMOKE-BRIEF-FEATURE-BUGFIX:linear:SMOKE_FEATURE_SCOREBOARD:upsert\" and .status == \"failed\")' '$tmp_dir/partial-result.json' >/dev/null; fi"
assert "emit-work-items preserves partial stop reason on failed provider batches" "if '$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --workspace '$tmp_dir/failed-emitter' --allow-mutation --provider-command '$failed_provider' --json >'$tmp_dir/failed-result.json' 2>/dev/null; then false; else jq -e '.provider_result.status == \"failed\" and .provider_result.stop_reason == \"external_mutation_partial\" and any(.state.side_effects[]; .idempotency_key == \"SMOKE-BRIEF-FEATURE-BUGFIX:linear:SMOKE_FEATURE_SCOREBOARD:upsert\" and .status == \"failed\")' '$tmp_dir/failed-result.json' >/dev/null; fi"

echo ""
echo "--- MCP Wrapper ---"
assert "mcp-tools emits MCP tool declarations" "'$ROOT/bin/adlc' mcp-tools --json | jq -e '(.tools | length) >= 6 and any(.tools[]; .name == \"adlc_validate_artifact\" and (.inputSchema.required | index(\"schema\"))) and any(.tools[]; .name == \"adlc_run_phase\") and any(.tools[]; .name == \"adlc_emit_work_items\")' >/dev/null"
assert "mcp-serve handles initialize and tools/list" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"0\"}}}' '{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}' | '$ROOT/bin/adlc' mcp-serve | jq -s -e '.[0].result.capabilities.tools.listChanged == false and any(.[1].result.tools[]; .name == \"adlc_list_agents\")' >/dev/null"
assert "mcp-serve calls adlc_list_agents" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_list_agents\",\"arguments\":{}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.count >= 11' >/dev/null"

echo ""
printf 'Results: %b%s passed%b, %b%s failed%b, %s total\n' "$GREEN" "$PASS" "$NC" "$RED" "$FAIL" "$NC" "$TOTAL"

if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
