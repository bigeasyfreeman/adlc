#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP_PARENT="${ADLC_ACCEPTANCE_TMPDIR:-${TMPDIR:-/tmp}}"
TMP_ROOT="$(mktemp -d "$TMP_PARENT/adlc-public-fix.XXXXXX")"
TARGET="$TMP_ROOT/target"
REPORT="$TMP_ROOT/public-fix.report.json"
START_MS="$(python3 -c 'import time; print(int(time.time() * 1000))')"

cleanup() {
  local status=$?
  if [ "$status" -eq 0 ] && [ "${ADLC_ACCEPTANCE_KEEP_TMP:-0}" != "1" ]; then
    rm -rf "$TMP_ROOT"
  else
    printf 'Public Fix temp retained: %s\n' "$TMP_ROOT" >&2
  fi
}
trap cleanup EXIT

for command in git jq python3 sha256sum; do
  if ! command -v "$command" >/dev/null 2>&1; then
    if [ "$command" = "sha256sum" ] && command -v shasum >/dev/null 2>&1; then
      continue
    fi
    printf 'Missing required command: %s\n' "$command" >&2
    exit 2
  fi
done

digest_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

step() {
  printf '  %s\n' "$1"
}

echo "ADLC Public Fix Loop"
echo "Target: $TARGET"

step "Create real product code with a red verifier"
mkdir -p "$TARGET/app" "$TARGET/tests"
cat > "$TARGET/.gitignore" <<'EOF'
.adlc/
__pycache__/
*.pyc
EOF
cat > "$TARGET/app/calculator.py" <<'PY'
def average(values):
    if not values:
        return 0
    return sum(values)
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
git -C "$TARGET" config user.email adlc-fix@example.invalid
git -C "$TARGET" config user.name "ADLC Fix Harness"
git -C "$TARGET" add .
git -C "$TARGET" commit -qm "red fixture"

step "Install the Codex target without claiming provider invocation"
"$ROOT/setup.sh" codex "$TARGET" >/dev/null
ADLC="$TARGET/.adlc/bin/adlc"
"$ADLC" health-check --json | jq -e '.status == "pass"' >/dev/null
git -C "$TARGET" add .agents AGENTS.md
git -C "$TARGET" commit -qm "Install ADLC Codex target"

step "Record red-before-green verifier evidence"
if "$ADLC" run-phase qa \
  --brief-id PUBLIC-FIX \
  --workspace "$TARGET" \
  --state .adlc/fix_state.json \
  --verifier 'python3 -m unittest discover -s tests' \
  --json > "$TMP_ROOT/red.json" 2>/dev/null; then
  echo "Expected red verifier to fail." >&2
  exit 1
fi
jq -e '.tool_result.status == "fail" and .tool_result.stop_reason == "verifier_failed"' "$TMP_ROOT/red.json" >/dev/null

step "Stop at a human gate and resume without replaying a completed side effect"
"$ADLC" run-phase intent_validation \
  --brief-id PUBLIC-FIX-RESUME \
  --workspace "$TARGET" \
  --state .adlc/resume_state.json \
  --dry-run \
  --json > "$TMP_ROOT/interrupted.json"
jq -e '.state.status == "awaiting_approval" and .state.stop_reason == "human_gate"' "$TMP_ROOT/interrupted.json" >/dev/null
timestamp="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
jq --arg timestamp "$timestamp" '.side_effects = [{
  "idempotency_key":"public-fix:completed-once",
  "tool_name":"fixture-repair",
  "operation":"repair_average",
  "status":"completed",
  "timestamp":$timestamp
}]' "$TARGET/.adlc/resume_state.json" > "$TMP_ROOT/resume-seeded.json"
mv "$TMP_ROOT/resume-seeded.json" "$TARGET/.adlc/resume_state.json"
"$ADLC" resume \
  --workspace "$TARGET" \
  --state .adlc/resume_state.json \
  --approve intent_validation \
  --reason 'Resume the bounded public Fix proof.' \
  --json > "$TMP_ROOT/resumed.json"
jq -e '
  .state.resume_count == 1 and
  ([.state.side_effects[].idempotency_key] | length) == 1 and
  ([.state.side_effects[].idempotency_key] | unique | length) == 1 and
  .state.side_effects[0].status == "completed" and
  .state.approval_records[-1].gate_id == "intent_validation"
' "$TMP_ROOT/resumed.json" >/dev/null

step "Apply the bounded product-code Fix and record its diff"
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
git -C "$TARGET" diff -- app/calculator.py > "$TMP_ROOT/final.diff"
grep -q 'sum(values) / len(values)' "$TMP_ROOT/final.diff"

step "Record the green verifier and PR-ready repository state"
"$ADLC" run-phase qa \
  --brief-id PUBLIC-FIX \
  --workspace "$TARGET" \
  --state .adlc/fix_state.json \
  --verifier 'python3 -m unittest discover -s tests' \
  --json > "$TMP_ROOT/green.json"
jq -e '.tool_result.status == "pass" and .state.phase == "pr_prep"' "$TMP_ROOT/green.json" >/dev/null
git -C "$TARGET" add app/calculator.py
git -C "$TARGET" commit -qm "Fix calculator average"
test -z "$(git -C "$TARGET" status --porcelain --untracked-files=all)"

step "Run an independent deterministic completion audit"
cat > "$TMP_ROOT/completion-plan.json" <<'JSON'
{
  "claims": [
    {
      "id": "FIX-GREEN",
      "claim": "The product-code verifier passes after the fix.",
      "verifier": {"type": "command", "command": "python3 -m unittest discover -s tests", "expect_exit": 0}
    },
    {
      "id": "FIX-PR-READY",
      "claim": "The target worktree is clean and PR-ready.",
      "verifier": {"type": "command", "command": "test -z \"$(git status --porcelain --untracked-files=all)\"", "expect_exit": 0}
    }
  ]
}
JSON
cat > "$TMP_ROOT/independence.json" <<'JSON'
{
  "contract_version": "1.0.0",
  "basis": "separate_session",
  "executor": {"identity": "public-fix-executor", "session_id": "public-fix-executor-session"},
  "auditor": {"identity": "public-fix-auditor", "session_id": "public-fix-auditor-session"},
  "evidence_refs": ["tests/acceptance/run_public_fix_loop.sh"]
}
JSON
"$ADLC" completion-audit \
  --input "$TMP_ROOT/completion-plan.json" \
  --workspace "$TARGET" \
  --executor public-fix-executor \
  --auditor public-fix-auditor \
  --independence-evidence "$TMP_ROOT/independence.json" \
  --json > "$TMP_ROOT/audit.json"
jq -e '.status == "pass" and (.verified | length) == 2 and .independence.executor_session_id != .independence.auditor_session_id' "$TMP_ROOT/audit.json" >/dev/null

step "Generate and validate the redacted conformance report"
END_MS="$(python3 -c 'import time; print(int(time.time() * 1000))')"
SOURCE_COMMIT="$(git -C "$ROOT" rev-parse HEAD)"
SOURCE_TREE_CLEAN=true
test -z "$(git -C "$ROOT" status --porcelain --untracked-files=all)" || SOURCE_TREE_CLEAN=false
ADAPTER_PATH="scripts/adlc_runtime/adapters/codex.sh"
ADAPTER_DIGEST="$(digest_file "$ROOT/$ADAPTER_PATH")"
FIXTURE_DIGEST="$(digest_file "$TMP_ROOT/final.diff")"
EVIDENCE_STATUS=candidate_conformance
if [ "$SOURCE_TREE_CLEAN" = true ]; then EVIDENCE_STATUS=current_conformance; fi
jq -n \
  --arg evidence_status "$EVIDENCE_STATUS" \
  --arg source_commit "$SOURCE_COMMIT" \
  --argjson source_tree_clean "$SOURCE_TREE_CLEAN" \
  --arg adapter_path "$ADAPTER_PATH" \
  --arg adapter_sha256 "$ADAPTER_DIGEST" \
  --arg fixture_sha256 "$FIXTURE_DIGEST" \
  --arg started_at "$(date -u -r $((START_MS / 1000)) '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  --arg finished_at "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  --arg run_id "public-fix-${SOURCE_COMMIT:0:12}" \
  --argjson duration_ms "$((END_MS - START_MS))" \
  '{
    contract_version:"1.0.0",
    evidence_status:$evidence_status,
    runtime:"codex",
    model:"not-invoked",
    source_commit:$source_commit,
    source_tree_clean:$source_tree_clean,
    adapter:{path:$adapter_path,sha256:$adapter_sha256},
    fixture_sha256:$fixture_sha256,
    auth_path:"not-required:deterministic",
    started_at:$started_at,
    finished_at:$finished_at,
    stages:[
      {name:"red_verifier",ok:true,artifact:"red.json",duration_ms:0},
      {name:"interrupt_resume",ok:true,artifact:"resumed.json",duration_ms:0},
      {name:"product_fix",ok:true,artifact:"final.diff",duration_ms:0},
      {name:"green_verifier",ok:true,artifact:"green.json",duration_ms:0},
      {name:"independent_audit",ok:true,artifact:"audit.json",duration_ms:0}
    ],
    overall:"pass",
    cost_estimate_tokens:0,
    provider:"codex",
    harness:"public-fix-deterministic",
    provider_version:"not-invoked",
    loop:"fix",
    run_id:$run_id,
    status:"pass",
    credential_status:"not_required",
    dimensions:{installation:"pass",invocation:"not_run",behavior:"pass",end_to_end:"pass"},
    duration_ms:$duration_ms,
    cost:{currency:"USD",min:0,max:0},
    trace:[
      {event:"red_verifier",status:"fail",stop_reason:"verifier_failed"},
      {event:"interrupt",status:"awaiting_approval",stop_reason:"human_gate"},
      {event:"resume",status:"planned",side_effect_idempotency_key:"public-fix:completed-once",side_effect_count:1},
      {event:"green_verifier",status:"pass"},
      {event:"completion_audit",status:"pass",auditor:"public-fix-auditor"}
    ],
    failures:[],
    no_overclaim:"This proves the deterministic public Fix loop on a temporary product-code repository; the Codex provider was installed but not invoked.",
    limitations:["Provider invocation remains not_run and cannot support a live Codex behavior claim."]
  }' > "$REPORT"
"$ROOT/bin/adlc" validate-artifact --schema provider-conformance-report --input "$REPORT" --json | jq -e '.valid == true' >/dev/null
jq -e '
  .overall == "pass" and
  .dimensions.invocation == "not_run" and
  .trace[0].status == "fail" and
  .trace[2].side_effect_count == 1 and
  .trace[-1].auditor == "public-fix-auditor"
' "$REPORT" >/dev/null
if rg -n '(sk-[A-Za-z0-9_-]{8,}|Bearer [A-Za-z0-9._~+/-]{8,}|password=)' "$REPORT" >/dev/null; then
  echo "Secret-like content found in public Fix report." >&2
  exit 1
fi

if [ -n "${ADLC_FIX_REPORT_OUT:-}" ]; then
  mkdir -p "$(dirname "$ADLC_FIX_REPORT_OUT")"
  cp "$REPORT" "$ADLC_FIX_REPORT_OUT"
fi

echo "Public Fix loop passed."
echo "Conformance report: $REPORT"
