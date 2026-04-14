#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: $0 <fixture-dir> <workspace-dir> <artifacts-dir>" >&2
  exit 1
fi

fixture_dir="$1"
workspace_dir="$2"
artifacts_dir="$3"
expected_path="$fixture_dir/expected/red_green.json"
plan_path="$workspace_dir/.adlc/test_plan.json"
pre_status_path="$workspace_dir/.adlc/pre_change_status.json"
post_status_path="$workspace_dir/.adlc/post_change_status.json"
pre_run_path="$workspace_dir/.adlc/pre_change_run.txt"

jq empty "$pre_status_path" >/dev/null
jq empty "$post_status_path" >/dev/null

jq -e --slurpfile expected "$expected_path" '
  .command == $expected[0].test_command and .exit_code != 0
' "$pre_status_path" >/dev/null

jq -e --slurpfile expected "$expected_path" '
  .command == $expected[0].test_command and .exit_code == 0
' "$post_status_path" >/dev/null

jq -e --slurpfile plan "$plan_path" '
  .generated_test_paths == ($plan[0].generated_tests | map(.test_path) | unique)
' "$pre_status_path" >/dev/null

jq -e --slurpfile pre "$pre_status_path" '
  .generated_test_paths == $pre[0].generated_test_paths
' "$post_status_path" >/dev/null

while IFS= read -r expected_substring; do
  [ -n "$expected_substring" ] || continue
  rg -Fq "$expected_substring" "$pre_run_path"
done < <(jq -r '.expected_failure_substrings[]' "$expected_path")

printf 'red_green assertion passed\n'
