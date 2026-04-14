#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <case-json>" >&2
  exit 1
fi

case_file="$1"

jq -ce '
  .expected_manifest.task_classification_confidence as $confidence
  | (if .judge_policy.fast_judge_available? == null then true else .judge_policy.fast_judge_available end) as $fast
  | (if .judge_policy.deep_judge_available? == null then true else .judge_policy.deep_judge_available end) as $deep
  | (.expected_manifest.verification_spec.primary_verifier.target_files // .expected_manifest.verification_spec.target_files // []) as $targets
  | ((.task.files_to_modify // []) + (.task.files_to_create // [])) as $task_files
  | ([ $targets[]? as $target | select($task_files | index($target)) ] | length > 0) as $intersects
  | ((.judge_policy.content_slop_regex_pass // false)) as $slop
  | ((.judge_policy.section_policy_review // false)) as $section_policy_review
  | (((.post_qa.surviving_mutants // []) | length) > 0) as $surviving_mutants
  | [
      (
        if ($confidence >= 0.6 and $confidence < 0.8) then
          if $fast then
            {judge: "brief-clarity-judge", decision: "invoke", reason: "middle_confidence_band"}
          else
            {judge: "brief-clarity-judge", decision: "unavailable", reason: "fast_judge_unavailable"}
          end
        else
          {judge: "brief-clarity-judge", decision: "skip", reason: "outside_middle_band"}
        end
      ),
      (
        if $fast then
          {judge: "specificity-judge", decision: "invoke", reason: "gate_0_specificity"}
        else
          {judge: "specificity-judge", decision: "unavailable", reason: "specificity_judge_unavailable"}
        end
      ),
      (
        if $intersects then
          if $fast then
            {judge: "verifier-semantic-judge", decision: "invoke", reason: "target_files_intersect"}
          else
            {judge: "verifier-semantic-judge", decision: "unavailable", reason: "fast_judge_unavailable"}
          end
        else
          {judge: "verifier-semantic-judge", decision: "skip", reason: "target_files_unset_or_disjoint"}
        end
      ),
      (
        if $surviving_mutants then
          if $deep then
            {judge: "mutant-materiality-judge", decision: "invoke", reason: "surviving_mutants_present"}
          else
            {judge: "mutant-materiality-judge", decision: "unavailable", reason: "deep_judge_unavailable"}
          end
        else
          {judge: "mutant-materiality-judge", decision: "skip", reason: "no_surviving_mutants"}
        end
      ),
      (
        if $slop then
          if $fast then
            {judge: "slop-judge", decision: "invoke", reason: "content_regex_cleared"}
          else
            {judge: "slop-judge", decision: "unavailable", reason: "fast_judge_unavailable"}
          end
        else
          {judge: "slop-judge", decision: "skip", reason: "content_mode_not_active"}
        end
      ),
      (
        if $section_policy_review then
          if $fast then
            {judge: "section-policy-judge", decision: "invoke", reason: "suppressed_section_review_requested"}
          else
            {judge: "section-policy-judge", decision: "unavailable", reason: "fast_judge_unavailable"}
          end
        else
          {judge: "section-policy-judge", decision: "skip", reason: "no_override_candidate"}
        end
      )
    ]
' "$case_file"
