#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: $0 <fixture-dir> <workspace-dir> <artifacts-dir>" >&2
  exit 1
fi

fixture_dir="$1"
workspace_dir="$2"
artifacts_dir="$3"
expected_path="$fixture_dir/expected/council_verdict_shape.json"
actual_path="$artifacts_dir/council.json"

jq empty "$actual_path" >/dev/null

jq -e \
  --slurpfile expected "$expected_path" \
  '
    .label == $expected[0].label
    and ([ $expected[0].required_core_personas[] as $name | select(.verdict.personas | map(.name) | index($name) | . == null) ] | length) == 0
    and ([ $expected[0].required_core_personas[] as $name | select(.verdict.applicability_manifest.core_personas | index($name) | . == null) ] | length) == 0
    and ([ $expected[0].required_overlay_personas[] as $name | select(.verdict.applicability_manifest.overlay_personas | index($name) | . == null) ] | length) == 0
    and ([ $expected[0].forbidden_overlay_personas[] as $name | select(.verdict.applicability_manifest.overlay_personas | index($name) | . != null) ] | length) == 0
  ' "$actual_path" >/dev/null

printf 'council assertion passed\n'
