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
mkdir -p "$tmp_dir/workflow" "$tmp_dir/emitter" "$tmp_dir/no-solutions"

echo "ADLC CLI Tests"
echo "Root: $ROOT"
echo ""

echo "--- Discovery ---"
assert "CLI wrapper exists and is executable" "[ -x '$ROOT/bin/adlc' ]"
assert "list-agents emits JSON with planner" "'$ROOT/bin/adlc' list-agents --json | jq -e '.count >= 11 and any(.agents[]; .name == \"planner\" and .dag_node == \"plan\")' >/dev/null"
assert "list-phases emits workflow nodes and edges" "'$ROOT/bin/adlc' list-phases --json | jq -e '.count >= 17 and any(.nodes[]; .id == \"compound_preflight\" and .type == \"tool\") and any(.nodes[]; .id == \"learning_capture\" and .type == \"tool\") and any(.edges[]; .from == \"triage\" and .to == \"compound_preflight\") and any(.edges[]; .from == \"compound_preflight\" and .to == \"research\")' >/dev/null"
assert "list-phases emits readable text" "'$ROOT/bin/adlc' list-phases | rg -q '^plan[[:space:]]+agent[[:space:]]+planner'"

echo ""
echo "--- Schema Validation ---"
assert "validate-artifact accepts smoke build brief" "'$ROOT/bin/adlc' validate-artifact --schema build-brief --input '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts loop contract fixture" "'$ROOT/bin/adlc' validate-artifact --schema loop-contract --input '$ROOT/tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts loop action fixture" "'$ROOT/bin/adlc' validate-artifact --schema loop-action --input '$ROOT/tests/fixtures/loop_maturity/valid-loop-action.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts loop test result fixture" "'$ROOT/bin/adlc' validate-artifact --schema loop-test-result --input '$ROOT/tests/fixtures/loop_maturity/test-results-complete-required.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts loop maturity report fixture" "'$ROOT/bin/adlc' validate-artifact --schema loop-maturity-report --input '$ROOT/tests/fixtures/loop_maturity/assisted-loop-report.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts token budget fixture" "'$ROOT/bin/adlc' validate-artifact --schema token-budget --input '$ROOT/tests/fixtures/loop_maturity/token-budget-healthy.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts budgeted loop contract fixture" "'$ROOT/bin/adlc' validate-artifact --schema loop-contract --input '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-contract.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts budgeted loop action fixture" "'$ROOT/bin/adlc' validate-artifact --schema loop-action --input '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-action.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts budgeted loop maturity report fixture" "'$ROOT/bin/adlc' validate-artifact --schema loop-maturity-report --input '$ROOT/tests/fixtures/loop_maturity/budgeted-maturity-report.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts work queue fixture" "'$ROOT/bin/adlc' validate-artifact --schema work-queue --input '$ROOT/tests/fixtures/work_queue/valid-queue.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts work-item sync fixture" "'$ROOT/bin/adlc' validate-artifact --schema work-item-sync --input '$ROOT/tests/fixtures/tracker_sync/run-update.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts tool-node result fixture" "'$ROOT/bin/adlc' validate-artifact --schema tool-node-result --input '$ROOT/tests/fixtures/tool_node/valid-qa-result.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts loop template catalog" "'$ROOT/bin/adlc' validate-artifact --schema loop-template-catalog --input '$ROOT/docs/loop-library/catalog.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts loop design fixture" "'$ROOT/bin/adlc' validate-artifact --schema loop-design --input '$ROOT/tests/fixtures/loop_design/valid-looper-design.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts Kitchen Loop spec surface fixture" "'$ROOT/bin/adlc' validate-artifact --schema spec-surface --input '$ROOT/tests/fixtures/kitchen_loop/valid-spec-surface.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts Kitchen Loop scenario coverage fixture" "'$ROOT/bin/adlc' validate-artifact --schema scenario-coverage-plan --input '$ROOT/tests/fixtures/kitchen_loop/valid-scenario-coverage-plan.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts Kitchen Loop regression oracle fixture" "'$ROOT/bin/adlc' validate-artifact --schema regression-oracle --input '$ROOT/tests/fixtures/kitchen_loop/valid-regression-oracle.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact accepts Kitchen Loop drift gate fixture" "'$ROOT/bin/adlc' validate-artifact --schema drift-gate-report --input '$ROOT/tests/fixtures/kitchen_loop/valid-drift-gate-report.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "Ponytail scenario fixture parses" "jq empty '$ROOT/tests/fixtures/ponytail/scenarios.json' >/dev/null 2>&1"
assert "schema aliases include control-plane drift report" "'$ROOT/bin/adlc' health-check --json | jq -e '.status == \"pass\" and any(.checks[]; .name == \"schemas\" and .status == \"pass\")' >/dev/null"
cat > "$tmp_dir/tool-registry.json" <<'JSON'
{"version":"1.0.0","default_policy":"deny","tools":[{"name":"Read","description":"Read files","inputSchema":{},"side_effect_profile":"read_only","permission_tier":"unrestricted","available_phases":["phase_0_codebase_research"]}]}
JSON
assert "validate-artifact accepts tool registry fixture" "'$ROOT/bin/adlc' validate-artifact --schema tool-registry --input '$tmp_dir/tool-registry.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
cat > "$tmp_dir/permission-audit-trail.json" <<'JSON'
{"session_id":"adlc-test","brief_id":"BRF-TEST","entries":[{"decision_id":"decision-1","tool_name":"Read","action":"read_file","tier":"unrestricted","decision":"approved","reason":"read-only phase","decided_by":"policy","timestamp":"2026-01-01T00:00:00Z","session_id":"adlc-test","brief_id":"BRF-TEST"}],"denial_summary":{"count":0,"patterns":[]}}
JSON
assert "validate-artifact accepts permission audit trail fixture" "'$ROOT/bin/adlc' validate-artifact --schema permission-audit-trail --input '$tmp_dir/permission-audit-trail.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "validate-artifact rejects invalid loop contract" "if '$ROOT/bin/adlc' validate-artifact --schema loop-contract --input '$ROOT/tests/fixtures/loop_maturity/invalid-missing-test-floor.json' --json >'$tmp_dir/invalid-loop-contract.json' 2>/dev/null; then false; else jq -e '.valid == false and any(.errors[]; contains(\"mandatory_floor\"))' '$tmp_dir/invalid-loop-contract.json' >/dev/null; fi"
assert "validate-artifact rejects work-item sync missing run identity" "if '$ROOT/bin/adlc' validate-artifact --schema work-item-sync --input '$ROOT/tests/fixtures/tracker_sync/invalid-missing-run-identity.json' --json >'$tmp_dir/invalid-work-item-sync.json' 2>/dev/null; then false; else jq -e '.valid == false and any(.errors[]; contains(\"run_id\")) and any(.errors[]; contains(\"session_id\"))' '$tmp_dir/invalid-work-item-sync.json' >/dev/null; fi"
assert "validate-artifact rejects work queue missing task id" "if '$ROOT/bin/adlc' validate-artifact --schema work-queue --input '$ROOT/tests/fixtures/work_queue/invalid-missing-task-id.json' --json >'$tmp_dir/invalid-work-queue-task-id.json' 2>/dev/null; then false; else jq -e '.valid == false and any(.errors[]; contains(\"task_id\"))' '$tmp_dir/invalid-work-queue-task-id.json' >/dev/null; fi"
assert "validate-artifact rejects work queue invalid status" "if '$ROOT/bin/adlc' validate-artifact --schema work-queue --input '$ROOT/tests/fixtures/work_queue/invalid-status.json' --json >'$tmp_dir/invalid-work-queue-status.json' 2>/dev/null; then false; else jq -e '.valid == false and any(.errors[]; contains(\"maybe\"))' '$tmp_dir/invalid-work-queue-status.json' >/dev/null; fi"
assert "validate-artifact rejects work queue invalid path owner" "if '$ROOT/bin/adlc' validate-artifact --schema work-queue --input '$ROOT/tests/fixtures/work_queue/invalid-path-owner.json' --json >'$tmp_dir/invalid-work-queue-path.json' 2>/dev/null; then false; else jq -e '.valid == false and any(.errors[]; contains(\"path\"))' '$tmp_dir/invalid-work-queue-path.json' >/dev/null; fi"
assert "validate-artifact rejects tool-node result missing status" "if '$ROOT/bin/adlc' validate-artifact --schema tool-node-result --input '$ROOT/tests/fixtures/tool_node/invalid-missing-status.json' --json >'$tmp_dir/invalid-tool-node-result.json' 2>/dev/null; then false; else jq -e '.valid == false and any(.errors[]; contains(\"status\"))' '$tmp_dir/invalid-tool-node-result.json' >/dev/null; fi"
assert "validate-artifact rejects Kitchen Loop missing oracle surface" "if '$ROOT/bin/adlc' validate-artifact --schema spec-surface --input '$ROOT/tests/fixtures/kitchen_loop/invalid-spec-surface-missing-oracle.json' --json >'$tmp_dir/invalid-kl-surface.json' 2>/dev/null; then false; else jq -e '.valid == false and any(.errors[]; contains(\"oracle_refs\"))' '$tmp_dir/invalid-kl-surface.json' >/dev/null; fi"
assert "validate-artifact rejects Kitchen Loop unbounded scenario plan" "if '$ROOT/bin/adlc' validate-artifact --schema scenario-coverage-plan --input '$ROOT/tests/fixtures/kitchen_loop/invalid-scenario-coverage-unbounded.json' --json >'$tmp_dir/invalid-kl-plan.json' 2>/dev/null; then false; else jq -e '.valid == false and any(.errors[]; contains(\"bounded\"))' '$tmp_dir/invalid-kl-plan.json' >/dev/null; fi"
assert "validate-artifact rejects Kitchen Loop weak regression oracle" "if '$ROOT/bin/adlc' validate-artifact --schema regression-oracle --input '$ROOT/tests/fixtures/kitchen_loop/invalid-regression-oracle-weak-ground-truth.json' --json >'$tmp_dir/invalid-kl-oracle.json' 2>/dev/null; then false; else jq -e '.valid == false and any(.errors[]; contains(\"independent\"))' '$tmp_dir/invalid-kl-oracle.json' >/dev/null; fi"
assert "validate-artifact rejects Kitchen Loop drift gate missing status" "if '$ROOT/bin/adlc' validate-artifact --schema drift-gate-report --input '$ROOT/tests/fixtures/kitchen_loop/invalid-drift-gate-missing-status.json' --json >'$tmp_dir/invalid-kl-drift.json' 2>/dev/null; then false; else jq -e '.valid == false and any(.errors[]; contains(\"status\"))' '$tmp_dir/invalid-kl-drift.json' >/dev/null; fi"
jq 'del(.adlc_mode)' "$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json" > "$tmp_dir/invalid-build-brief.json"
assert "validate-artifact rejects missing required field" "if '$ROOT/bin/adlc' validate-artifact --schema build-brief --input '$tmp_dir/invalid-build-brief.json' --json >'$tmp_dir/invalid-result.json' 2>/dev/null; then false; else jq -e '.valid == false and any(.errors[]; contains(\"adlc_mode\"))' '$tmp_dir/invalid-result.json' >/dev/null; fi"

echo ""
echo "--- Kitchen Loop Coverage Admission ---"
assert "coverage-surface-validate passes valid spec surface" "'$ROOT/bin/adlc' coverage-surface-validate --input '$ROOT/tests/fixtures/kitchen_loop/valid-spec-surface.json' --json | jq -e '.status == \"pass\" and .summary.supported_combinations == 2 and .summary.oracle_refs == 1' >/dev/null"
assert "coverage-surface-validate blocks missing oracle surface" "if '$ROOT/bin/adlc' coverage-surface-validate --input '$ROOT/tests/fixtures/kitchen_loop/invalid-spec-surface-missing-oracle.json' --json >'$tmp_dir/kl-surface-blocked.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and any(.issues[]; .rule == \"schema\")' '$tmp_dir/kl-surface-blocked.json' >/dev/null; fi"
assert "scenario-coverage-plan passes bounded plan with matching surface" "'$ROOT/bin/adlc' scenario-coverage-plan --input '$ROOT/tests/fixtures/kitchen_loop/valid-scenario-coverage-plan.json' --spec-surface '$ROOT/tests/fixtures/kitchen_loop/valid-spec-surface.json' --json | jq -e '.status == \"pass\" and .summary.coverage.covered == 1 and .summary.coverage.blocked == 1' >/dev/null"
assert "scenario-coverage-plan blocks unbounded generation" "if '$ROOT/bin/adlc' scenario-coverage-plan --input '$ROOT/tests/fixtures/kitchen_loop/invalid-scenario-coverage-unbounded.json' --json >'$tmp_dir/kl-plan-blocked.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and any(.issues[]; .rule == \"schema\" or .rule == \"unbounded_scenario_plan\")' '$tmp_dir/kl-plan-blocked.json' >/dev/null; fi"
assert "regression-oracle-validate passes independent oracle" "'$ROOT/bin/adlc' regression-oracle-validate --input '$ROOT/tests/fixtures/kitchen_loop/valid-regression-oracle.json' --json | jq -e '.status == \"pass\" and .summary.ground_truth_strength == \"independent\" and .summary.anti_canaries == 1' >/dev/null"
assert "regression-oracle-validate blocks weak ground truth" "if '$ROOT/bin/adlc' regression-oracle-validate --input '$ROOT/tests/fixtures/kitchen_loop/invalid-regression-oracle-weak-ground-truth.json' --json >'$tmp_dir/kl-oracle-blocked.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and any(.issues[]; .rule == \"schema\" or .rule == \"weak_ground_truth\")' '$tmp_dir/kl-oracle-blocked.json' >/dev/null; fi"
assert "drift-gate-evaluate passes clean drift gate" "'$ROOT/bin/adlc' drift-gate-evaluate --input '$ROOT/tests/fixtures/kitchen_loop/valid-drift-gate-report.json' --json | jq -e '.status == \"pass\" and .gate_status == \"pass\" and .summary.metrics == 2' >/dev/null"
assert "drift-gate-evaluate blocks missing drift status" "if '$ROOT/bin/adlc' drift-gate-evaluate --input '$ROOT/tests/fixtures/kitchen_loop/invalid-drift-gate-missing-status.json' --json >'$tmp_dir/kl-drift-blocked.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and any(.issues[]; .rule == \"schema\")' '$tmp_dir/kl-drift-blocked.json' >/dev/null; fi"

echo ""
echo "--- Ponytail Minimality Admission ---"
assert "ponytail-admit passes ready Build Brief" "'$ROOT/bin/adlc' ponytail-admit --build-brief '$ROOT/docs/build-briefs/xia-adlc-remediation.json' --output '$tmp_dir/ponytail-admission.json' --json | jq -e '.status == \"pass\" and .summary.executable_tasks == 5 and .summary.issues == 0' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema ponytail-admission-report --input '$tmp_dir/ponytail-admission.json' --json | jq -e '.valid == true' >/dev/null"
jq 'del(.sections."8_task_tickets"[0].minimality_contract)' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp_dir/ponytail-missing-contract.json"
assert "ponytail-admit blocks missing minimality contract" "if '$ROOT/bin/adlc' ponytail-admit --build-brief '$tmp_dir/ponytail-missing-contract.json' --json >'$tmp_dir/ponytail-missing-result.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and any(.issues[]; .rule == \"missing_minimality_contract\")' '$tmp_dir/ponytail-missing-result.json' >/dev/null; fi"
assert "emit-work-items require-ready blocks missing Ponytail contract" "if '$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/ponytail-missing-contract.json' --dry-run --require-ready --json >'$tmp_dir/ponytail-readiness-block.json' 2>/dev/null; then false; else true; fi"
assert "emit-work-items preserves Ponytail contract in tickets" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/docs/build-briefs/xia-adlc-remediation.json' --dry-run --require-ready --json | jq -e '.readiness_report.status == \"ready\" and all(.artifacts[]; (.executable == false) or ((.minimality_contract | type) == \"object\" and (.minimality_contract.mode == \"full\")))' >/dev/null"
assert "ponytail-scenario-canary validates three live with/without tasks" "'$ROOT/bin/adlc' ponytail-scenario-canary --output '$tmp_dir/ponytail-canary.json' --json | jq -e '.status == \"pass\" and .summary.scenarios == 3 and .summary.passed == 3 and .summary.without_ponytail_ready == 0 and .summary.with_ponytail_ready == 3 and .summary.scripts_passed == 3 and all(.scenarios[]; .with_ponytail.ticket_inherits_minimality_contract == true and .with_ponytail.lines_of_code <= .without_ponytail.lines_of_code)' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema ponytail-scenario-canary-report --input '$tmp_dir/ponytail-canary.json' --json | jq -e '.valid == true' >/dev/null"

echo ""
echo "--- Compound Context ---"
assert "health-check passes required runtime checks" "'$ROOT/bin/adlc' health-check --json | jq -e '.status == \"pass\" and .summary.failed_required == 0 and any(.checks[]; .name == \"jsonschema\" and .status == \"pass\") and any(.checks[]; .name == \"schemas\" and .status == \"pass\") and any(.checks[]; .name == \"workflow-state-phase-parity\" and .status == \"pass\")' >/dev/null"
assert "ci command runs selectable canonical suites" "'$ROOT/bin/adlc' ci --suite health-check --suite py-compile --json | jq -e '.status == \"pass\" and .summary.total == 2 and .summary.failed == 0 and ([.suites[].name] == [\"health-check\", \"py-compile\"])' >/dev/null"
assert "compound-context no-ops cleanly without learning store" "'$ROOT/bin/adlc' compound-context --workspace '$tmp_dir/no-solutions' --json | jq -e '.contract_version == \"1.0.0\" and .summary.learning_refs == 0 and (.no_op_reasons | index(\"docs/solutions not found\")) != null' >/dev/null"
mkdir -p "$tmp_dir/compound/docs/solutions"
cp "$ROOT/tests/fixtures/learning-entry-knowledge.md" "$tmp_dir/compound/docs/solutions/ref.md"
assert "compound-context emits compact learning refs" "'$ROOT/bin/adlc' compound-context --workspace '$tmp_dir/compound' --input 'compound context learning refs' --json | jq -e '.summary.learning_refs == 1 and (.learning_refs[0].path | endswith(\"/compound/docs/solutions/ref.md\")) and (.learning_refs[0].summary | length) > 0 and (.learning_refs[0] | has(\"verifier\"))' >/dev/null"
assert "compound-context emits Build Brief task and verifier refs" "'$ROOT/bin/adlc' compound-context --workspace '$ROOT' --build-brief '$ROOT/docs/build-briefs/compound-engineering-workflow-integration.json' --json | jq -e '.summary.task_refs == 7 and .summary.verifier_refs == 7 and any(.task_refs[]; .task_id == \"ADLC-CEI-004\")' >/dev/null"

echo ""
echo "--- Workflow Runner ---"
assert "run dry-run creates workflow state with durable identity" "'$ROOT/bin/adlc' run --brief-id CLI-WF --workspace '$tmp_dir/workflow' --dry-run --json | jq -e '.state.brief_id == \"CLI-WF\" and (.state.run_id | startswith(\"adlc-run-\")) and (.state.session_id | startswith(\"adlc-\")) and .state.attempt == 1 and .run_identity.run_id == .state.run_id and .state.phase == \"triage\" and .state.status == \"planned\" and (.state.checkpoint.history | length) == 1' >/dev/null"
workflow_run_id="$(jq -r '.run_id // empty' "$tmp_dir/workflow/.adlc/workflow_state.json" 2>/dev/null || true)"
workflow_session_id="$(jq -r '.session_id // empty' "$tmp_dir/workflow/.adlc/workflow_state.json" 2>/dev/null || true)"
assert "run-phase dry-run persists intent validation human gate" "'$ROOT/bin/adlc' run-phase intent_validation --brief-id CLI-INTENT --workspace '$tmp_dir/intent' --dry-run --json | jq -e '.result == \"awaiting_approval\" and .state.phase == \"intent_validation\" and .state.status == \"awaiting_approval\" and .state.stop_reason == \"human_gate\"' >/dev/null"
assert "resume-workflow preserves human-gate stop reason" "'$ROOT/bin/adlc' resume-workflow --workspace '$tmp_dir/intent' --json >'$tmp_dir/intent-resume.json' && jq -e '.state.stop_reason == \"human_gate\" and .next_action.stop_reason == \"human_gate\" and .state.resume_count == 1 and .state.attempt == 2 and .run_identity.run_id == .state.run_id and .next_action.run_identity.run_id == .state.run_id' '$tmp_dir/intent-resume.json' >/dev/null"
assert "run-phase dry-run advances triage to compound preflight" "'$ROOT/bin/adlc' run-phase --workspace '$tmp_dir/workflow' --dry-run --json | jq -e '.state.phase == \"compound_preflight\" and .state.status == \"planned\" and (.state.checkpoint.history[-1].phase == \"triage\")' >/dev/null"
assert "resume-workflow preserves identity and increments resume metadata" "'$ROOT/bin/adlc' resume-workflow --workspace '$tmp_dir/workflow' --json >'$tmp_dir/resume-1.json' && jq -e --arg run_id '$workflow_run_id' --arg session_id '$workflow_session_id' '.state.run_id == \$run_id and .state.session_id == \$session_id and .state.resume_count == 1 and .state.attempt == 2 and .run_identity.run_id == \$run_id and .next_action.run_identity.run_id == \$run_id and .next_action.phase == \"compound_preflight\" and .next_action.runnable == true and .next_action.task_resume_status.total == 0' '$tmp_dir/resume-1.json' >/dev/null"
assert "tool-node dry-run emits planned artifact without completing phase" "'$ROOT/bin/adlc' run-phase --workspace '$tmp_dir/workflow' --dry-run --json >'$tmp_dir/compound-dry-run.json' && jq -e '.tool_result.status == \"planned\" and .state.phase == \"compound_preflight\" and .state.status == \"planned\" and .state.phase_artifacts[-1].phase == \"compound_preflight\" and .state.phase_artifacts[-1].status == \"planned\"' '$tmp_dir/compound-dry-run.json' >/dev/null"
assert "run-phase executes compound preflight and advances to research" "'$ROOT/bin/adlc' run-phase --workspace '$tmp_dir/workflow' --json | jq -e '.tool_result.status == \"pass\" and .state.phase == \"research\" and .state.status == \"planned\" and (.state.checkpoint.history[-1].phase == \"compound_preflight\")' >/dev/null"
jq '.task_fingerprints = [{"task_id":"SMOKE_FEATURE_SCOREBOARD","input_hash":"abc123","status":"failed","primary_verifier":"pytest tests/test_scoreboard.py","pre_change_status":"failed_expected","post_change_status":"failed","changed_files":["src/scoreboard.py"],"commit":null,"evidence":["pytest failed"]}]' "$tmp_dir/workflow/.adlc/workflow_state.json" > "$tmp_dir/workflow-state-with-fingerprints.json"
mv "$tmp_dir/workflow-state-with-fingerprints.json" "$tmp_dir/workflow/.adlc/workflow_state.json"
assert "second resume preserves identity and reports incomplete task fingerprints" "'$ROOT/bin/adlc' resume-workflow --workspace '$tmp_dir/workflow' --json >'$tmp_dir/resume-2.json' && jq -e --arg run_id '$workflow_run_id' --arg session_id '$workflow_session_id' '.state.run_id == \$run_id and .state.session_id == \$session_id and .state.resume_count == 2 and .state.attempt == 3 and .next_action.task_resume_status.total == 1 and .next_action.task_resume_status.counts.failed == 1 and .next_action.task_resume_status.incomplete[0].task_id == \"SMOKE_FEATURE_SCOREBOARD\"' '$tmp_dir/resume-2.json' >/dev/null"
assert "workflow state validates against schema" "'$ROOT/bin/adlc' validate-artifact --schema workflow-state --input '$tmp_dir/workflow/.adlc/workflow_state.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
cp "$ROOT/tests/fixtures/loop_maturity/workflow-state-control-progress.json" "$tmp_dir/loop-workflow-state.json"
assert "resume-workflow reports loop progress and control state" "'$ROOT/bin/adlc' resume-workflow --state '$tmp_dir/loop-workflow-state.json' --json | jq -e '.next_action.loop_progress.last_progress_signal == \"resolved_missing_required_test\" and .next_action.no_progress_count == 0 and .next_action.control_events[0].event_type == \"steer\" and .next_action.safe_checkpoint.idempotent == true and .next_action.escalation_context.no_progress_after == 2' >/dev/null"
cp "$ROOT/tests/fixtures/loop_maturity/workflow-state-budget-progress.json" "$tmp_dir/loop-workflow-state-budget.json"
assert "resume-workflow reports loop budget status" "'$ROOT/bin/adlc' resume-workflow --state '$tmp_dir/loop-workflow-state-budget.json' --json | jq -e '.next_action.budget_status.status == \"healthy\" and .next_action.budget_status.decision == \"proceed\" and .next_action.budget_status.token_budget_ref == \"tests/fixtures/loop_maturity/token-budget-healthy.json\"' >/dev/null"

echo ""
echo "--- Executable Tool Nodes ---"
assert "run-phase qa dry-run plans verifiers without claiming pass" "'$ROOT/bin/adlc' run-phase qa --brief-id CLI-QA-DRY --workspace '$tmp_dir/tool-qa-dry' --verifier true --dry-run --json | jq -e '.tool_result.status == \"planned\" and .tool_result.dry_run == true and .state.phase == \"qa\" and .state.status == \"planned\" and .state.phase_artifacts[-1].status == \"planned\"' >/dev/null"
assert "run-phase qa executes passing verifier and records artifact" "'$ROOT/bin/adlc' run-phase qa --brief-id CLI-QA-PASS --workspace '$tmp_dir/tool-qa-pass' --verifier true --json | jq -e '.tool_result.status == \"pass\" and .state.phase == \"pr_prep\" and .state.phase_artifacts[-1].phase == \"qa\" and (.tool_result.evidence_refs | length) >= 2' >/dev/null"
assert "run-phase qa fails closed on failing verifier" "if '$ROOT/bin/adlc' run-phase qa --brief-id CLI-QA-FAIL --workspace '$tmp_dir/tool-qa-fail' --verifier false --json >'$tmp_dir/qa-fail.json'; then false; else jq -e '.tool_result.status == \"fail\" and .tool_result.stop_reason == \"verifier_failed\" and .state.status == \"failed\"' '$tmp_dir/qa-fail.json' >/dev/null; fi"
assert "run-phase qa blocks missing verifier command" "if '$ROOT/bin/adlc' run-phase qa --brief-id CLI-QA-MISSING --workspace '$tmp_dir/tool-qa-missing' --json >'$tmp_dir/qa-missing.json'; then false; else jq -e '.tool_result.status == \"blocked\" and .tool_result.stop_reason == \"missing_verifier_command\" and .state.status == \"failed\"' '$tmp_dir/qa-missing.json' >/dev/null; fi"
assert "run-phase context assembly emits per-task packages" "'$ROOT/bin/adlc' run-phase context_assembly --brief-id CLI-CTX --workspace '$tmp_dir/tool-context' --build-brief '$ROOT/docs/build-briefs/xia-adlc-remediation.json' --json | jq -e '.tool_result.status == \"pass\" and .state.phase == \"code\" and .tool_result.outputs.package_count > 0 and any(.tool_result.outputs.context_packages[]; .task_id == \"XIA-SOC-INDEX\")' >/dev/null"
assert "run-phase scaffold dry-run emits planned writes" "'$ROOT/bin/adlc' run-phase scaffold --brief-id CLI-SCAFFOLD --workspace '$tmp_dir/tool-scaffold' --build-brief '$ROOT/docs/build-briefs/xia-adlc-remediation.json' --dry-run --json | jq -e '.tool_result.status == \"planned\" and .state.phase == \"scaffold\" and (.tool_result.outputs.planned_writes | length) > 0' >/dev/null"
assert "run-phase scaffold write intent requires admission" "if '$ROOT/bin/adlc' run-phase scaffold --brief-id CLI-SCAFFOLD-BLOCK --workspace '$tmp_dir/tool-scaffold-block' --build-brief '$ROOT/docs/build-briefs/xia-adlc-remediation.json' --json >'$tmp_dir/scaffold-block.json'; then false; else jq -e '.tool_result.status == \"blocked\" and .tool_result.stop_reason == \"action_not_admitted\"' '$tmp_dir/scaffold-block.json' >/dev/null; fi"
assert "run-phase slop gate reuses deterministic gate" "'$ROOT/bin/adlc' run-phase slop_gate --brief-id CLI-SLOP --workspace '$tmp_dir/tool-slop' --build-brief '$ROOT/docs/build-briefs/xia-adlc-remediation.json' --json | jq -e '.tool_result.status == \"skipped\" and .tool_result.skip_reason == \"generated_output_surface_inactive\" and .state.phase == \"pr_prep\"' >/dev/null"
assert "run-phase learning capture skips without candidates" "'$ROOT/bin/adlc' run-phase learning_capture --brief-id CLI-LEARN --workspace '$tmp_dir/tool-learn' --json | jq -e '.tool_result.status == \"skipped\" and .tool_result.skip_reason == \"no_verified_learning_candidates\" and .state.phase == \"engineer_review\"' >/dev/null"
assert "resume-workflow exposes phase artifacts" "'$ROOT/bin/adlc' resume-workflow --workspace '$tmp_dir/tool-qa-pass' --json | jq -e '.next_action.phase_artifacts[-1].phase == \"qa\" and .next_action.phase_artifacts[-1].status == \"pass\"' >/dev/null"

echo ""
echo "--- Control-Plane Dogfood Loop ---"
dogfood_repo="$tmp_dir/control-plane-repo"
mkdir -p "$dogfood_repo/scripts/adlc_runtime" "$dogfood_repo/docs/schemas"
cp "$ROOT/scripts/adlc_runtime/metadata.py" "$dogfood_repo/scripts/adlc_runtime/metadata.py"
cp "$ROOT"/docs/schemas/*.schema.json "$dogfood_repo/docs/schemas/"
python3 -c "from pathlib import Path; p = Path('$dogfood_repo/scripts/adlc_runtime/metadata.py'); p.write_text(p.read_text().replace('    \"learning-entry\": \"docs/schemas/learning-entry.schema.json\",\\n', ''))"
printf '.adlc/\n__pycache__/\n*.pyc\n' > "$dogfood_repo/.gitignore"
git -C "$dogfood_repo" init -q
git -C "$dogfood_repo" config user.email adlc@example.invalid
git -C "$dogfood_repo" config user.name ADLC
git -C "$dogfood_repo" add .
git -C "$dogfood_repo" commit -q -m init
assert "control-plane drift loop dry-run detects schema alias drift" "'$ROOT/bin/adlc' control-plane-drift-loop --brief-id ADLC-G7-TEST --workspace '$dogfood_repo' --verifier 'python3 -m py_compile scripts/adlc_runtime/metadata.py' --dry-run --json >'$tmp_dir/control-plane-dry.json' && jq -e '.status == \"planned\" and .drift.detected == true and (.drift.missing_aliases | length) >= 1 and .work_item_sync.summary.total == 1 and .action_validation.status == \"admitted\" and .repair.applied == false' '$tmp_dir/control-plane-dry.json' >/dev/null"
assert "control-plane drift loop blocks repair without admission" "if '$ROOT/bin/adlc' control-plane-drift-loop --brief-id ADLC-G7-TEST --workspace '$dogfood_repo' --verifier 'python3 -m py_compile scripts/adlc_runtime/metadata.py' --json >'$tmp_dir/control-plane-blocked.json'; then false; else jq -e '.status == \"blocked\" and .stop_reason == \"action_not_admitted\" and any(.issues[]; .rule == \"action_not_admitted\")' '$tmp_dir/control-plane-blocked.json' >/dev/null; fi"
assert "control-plane drift loop repairs schema alias drift with admission" "'$ROOT/bin/adlc' control-plane-drift-loop --brief-id ADLC-G7-TEST --workspace '$dogfood_repo' --verifier 'python3 -m py_compile scripts/adlc_runtime/metadata.py' --allow-mutation --tool-registry '$ROOT/tests/fixtures/control_plane/tool-registry.json' --json >'$tmp_dir/control-plane-repaired.json' && jq -e '.status == \"needs_human\" and .repair.applied == true and (.repair.changed_files | index(\"scripts/adlc_runtime/metadata.py\")) != null and (.repair.added_aliases | length) >= 1 and .repair.admission.status == \"admitted\" and .verification.final.status == \"pass\" and .drift.detected == true and .repair.post_drift.detected == false' '$tmp_dir/control-plane-repaired.json' >/dev/null"
assert "control-plane drift report validates after repair" "'$ROOT/bin/adlc' validate-artifact --schema control-plane-drift-report --input '$dogfood_repo/.adlc/outputs/control_plane_drift_loop.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "control-plane drift loop rerun reports no drift" "'$ROOT/bin/adlc' control-plane-drift-loop --brief-id ADLC-G7-TEST --workspace '$dogfood_repo' --verifier 'python3 -m py_compile scripts/adlc_runtime/metadata.py' --dry-run --json >'$tmp_dir/control-plane-clean.json' && jq -e '.status == \"no_drift\" and .drift.detected == false and .human_review_required == true' '$tmp_dir/control-plane-clean.json' >/dev/null"

echo ""
echo "--- Learning And Architecture Memory ---"
memory_repo="$tmp_dir/memory-repo"
mkdir -p "$memory_repo/docs/specs" "$memory_repo/.adlc"
printf '# Compound Engineering Learning Store\n' > "$memory_repo/docs/specs/compound-engineering-learning-store.md"
cat > "$tmp_dir/architecture-memory-candidate.json" <<'JSON'
{
  "contract_version": "1.0.0",
  "decisions": [
    {
      "decision_id": "ADR-G8-001",
      "title": "Preserve architecture memory as evidence-backed repo entries",
      "status": "accepted",
      "context": "ADLC needs architecture constraints to survive across loop runs.",
      "decision": "Store architecture memory in docs/architecture/decisions with evidence and stale conditions.",
      "architecture_boundary": "ADLC memory captures boundaries, not approval to rewrite architecture.",
      "affected_paths": ["docs/architecture/decisions"],
      "source_evidence": ["docs/specs/compound-engineering-learning-store.md"],
      "verifier_evidence": ["python3 -m py_compile scripts/adlc_runtime/cli.py"],
      "stale_conditions": ["docs/specs/compound-engineering-learning-store.md"],
      "no_overclaim": ["Does not prove future architecture decisions remain correct without memory-health refresh."]
    }
  ]
}
JSON
cat > "$tmp_dir/memory-tool-registry.json" <<'JSON'
{"version":"1.0.0","default_policy":"deny","tools":[{"name":"adlc-memory","description":"ADLC memory writes","inputSchema":{},"side_effect_profile":"mutating","permission_tier":"unrestricted","available_phases":["learning_capture"]}]}
JSON
assert "architecture-memory dry-run plans evidence-backed decision write" "'$ROOT/bin/adlc' architecture-memory --input '$tmp_dir/architecture-memory-candidate.json' --workspace '$memory_repo' --dry-run --json | jq -e '.status == \"planned\" and .summary.candidates == 1 and .candidates[0].result == \"planned\" and (.candidates[0].no_overclaim | length) == 1' >/dev/null"
assert "architecture-memory admitted write records report evidence" "'$ROOT/bin/adlc' architecture-memory --input '$tmp_dir/architecture-memory-candidate.json' --workspace '$memory_repo' --allow-mutation --tool-registry '$tmp_dir/memory-tool-registry.json' --json >'$tmp_dir/architecture-memory-write.json' && jq -e '.status == \"pass\" and .summary.written == 1 and .admission.status == \"admitted\" and (.written[0] | contains(\"docs/architecture/decisions/adr-g8-001.md\"))' '$tmp_dir/architecture-memory-write.json' >/dev/null"
assert "architecture memory report validates" "'$ROOT/bin/adlc' validate-artifact --schema architecture-memory-report --input '$memory_repo/.adlc/outputs/architecture_memory_report.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "memory-health flags stale architecture memory from changed path" "'$ROOT/bin/adlc' memory-health --workspace '$memory_repo' --changed-path docs/specs/compound-engineering-learning-store.md --output '$tmp_dir/memory-health-stale.json' --json | jq -e '.status == \"stale\" and (.stale_refs | length) >= 1 and .summary.architecture_entries == 1' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema memory-health-report --input '$tmp_dir/memory-health-stale.json' --json | jq -e '.valid == true' >/dev/null"
cat > "$tmp_dir/primitive-proposals.json" <<'JSON'
{
  "proposals": [
    {
      "name": "learning-capture",
      "kind": "skill",
      "proposed_path": "skills/learning-capture/SKILL.md",
      "reuse_refs": []
    }
  ]
}
JSON
assert "memory-health blocks duplicate primitive proposals without reuse refs" "if '$ROOT/bin/adlc' memory-health --workspace '$ROOT' --primitive-proposals '$tmp_dir/primitive-proposals.json' --json >'$tmp_dir/memory-health-duplicate.json'; then false; else jq -e '.status == \"blocked\" and any(.duplicate_primitive_issues[]; .rule == \"duplicate_primitive_without_reuse_ref\")' '$tmp_dir/memory-health-duplicate.json' >/dev/null; fi"

# beads-status: optional Beads (bd) preflight is read-only and must no-op safely when bd/.beads are absent.
mkdir -p "$tmp_dir/beads-bin" "$tmp_dir/beads-ws/.beads" "$tmp_dir/beads-ws-nodir"
mkdir -p "$tmp_dir/beads-bad-bin" "$tmp_dir/beads-bad-ws/.beads"
cat > "$tmp_dir/beads-bin/bd" <<'EOF'
#!/usr/bin/env bash
case "$1" in
  --version) echo "bd 9.9.9-fake" ;;
  *) echo '{}' ;;
esac
EOF
chmod +x "$tmp_dir/beads-bin/bd"
cat > "$tmp_dir/beads-bad-bin/bd" <<'EOF'
#!/usr/bin/env bash
exit 17
EOF
chmod +x "$tmp_dir/beads-bad-bin/bd"
assert "beads-status reports not_configured when bd and .beads are absent" "'$ROOT/bin/adlc' beads-status --workspace '$tmp_dir' --output '$tmp_dir/beads-status-absent.json' --json | jq -e '.status == \"not_configured\" and .bd_present == false and .beads_dir_present == false and .safe_to_use == false' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema beads-status-report --input '$tmp_dir/beads-status-absent.json' --json | jq -e '.valid == true' >/dev/null"
assert "beads-status reports available when bd and .beads are present" "PATH='$tmp_dir/beads-bin:$PATH' '$ROOT/bin/adlc' beads-status --workspace '$tmp_dir/beads-ws' --output '$tmp_dir/beads-status-available.json' --json | jq -e '.status == \"available\" and .bd_present == true and .beads_dir_present == true and .safe_to_use == true and (.bd_version | test(\"9.9.9-fake\"))' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema beads-status-report --input '$tmp_dir/beads-status-available.json' --json | jq -e '.valid == true' >/dev/null"
assert "beads-status warns unavailable when bd present without .beads" "PATH='$tmp_dir/beads-bin:$PATH' '$ROOT/bin/adlc' beads-status --workspace '$tmp_dir/beads-ws-nodir' --json | jq -e '.status == \"unavailable\" and .safe_to_use == false and (.warnings | length) >= 1' >/dev/null"
assert "beads-status blocks availability when bd version check fails" "PATH='$tmp_dir/beads-bad-bin:$PATH' '$ROOT/bin/adlc' beads-status --workspace '$tmp_dir/beads-bad-ws' --json | jq -e '.status == \"unavailable\" and .bd_present == true and .beads_dir_present == true and .safe_to_use == false and any(.checks[]; .name == \"bd-version\" and .status == \"warn\")' >/dev/null"

mkdir -p "$tmp_dir/looper-bin" "$tmp_dir/looper-ws"
cat > "$tmp_dir/looper-bin/looper" <<'EOF'
#!/usr/bin/env bash
echo "looper fake"
EOF
chmod +x "$tmp_dir/looper-bin/looper"
assert "looper-status reports not_configured without looper command or skill" "'$ROOT/bin/adlc' looper-status --workspace '$tmp_dir' --output '$tmp_dir/looper-status.json' --json | jq -e '.status == \"not_configured\" and .safe_to_use == false and .loop_design_schema_present == true' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema looper-status-report --input '$tmp_dir/looper-status.json' --json | jq -e '.valid == true' >/dev/null"
assert "looper-status reports available with looper command" "PATH='$tmp_dir/looper-bin:$PATH' '$ROOT/bin/adlc' looper-status --workspace '$tmp_dir/looper-ws' --json | jq -e '.status == \"available\" and .safe_to_use == true and .looper_command_present == true and .loop_design_schema_present == true' >/dev/null"
assert "loop-design-validate passes valid Looper design" "'$ROOT/bin/adlc' loop-design-validate --input '$ROOT/tests/fixtures/loop_design/valid-looper-design.json' --output '$tmp_dir/loop-design-validation.json' --json | jq -e '.status == \"pass\" and .summary.programmatic_verifiers == 2' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema loop-design-validation-report --input '$tmp_dir/loop-design-validation.json' --json | jq -e '.valid == true' >/dev/null"
assert "loop-design-validate blocks missing stop guards" "if '$ROOT/bin/adlc' loop-design-validate --input '$ROOT/tests/fixtures/loop_design/missing-stop-guards.json' --json >'$tmp_dir/loop-design-blocked.json'; then false; else jq -e '.status == \"blocked\" and any(.issues[]; .rule == \"missing_programmatic_verifier\") and any(.issues[]; .rule == \"missing_no_progress_rule\")' '$tmp_dir/loop-design-blocked.json' >/dev/null; fi"
assert "loop-contract-from-design emits valid ADLC Loop Contract" "'$ROOT/bin/adlc' loop-contract-from-design --loop-design '$ROOT/tests/fixtures/loop_design/valid-looper-design.json' --output '$tmp_dir/loop-contract-from-design.json' --json | jq -e '.contract_id == \"adlc-loop-design:shipped-change-reconcile\" and .autonomy_claim == \"assisted_loop\" and (.test_selection.mandatory_floor | length) == 2' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema loop-contract --input '$tmp_dir/loop-contract-from-design.json' --json | jq -e '.valid == true' >/dev/null"
cat > "$tmp_dir/champion-holdout-pass.json" <<'JSON'
{
  "evaluation_id": "g8-skill-loop",
  "artifact_type": "skill",
  "promotion_margin": 0.05,
  "champion": {"id": "current"},
  "challenger": {"id": "candidate"},
  "working_set": [
    {"id": "w1", "champion_score": 0.70, "challenger_score": 0.82},
    {"id": "w2", "champion_score": 0.72, "challenger_score": 0.84}
  ],
  "holdout_set": [
    {"id": "h1", "champion_score": 0.70, "challenger_score": 0.78},
    {"id": "h2", "champion_score": 0.71, "challenger_score": 0.79}
  ],
  "must_pass_rules": [
    {"id": "redaction", "status": "pass"},
    {"id": "format", "status": "pass"}
  ]
}
JSON
assert "champion-holdout promotes only on holdout margin and must-pass rules" "'$ROOT/bin/adlc' champion-holdout --input '$tmp_dir/champion-holdout-pass.json' --output '$tmp_dir/champion-holdout-report.json' --json | jq -e '.status == \"promote\" and .decision == \"promote_challenger\" and .summary.holdout_delta >= 0.05' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema champion-holdout-report --input '$tmp_dir/champion-holdout-report.json' --json | jq -e '.valid == true' >/dev/null"
cat > "$tmp_dir/champion-holdout-fail.json" <<'JSON'
{
  "evaluation_id": "g8-prompt-loop",
  "artifact_type": "prompt",
  "promotion_margin": 0.05,
  "champion": {"id": "current"},
  "challenger": {"id": "candidate"},
  "working_set": [{"id": "w1", "champion_score": 0.60, "challenger_score": 0.80}],
  "holdout_set": [{"id": "h1", "champion_score": 0.70, "challenger_score": 0.71}],
  "must_pass_rules": [{"id": "redaction", "status": "pass"}]
}
JSON
assert "champion-holdout rejects working-set-only improvement" "if '$ROOT/bin/adlc' champion-holdout --input '$tmp_dir/champion-holdout-fail.json' --json >'$tmp_dir/champion-holdout-fail-report.json'; then false; else jq -e '.status == \"reject\" and .decision == \"keep_champion\" and any(.issues[]; .rule == \"working_set_only_improvement\")' '$tmp_dir/champion-holdout-fail-report.json' >/dev/null; fi"

echo ""
echo "--- Packaged Loop Library ---"
loop_install_workspace="$tmp_dir/loop-install-workspace"
mkdir -p "$loop_install_workspace"
cat > "$tmp_dir/loop-library-tool-registry.json" <<'JSON'
{
  "version": "1.0.0",
  "default_policy": "deny",
  "tools": [
    {
      "name": "adlc-loop-library",
      "description": "Install ADLC loop templates",
      "inputSchema": {},
      "side_effect_profile": "mutating",
      "permission_tier": "unrestricted",
      "available_phases": ["learning_capture"]
    }
  ]
}
JSON
assert "loop-library lists the seven packaged templates" "'$ROOT/bin/adlc' loop-library --json | jq -e '.count == 7 and any(.templates[]; .template_id == \"ci-triage\") and any(.templates[]; .template_id == \"skill-champion\")' >/dev/null"
assert "loop-library inspect validates generated artifacts" "'$ROOT/bin/adlc' loop-library --template-id ci-triage --json | jq -e '.summary.template_id == \"ci-triage\" and .generated_artifact_validation.valid == true and any(.install_plan.gates[]; .gate_id == \"ci-local-verifier\")' >/dev/null"
assert "loop-template-install dry-run plans schema-backed artifacts" "'$ROOT/bin/adlc' loop-template-install --template-id ci-triage --workspace '$loop_install_workspace' --dry-run --json >'$tmp_dir/loop-install-dry.json' && jq -e '.status == \"planned\" and .dry_run == true and .summary.planned == 6 and any(.artifacts[]; .artifact_type == \"loop_contract\" and .valid == true) and any(.artifacts[]; .artifact_type == \"token_budget\" and .valid == true)' '$tmp_dir/loop-install-dry.json' >/dev/null"
assert "loop-template-install mutation requires action admission" "if '$ROOT/bin/adlc' loop-template-install --template-id ci-triage --workspace '$loop_install_workspace' --allow-mutation --json >'$tmp_dir/loop-install-blocked.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and .summary.written == 0 and any(.issues[]; .rule == \"action_not_admitted\")' '$tmp_dir/loop-install-blocked.json' >/dev/null; fi"
assert "loop-template-install writes admitted loop contracts" "'$ROOT/bin/adlc' loop-template-install --template-id ci-triage --workspace '$loop_install_workspace' --allow-mutation --tool-registry '$tmp_dir/loop-library-tool-registry.json' --json >'$tmp_dir/loop-install-pass.json' && jq -e '.status == \"pass\" and .admission.status == \"admitted\" and .summary.written == 6' '$tmp_dir/loop-install-pass.json' >/dev/null"
assert "installed loop contract validates" "'$ROOT/bin/adlc' validate-artifact --schema loop-contract --input '$loop_install_workspace/.adlc/loops/ci-triage/loop_contract.json' --json | jq -e '.valid == true' >/dev/null"
assert "installed loop tool registry validates" "'$ROOT/bin/adlc' validate-artifact --schema tool-registry --input '$loop_install_workspace/.adlc/loops/ci-triage/tool_registry.json' --json | jq -e '.valid == true' >/dev/null"
assert "installed loop work queue seed validates" "'$ROOT/bin/adlc' validate-artifact --schema work-queue --input '$loop_install_workspace/.adlc/loops/ci-triage/work_queue_seed.json' --json | jq -e '.valid == true' >/dev/null"
assert "installed loop token budget validates" "'$ROOT/bin/adlc' validate-artifact --schema token-budget --input '$loop_install_workspace/.adlc/loops/ci-triage/token_budget.json' --json | jq -e '.valid == true' >/dev/null"
assert "installed loop report validates" "'$ROOT/bin/adlc' validate-artifact --schema loop-template-install-report --input '$loop_install_workspace/.adlc/loops/ci-triage/install_report.json' --json | jq -e '.valid == true' >/dev/null"

echo ""
echo "--- Self-Actioning Meta-Harness ---"
cat > "$tmp_dir/meta-signals.json" <<'JSON'
{
  "signals": [
    {
      "signal_id": "ci-auth-failure",
      "title": "Nightly CI failure in auth middleware",
      "labels": ["workflow_run_failed", "ci"],
      "expected_paths": [{"path": "src/auth/middleware.py", "kind": "file", "reason": "failing test scope"}],
      "verifier_refs": ["pytest tests/auth"],
      "value_score": 85,
      "risk_score": 30,
      "repeatability_score": 85,
      "urgency_score": 80
    },
    {
      "signal_id": "billing-architecture-rewrite",
      "title": "Rewrite billing architecture",
      "labels": ["architecture", "billing"],
      "expected_paths": [{"path": "src/billing", "kind": "directory", "reason": "high-risk domain"}],
      "verifier_refs": ["pytest tests/billing"],
      "value_score": 90,
      "risk_score": 95,
      "repeatability_score": 30,
      "urgency_score": 40
    }
  ]
}
JSON
assert "meta-harness-plan ranks signals and stops before dispatch" "'$ROOT/bin/adlc' meta-harness-plan --signals '$tmp_dir/meta-signals.json' --max-candidates 2 --output '$tmp_dir/meta-plan-report.json' --json >'$tmp_dir/meta-plan.json' && jq -e '.status == \"planned\" and .autonomy_claim == \"bounded_meta_harness_plan\" and .summary.candidate_count == 2 and .summary.selected_count == 2 and .summary.admitted_count == 1 and .summary.needs_human_count == 1 and any(.selected[]; .candidate_id == \"ci-auth-failure\" and .selected_template_id == \"ci-triage\" and .decision == \"admit_to_queue\") and any(.selected[]; .candidate_id == \"billing-architecture-rewrite\" and .decision == \"needs_human\") and (.generated_artifacts.validation | all(.valid == true)) and (.boundary.does_not | index(\"dispatch agents\")) != null' '$tmp_dir/meta-plan.json' >/dev/null"
assert "meta-harness-plan emits valid queue and sync seeds" "jq -e '(.generated_artifacts.work_queue_seed.tasks | length) == 1 and (.generated_artifacts.work_item_syncs | length) == 2 and any(.planned_actions[]; .type == \"queue_claim\") and any(.planned_actions[]; .type == \"human_review\" and .requires_admission == true)' '$tmp_dir/meta-plan.json' >/dev/null"
assert "meta-harness plan report validates" "'$ROOT/bin/adlc' validate-artifact --schema meta-harness-plan-report --input '$tmp_dir/meta-plan-report.json' --json | jq -e '.valid == true' >/dev/null"
assert "meta-harness-plan blocks empty input" "if '$ROOT/bin/adlc' meta-harness-plan --json >'$tmp_dir/meta-empty.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and any(.issues[]; .rule == \"no_task_candidates\")' '$tmp_dir/meta-empty.json' >/dev/null; fi"

echo ""
echo "--- Work Queue And Worktrees ---"
queue_repo="$tmp_dir/queue-repo"
dirty_queue_repo="$tmp_dir/dirty-queue-repo"
mkdir -p "$queue_repo" "$dirty_queue_repo"
git -C "$queue_repo" init -q
git -C "$queue_repo" config user.email adlc@example.invalid
git -C "$queue_repo" config user.name ADLC
printf 'base\n' > "$queue_repo/README.md"
git -C "$queue_repo" add README.md
git -C "$queue_repo" commit -q -m init
git -C "$dirty_queue_repo" init -q
git -C "$dirty_queue_repo" config user.email adlc@example.invalid
git -C "$dirty_queue_repo" config user.name ADLC
printf 'base\n' > "$dirty_queue_repo/README.md"
git -C "$dirty_queue_repo" add README.md
git -C "$dirty_queue_repo" commit -q -m init
printf 'dirty\n' >> "$dirty_queue_repo/README.md"
cp "$ROOT/tests/fixtures/work_queue/valid-queue.json" "$tmp_dir/work_queue.json"
cp "$ROOT/tests/fixtures/work_queue/valid-queue.json" "$tmp_dir/mutable-work_queue.json"
cat > "$tmp_dir/queue-workflow-state.json" <<'JSON'
{"brief_id":"ADLC-GOAL-5","run_id":"adlc-run-goal5","session_id":"adlc-session-goal5","phase":"code","status":"planned","step":"ready","started_at":"2026-06-22T00:00:00Z","updated_at":"2026-06-22T00:00:00Z","checkpoint":{"workspace":"/tmp","history":[]},"side_effects":[],"resume_count":0,"attempt":1}
JSON
cp "$tmp_dir/queue-workflow-state.json" "$tmp_dir/mutable-workflow-state.json"
cat > "$tmp_dir/queue-tool-registry.json" <<'JSON'
{"version":"1.0.0","default_policy":"deny","tools":[{"name":"adlc-queue","description":"ADLC queue mutation","inputSchema":{},"side_effect_profile":"mutating","permission_tier":"unrestricted","available_phases":["code"]},{"name":"adlc-worktree","description":"ADLC worktree mutation","inputSchema":{},"side_effect_profile":"mutating","permission_tier":"unrestricted","available_phases":["code"]}]}
JSON
assert "queue-status reports deterministic status counts" "'$ROOT/bin/adlc' queue-status --queue '$ROOT/tests/fixtures/work_queue/valid-queue.json' --json | jq -e '.summary.total == 8 and .summary.counts.queued == 3 and .summary.counts.claimed == 1 and .summary.counts.running == 1 and .summary.counts.blocked == 1 and .summary.counts.done == 1 and .summary.counts.escalated == 1 and (.active_claims | length) == 2' >/dev/null"
assert "queue-claim dry-run succeeds for clean queued task" "'$ROOT/bin/adlc' queue-claim --queue '$ROOT/tests/fixtures/work_queue/valid-queue.json' --task-id ADLC-G5-CLAIMABLE --workspace '$queue_repo' --dry-run --json | jq -e '.status == \"pass\" and .dry_run == true and .planned_task.status == \"claimed\" and .git.dirty == false and (.issues | length) == 0' >/dev/null"
assert "queue-claim dry-run blocks already claimed task" "if '$ROOT/bin/adlc' queue-claim --queue '$ROOT/tests/fixtures/work_queue/valid-queue.json' --task-id ADLC-G5-ACTIVE --workspace '$queue_repo' --dry-run --json >'$tmp_dir/queue-already-claimed.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and .stop_reason == \"task_not_claimable\" and any(.issues[]; .rule == \"task_not_claimable\")' '$tmp_dir/queue-already-claimed.json' >/dev/null; fi"
assert "queue-claim dry-run blocks dirty checkout" "if '$ROOT/bin/adlc' queue-claim --queue '$ROOT/tests/fixtures/work_queue/valid-queue.json' --task-id ADLC-G5-CLAIMABLE --workspace '$dirty_queue_repo' --dry-run --json >'$tmp_dir/queue-dirty.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and .stop_reason == \"dirty_checkout\" and .git.dirty == true and any(.issues[]; .rule == \"dirty_checkout\")' '$tmp_dir/queue-dirty.json' >/dev/null; fi"
assert "queue-claim dry-run blocks file overlap" "if '$ROOT/bin/adlc' queue-claim --queue '$ROOT/tests/fixtures/work_queue/valid-queue.json' --task-id ADLC-G5-OVERLAP --workspace '$queue_repo' --dry-run --json >'$tmp_dir/queue-overlap.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and .stop_reason == \"file_overlap\" and any(.issues[]; .rule == \"file_overlap\" and .conflicting_task_id == \"ADLC-G5-ACTIVE\")' '$tmp_dir/queue-overlap.json' >/dev/null; fi"
assert "queue-complete dry-run requires verifier evidence" "if '$ROOT/bin/adlc' queue-complete --queue '$ROOT/tests/fixtures/work_queue/valid-queue.json' --task-id ADLC-G5-NEEDS-EVIDENCE --workspace '$queue_repo' --dry-run --json >'$tmp_dir/queue-complete-missing-evidence.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and .stop_reason == \"missing_verifier_evidence\" and any(.issues[]; .rule == \"missing_verifier_evidence\")' '$tmp_dir/queue-complete-missing-evidence.json' >/dev/null; fi"
assert "queue-complete dry-run accepts verifier evidence" "'$ROOT/bin/adlc' queue-complete --queue '$ROOT/tests/fixtures/work_queue/valid-queue.json' --task-id ADLC-G5-NEEDS-EVIDENCE --workspace '$queue_repo' --evidence 'python3 -m py_compile scripts/adlc_runtime/metadata.py' --dry-run --json | jq -e '.status == \"pass\" and .planned_task.status == \"done\" and (.planned_task.evidence_refs | index(\"python3 -m py_compile scripts/adlc_runtime/metadata.py\")) != null' >/dev/null"
assert "queue-block dry-run records structured reason and next action" "'$ROOT/bin/adlc' queue-block --queue '$ROOT/tests/fixtures/work_queue/valid-queue.json' --task-id ADLC-G5-CLAIMABLE --workspace '$queue_repo' --reason verifier_unavailable --next-action 'install verifier dependency' --dry-run --json | jq -e '.status == \"pass\" and .planned_task.status == \"blocked\" and .planned_task.reason == \"verifier_unavailable\" and .planned_task.next_action == \"install verifier dependency\"' >/dev/null"
assert "queue-escalate dry-run records structured reason and next action" "'$ROOT/bin/adlc' queue-escalate --queue '$ROOT/tests/fixtures/work_queue/valid-queue.json' --task-id ADLC-G5-CLAIMABLE --workspace '$queue_repo' --reason architecture_decision --next-action 'human reviews boundary' --dry-run --json | jq -e '.status == \"pass\" and .planned_task.status == \"escalated\" and .planned_task.reason == \"architecture_decision\" and .planned_task.next_action == \"human reviews boundary\"' >/dev/null"
assert "worktree-prepare dry-run plans deterministic branch and path" "'$ROOT/bin/adlc' worktree-prepare --queue '$ROOT/tests/fixtures/work_queue/valid-queue.json' --task-id ADLC-G5-CLAIMABLE --workspace '$queue_repo' --dry-run --json | jq -e '.status == \"pass\" and .worktree.branch == \"adlc/adlc-g5-claimable-47fdcbfd\" and (.worktree.path | contains(\"adlc-g5-claimable\")) and .git.dirty == false' >/dev/null"
assert "worktree-prepare dry-run blocks dirty checkout" "if '$ROOT/bin/adlc' worktree-prepare --queue '$ROOT/tests/fixtures/work_queue/valid-queue.json' --task-id ADLC-G5-CLAIMABLE --workspace '$dirty_queue_repo' --dry-run --json >'$tmp_dir/worktree-dirty.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and .stop_reason == \"dirty_checkout\" and any(.issues[]; .rule == \"dirty_checkout\")' '$tmp_dir/worktree-dirty.json' >/dev/null; fi"
assert "worktree-status reports linked queue task and cleanup eligibility" "'$ROOT/bin/adlc' worktree-status --queue '$ROOT/tests/fixtures/work_queue/valid-queue.json' --task-id ADLC-G5-RUNNING --workspace '$queue_repo' --json | jq -e '.summary.total == 1 and .worktrees[0].task_id == \"ADLC-G5-RUNNING\" and .worktrees[0].task_status == \"running\" and .worktrees[0].dirty_state.exists == false' >/dev/null"
assert "worktree-cleanup dry-run refuses dirty worktree evidence" "if '$ROOT/bin/adlc' worktree-cleanup --queue '$ROOT/tests/fixtures/work_queue/valid-queue.json' --task-id ADLC-G5-CLAIMABLE --workspace '$queue_repo' --worktree-path '$dirty_queue_repo' --dry-run --json >'$tmp_dir/worktree-cleanup-dirty.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and .stop_reason == \"dirty_worktree\" and any(.issues[]; .rule == \"dirty_worktree\")' '$tmp_dir/worktree-cleanup-dirty.json' >/dev/null; fi"
assert "queue-claim mutation records state claim and side effect" "'$ROOT/bin/adlc' queue-claim --queue '$tmp_dir/mutable-work_queue.json' --task-id ADLC-G5-CLAIMABLE --workspace '$queue_repo' --state '$tmp_dir/mutable-workflow-state.json' --allow-mutation --tool-registry '$tmp_dir/queue-tool-registry.json' --json >'$tmp_dir/queue-claim-mutated.json' && jq -e '.status == \"committed\" and .state.queue_claims[0].task_id == \"ADLC-G5-CLAIMABLE\" and .state.side_effects[0].tool_name == \"adlc-queue\" and .admission.status == \"admitted\"' '$tmp_dir/queue-claim-mutated.json' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema work-queue --input '$tmp_dir/mutable-work_queue.json' --json | jq -e '.valid == true' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema workflow-state --input '$tmp_dir/mutable-workflow-state.json' --json | jq -e '.valid == true' >/dev/null"
assert "resume-workflow exposes queue claims" "'$ROOT/bin/adlc' resume-workflow --state '$tmp_dir/mutable-workflow-state.json' --json | jq -e '.next_action.queue_claims[0].task_id == \"ADLC-G5-CLAIMABLE\" and .next_action.queue_claims[0].status == \"claimed\"' >/dev/null"

echo ""
echo "--- Action Admission ---"
cat > "$tmp_dir/action-tool-registry.json" <<'JSON'
{
  "version": "1.0.0",
  "default_policy": "deny",
  "tools": [
    {
      "name": "Read",
      "description": "Read files",
      "inputSchema": {},
      "side_effect_profile": "read_only",
      "permission_tier": "unrestricted",
      "available_phases": ["research"]
    },
    {
      "name": "Write",
      "description": "Write files",
      "inputSchema": {},
      "side_effect_profile": "mutating",
      "permission_tier": "requires_approval",
      "available_phases": ["code"]
    },
    {
      "name": "linear-work-item-emitter",
      "description": "Mutate Linear work items",
      "inputSchema": {},
      "side_effect_profile": "mutating",
      "permission_tier": "requires_approval",
      "available_phases": ["pr_prep"]
    },
    {
      "name": "Shell",
      "description": "Run destructive shell operations",
      "inputSchema": {},
      "side_effect_profile": "destructive",
      "permission_tier": "requires_escalation",
      "available_phases": ["code"]
    }
  ]
}
JSON
assert "validate-artifact accepts workflow-phase tool registry" "'$ROOT/bin/adlc' validate-artifact --schema tool-registry --input '$tmp_dir/action-tool-registry.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "action-admit admits read-only action and writes audit trail" "'$ROOT/bin/adlc' action-admit --tool-registry '$tmp_dir/action-tool-registry.json' --tool Read --action read_file --phase research --brief-id BRF-ACTION --session-id SESSION-ACTION --audit-trail '$tmp_dir/action-read-audit.json' --json | jq -e '.status == \"admitted\" and .audit_trail.entries[0].decision == \"approved\" and .audit_trail.denial_summary.count == 0' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema permission-audit-trail --input '$tmp_dir/action-read-audit.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "action-admit correlates state identity into audit trail" "'$ROOT/bin/adlc' action-admit --tool-registry '$tmp_dir/action-tool-registry.json' --tool Read --action read_file --state '$tmp_dir/workflow/.adlc/workflow_state.json' --audit-trail '$tmp_dir/action-state-audit.json' --json >'$tmp_dir/action-state.json' && jq -e '.status == \"admitted\" and .run_identity.run_id == .audit_trail.run_id and .audit_trail.entries[0].run_id == .run_identity.run_id and .audit_trail.entries[0].session_id == .run_identity.session_id and .audit_trail.entries[0].brief_id == .run_identity.brief_id' '$tmp_dir/action-state.json' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema permission-audit-trail --input '$tmp_dir/action-state-audit.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"
assert "action-admit denies mutating action without explicit approval" "if '$ROOT/bin/adlc' action-admit --tool-registry '$tmp_dir/action-tool-registry.json' --tool Write --action edit_file --phase code --brief-id BRF-ACTION --session-id SESSION-ACTION --run-id RUN-ACTION --audit-trail '$tmp_dir/action-denied-audit.json' --json >'$tmp_dir/action-denied.json' 2>/dev/null; then false; else jq -e '.status == \"denied\" and .stop_reason == \"permission_denied\" and any(.issues[]; .rule == \"mutation_requires_allow_mutation\") and any(.issues[]; .rule == \"permission_requires_human_approval\") and .audit_trail.run_id == \"RUN-ACTION\" and .audit_trail.entries[0].decision == \"denied\" and .audit_trail.entries[0].run_id == \"RUN-ACTION\" and .audit_trail.entries[0].stop_reason == \"permission_denied\"' '$tmp_dir/action-denied.json' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema permission-audit-trail --input '$tmp_dir/action-denied-audit.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null; fi"
assert "action-admit admits approved mutation" "'$ROOT/bin/adlc' action-admit --tool-registry '$tmp_dir/action-tool-registry.json' --tool Write --action edit_file --phase code --brief-id BRF-ACTION --session-id SESSION-ACTION --allow-mutation --human-approved --approval-ref human:cli-test --audit-trail '$tmp_dir/action-approved-audit.json' --json | jq -e '.status == \"admitted\" and .audit_trail.entries[0].decision == \"approved\" and .audit_trail.entries[0].decided_by == \"human\" and .audit_trail.entries[0].human_approval_ref == \"human:cli-test\"' >/dev/null"
assert "action-admit denies out-of-phase invocation" "if '$ROOT/bin/adlc' action-admit --tool-registry '$tmp_dir/action-tool-registry.json' --tool Read --action read_file --phase code --brief-id BRF-ACTION --session-id SESSION-ACTION --json >'$tmp_dir/action-phase-denied.json' 2>/dev/null; then false; else jq -e '.status == \"denied\" and any(.issues[]; .rule == \"phase_not_allowed\") and .audit_trail.denial_summary.count == 1' '$tmp_dir/action-phase-denied.json' >/dev/null; fi"
assert "action-admit escalates requires-escalation tools" "if '$ROOT/bin/adlc' action-admit --tool-registry '$tmp_dir/action-tool-registry.json' --tool Shell --action remove_path --phase code --brief-id BRF-ACTION --session-id SESSION-ACTION --allow-mutation --human-approved --json >'$tmp_dir/action-escalate.json' 2>/dev/null; then false; else jq -e '.status == \"escalate\" and .stop_reason == \"permission_requires_escalation\" and any(.issues[]; .rule == \"permission_requires_escalation\") and .audit_trail.entries[0].decision == \"escalated\" and .audit_trail.entries[0].stop_reason == \"permission_requires_escalation\"' '$tmp_dir/action-escalate.json' >/dev/null; fi"
assert "action-admit denies exhausted budget before execution" "if '$ROOT/bin/adlc' action-admit --tool-registry '$tmp_dir/action-tool-registry.json' --tool Read --action read_file --phase research --brief-id BRF-ACTION --session-id SESSION-ACTION --token-budget '$ROOT/tests/fixtures/loop_maturity/token-budget-exhausted.json' --estimated-input-tokens 10 --expected-output-tokens 10 --json >'$tmp_dir/action-budget-denied.json' 2>/dev/null; then false; else jq -e '.status == \"denied\" and .stop_reason == \"budget_exhausted\" and .budget_status.status == \"exhausted\" and any(.issues[]; .rule == \"budget_exhausted\")' '$tmp_dir/action-budget-denied.json' >/dev/null; fi"
assert "action-admit denies external provider mutation until approved" "if '$ROOT/bin/adlc' action-admit --tool-registry '$tmp_dir/action-tool-registry.json' --tool linear-work-item-emitter --action upsert_artifacts --phase pr_prep --brief-id BRF-ACTION --session-id SESSION-ACTION --json >'$tmp_dir/action-provider-denied.json' 2>/dev/null; then false; else jq -e '.status == \"denied\" and any(.issues[]; .rule == \"mutation_requires_allow_mutation\") and any(.issues[]; .rule == \"permission_requires_human_approval\")' '$tmp_dir/action-provider-denied.json' >/dev/null; fi"

echo ""
echo "--- Loop System Maturity ---"
assert "loop-test-selection passes complete required plan" "'$ROOT/bin/adlc' loop-test-selection --loop-contract '$ROOT/tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json' --test-plan '$ROOT/tests/fixtures/loop_maturity/test-plan-complete-required.json' --json | jq -e '.status == \"pass\" and (.missing_required_tests | length) == 0 and (.provided_required_tests | index(\"required:test-selection\")) != null' >/dev/null"
assert "loop-test-selection passes strict executed required results" "'$ROOT/bin/adlc' loop-test-selection --loop-contract '$ROOT/tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json' --test-plan '$ROOT/tests/fixtures/loop_maturity/test-plan-complete-required.json' --require-test-results '$ROOT/tests/fixtures/loop_maturity/test-results-complete-required.json' --json | jq -e '.status == \"pass\" and (.missing_executed_required_tests | length) == 0 and (.executed_required_tests | index(\"required:test-selection\")) != null' >/dev/null"
assert "loop-test-selection blocks missing executed required results" "if '$ROOT/bin/adlc' loop-test-selection --loop-contract '$ROOT/tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json' --test-plan '$ROOT/tests/fixtures/loop_maturity/test-plan-complete-required.json' --require-test-results '$ROOT/tests/fixtures/loop_maturity/test-results-missing-required.json' --json >'$tmp_dir/loop-tests-missing-results.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and (.missing_executed_required_tests | index(\"required:test-selection\")) != null and any(.issues[]; .rule == \"missing_executed_required_tests\")' '$tmp_dir/loop-tests-missing-results.json' >/dev/null; fi"
assert "loop-test-selection blocks missing required tests" "if '$ROOT/bin/adlc' loop-test-selection --loop-contract '$ROOT/tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json' --test-plan '$ROOT/tests/fixtures/loop_maturity/test-plan-missing-required.json' --json >'$tmp_dir/loop-tests-missing.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and (.missing_required_tests | index(\"required:test-selection\")) != null and any(.issues[]; .rule == \"missing_required_tests\")' '$tmp_dir/loop-tests-missing.json' >/dev/null; fi"
assert "loop-budget-check proceeds on healthy budget" "'$ROOT/bin/adlc' loop-budget-check --token-budget '$ROOT/tests/fixtures/loop_maturity/token-budget-healthy.json' --estimated-input-tokens 10 --expected-output-tokens 10 --phase phase_5_codegen_context --skill codegen-context --json | jq -e '.status == \"proceed\" and .budget_status.status == \"healthy\" and .projected_total == 1020 and .budget_remaining == 98980' >/dev/null"
assert "loop-budget-check warns on warning budget" "'$ROOT/bin/adlc' loop-budget-check --token-budget '$ROOT/tests/fixtures/loop_maturity/token-budget-warning.json' --estimated-input-tokens 10 --expected-output-tokens 10 --phase phase_5_codegen_context --skill codegen-context --json | jq -e '.status == \"warning\" and .budget_status.status == \"warning\"' >/dev/null"
assert "loop-budget-check wraps up on alert threshold" "'$ROOT/bin/adlc' loop-budget-check --token-budget '$ROOT/tests/fixtures/loop_maturity/token-budget-warning.json' --estimated-input-tokens 30000 --expected-output-tokens 0 --phase phase_5_codegen_context --skill codegen-context --json | jq -e '.status == \"wrap_up\" and .budget_status.status == \"alert\" and .threshold == \"alert_at\"' >/dev/null"
assert "loop-budget-check blocks exhausted budget" "if '$ROOT/bin/adlc' loop-budget-check --token-budget '$ROOT/tests/fixtures/loop_maturity/token-budget-exhausted.json' --estimated-input-tokens 10 --expected-output-tokens 10 --phase phase_5_codegen_context --skill codegen-context --json >'$tmp_dir/loop-budget-exhausted.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and .stop_reason == \"budget_exhausted\" and .budget_status.status == \"exhausted\"' '$tmp_dir/loop-budget-exhausted.json' >/dev/null; fi"
assert "loop-budget-check blocks stale budget" "if '$ROOT/bin/adlc' loop-budget-check --token-budget '$ROOT/tests/fixtures/loop_maturity/token-budget-stale.json' --estimated-input-tokens 10 --expected-output-tokens 10 --phase phase_5_codegen_context --skill codegen-context --json >'$tmp_dir/loop-budget-stale.json' 2>/dev/null; then false; else jq -e '.status == \"blocked\" and .stop_reason == \"budget_stale\" and .budget_status.status == \"stale\"' '$tmp_dir/loop-budget-stale.json' >/dev/null; fi"
assert "loop-action-validate admits allowed action" "'$ROOT/bin/adlc' loop-action-validate --loop-contract '$ROOT/tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json' --action '$ROOT/tests/fixtures/loop_maturity/valid-loop-action.json' --state '$ROOT/tests/fixtures/loop_maturity/workflow-state-control-progress.json' --json | jq -e '.status == \"admitted\" and .action_id == \"action:run-required-test-selection\"' >/dev/null"
assert "loop-action-validate admits budgeted action with healthy budget" "'$ROOT/bin/adlc' loop-action-validate --loop-contract '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-contract.json' --action '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-action.json' --state '$ROOT/tests/fixtures/loop_maturity/workflow-state-budget-progress.json' --token-budget '$ROOT/tests/fixtures/loop_maturity/token-budget-healthy.json' --json | jq -e '.status == \"admitted\" and .budget_status.status == \"healthy\" and .budget_check.status == \"proceed\"' >/dev/null"
assert "loop-action-validate resolves contract budget guard ref" "'$ROOT/bin/adlc' loop-action-validate --loop-contract '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-contract.json' --action '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-action.json' --state '$ROOT/tests/fixtures/loop_maturity/workflow-state-budget-progress.json' --json | jq -e '.status == \"admitted\" and .budget_status.token_budget_ref == \"tests/fixtures/loop_maturity/token-budget-healthy.json\" and .budget_check.status == \"proceed\"' >/dev/null"
assert "loop-action-validate rejects exhausted budget before execution" "if '$ROOT/bin/adlc' loop-action-validate --loop-contract '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-contract.json' --action '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-action.json' --state '$ROOT/tests/fixtures/loop_maturity/workflow-state-budget-progress.json' --token-budget '$ROOT/tests/fixtures/loop_maturity/token-budget-exhausted.json' --json >'$tmp_dir/loop-action-budget-rejected.json' 2>/dev/null; then false; else jq -e '.status == \"rejected\" and .budget_status.status == \"exhausted\" and any(.issues[]; .rule == \"budget_exhausted\")' '$tmp_dir/loop-action-budget-rejected.json' >/dev/null; fi"
assert "loop-action-validate rejects skipped required tests" "if '$ROOT/bin/adlc' loop-action-validate --loop-contract '$ROOT/tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json' --action '$ROOT/tests/fixtures/loop_maturity/rejected-loop-action.json' --state '$ROOT/tests/fixtures/loop_maturity/workflow-state-control-progress.json' --json >'$tmp_dir/loop-action-rejected.json' 2>/dev/null; then false; else jq -e '.status == \"rejected\" and any(.issues[]; .rule == \"action_skips_required_tests\" and (.missing_required_tests | index(\"required:test-selection\")))' '$tmp_dir/loop-action-rejected.json' >/dev/null; fi"
assert "loop-action-validate routes escalation with context" "'$ROOT/bin/adlc' loop-action-validate --loop-contract '$ROOT/tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json' --action '$ROOT/tests/fixtures/loop_maturity/escalate-loop-action.json' --state '$ROOT/tests/fixtures/loop_maturity/workflow-state-control-progress.json' --json | jq -e '.status == \"escalate\" and .escalation_context.no_progress_after == 2' >/dev/null"
assert "loop-maturity-audit caps tag-only test selection score" "'$ROOT/bin/adlc' loop-maturity-audit --loop-contract '$ROOT/tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json' --workflow '$ROOT/WORKFLOW.dot' --state '$ROOT/tests/fixtures/loop_maturity/workflow-state-control-progress.json' --test-plan '$ROOT/tests/fixtures/loop_maturity/test-plan-complete-required.json' --action '$ROOT/tests/fixtures/loop_maturity/valid-loop-action.json' --json | jq -e '.maturity_verdict == \"assisted_loop\" and .dimension_scores.test_selection_cannot_be_gamed.score == 2 and (.dimension_scores.test_selection_cannot_be_gamed.missing_mechanisms | index(\"executed required-test evidence\")) != null' >/dev/null"
assert "loop-maturity-audit emits schema-valid execution-backed assisted-loop report" "'$ROOT/bin/adlc' loop-maturity-audit --loop-contract '$ROOT/tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json' --workflow '$ROOT/WORKFLOW.dot' --state '$ROOT/tests/fixtures/loop_maturity/workflow-state-control-progress.json' --test-plan '$ROOT/tests/fixtures/loop_maturity/test-plan-complete-required.json' --test-results '$ROOT/tests/fixtures/loop_maturity/test-results-complete-required.json' --action '$ROOT/tests/fixtures/loop_maturity/valid-loop-action.json' --output '$tmp_dir/generated-loop-report.json' --json | jq -e '.maturity_verdict == \"assisted_loop\" and .action_admission.status == \"admitted\" and .dimension_scores.test_selection_cannot_be_gamed.score == 3' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema loop-maturity-report --input '$tmp_dir/generated-loop-report.json' --json | jq -e '.valid == true' >/dev/null"
assert "loop-maturity-audit emits budget status with healthy budget" "'$ROOT/bin/adlc' loop-maturity-audit --loop-contract '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-contract.json' --workflow '$ROOT/WORKFLOW.dot' --state '$ROOT/tests/fixtures/loop_maturity/workflow-state-budget-progress.json' --test-plan '$ROOT/tests/fixtures/loop_maturity/test-plan-complete-required.json' --test-results '$ROOT/tests/fixtures/loop_maturity/test-results-complete-required.json' --action '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-action.json' --token-budget '$ROOT/tests/fixtures/loop_maturity/token-budget-healthy.json' --output '$tmp_dir/generated-budgeted-loop-report.json' --json | jq -e '.maturity_verdict == \"assisted_loop\" and .budget_status.status == \"healthy\" and .budget_status.decision == \"proceed\"' >/dev/null && '$ROOT/bin/adlc' validate-artifact --schema loop-maturity-report --input '$tmp_dir/generated-budgeted-loop-report.json' --json | jq -e '.valid == true' >/dev/null"
assert "loop-maturity-audit resolves contract budget guard ref" "'$ROOT/bin/adlc' loop-maturity-audit --loop-contract '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-contract.json' --workflow '$ROOT/WORKFLOW.dot' --state '$ROOT/tests/fixtures/loop_maturity/workflow-state-budget-progress.json' --test-plan '$ROOT/tests/fixtures/loop_maturity/test-plan-complete-required.json' --test-results '$ROOT/tests/fixtures/loop_maturity/test-results-complete-required.json' --action '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-action.json' --json | jq -e '.maturity_verdict == \"assisted_loop\" and .budget_status.token_budget_ref == \"tests/fixtures/loop_maturity/token-budget-healthy.json\" and .budget_status.status == \"healthy\"' >/dev/null"
assert "loop-maturity-audit allows self-autonomous only with healthy budget evidence" "'$ROOT/bin/adlc' loop-maturity-audit --loop-contract '$ROOT/tests/fixtures/loop_maturity/self-autonomous-budgeted-contract.json' --workflow '$ROOT/WORKFLOW.dot' --state '$ROOT/tests/fixtures/loop_maturity/workflow-state-budget-progress.json' --test-plan '$ROOT/tests/fixtures/loop_maturity/test-plan-complete-required.json' --test-results '$ROOT/tests/fixtures/loop_maturity/test-results-complete-required.json' --action '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-action.json' --token-budget '$ROOT/tests/fixtures/loop_maturity/token-budget-healthy.json' --json | jq -e '.maturity_verdict == \"self_autonomous\" and .budget_status.status == \"healthy\"' >/dev/null"
assert "loop-maturity-audit downgrades self-autonomous warning budget" "'$ROOT/bin/adlc' loop-maturity-audit --loop-contract '$ROOT/tests/fixtures/loop_maturity/self-autonomous-budgeted-contract.json' --workflow '$ROOT/WORKFLOW.dot' --state '$ROOT/tests/fixtures/loop_maturity/workflow-state-budget-progress.json' --test-plan '$ROOT/tests/fixtures/loop_maturity/test-plan-complete-required.json' --test-results '$ROOT/tests/fixtures/loop_maturity/test-results-complete-required.json' --action '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-action.json' --token-budget '$ROOT/tests/fixtures/loop_maturity/token-budget-warning.json' --json | jq -e '.maturity_verdict == \"assisted_loop\" and .budget_status.status == \"warning\" and (.prioritized_gaps.blocks_autonomy[0] | contains(\"Loop Budget Guard\"))' >/dev/null"
jq 'del(.budget_guard)' "$ROOT/tests/fixtures/loop_maturity/self-autonomous-budgeted-contract.json" > "$tmp_dir/self-autonomous-missing-budget-contract.json"
assert "loop-maturity-audit downgrades self-autonomous missing budget" "'$ROOT/bin/adlc' loop-maturity-audit --loop-contract '$tmp_dir/self-autonomous-missing-budget-contract.json' --workflow '$ROOT/WORKFLOW.dot' --state '$ROOT/tests/fixtures/loop_maturity/workflow-state-budget-progress.json' --test-plan '$ROOT/tests/fixtures/loop_maturity/test-plan-complete-required.json' --test-results '$ROOT/tests/fixtures/loop_maturity/test-results-complete-required.json' --action '$ROOT/tests/fixtures/loop_maturity/budgeted-loop-action.json' --json | jq -e '.maturity_verdict == \"assisted_loop\" and .budget_status.status == \"missing\" and .budget_status.stop_reason == \"budget_missing\"' >/dev/null"
assert "loop-maturity-audit help exposes test-results and omits dead build-brief flag" "'$ROOT/bin/adlc' loop-maturity-audit --help >'$tmp_dir/loop-maturity-help.txt' && rg -q -- '--test-results' '$tmp_dir/loop-maturity-help.txt' && ! rg -q -- '--build-brief' '$tmp_dir/loop-maturity-help.txt'"

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
jq '(.sections."8_task_tickets"[0].work_item_metadata.loop_contract_path) = "tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json" | (.sections."8_task_tickets"[0].work_item_metadata.loop_action_path) = "tests/fixtures/loop_maturity/valid-loop-action.json" | (.sections."8_task_tickets"[0].work_item_metadata.loop_maturity_report_path) = "tests/fixtures/loop_maturity/assisted-loop-report.json"' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp_dir/loop-ref-brief.json"
assert "emit-work-items preserves loop contract refs" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/loop-ref-brief.json' --dry-run --json | jq -e '.artifacts[0].loop_contract_path == \"tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json\" and .artifacts[0].loop_action_path == \"tests/fixtures/loop_maturity/valid-loop-action.json\" and .artifacts[0].loop_maturity_report_path == \"tests/fixtures/loop_maturity/assisted-loop-report.json\"' >/dev/null"
jq '(.sections."8_task_tickets"[0].implementation_interface_contract) = {"id":"iface:cli-smoke","reuse":["scripts/adlc.py normalized_work_item_payload"],"consumes":["Build Brief task"],"emits":["normalized artifact"],"minimum_fields":[{"name":"task_id","kind":"string","constraint":"stable"}],"invariants":["optional fields remain optional"],"integration_points":["bin/adlc emit-work-items"],"validation_gates":["tests/test_adlc_cli.sh"]} | (.sections."8_task_tickets"[0].productionization_gate) = {"id":"prod:cli-smoke","claim":"CLI dry-run payload is production ready for local normalization.","coverage_state":"production_ready","operational_readiness":{"owner":"ADLC","rollback_path":"Revert the patch.","runbook_refs":["docs/specs/emitter-contract.md"]},"security_privacy":{"redaction_posture":"No secrets emitted."},"reliability_failure_modes":["Schema mismatch blocks mutation."],"validation_evidence":["tests/test_adlc_cli.sh"],"no_overclaim":["Does not prove external provider mutation."]}' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp_dir/interface-prod-brief.json"
assert "emit-work-items preserves implementation interface and productionization contracts" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/interface-prod-brief.json' --dry-run --require-ready --json | jq -e '.readiness_report.status == \"ready\" and .artifacts[0].implementation_interface_contract.id == \"iface:cli-smoke\" and .artifacts[0].productionization_gate.coverage_state == \"production_ready\" and .artifacts[0].productionization_gate.no_overclaim[0] == \"Does not prove external provider mutation.\"' >/dev/null"
jq '(.sections."8_task_tickets"[0].productionization_gate) = {"id":"prod:overclaim","claim":"Task is production ready without evidence.","coverage_state":"production_ready","operational_readiness":{"owner":"ADLC","rollback_path":"Revert the patch.","runbook_refs":["docs/specs/emitter-contract.md"]},"security_privacy":{"redaction_posture":"No secrets emitted."},"reliability_failure_modes":[],"validation_evidence":[],"no_overclaim":[]}' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp_dir/overclaimed-prod-brief.json"
assert "emit-work-items require-ready blocks overclaimed production_ready" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/overclaimed-prod-brief.json' --dry-run --json >'$tmp_dir/overclaimed-prod-result.json' && jq -e '.readiness_report.status == \"blocked\" and any(.readiness_report.issues[]; .rule == \"overclaimed_production_ready\")' '$tmp_dir/overclaimed-prod-result.json' >/dev/null && if '$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/overclaimed-prod-brief.json' --dry-run --require-ready --json >/dev/null 2>&1; then false; else true; fi"
jq '(.sections."8_task_tickets"[0].work_item_metadata.labels) = ["kitchen-loop","coverage-admission"] | (.sections."8_task_tickets"[0].implementation_interface_contract) = {"id":"iface:kitchen-loop-coverage-admission","reuse":["scripts/adlc_runtime/cli.py compute_readiness_report"],"consumes":["Build Brief task"],"emits":["readiness report"],"minimum_fields":[{"name":"task_id","kind":"string","constraint":"stable"}],"invariants":["Kitchen Loop refs are explicit and fail closed when missing."],"integration_points":["bin/adlc emit-work-items --require-ready"],"validation_gates":["tests/test_adlc_cli.sh"],"evidence_refs":["spec-surface:tests/fixtures/kitchen_loop/valid-spec-surface.json","scenario-coverage-plan:tests/fixtures/kitchen_loop/valid-scenario-coverage-plan.json","regression-oracle:tests/fixtures/kitchen_loop/valid-regression-oracle.json","drift-gate-report:tests/fixtures/kitchen_loop/valid-drift-gate-report.json"]}' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp_dir/kitchen-loop-ready-brief.json"
assert "emit-work-items passes Kitchen Loop coverage admission refs" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/kitchen-loop-ready-brief.json' --dry-run --require-ready --json | jq -e '.readiness_report.status == \"ready\" and .artifacts[0].implementation_interface_contract.id == \"iface:kitchen-loop-coverage-admission\"' >/dev/null"
jq '(.sections."8_task_tickets"[0].work_item_metadata.labels) = ["kitchen-loop","coverage-admission"] | (.sections."8_task_tickets"[0].implementation_interface_contract) = {"id":"iface:kitchen-loop-coverage-admission","reuse":["scripts/adlc_runtime/cli.py compute_readiness_report"],"consumes":["Build Brief task"],"emits":["readiness report"],"minimum_fields":[{"name":"task_id","kind":"string","constraint":"stable"}],"invariants":["Kitchen Loop refs are explicit and fail closed when missing."],"integration_points":["bin/adlc emit-work-items --require-ready"],"validation_gates":["tests/test_adlc_cli.sh"],"evidence_refs":["spec-surface:tests/fixtures/kitchen_loop/valid-spec-surface.json","scenario-coverage-plan:tests/fixtures/kitchen_loop/valid-scenario-coverage-plan.json","regression-oracle:tests/fixtures/kitchen_loop/valid-regression-oracle.json"]}' "$ROOT/docs/build-briefs/xia-adlc-remediation.json" > "$tmp_dir/kitchen-loop-missing-drift-brief.json"
assert "emit-work-items blocks Kitchen Loop coverage admission missing drift gate ref" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/kitchen-loop-missing-drift-brief.json' --dry-run --json >'$tmp_dir/kitchen-loop-missing-drift-result.json' && jq -e '.readiness_report.status == \"blocked\" and any(.readiness_report.issues[]; .rule == \"missing_kitchen_loop_drift_gate_ref\")' '$tmp_dir/kitchen-loop-missing-drift-result.json' >/dev/null && if '$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/kitchen-loop-missing-drift-brief.json' --dry-run --require-ready --json >/dev/null 2>&1; then false; else true; fi"
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
assert "emit-work-items mutation records side-effect run identity" "jq -e '. as \$state | (.run_id | startswith(\"adlc-run-\")) and (.session_id | startswith(\"adlc-\")) and .brief_id == \"SMOKE-BRIEF-FEATURE-BUGFIX\" and all(.side_effects[]; .brief_id == \$state.brief_id and .run_id == \$state.run_id and .session_id == \$state.session_id)' '$tmp_dir/emitter/.adlc/workflow_state.json' >/dev/null"
assert "emit-work-items mutation records provider-returned target metadata" "jq -e 'any(.side_effects[]; .idempotency_key == \"SMOKE-BRIEF-FEATURE-BUGFIX:linear:SMOKE_BUGFIX_AVERAGE:upsert\" and .artifact_id == \"LIN-SMOKE_BUGFIX_AVERAGE\" and .artifact_ref == \"linear://LIN-SMOKE_BUGFIX_AVERAGE\")' '$tmp_dir/emitter/.adlc/workflow_state.json' >/dev/null"
jq '.sections."8_task_tickets"[1].dependencies = ["LIN-SMOKE_BUGFIX_AVERAGE"]' "$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json" > "$tmp_dir/provider-dep-brief.json"
assert "emit-work-items resolves dependencies to provider-returned target artifact ids" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$tmp_dir/provider-dep-brief.json' --workspace '$tmp_dir/emitter' --dry-run --require-ready --json | jq -e '.readiness_report.status == \"ready\" and any(.dependency_links[]; .from == \"LIN-SMOKE_BUGFIX_AVERAGE\" and .to == \"SMOKE_FEATURE_SCOREBOARD\" and .type == \"blocks\")' >/dev/null"
assert "emit-work-items idempotency keys stay stable after resume" "'$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --workspace '$tmp_dir/emitter' --dry-run --json >'$tmp_dir/emitter-before-resume.json' && '$ROOT/bin/adlc' resume-workflow --workspace '$tmp_dir/emitter' --json >'$tmp_dir/emitter-resume.json' && '$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --workspace '$tmp_dir/emitter' --dry-run --json >'$tmp_dir/emitter-after-resume.json' && jq -s -e '.[0].run_identity.run_id == .[1].run_identity.run_id and (.[0].artifacts | map(.idempotency_key)) == (.[1].artifacts | map(.idempotency_key))' '$tmp_dir/emitter-before-resume.json' '$tmp_dir/emitter-after-resume.json' >/dev/null"
assert "emit-work-items surfaces per-artifact provider failures" "if '$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --workspace '$tmp_dir/partial-emitter' --allow-mutation --provider-command '$partial_provider' --json >'$tmp_dir/partial-result.json' 2>/dev/null; then false; else jq -e '.provider_result.status == \"failed\" and .provider_result.stop_reason == \"external_mutation_partial\" and any(.state.side_effects[]; .idempotency_key == \"SMOKE-BRIEF-FEATURE-BUGFIX:linear:SMOKE_FEATURE_SCOREBOARD:upsert\" and .status == \"failed\")' '$tmp_dir/partial-result.json' >/dev/null; fi"
assert "emit-work-items preserves partial stop reason on failed provider batches" "if '$ROOT/bin/adlc' emit-work-items --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --workspace '$tmp_dir/failed-emitter' --allow-mutation --provider-command '$failed_provider' --json >'$tmp_dir/failed-result.json' 2>/dev/null; then false; else jq -e '.provider_result.status == \"failed\" and .provider_result.stop_reason == \"external_mutation_partial\" and any(.state.side_effects[]; .idempotency_key == \"SMOKE-BRIEF-FEATURE-BUGFIX:linear:SMOKE_FEATURE_SCOREBOARD:upsert\" and .status == \"failed\")' '$tmp_dir/failed-result.json' >/dev/null; fi"

echo ""
echo "--- Work-Item State Sync ---"
sync_provider="$tmp_dir/sync-provider.sh"
cat > "$sync_provider" <<'SH'
#!/usr/bin/env bash
jq '{status:"completed", artifacts:(.operations | map({idempotency_key:.sync_idempotency_key, status:"completed", artifact_id:(.work_item.artifact_id // ("LIN-" + .work_item.task_id)), artifact_ref:(.work_item.artifact_ref // ("linear://" + .work_item.task_id))}))}'
SH
chmod +x "$sync_provider"
cat > "$tmp_dir/sync-tool-registry.json" <<'JSON'
{
  "version": "1.0.0",
  "default_policy": "deny",
  "tools": [
    {
      "name": "linear-work-item-sync",
      "description": "Sync Linear work-item state",
      "inputSchema": {},
      "side_effect_profile": "mutating",
      "permission_tier": "unrestricted",
      "available_phases": ["pr_prep"]
    }
  ]
}
JSON
assert "sync-work-item dry-run plans create for unknown stable ID" "'$ROOT/bin/adlc' sync-work-item --work-item '$ROOT/tests/fixtures/tracker_sync/run-update.json' --dry-run --json | jq -e '.dry_run == true and .operations[0].operation == \"create\" and .operations[0].reason == \"no_existing_external_id\" and .operations[0].external_id == \"SMOKE-BRIEF-FEATURE-BUGFIX:linear:SMOKE_BUGFIX_AVERAGE:upsert\" and .operations[0].status_update.blockers[0].code == \"verifier_failed\"' >/dev/null"
assert "sync-work-item dry-run appends to existing stable ID" "'$ROOT/bin/adlc' sync-work-item --work-item '$ROOT/tests/fixtures/tracker_sync/run-update.json' --existing-work-items '$ROOT/tests/fixtures/tracker_sync/existing-work-items.json' --dry-run --json | jq -e '.dry_run == true and .operations[0].operation == \"append\" and .operations[0].reason == \"matched_existing_work_items\" and .operations[0].work_item.artifact_id == \"LIN-SMOKE_BUGFIX_AVERAGE\"' >/dev/null"
assert "sync-work-item derives append operations from emitted Build Brief state" "'$ROOT/bin/adlc' sync-work-item --target linear --build-brief '$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json' --workspace '$tmp_dir/emitter' --dry-run --json | jq -e '.dry_run == true and (.operations | length) == 3 and all(.operations[]; .operation == \"append\" and .reason == \"matched_side_effects\") and .run_identity.run_id == .operations[0].run_identity.run_id and (.operations[0].status_update.evidence_refs[0] | endswith(\"/emitter/.adlc/workflow_state.json\"))' >/dev/null"
assert "sync-work-item mutation without provider command fails closed" "if '$ROOT/bin/adlc' sync-work-item --work-item '$ROOT/tests/fixtures/tracker_sync/run-update.json' --workspace '$tmp_dir/sync-missing-provider' --allow-mutation --tool-registry '$tmp_dir/sync-tool-registry.json' --json >'$tmp_dir/sync-missing-provider.json' 2>/dev/null; then false; else [ ! -e '$tmp_dir/sync-missing-provider/.adlc/workflow_state.json' ]; fi"
assert "sync-work-item mutation requires action admission and records state links" "'$ROOT/bin/adlc' sync-work-item --work-item '$ROOT/tests/fixtures/tracker_sync/run-update.json' --workspace '$tmp_dir/sync-mutate' --allow-mutation --provider-command '$sync_provider' --tool-registry '$tmp_dir/sync-tool-registry.json' --json >'$tmp_dir/sync-mutate.json' && jq -e '.dry_run == false and .admission.status == \"admitted\" and .provider_result.status == \"completed\" and .state.work_item_links[0].external_id == \"SMOKE-BRIEF-FEATURE-BUGFIX:linear:SMOKE_BUGFIX_AVERAGE:upsert\" and .state.work_item_links[0].status == \"created\" and any(.state.side_effects[]; .tool_name == \"linear-work-item-sync\" and .operation == \"create_work_item_status\" and .status == \"completed\")' '$tmp_dir/sync-mutate.json' >/dev/null"
assert "sync-work-item repeated mutation appends existing state link instead of creating duplicate" "'$ROOT/bin/adlc' sync-work-item --work-item '$ROOT/tests/fixtures/tracker_sync/run-update.json' --workspace '$tmp_dir/sync-mutate' --allow-mutation --provider-command '$sync_provider' --tool-registry '$tmp_dir/sync-tool-registry.json' --json >'$tmp_dir/sync-append.json' && jq -e '.operations[0].operation == \"append\" and .state.work_item_links[0].status == \"appended\" and (.state.work_item_links | length) == 1' '$tmp_dir/sync-append.json' >/dev/null"
assert "resume-workflow exposes linked work item state" "'$ROOT/bin/adlc' resume-workflow --workspace '$tmp_dir/sync-mutate' --json >'$tmp_dir/sync-resume.json' && jq -e '.next_action.work_item_links[0].external_id == \"SMOKE-BRIEF-FEATURE-BUGFIX:linear:SMOKE_BUGFIX_AVERAGE:upsert\" and .next_action.work_item_links[0].last_sync_idempotency_key != null' '$tmp_dir/sync-resume.json' >/dev/null"
assert "sync-work-item validates mutated workflow state" "'$ROOT/bin/adlc' validate-artifact --schema workflow-state --input '$tmp_dir/sync-mutate/.adlc/workflow_state.json' --json | jq -e '.valid == true and (.errors | length) == 0' >/dev/null"

echo ""
echo "--- MCP Wrapper ---"
cat > "$tmp_dir/mcp-tools-filter.jq" <<'JQ'
(.tools | length) >= 37
and any(.tools[]; .name == "adlc_validate_artifact" and (.inputSchema.required | index("schema")))
and any(.tools[]; .name == "adlc_health_check")
and any(.tools[]; .name == "adlc_ci" and .inputSchema.properties.suite.type == "array")
and any(.tools[]; .name == "adlc_action_admit" and (.inputSchema.required | index("tool_registry")) and .inputSchema.properties.allow_mutation.type == "boolean" and .inputSchema.properties.run_id.type == "string")
and any(.tools[]; .name == "adlc_run_phase")
and any(.tools[]; .name == "adlc_emit_work_items")
and any(.tools[]; .name == "adlc_sync_work_item" and .inputSchema.properties.allow_mutation.type == "boolean" and .inputSchema.properties.tool_registry.type == "string")
and any(.tools[]; .name == "adlc_queue_status")
and any(.tools[]; .name == "adlc_queue_claim" and .inputSchema.properties.tool_registry.type == "string")
and any(.tools[]; .name == "adlc_queue_complete" and .inputSchema.properties.evidence.type == "array")
and any(.tools[]; .name == "adlc_queue_block")
and any(.tools[]; .name == "adlc_queue_escalate")
and any(.tools[]; .name == "adlc_worktree_prepare" and .inputSchema.properties.worktree_root.type == "string")
and any(.tools[]; .name == "adlc_worktree_status")
and any(.tools[]; .name == "adlc_worktree_cleanup" and .inputSchema.properties.force.type == "boolean")
and any(.tools[]; .name == "adlc_compound_context")
and any(.tools[]; .name == "adlc_architecture_memory" and .inputSchema.properties.tool_registry.type == "string")
and any(.tools[]; .name == "adlc_memory_health" and .inputSchema.properties.primitive_proposals.type == "string")
and any(.tools[]; .name == "adlc_champion_holdout" and (.inputSchema.required | index("input")))
and any(.tools[]; .name == "adlc_loop_library" and .inputSchema.properties.template_id.pattern == "^[a-z0-9][a-z0-9-]*$")
and any(.tools[]; .name == "adlc_loop_template_install" and (.inputSchema.required | index("template_id")) and .inputSchema.properties.tool_registry.type == "string")
and any(.tools[]; .name == "adlc_coverage_surface_validate" and (.inputSchema.required | index("input")))
and any(.tools[]; .name == "adlc_scenario_coverage_plan" and (.inputSchema.required | index("input")) and .inputSchema.properties.spec_surface.type == "string")
and any(.tools[]; .name == "adlc_regression_oracle_validate" and (.inputSchema.required | index("input")))
and any(.tools[]; .name == "adlc_drift_gate_evaluate" and (.inputSchema.required | index("input")) and .inputSchema.properties.history.type == "string")
and any(.tools[]; .name == "adlc_loop_test_selection" and .inputSchema.properties.require_test_results.type == "boolean")
and any(.tools[]; .name == "adlc_loop_budget_check" and (.inputSchema.required | index("token_budget")) and .inputSchema.properties.estimated_input_tokens.type == "integer")
and any(.tools[]; .name == "adlc_loop_action_validate" and .inputSchema.properties.token_budget.type == "string")
and any(.tools[]; .name == "adlc_loop_maturity_audit" and .inputSchema.properties.test_results.type == "string" and .inputSchema.properties.token_budget.type == "string" and (.inputSchema.properties | has("build_brief") | not))
and any(.tools[]; .name == "adlc_looper_status" and .inputSchema.properties.workspace.type == "string")
and any(.tools[]; .name == "adlc_loop_design_validate" and (.inputSchema.required | index("input")))
and any(.tools[]; .name == "adlc_loop_contract_from_design" and (.inputSchema.required | index("loop_design")))
and any(.tools[]; .name == "adlc_beads_status" and .inputSchema.properties.workspace.type == "string")
JQ
assert "mcp-tools emits MCP tool declarations" "'$ROOT/bin/adlc' mcp-tools --json | jq -e -f '$tmp_dir/mcp-tools-filter.jq' >/dev/null"
assert "mcp-serve handles initialize and tools/list" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"0\"}}}' '{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}' | '$ROOT/bin/adlc' mcp-serve | jq -s -e '.[0].result.capabilities.tools.listChanged == false and any(.[1].result.tools[]; .name == \"adlc_list_agents\")' >/dev/null"
assert "mcp-serve calls adlc_list_agents" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_list_agents\",\"arguments\":{}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.count >= 11' >/dev/null"
assert "mcp-serve calls health check" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_health_check\",\"arguments\":{}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"pass\"' >/dev/null"
assert "mcp-serve calls beads status preflight" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_beads_status\",\"arguments\":{\"workspace\":\"'$tmp_dir'\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"not_configured\"' >/dev/null"
assert "mcp-serve calls looper status preflight" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_looper_status\",\"arguments\":{\"workspace\":\"'$tmp_dir'\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"not_configured\"' >/dev/null"
assert "mcp-serve calls loop design validation" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_loop_design_validate\",\"arguments\":{\"input\":\"tests/fixtures/loop_design/valid-looper-design.json\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"pass\"' >/dev/null"
assert "mcp-serve calls loop contract from design" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_loop_contract_from_design\",\"arguments\":{\"loop_design\":\"tests/fixtures/loop_design/valid-looper-design.json\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.contract_id == \"adlc-loop-design:shipped-change-reconcile\"' >/dev/null"
assert "mcp-serve calls Kitchen Loop surface validation" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_coverage_surface_validate\",\"arguments\":{\"input\":\"tests/fixtures/kitchen_loop/valid-spec-surface.json\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"pass\"' >/dev/null"
assert "mcp-serve calls Kitchen Loop scenario coverage validation" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_scenario_coverage_plan\",\"arguments\":{\"input\":\"tests/fixtures/kitchen_loop/valid-scenario-coverage-plan.json\",\"spec_surface\":\"tests/fixtures/kitchen_loop/valid-spec-surface.json\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"pass\"' >/dev/null"
assert "mcp-serve calls Kitchen Loop oracle validation" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_regression_oracle_validate\",\"arguments\":{\"input\":\"tests/fixtures/kitchen_loop/valid-regression-oracle.json\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"pass\"' >/dev/null"
assert "mcp-serve calls Kitchen Loop drift gate evaluation" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_drift_gate_evaluate\",\"arguments\":{\"input\":\"tests/fixtures/kitchen_loop/valid-drift-gate-report.json\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"pass\"' >/dev/null"
assert "mcp-serve calls selectable ci suites" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_ci\",\"arguments\":{\"suite\":[\"health-check\",\"py-compile\"]}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"pass\" and .result.structuredContent.summary.total == 2' >/dev/null"
assert "mcp-serve calls action admission" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_action_admit\",\"arguments\":{\"tool_registry\":\"'$tmp_dir'/action-tool-registry.json\",\"tool\":\"Read\",\"action\":\"read_file\",\"phase\":\"research\",\"brief_id\":\"BRF-ACTION\",\"run_id\":\"RUN-ACTION\",\"session_id\":\"SESSION-ACTION\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"admitted\" and .result.structuredContent.run_identity.run_id == \"RUN-ACTION\" and .result.structuredContent.audit_trail.entries[0].decision == \"approved\" and .result.structuredContent.audit_trail.entries[0].run_id == \"RUN-ACTION\"' >/dev/null"
assert "mcp-serve calls architecture memory dry-run" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_architecture_memory\",\"arguments\":{\"input\":\"'$tmp_dir'/architecture-memory-candidate.json\",\"workspace\":\"'$memory_repo'\",\"dry_run\":true}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"planned\" and .result.structuredContent.summary.candidates == 1' >/dev/null"
assert "mcp-serve calls memory health audit" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_memory_health\",\"arguments\":{\"workspace\":\"'$memory_repo'\",\"changed_path\":[\"docs/specs/compound-engineering-learning-store.md\"]}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"stale\" and .result.structuredContent.summary.architecture_entries == 1' >/dev/null"
assert "mcp-serve calls champion holdout evaluation" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_champion_holdout\",\"arguments\":{\"input\":\"'$tmp_dir'/champion-holdout-pass.json\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"promote\" and .result.structuredContent.decision == \"promote_challenger\"' >/dev/null"
assert "mcp-serve calls loop library inspect" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_loop_library\",\"arguments\":{\"template_id\":\"ci-triage\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.summary.template_id == \"ci-triage\" and .result.structuredContent.generated_artifact_validation.valid == true' >/dev/null"
assert "mcp-serve calls loop template install dry-run" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_loop_template_install\",\"arguments\":{\"template_id\":\"ci-triage\",\"workspace\":\"'$tmp_dir'/mcp-loop-install\",\"dry_run\":true}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"planned\" and .result.structuredContent.summary.planned == 6' >/dev/null"
assert "mcp-serve calls work item sync dry-run" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_sync_work_item\",\"arguments\":{\"work_item\":\"tests/fixtures/tracker_sync/run-update.json\",\"existing_work_items\":\"tests/fixtures/tracker_sync/existing-work-items.json\",\"dry_run\":true}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.operations[0].operation == \"append\" and .result.structuredContent.operations[0].reason == \"matched_existing_work_items\"' >/dev/null"
assert "mcp-serve calls queue status" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_queue_status\",\"arguments\":{\"queue\":\"tests/fixtures/work_queue/valid-queue.json\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.summary.counts.queued == 3 and .result.structuredContent.summary.active == 2' >/dev/null"
assert "mcp-serve calls queue claim dry-run" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_queue_claim\",\"arguments\":{\"queue\":\"tests/fixtures/work_queue/valid-queue.json\",\"task_id\":\"ADLC-G5-CLAIMABLE\",\"workspace\":\"'$queue_repo'\",\"dry_run\":true}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"pass\" and .result.structuredContent.planned_task.status == \"claimed\"' >/dev/null"
assert "mcp-serve calls worktree prepare dry-run" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_worktree_prepare\",\"arguments\":{\"queue\":\"tests/fixtures/work_queue/valid-queue.json\",\"task_id\":\"ADLC-G5-CLAIMABLE\",\"workspace\":\"'$queue_repo'\",\"dry_run\":true}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"pass\" and .result.structuredContent.worktree.branch == \"adlc/adlc-g5-claimable-47fdcbfd\"' >/dev/null"
assert "mcp-serve calls strict loop test selection" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_loop_test_selection\",\"arguments\":{\"loop_contract\":\"tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json\",\"test_plan\":\"tests/fixtures/loop_maturity/test-plan-complete-required.json\",\"test_results\":\"tests/fixtures/loop_maturity/test-results-complete-required.json\",\"require_test_results\":true}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"pass\" and (.result.structuredContent.executed_required_tests | index(\"required:test-selection\")) != null' >/dev/null"
assert "mcp-serve calls loop budget check" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_loop_budget_check\",\"arguments\":{\"token_budget\":\"tests/fixtures/loop_maturity/token-budget-healthy.json\",\"estimated_input_tokens\":10,\"expected_output_tokens\":10,\"phase\":\"phase_5_codegen_context\",\"skill\":\"codegen-context\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"proceed\" and .result.structuredContent.budget_status.status == \"healthy\"' >/dev/null"
assert "mcp-serve calls loop action validation" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_loop_action_validate\",\"arguments\":{\"loop_contract\":\"tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json\",\"action\":\"tests/fixtures/loop_maturity/valid-loop-action.json\",\"state\":\"tests/fixtures/loop_maturity/workflow-state-control-progress.json\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"admitted\"' >/dev/null"
assert "mcp-serve calls budgeted loop action validation" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_loop_action_validate\",\"arguments\":{\"loop_contract\":\"tests/fixtures/loop_maturity/budgeted-loop-contract.json\",\"action\":\"tests/fixtures/loop_maturity/budgeted-loop-action.json\",\"state\":\"tests/fixtures/loop_maturity/workflow-state-budget-progress.json\",\"token_budget\":\"tests/fixtures/loop_maturity/token-budget-healthy.json\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"admitted\" and .result.structuredContent.budget_status.status == \"healthy\"' >/dev/null"
assert "mcp-serve resolves contract budget guard ref for action validation" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_loop_action_validate\",\"arguments\":{\"loop_contract\":\"tests/fixtures/loop_maturity/budgeted-loop-contract.json\",\"action\":\"tests/fixtures/loop_maturity/budgeted-loop-action.json\",\"state\":\"tests/fixtures/loop_maturity/workflow-state-budget-progress.json\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.status == \"admitted\" and .result.structuredContent.budget_status.token_budget_ref == \"tests/fixtures/loop_maturity/token-budget-healthy.json\"' >/dev/null"
assert "mcp-serve calls loop maturity audit" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_loop_maturity_audit\",\"arguments\":{\"loop_contract\":\"tests/fixtures/loop_maturity/adlc-assisted-loop-contract.json\",\"workflow\":\"WORKFLOW.dot\",\"state\":\"tests/fixtures/loop_maturity/workflow-state-control-progress.json\",\"test_plan\":\"tests/fixtures/loop_maturity/test-plan-complete-required.json\",\"test_results\":\"tests/fixtures/loop_maturity/test-results-complete-required.json\",\"action\":\"tests/fixtures/loop_maturity/valid-loop-action.json\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.maturity_verdict == \"assisted_loop\" and .result.structuredContent.dimension_scores.test_selection_cannot_be_gamed.score == 3' >/dev/null"
assert "mcp-serve calls budgeted loop maturity audit" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_loop_maturity_audit\",\"arguments\":{\"loop_contract\":\"tests/fixtures/loop_maturity/budgeted-loop-contract.json\",\"workflow\":\"WORKFLOW.dot\",\"state\":\"tests/fixtures/loop_maturity/workflow-state-budget-progress.json\",\"test_plan\":\"tests/fixtures/loop_maturity/test-plan-complete-required.json\",\"test_results\":\"tests/fixtures/loop_maturity/test-results-complete-required.json\",\"action\":\"tests/fixtures/loop_maturity/budgeted-loop-action.json\",\"token_budget\":\"tests/fixtures/loop_maturity/token-budget-healthy.json\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.maturity_verdict == \"assisted_loop\" and .result.structuredContent.budget_status.status == \"healthy\"' >/dev/null"
assert "mcp-serve resolves contract budget guard ref for maturity audit" "printf '%s\n' '{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"tools/call\",\"params\":{\"name\":\"adlc_loop_maturity_audit\",\"arguments\":{\"loop_contract\":\"tests/fixtures/loop_maturity/budgeted-loop-contract.json\",\"workflow\":\"WORKFLOW.dot\",\"state\":\"tests/fixtures/loop_maturity/workflow-state-budget-progress.json\",\"test_plan\":\"tests/fixtures/loop_maturity/test-plan-complete-required.json\",\"test_results\":\"tests/fixtures/loop_maturity/test-results-complete-required.json\",\"action\":\"tests/fixtures/loop_maturity/budgeted-loop-action.json\"}}}' | '$ROOT/bin/adlc' mcp-serve | jq -e '.result.isError == false and .result.structuredContent.maturity_verdict == \"assisted_loop\" and .result.structuredContent.budget_status.token_budget_ref == \"tests/fixtures/loop_maturity/token-budget-healthy.json\"' >/dev/null"

echo ""
printf 'Results: %b%s passed%b, %b%s failed%b, %s total\n' "$GREEN" "$PASS" "$NC" "$RED" "$FAIL" "$NC" "$TOTAL"

if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
