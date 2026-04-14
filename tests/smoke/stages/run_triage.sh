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
output_path="$artifacts_dir/triage.json"
schema_path="$repo_root/docs/schemas/triage-output.schema.json"
input_path="$(mktemp)"

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
  --rawfile request "$fixture_dir/request.md" \
  --slurpfile brief "$workspace_dir/.adlc/build_brief.json" \
  --slurpfile manifest "$workspace_dir/.adlc/applicability_manifest.json" \
  --arg repo_path "$workspace_dir" \
  '{
    request: $request,
    repo_path: $repo_path,
    build_brief: $brief[0],
    applicability_manifest: $manifest[0]
  }' > "$input_path"

chmod -R a-w "$workspace_dir"

(
  cd "$workspace_dir"
  ADLC_MODEL="$model" \
    invoke_agent \
      --agent "$repo_root/agents/triage.md" \
      --input "$input_path" \
      --output "$output_path" \
      --tools "" \
      --schema "$schema_path"
)

validate_json "$output_path" "$schema_path"

if git -C "$workspace_dir" status --porcelain | grep -q .; then
  echo "triage stage mutated the read-only workspace" >&2
  git -C "$workspace_dir" status --short >&2
  exit 1
fi

printf 'triage artifact: %s\n' "$output_path"
