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
schema_path="$repo_root/docs/schemas/coder-output.schema.json"
combined_plan_path="$workspace_dir/.adlc/test_plan.all.json"
combined_pre_run_path="$workspace_dir/.adlc/pre_change_run.all.txt"
summary_path="$artifacts_dir/coder.json"
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

  cp "$workspace_dir/.adlc/test_plan.${task_id}.json" "$workspace_dir/.adlc/test_plan.json"
  cp "$workspace_dir/.adlc/pre_change_run.${task_id}.txt" "$workspace_dir/.adlc/pre_change_run.txt"

  jq -n \
    --slurpfile brief "$brief_path" \
    --slurpfile task_plan "$workspace_dir/.adlc/test_plan.${task_id}.json" \
    --rawfile pre_change_run "$workspace_dir/.adlc/pre_change_run.${task_id}.txt" \
    --rawfile source_file "$workspace_dir/src/scoreboard.py" \
    --arg task_id "$task_id" \
    '
      ($brief[0]) as $brief_doc
      | ($brief_doc.sections."8_task_tickets"[] | select(.task_id == $task_id)) as $task
      | {
          brief_id: $brief_doc.brief_id,
          task_id: $task.task_id,
          task_classification: $task.task_classification,
          objective: $task.objective,
          verification_spec: $task.verification_spec,
          acceptance_criteria: $task.acceptance_criteria,
          files_to_modify: ($task.files_to_modify // []),
          files_to_create: ($task.files_to_create // []),
          reference_impl: ($task.reference_impl // "src/scoreboard.py"),
          test_plan: $task_plan[0],
          pre_change_run: $pre_change_run,
          source_files: {
            "src/scoreboard.py": $source_file
          }
        }
    ' > "$input_path"

  (
    cd "$workspace_dir"
    ADLC_MODEL="$model" \
      invoke_agent \
        --agent "$repo_root/agents/coder.md" \
        --input "$input_path" \
        --output "$artifacts_dir/coder.${task_id}.json" \
        --tools "Read,Write,Edit,Bash,Glob,Grep" \
        --schema "$schema_path"
  )

  validate_json "$artifacts_dir/coder.${task_id}.json" "$schema_path"

  jq -cn \
    --arg task_id "$task_id" \
    --arg output "tests/smoke/artifacts/coder.${task_id}.json" \
    '{
      task_id: $task_id,
      output: $output
    }' >> "$summary_items_file"
done < "$task_ids_file"

cp "$combined_plan_path" "$workspace_dir/.adlc/test_plan.json"
cp "$combined_pre_run_path" "$workspace_dir/.adlc/pre_change_run.txt"

post_exit=0
(
  cd "$workspace_dir"
  python3 -m unittest discover -s tests -p 'test_*.py'
) > "$workspace_dir/.adlc/post_change_run.txt" 2>&1 || post_exit=$?

jq -cn \
  --arg command "python3 -m unittest discover -s tests -p 'test_*.py'" \
  --argjson exit_code "$post_exit" \
  --argjson generated_test_paths "$(jq -c '[.generated_tests[].test_path] | unique' "$workspace_dir/.adlc/test_plan.json")" \
  '{
    command: $command,
    exit_code: $exit_code,
    generated_test_paths: $generated_test_paths
  }' > "$workspace_dir/.adlc/post_change_status.json"

jq -s '
  {
    tasks: .,
    post_change_run: ".adlc/post_change_run.txt",
    post_change_status: ".adlc/post_change_status.json"
  }' "$summary_items_file" > "$summary_path"

jq empty "$summary_path" >/dev/null
printf 'coder artifact: %s\n' "$summary_path"
