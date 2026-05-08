#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FIXTURE="${1:-$ROOT/tests/fixtures/adlc-artifact-contract-cases.json}"

jq empty "$FIXTURE" >/dev/null

failures="$(jq -r '
  def tasks($case):
    ($case.brief.sections."8_task_tickets" // []);

  def task_ids($case):
    [tasks($case)[] | .task_id];

  def expected_validation_ids($case):
    ($case.brief.enterprise_readiness_contract.validation_tasks // []);

  def emitted_artifacts($case):
    [($case.emitter_dry_runs // {}) | to_entries[] | .value.artifacts[]?];

  def reason_list($case):
    tasks($case) as $tasks
    | task_ids($case) as $ids
    | expected_validation_ids($case) as $validation_ids
    | emitted_artifacts($case) as $emitted
    | [
        (
          if ([
            $tasks[]
            | select(
                .artifact_type == "implementation_task"
                and (
                  .decision_contract.status == "unresolved"
                  or .decision_contract.blocks_implementation == true
                  or .decision_contract.type1_decision == true
                )
              )
          ] | length) > 0
          then "unresolved_type1_in_implementation"
          else empty
          end
        ),
        (
          if ([
            $tasks[]
            | select(
                .artifact_type == "decision_gate"
                and (
                  .bpe_classification != "type_1"
                  or .decision_contract.type1_decision != true
                  or .decision_contract.status != "unresolved"
                  or .decision_contract.blocks_implementation != true
                )
              )
          ] | length) > 0
          then "decision_gate_not_blocking"
          else empty
          end
        ),
        (
          if ([
            $tasks[]
            | select(
                .artifact_type == "scope_lock_epic"
                and (((.files_to_modify // []) | length) > 0 or ((.files_to_create // []) | length) > 0)
              )
          ] | length) > 0
          then "scope_lock_has_file_changes"
          else empty
          end
        ),
        (
          [
            $tasks[]
            | select(.artifact_type == "scope_lock_epic")
            | (.acceptance_criteria // [])[]
            | select(type == "object")
            | .id
          ] as $scope_ac_ids
          | if ([
              $tasks[]
              | select(.artifact_type != "scope_lock_epic")
              | (.acceptance_criteria // [])[]
              | select(type == "object" and (.id as $ac_id | ($scope_ac_ids | index($ac_id))))
            ] | length) > 0
            then "parent_child_duplicate_scope"
            else empty
            end
        ),
        (
          if (($case.brief.adlc_mode == "decompose_only" or $case.brief.adlc_mode == "prd_and_decompose")
              and (
                ($validation_ids | length) == 0
                or ([
                  $validation_ids[] as $id
                  | select(([$tasks[] | select(.task_id == $id and .artifact_type == "validation_task")] | length) == 0)
                ] | length) > 0
              )
            )
          then "missing_validation_task"
          else empty
          end
        ),
        (
          if ([
            $tasks[]
            | (.dependencies // [])[] as $dep
            | select($ids | index($dep) | not)
          ] | length) > 0
          then "unresolved_dependency_alias"
          else empty
          end
        ),
        (
          if ([
            ($case.emitter_dry_runs // {}) | to_entries[] | select(.value.dry_run != true)
          ] | length) > 0
          then "emitter_mutating_dry_run"
          else empty
          end
        ),
        (
          if ([
            $emitted[] as $artifact
            | ($artifact.id) as $id
            | ([$tasks[] | select(.task_id == $id)][0] // {}) as $task
            | select(($task.task_id != null) and ($artifact.artifact_type != $task.artifact_type))
          ] | length) > 0
          then "emitter_drops_artifact_taxonomy"
          else empty
          end
        ),
        (
          if ([
            $emitted[] as $artifact
            | ($artifact.id) as $id
            | ([$tasks[] | select(.task_id == $id)][0] // {}) as $task
            | select(
                ($task.task_id != null)
                and (
                  ($artifact.decision_contract.status // null) != $task.decision_contract.status
                  or (($artifact.decision_contract | if has("blocks_implementation") then .blocks_implementation else null end) != $task.decision_contract.blocks_implementation)
                )
              )
          ] | length) > 0
          then "emitter_missing_decision_contract"
          else empty
          end
        ),
        (
          if (($validation_ids | length) > 0
              and (($case.emitter_dry_runs // {}) | length) > 0
              and ([
                $validation_ids[] as $id
                | select(([$emitted[] | select(.id == $id and .artifact_type == "validation_task")] | length) == 0)
              ] | length) > 0
            )
          then "emitter_missing_validation_task"
          else empty
          end
        )
      ]
      | unique;

  .cases[]
  | reason_list(.) as $actual_reasons
  | (.expected_reasons // []) as $expected_reasons
  | (if ($actual_reasons | length) == 0 then "pass" else "fail" end) as $actual_verdict
  | if (
      $actual_verdict == .expected_verdict
      and (($actual_reasons | sort) == ($expected_reasons | sort))
    )
    then empty
    else "\(.id): expected \(.expected_verdict) \($expected_reasons | sort | join(",")); got \($actual_verdict) \($actual_reasons | sort | join(","))"
    end
' "$FIXTURE")"

if [ -n "$failures" ]; then
  printf '%s\n' "$failures" >&2
  exit 1
fi

printf 'artifact contract cases passed: %s\n' "$(jq -r '.cases | length' "$FIXTURE")"
