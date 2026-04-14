#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: $0 <fixture-dir> <workspace-dir> <artifacts-dir>" >&2
  exit 1
fi

fixture_dir="$1"
workspace_dir="$2"
artifacts_dir="$3"
thresholds_path="$fixture_dir/expected/test_strength_thresholds.json"
report_path="$workspace_dir/.adlc/test_strength_report.json"
envelope_path="$artifacts_dir/test_strength.json"

jq empty "$report_path" >/dev/null
jq empty "$envelope_path" >/dev/null

jq -e --slurpfile thresholds "$thresholds_path" '
  .coverage_threshold == 0.8
  and .mutation_threshold == 0.6
  and .kill_rate >= $thresholds[0].min_mutation_kill_rate
  and (.files[] | select(.path == $thresholds[0].bugfix_target_file) | .coverage_ratio >= $thresholds[0].min_bugfix_coverage)
  and .verdict == "pass"
' "$report_path" >/dev/null

jq -e '.verdict == "pass" and .coverage >= 0.8 and .mutation_kill_rate >= 0.6 and .report_path == ".adlc/test_strength_report.json"' "$envelope_path" >/dev/null

printf 'test_strength assertion passed\n'
