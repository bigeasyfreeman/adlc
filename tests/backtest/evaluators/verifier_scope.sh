#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <case-json>" >&2
  exit 1
fi

case_file="$1"

jq -ce '
  (.expected_manifest.verification_spec.primary_verifier.target_files // .expected_manifest.verification_spec.target_files // []) as $targets
  | ((.task.files_to_modify // []) + (.task.files_to_create // [])) as $task_files
  | if ($targets | type) != "array" then
      error("target_files must be an array when present")
    elif ($targets | length) == 0 then
      {"verdict": "legacy_warn", "reason": "target_files_unset"}
    elif ([ $targets[] as $target | select($task_files | index($target)) ] | length) > 0 then
      {"verdict": "pass", "reason": "target_files_intersect"}
    else
      {"verdict": "revise", "reason": "verifier_no_coverage"}
    end
' "$case_file"
