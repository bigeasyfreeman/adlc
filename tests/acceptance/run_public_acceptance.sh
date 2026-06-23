#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP_PARENT="${ADLC_ACCEPTANCE_TMPDIR:-${TMPDIR:-/tmp}}"
TMP_ROOT="$(mktemp -d "$TMP_PARENT/adlc-public-acceptance.XXXXXX")"
TARGET="$TMP_ROOT/target"

cleanup() {
  local status=$?
  if [ "$status" -eq 0 ] && [ "${ADLC_ACCEPTANCE_KEEP_TMP:-0}" != "1" ]; then
    rm -rf "$TMP_ROOT"
  else
    printf 'Acceptance temp retained: %s\n' "$TMP_ROOT" >&2
  fi
}
trap cleanup EXIT

step() {
  printf '  %s\n' "$1"
}

require() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$name" >&2
    exit 2
  fi
}

require git
require jq
require python3

echo "ADLC Public Acceptance"
echo "Root:   $ROOT"
echo "Target: $TARGET"
echo ""

step "Create a realistic target repo with a failing verifier"
mkdir -p "$TARGET/app" "$TARGET/tests" "$TARGET/.adlc"
cat > "$TARGET/.gitignore" <<'EOF'
.adlc/
__pycache__/
*.pyc
EOF
cat > "$TARGET/app/calculator.py" <<'PY'
def average(values):
    if not values:
        return 0
    return sum(values)  # bug: missing division
PY
cat > "$TARGET/tests/test_calculator.py" <<'PY'
import unittest
from app.calculator import average


class CalculatorTests(unittest.TestCase):
    def test_average(self):
        self.assertEqual(average([2, 4, 6]), 4)


if __name__ == "__main__":
    unittest.main()
PY
: > "$TARGET/app/__init__.py"
git -C "$TARGET" init -q
git -C "$TARGET" config user.email adlc@example.invalid
git -C "$TARGET" config user.name ADLC
git -C "$TARGET" add .
git -C "$TARGET" commit -qm init

step "Install ADLC into the target repo and commit installable config"
"$ROOT/setup.sh" codex "$TARGET" >/dev/null
git -C "$TARGET" add .agents AGENTS.md .gitignore
git -C "$TARGET" commit -qm "Install ADLC codex config"
ADLC="$TARGET/.adlc/bin/adlc"
"$ADLC" health-check --json | jq -e '.status == "pass"' >/dev/null

step "Feed realistic repo and ticket signals into the meta-harness planner"
cat > "$TARGET/.adlc/signals.json" <<'JSON'
{
  "signals": [
    {
      "signal_id": "calc-average-ci-failure",
      "title": "CI failure in calculator average behavior",
      "summary": "The average helper returns the sum instead of the arithmetic mean.",
      "labels": ["workflow_run_failed", "ci", "bugfix"],
      "expected_paths": [
        {"path": "app/calculator.py", "kind": "file", "reason": "failing implementation scope"}
      ],
      "verifier_refs": ["python3 -m unittest discover -s tests"],
      "value_score": 82,
      "risk_score": 20,
      "verifiability_score": 95,
      "repeatability_score": 80,
      "urgency_score": 70,
      "template_id": "ci-triage"
    },
    {
      "signal_id": "payment-provider-rewrite",
      "title": "Rewrite payment provider abstraction",
      "labels": ["payments", "architecture"],
      "expected_paths": [
        {"path": "app/payments", "kind": "directory", "reason": "high-risk domain"}
      ],
      "verifier_refs": ["python3 -m unittest discover -s tests"],
      "value_score": 90,
      "risk_score": 96,
      "verifiability_score": 35,
      "repeatability_score": 25,
      "urgency_score": 30
    }
  ]
}
JSON
"$ADLC" meta-harness-plan \
  --signals "$TARGET/.adlc/signals.json" \
  --workspace "$TARGET" \
  --output "$TARGET/.adlc/meta_plan.json" \
  --json > "$TMP_ROOT/meta.json"
jq -e '
  .status == "planned" and
  .summary.admitted_count == 1 and
  .summary.needs_human_count == 1 and
  any(.selected[]; .candidate_id == "calc-average-ci-failure" and .selected_template_id == "ci-triage" and .decision == "admit_to_queue") and
  any(.selected[]; .candidate_id == "payment-provider-rewrite" and .decision == "needs_human") and
  (.boundary.does_not | index("dispatch agents")) != null
' "$TMP_ROOT/meta.json" >/dev/null

step "Materialize and validate planner-generated queue and tracker sync artifacts"
jq '.generated_artifacts.work_queue_seed' "$TMP_ROOT/meta.json" > "$TARGET/.adlc/work_queue.json"
"$ADLC" validate-artifact --schema work-queue --input "$TARGET/.adlc/work_queue.json" --json |
  jq -e '.valid == true' >/dev/null
TASK_ID="$(jq -r '.generated_artifacts.work_queue_seed.tasks[0].task_id' "$TMP_ROOT/meta.json")"
SYNC_FILE="$TARGET/.adlc/work_item_sync.json"
jq '.generated_artifacts.work_item_syncs[0]' "$TMP_ROOT/meta.json" > "$SYNC_FILE"
"$ADLC" validate-artifact --schema work-item-sync --input "$SYNC_FILE" --json |
  jq -e '.valid == true' >/dev/null

step "Install the selected packaged loop through action admission"
cat > "$TARGET/.adlc/loop-library-tool-registry.json" <<'JSON'
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
"$ADLC" loop-template-install \
  --template-id ci-triage \
  --workspace "$TARGET" \
  --allow-mutation \
  --tool-registry "$TARGET/.adlc/loop-library-tool-registry.json" \
  --json > "$TMP_ROOT/install.json"
jq -e '.status == "pass" and .summary.written == 6' "$TMP_ROOT/install.json" >/dev/null
for schema_file in \
  loop-contract:"$TARGET/.adlc/loops/ci-triage/loop_contract.json" \
  tool-registry:"$TARGET/.adlc/loops/ci-triage/tool_registry.json" \
  work-queue:"$TARGET/.adlc/loops/ci-triage/work_queue_seed.json" \
  token-budget:"$TARGET/.adlc/loops/ci-triage/token_budget.json" \
  loop-template-install-report:"$TARGET/.adlc/loops/ci-triage/install_report.json"; do
  schema="${schema_file%%:*}"
  file="${schema_file#*:}"
  "$ADLC" validate-artifact --schema "$schema" --input "$file" --json |
    jq -e '.valid == true' >/dev/null
done

step "Prove queue and worktree gates operate against a clean target checkout"
"$ADLC" queue-claim \
  --queue "$TARGET/.adlc/work_queue.json" \
  --task-id "$TASK_ID" \
  --workspace "$TARGET" \
  --dry-run \
  --json > "$TMP_ROOT/claim.json"
jq -e '.status == "pass" and .planned_task.status == "claimed" and .git.dirty == false' \
  "$TMP_ROOT/claim.json" >/dev/null
"$ADLC" worktree-prepare \
  --queue "$TARGET/.adlc/work_queue.json" \
  --task-id "$TASK_ID" \
  --workspace "$TARGET" \
  --dry-run \
  --json > "$TMP_ROOT/worktree.json"
jq -e '.status == "pass" and .git.dirty == false and (.worktree.branch | startswith("adlc/"))' \
  "$TMP_ROOT/worktree.json" >/dev/null

step "Prove the verifier fails before the fix and passes after a bounded repair"
if "$ADLC" run-phase qa \
  --brief-id ACCEPTANCE \
  --workspace "$TARGET" \
  --verifier 'python3 -m unittest discover -s tests' \
  --json > "$TMP_ROOT/qa-fail.json" 2>/dev/null; then
  printf 'Expected pre-fix QA to fail, but it passed.\n' >&2
  exit 1
fi
jq -e '.tool_result.status == "fail" and .tool_result.stop_reason == "verifier_failed"' \
  "$TMP_ROOT/qa-fail.json" >/dev/null
python3 - "$TARGET/app/calculator.py" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.write_text(
    "def average(values):\n"
    "    if not values:\n"
    "        return 0\n"
    "    return sum(values) / len(values)\n",
    encoding="utf-8",
)
PY
git -C "$TARGET" add app/calculator.py
git -C "$TARGET" commit -qm "Fix calculator average"
"$ADLC" run-phase qa \
  --brief-id ACCEPTANCE \
  --workspace "$TARGET" \
  --verifier 'python3 -m unittest discover -s tests' \
  --json > "$TMP_ROOT/qa-pass.json"
jq -e '.tool_result.status == "pass" and .state.phase == "pr_prep"' "$TMP_ROOT/qa-pass.json" >/dev/null

step "Complete the queue item and produce a tracker sync dry-run"
"$ADLC" queue-complete \
  --queue "$TARGET/.adlc/work_queue.json" \
  --task-id "$TASK_ID" \
  --workspace "$TARGET" \
  --evidence 'python3 -m unittest discover -s tests' \
  --dry-run \
  --json > "$TMP_ROOT/complete.json"
jq -e '.status == "pass" and .planned_task.status == "done"' "$TMP_ROOT/complete.json" >/dev/null
"$ADLC" sync-work-item \
  --work-item "$SYNC_FILE" \
  --workspace "$TARGET" \
  --dry-run \
  --json > "$TMP_ROOT/sync.json"
jq -e '.dry_run == true and (.operations | length) == 1 and (.operations[0].operation == "create" or .operations[0].operation == "append")' \
  "$TMP_ROOT/sync.json" >/dev/null

step "Verify the installed wrapper exposes the control-plane MCP tools"
"$ADLC" mcp-tools --json |
  jq -e '
    any(.tools[]; .name == "adlc_meta_harness_plan") and
    any(.tools[]; .name == "adlc_queue_claim") and
    any(.tools[]; .name == "adlc_sync_work_item")
  ' >/dev/null

echo ""
echo "Public acceptance passed."
