#!/usr/bin/env bash
# Layer 2 smoke harness. tests/smoke/artifacts/smoke_report.json is overwritten on each run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SMOKE_ROOT="$ROOT/tests/smoke"
FIXTURE_DIR="$SMOKE_ROOT/fixtures/feature_bugfix"
SPECIFICITY_FIXTURE_DIR="$SMOKE_ROOT/fixtures/feature_vague"
ARTIFACTS_DIR="$SMOKE_ROOT/artifacts"
WORKSPACE_DIR="$ARTIFACTS_DIR/workspace"
STATE_DIR="$ARTIFACTS_DIR/stage_state"
REPORT_PATH="$ARTIFACTS_DIR/smoke_report.json"
COST_ESTIMATE_TOKENS=50000
MODEL_NAME="${MODEL:-}"
RUNTIME_NAME="${ADLC_RUNTIME:-claude}"
report_items_file="$(mktemp)"

# shellcheck source=/dev/null
source "$SMOKE_ROOT/stages/_invoke.sh"

cleanup() {
  rm -f "$report_items_file"
}

trap cleanup EXIT

now_ms() {
  python3 -c 'import time; print(int(time.time() * 1000))'
}

finalize_report() {
  local overall="$1"
  local run_at
  run_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  jq -s \
    --arg run_at "$run_at" \
    --arg model "$MODEL_NAME" \
    --arg overall "$overall" \
    --argjson cost_estimate_tokens "$COST_ESTIMATE_TOKENS" \
    '{
      run_at: $run_at,
      model: $model,
      stages: .,
      overall: $overall,
      cost_estimate_tokens: $cost_estimate_tokens
    }' "$report_items_file" > "$REPORT_PATH"
}

record_stage() {
  local name="$1"
  local ok="$2"
  local artifact="$3"
  local duration_ms="$4"

  jq -cn \
    --arg name "$name" \
    --arg artifact "$artifact" \
    --argjson ok "$ok" \
    --argjson duration_ms "$duration_ms" \
    '{
      name: $name,
      ok: $ok,
      artifact: $artifact,
      duration_ms: $duration_ms
    }' >> "$report_items_file"
}

reset_path() {
  local path="$1"

  if [ -e "$path" ]; then
    chmod -R u+w "$path" 2>/dev/null || true
    rm -rf "$path"
  fi
}

init_workspace_git() {
  local workspace_path="$1"

  (
    cd "$workspace_path"
    git init -q
    git config user.name "Smoke Harness"
    git config user.email "smoke@example.invalid"
    git add .
    git commit -qm "baseline fixture"
  )
}

prepare_workspace() {
  local source_dir="$1"

  reset_path "$WORKSPACE_DIR"
  cp -R "$source_dir" "$WORKSPACE_DIR"

  if [ ! -d "$WORKSPACE_DIR/.git" ]; then
    init_workspace_git "$WORKSPACE_DIR"
  fi
}

snapshot_workspace() {
  local snapshot_dir="$1"

  reset_path "$snapshot_dir"
  cp -R "$WORKSPACE_DIR" "$snapshot_dir"
  chmod -R u+w "$snapshot_dir" 2>/dev/null || true
}

run_stage() {
  run_stage_with_fixture "$FIXTURE_DIR" "$@"
}

run_stage_with_fixture() {
  local fixture_dir="$1"
  shift
  local name="$1"
  local stage_script="$2"
  local assertion_script="$3"
  local artifact_rel="$4"
  local source_dir="$5"
  local snapshot_dir="${6:-}"
  local log_path="$ARTIFACTS_DIR/${name}.log"
  local start_ms end_ms duration_ms

  prepare_workspace "$source_dir"
  start_ms="$(now_ms)"
  : > "$log_path"

  if "$stage_script" "$ROOT" "$fixture_dir" "$WORKSPACE_DIR" "$ARTIFACTS_DIR" "$MODEL_NAME" >> "$log_path" 2>&1 \
    && "$assertion_script" "$fixture_dir" "$WORKSPACE_DIR" "$ARTIFACTS_DIR" >> "$log_path" 2>&1; then
    if [ -n "$snapshot_dir" ]; then
      snapshot_workspace "$snapshot_dir"
    fi
    end_ms="$(now_ms)"
    duration_ms=$((end_ms - start_ms))
    record_stage "$name" true "$artifact_rel" "$duration_ms"
    return 0
  fi

  end_ms="$(now_ms)"
  duration_ms=$((end_ms - start_ms))
  record_stage "$name" false "$artifact_rel" "$duration_ms"
  finalize_report "fail"
  printf 'smoke stage failed: %s\n' "$name" >&2
  printf 'inspect: %s\n' "$log_path" >&2
  exit 1
}

if [ "${SMOKE:-}" != "1" ]; then
  echo "Refusing to run Layer 2 smoke without SMOKE=1. No token-spend path was started." >&2
  exit 64
fi

if [ -z "$MODEL_NAME" ]; then
  echo "MODEL must be set when SMOKE=1 is used." >&2
  exit 65
fi

AUTH_PATH="$(preflight)"
printf 'Layer 2 smoke runtime: %s\n' "$RUNTIME_NAME"
printf 'Layer 2 smoke auth path: %s\n' "$AUTH_PATH"
printf 'Layer 2 smoke cost estimate: %s tokens\n' "$COST_ESTIMATE_TOKENS"

mkdir -p "$ARTIFACTS_DIR"
find "$ARTIFACTS_DIR" -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} +
mkdir -p "$STATE_DIR"

run_stage "triage" \
  "$SMOKE_ROOT/stages/run_triage.sh" \
  "$SMOKE_ROOT/assertions/assert_triage.sh" \
  "tests/smoke/artifacts/triage.json" \
  "$FIXTURE_DIR"

run_stage "spec_to_tests" \
  "$SMOKE_ROOT/stages/run_spec_to_tests.sh" \
  "$SMOKE_ROOT/assertions/assert_test_plan.sh" \
  "tests/smoke/artifacts/spec_to_tests.json" \
  "$FIXTURE_DIR" \
  "$STATE_DIR/spec_to_tests"

run_stage "coder" \
  "$SMOKE_ROOT/stages/run_coder.sh" \
  "$SMOKE_ROOT/assertions/assert_red_green.sh" \
  "tests/smoke/artifacts/coder.json" \
  "$STATE_DIR/spec_to_tests" \
  "$STATE_DIR/coder"

run_stage "test_strength" \
  "$SMOKE_ROOT/stages/run_test_strength.sh" \
  "$SMOKE_ROOT/assertions/assert_test_strength.sh" \
  "tests/smoke/artifacts/test_strength.json" \
  "$STATE_DIR/coder" \
  "$STATE_DIR/test_strength"

run_stage "council" \
  "$SMOKE_ROOT/stages/run_council.sh" \
  "$SMOKE_ROOT/assertions/assert_council_verdict.sh" \
  "tests/smoke/artifacts/council.json" \
  "$STATE_DIR/test_strength"

run_stage_with_fixture "$SPECIFICITY_FIXTURE_DIR" \
  "specificity" \
  "$SMOKE_ROOT/stages/run_specificity.sh" \
  "$SMOKE_ROOT/assertions/assert_specificity.sh" \
  "tests/smoke/artifacts/specificity.json" \
  "$SPECIFICITY_FIXTURE_DIR"

finalize_report "pass"
printf 'smoke report: %s\n' "$REPORT_PATH"
