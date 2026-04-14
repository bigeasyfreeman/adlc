#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: $0 <fixture-dir> <workspace-dir> <artifacts-dir>" >&2
  exit 1
fi

fixture_dir="$1"
workspace_dir="$2"
artifacts_dir="$3"
expected_path="$fixture_dir/expected/triage.json"
actual_path="$artifacts_dir/triage.json"

jq empty "$actual_path" >/dev/null

jq -e --slurpfile expected "$expected_path" '
  .label == $expected[0].label
  and .task_classification == $expected[0].task_classification
  and ((.task_classification_confidence - $expected[0].confidence) | abs) <= 0.15
' "$actual_path" >/dev/null

printf 'triage assertion passed\n'
