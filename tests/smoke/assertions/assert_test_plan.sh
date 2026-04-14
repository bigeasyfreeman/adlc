#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: $0 <fixture-dir> <workspace-dir> <artifacts-dir>" >&2
  exit 1
fi

fixture_dir="$1"
workspace_dir="$2"
artifacts_dir="$3"
plan_path="$workspace_dir/.adlc/test_plan.json"
shape_path="$fixture_dir/expected/test_plan_shape.json"
pre_status_path="$workspace_dir/.adlc/pre_change_status.json"
pre_run_path="$workspace_dir/.adlc/pre_change_run.txt"

jq empty "$plan_path" >/dev/null
jq empty "$pre_status_path" >/dev/null

jq -e \
  --slurpfile shape "$shape_path" \
  '
    ([ $shape[0].required_top_level_fields[] as $field | select(has($field) | not) ] | length) == 0
    and (.generated_tests | type) == "array"
    and (.generated_tests | length) > 0
    and (
      [ .generated_tests[]
        | [ $shape[0].required_generated_test_fields[] as $field | select(has($field) | not) ]
        | length
      ] | all(. == 0)
    )
    and (
      [ $shape[0].required_self_check_fields[] as $field | select(.self_check[$field] == null) ]
      | length
    ) == 0
    and .pre_change_run_path == $shape[0].expected_pre_change_run_path
    and ([.generated_tests[].ac_id] | unique | sort) == ($shape[0].expected_ac_ids | sort)
    and (.generated_tests | all(.assertion_count >= 1))
  ' "$plan_path" >/dev/null

[ -f "$pre_run_path" ]
jq -e '.exit_code != 0' "$pre_status_path" >/dev/null

printf 'test_plan assertion passed\n'
