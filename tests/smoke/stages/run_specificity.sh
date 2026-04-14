#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 5 ]; then
  echo "usage: $0 <repo-root> <fixture-dir> <workspace-dir> <artifacts-dir> <model>" >&2
  exit 1
fi

repo_root="$1"
fixture_dir="$2"
workspace_dir="$3"
artifacts_dir="$4"
model="$5"
output_path="$artifacts_dir/specificity.json"
schema_path="$repo_root/docs/schemas/council-verdict-output.schema.json"
input_path="$(mktemp)"
pre_status="$(git -C "$workspace_dir" status --porcelain)"

# shellcheck source=/dev/null
source "$repo_root/tests/smoke/stages/_invoke.sh"
# shellcheck source=/dev/null
source "$repo_root/tests/smoke/stages/_validate.sh"

cleanup() {
  chmod -R u+w "$workspace_dir" 2>/dev/null || true
  rm -f "$input_path"
}

trap cleanup EXIT

jq -n \
  --slurpfile brief "$workspace_dir/.adlc/build_brief.json" \
  --slurpfile manifest "$workspace_dir/.adlc/applicability_manifest.json" \
  --slurpfile test_plan "$workspace_dir/.adlc/test_plan.json" \
  --slurpfile strength "$workspace_dir/.adlc/test_strength_report.json" \
  --slurpfile post_status "$workspace_dir/.adlc/post_change_status.json" \
  '{
    build_brief: $brief[0],
    applicability_manifest: $manifest[0],
    test_plan: $test_plan[0],
    test_strength_report: $strength[0],
    post_change_status: $post_status[0]
  }' > "$input_path"

chmod -R a-w "$workspace_dir"

(
  cd "$workspace_dir"
  ADLC_MODEL="$model" \
    invoke_agent \
      --agent "$repo_root/agents/plan-reviewer.md" \
      --input "$input_path" \
      --output "$output_path" \
      --tools "" \
      --schema "$schema_path"
)

validate_json "$output_path" "$schema_path"

post_status="$(git -C "$workspace_dir" status --porcelain)"
if [ "$post_status" != "$pre_status" ]; then
  echo "specificity stage mutated the read-only workspace" >&2
  printf 'before:\n%s\n' "$pre_status" >&2
  printf 'after:\n%s\n' "$post_status" >&2
  exit 1
fi

printf 'specificity artifact: %s\n' "$output_path"
