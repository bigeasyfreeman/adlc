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
output_path="$artifacts_dir/test_strength.json"
schema_path="$repo_root/docs/schemas/test-strength-output.schema.json"
input_path="$(mktemp)"

# shellcheck source=/dev/null
source "$repo_root/tests/smoke/stages/_invoke.sh"
# shellcheck source=/dev/null
source "$repo_root/tests/smoke/stages/_validate.sh"

cleanup() {
  rm -f "$input_path"
}

trap cleanup EXIT

jq -n \
  --arg workspace_path "$workspace_dir" \
  --argjson test_plan "$(jq -c '.' "$workspace_dir/.adlc/test_plan.json")" \
  --argjson changed_files "$(cd "$workspace_dir" && git diff --name-only | jq -R . | jq -s .)" \
  '{
    workspace_path: $workspace_path,
    changed_files: $changed_files,
    generated_tests: $test_plan.generated_tests,
    mutation_config: {
      language: "python",
      tool: "mutmut",
      test_command: "python3 -m unittest discover -s tests -p '\''test_*.py'\''",
      target_files: ["src/scoreboard.py"]
    }
  }' > "$input_path"

(
  cd "$workspace_dir"
  ADLC_MODEL="$model" \
    invoke_agent \
      --agent "$repo_root/agents/test-strength-auditor.md" \
      --input "$input_path" \
      --output "$output_path" \
      --tools "Read,Bash" \
      --schema "$schema_path"
)

validate_json "$output_path" "$schema_path"
printf 'test_strength artifact: %s\n' "$output_path"
