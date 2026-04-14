#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: $0 <fixture-dir> <workspace-dir> <artifacts-dir>" >&2
  exit 1
fi

fixture_dir="$1"
workspace_dir="$2"
artifacts_dir="$3"
actual_path="$artifacts_dir/specificity.json"

jq empty "$actual_path" >/dev/null

jq -e '
  .label == "revise"
  and .verdict.status == "REVISION_REQUIRED"
  and .verdict.gate_0.specificity.status == "revise"
  and .verdict.gate_0.specificity.reason == "low_specificity"
  and (.specificity_findings | length) >= 1
  and (.specificity_findings[0].score < 0.6)
' "$actual_path" >/dev/null

printf 'specificity assertion passed\n'
