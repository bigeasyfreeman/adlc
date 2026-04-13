#!/usr/bin/env bash
# tests/backtest/last_report.json is overwritten on each run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FIXTURE="$ROOT/tests/fixtures/applicability-issue-set.json"
EVALUATORS_DIR="$ROOT/tests/backtest/evaluators"
REPORT="$ROOT/tests/backtest/last_report.json"

stages=(
  triage
  section_policy
  verifier_scope
  dod_overlays
  council_personas
  test_strength
)

stage_script() {
  local stage_name="$1"

  case "$stage_name" in
    triage)
      printf '%s\n' "$EVALUATORS_DIR/triage.sh"
      ;;
    section_policy)
      printf '%s\n' "$EVALUATORS_DIR/section_policy.sh"
      ;;
    verifier_scope)
      printf '%s\n' "$EVALUATORS_DIR/verifier_scope.sh"
      ;;
    dod_overlays)
      printf '%s\n' "$EVALUATORS_DIR/dod_overlays.sh"
      ;;
    council_personas)
      printf '%s\n' "$EVALUATORS_DIR/council_personas.sh"
      ;;
    test_strength)
      printf '%s\n' "$EVALUATORS_DIR/test_strength.sh"
      ;;
    *)
      echo "unknown stage: $stage_name" >&2
      exit 1
      ;;
  esac
}

report_cases_file="$(mktemp)"
case_file="$(mktemp)"

cleanup() {
  rm -f "$report_cases_file" "$case_file"
}

trap cleanup EXIT

total=0
passed=0
failed=0

while IFS= read -r case_id; do
  jq --arg id "$case_id" '.cases[] | select(.id == $id)' "$FIXTURE" > "$case_file"

  triage_status=""
  section_policy_status=""
  verifier_scope_status=""
  dod_overlays_status=""
  council_personas_status=""
  test_strength_status=""

  for stage in "${stages[@]}"; do
    expected="$(jq -cS --arg stage "$stage" '.expected_stage_outputs[$stage]' "$case_file")"
    actual="$( "$(stage_script "$stage")" "$case_file" | jq -cS '.' )"

    total=$((total + 1))
    if [ "$expected" = "$actual" ]; then
      echo "PASS $case_id $stage expected=$expected actual=$actual"
      passed=$((passed + 1))
      stage_result="pass"
    else
      echo "FAIL $case_id $stage expected=$expected actual=$actual"
      failed=$((failed + 1))
      stage_result="fail"
    fi

    case "$stage" in
      triage)
        triage_status="$stage_result"
        ;;
      section_policy)
        section_policy_status="$stage_result"
        ;;
      verifier_scope)
        verifier_scope_status="$stage_result"
        ;;
      dod_overlays)
        dod_overlays_status="$stage_result"
        ;;
      council_personas)
        council_personas_status="$stage_result"
        ;;
      test_strength)
        test_strength_status="$stage_result"
        ;;
    esac
  done

  jq -cn \
    --arg id "$case_id" \
    --arg triage "$triage_status" \
    --arg section_policy "$section_policy_status" \
    --arg verifier_scope "$verifier_scope_status" \
    --arg dod_overlays "$dod_overlays_status" \
    --arg council_personas "$council_personas_status" \
    --arg test_strength "$test_strength_status" \
    '{
      id: $id,
      stages: {
        triage: $triage,
        section_policy: $section_policy,
        verifier_scope: $verifier_scope,
        dod_overlays: $dod_overlays,
        council_personas: $council_personas,
        test_strength: $test_strength
      }
    }' >> "$report_cases_file"
done < <(jq -r '.cases[].id' "$FIXTURE")

run_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

jq -s \
  --arg run_at "$run_at" \
  --argjson total "$total" \
  --argjson passed "$passed" \
  --argjson failed "$failed" \
  '{
    run_at: $run_at,
    total: $total,
    passed: $passed,
    failed: $failed,
    cases: .
  }' "$report_cases_file" > "$REPORT"

echo "RESULTS passed=$passed failed=$failed total=$total"

[ "$failed" -eq 0 ]
