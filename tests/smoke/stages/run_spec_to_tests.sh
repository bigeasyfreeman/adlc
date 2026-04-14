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
brief_path="$workspace_dir/.adlc/build_brief.json"
manifest_path="$workspace_dir/.adlc/applicability_manifest.json"
schema_path="$repo_root/docs/schemas/test-author-output.schema.json"
combined_plan_path="$workspace_dir/.adlc/test_plan.json"
combined_plan_backup="$workspace_dir/.adlc/test_plan.all.json"
combined_pre_run_path="$workspace_dir/.adlc/pre_change_run.txt"
combined_pre_run_backup="$workspace_dir/.adlc/pre_change_run.all.txt"
summary_path="$artifacts_dir/spec_to_tests.json"
task_ids_file="$(mktemp)"
input_path="$(mktemp)"
summary_items_file="$(mktemp)"

# shellcheck source=/dev/null
source "$repo_root/tests/smoke/stages/_invoke.sh"
# shellcheck source=/dev/null
source "$repo_root/tests/smoke/stages/_validate.sh"

cleanup() {
  rm -f "$task_ids_file" "$input_path" "$summary_items_file"
}

trap cleanup EXIT

jq -r '.sections."8_task_tickets"[] .task_id' "$brief_path" > "$task_ids_file"

while IFS= read -r task_id; do
  [ -n "$task_id" ] || continue

  jq -n \
    --slurpfile brief "$brief_path" \
    --slurpfile manifest "$manifest_path" \
    --arg task_id "$task_id" \
    --arg repo_path "$workspace_dir" \
    '
      ($brief[0]) as $brief_doc
      | ($brief_doc.sections."8_task_tickets"[] | select(.task_id == $task_id)) as $task
      | {
          brief_id: $brief_doc.brief_id,
          task_id: $task.task_id,
          task_classification: $task.task_classification,
          applicability_manifest: $manifest[0],
          verification_spec: $task.verification_spec,
          acceptance_criteria: $task.acceptance_criteria,
          files_to_modify: ($task.files_to_modify // []),
          files_to_create: ($task.files_to_create // []),
          reference_impl: ($task.reference_impl // "src/scoreboard.py"),
          repo_path: $repo_path,
          artifact_dir: ".adlc"
        }
    ' > "$input_path"

  (
    cd "$workspace_dir"
    ADLC_MODEL="$model" \
      invoke_agent \
        --agent "$repo_root/agents/test-author.md" \
        --input "$input_path" \
        --output "$artifacts_dir/spec_to_tests.${task_id}.json" \
        --tools "Read,Write,Bash" \
        --schema "$schema_path"
  )

  validate_json "$artifacts_dir/spec_to_tests.${task_id}.json" "$schema_path"
  cp "$workspace_dir/.adlc/test_plan.json" "$workspace_dir/.adlc/test_plan.${task_id}.json"
  cp "$workspace_dir/.adlc/pre_change_run.txt" "$workspace_dir/.adlc/pre_change_run.${task_id}.txt"

  jq -cn \
    --arg task_id "$task_id" \
    --arg output "tests/smoke/artifacts/spec_to_tests.${task_id}.json" \
    --arg plan ".adlc/test_plan.${task_id}.json" \
    --arg pre ".adlc/pre_change_run.${task_id}.txt" \
    '{
      task_id: $task_id,
      output: $output,
      test_plan: $plan,
      pre_change_run: $pre
    }' >> "$summary_items_file"
done < "$task_ids_file"

jq -s '
  {
    brief_id: (.[0].brief_id),
    task_id: "SMOKE_BUGFIX_AVERAGE__SMOKE_FEATURE_SCOREBOARD",
    generated_tests: (map(.generated_tests) | add),
    pre_change_run_path: ".adlc/pre_change_run.txt",
    verifier_target_intersection: (all(.[]; .verifier_target_intersection == true)),
    self_check: {
      gate_1: (if all(.[]; .self_check.gate_1 == "pass") then "pass" else "fail" end),
      gate_2: (if all(.[]; .self_check.gate_2 == "pass") then "pass" else "fail" end),
      gate_3: (if all(.[]; .self_check.gate_3 == "pass") then "pass" else "fail" end),
      gate_4: (if all(.[]; .self_check.gate_4 == "pass") then "pass" else "fail" end),
      gate_5: (if all(.[]; .self_check.gate_5 == "pass") then "pass" else "fail" end),
      gate_6: (if all(.[]; .self_check.gate_6 == "pass") then "pass" else "fail" end)
    }
  }
' "$workspace_dir"/.adlc/test_plan.SMOKE_*.json > "$combined_plan_path"

pre_exit=0
python3 -m unittest discover -s tests -p 'test_*.py' > "$combined_pre_run_path" 2>&1 || pre_exit=$?
cp "$combined_plan_path" "$combined_plan_backup"
cp "$combined_pre_run_path" "$combined_pre_run_backup"

jq -cn \
  --arg command "python3 -m unittest discover -s tests -p 'test_*.py'" \
  --argjson exit_code "$pre_exit" \
  --argjson generated_test_paths "$(jq -c '[.generated_tests[].test_path] | unique' "$combined_plan_path")" \
  '{
    command: $command,
    exit_code: $exit_code,
    generated_test_paths: $generated_test_paths
  }' > "$workspace_dir/.adlc/pre_change_status.json"

jq -s \
  --arg combined_plan ".adlc/test_plan.json" \
  --arg combined_pre ".adlc/pre_change_run.txt" \
  '{
    tasks: .,
    combined_test_plan: $combined_plan,
    combined_pre_change_run: $combined_pre
  }' "$summary_items_file" > "$summary_path"

jq empty "$summary_path" >/dev/null
printf 'spec_to_tests artifact: %s\n' "$summary_path"
