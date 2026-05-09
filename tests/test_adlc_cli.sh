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
jq '{status:"completed", artifact_count:(.artifacts | length)}'
SH
chmod +x "$provider"
assert "emit-work-items dry-run preserves ADLC task contracts" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --dry-run --json | jq -e '.dry_run == true and (.artifacts | length) >= 2 and all(.artifacts[]; (.artifact_type | length) > 0 and (.decision_contract | type) == \"object\" and (.verification_spec | type) == \"object\" and (.idempotency_key | contains(\":linear:\")))' >/dev/null"
assert "emit-work-items dry-run readiness report is ready" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --dry-run --json | jq -e '.readiness_report.status == \"ready\" and .readiness_report.totals.tasks >= 3' >/dev/null"
assert "emit-work-items preserves work_item_metadata in normalized artifacts" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --dry-run --json | jq -e 'any(.artifacts[]; .area == \"backend\" and .phase_label == \"coding\" and .target_project == \"smoke\" and (.labels | index(\"smoke\")) >= 0 and (.external_refs | index(\"EXT-1\")) >= 0)' >/dev/null"
printf '%s\n' '{"coding":"smoke"}' > "$tmp_dir/phase-project-map.json"
assert "emit-work-items phase-project map accepts matching metadata" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --dry-run --require-ready --phase-project-map '$tmp_dir/phase-project-map.json' --json | jq -e '.readiness_report.status == \"ready\"' >/dev/null"
assert "emit-work-items phase-project map blocks mismatched metadata" "if '$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --dry-run --require-ready --phase-project-map '{\"coding\":\"not-smoke\"}' --json >'$tmp_dir/invalid-phase-map.json' 2>/dev/null; then false; else true; fi"
jq '.enterprise_readiness_contract.validation_tasks = ["SMOKE_BUGFIX_AVERAGE"]' "$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json" > "$tmp_dir/invalid-brief.json"
assert "emit-work-items --require-ready fails on invalid validation task reference" "if '$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/invalid-brief.json' --dry-run --require-ready --json >'$tmp_dir/invalid-ready.json' 2>/dev/null; then false; else true; fi"
assert "XIA remediation decomposition emits ready Linear work items" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/docs/build-briefs/xia-adlc-remediation.json' --dry-run --require-ready --phase-project-map '{\"phase:m2\":\"M2: Hosted Foundation\",\"phase:m4\":\"M4: Policy Graduation\"}' --json | jq -e '.readiness_report.status == \"ready\" and (.artifacts | length) == 6' >/dev/null"
assert "emit-work-items mutation uses provider hook and records side effects" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --workspace '$tmp_dir/emitter' --allow-mutation --provider-command '$provider' --json | jq -e '.dry_run == false and .provider_result.artifact_count == (.artifacts | length) and (.state.side_effects | length) >= (.artifacts | length)' >/dev/null"

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
