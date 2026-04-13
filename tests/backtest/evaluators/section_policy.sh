#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <case-json>" >&2
  exit 1
fi

case_file="$1"

jq -ce '
  .expected_manifest.change_surface as $surface
  | if ($surface | type) != "object" then
      error("missing change_surface")
    else
      {
        "5_security_review": (
          if ($surface.new_attack_surface or $surface.auth_change or $surface.external_integration) then
            "active"
          else
            "suppressed"
          end
        ),
        "6_observability_slo": (
          if ($surface.runtime_path_change or $surface.user_facing_operation) then
            "active"
          else
            "suppressed"
          end
        ),
        "10_rollout": "not_applicable",
        "12_skill_trigger_configuration": "not_applicable"
      }
    end
' "$case_file"
