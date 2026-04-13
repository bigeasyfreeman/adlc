#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <case-json>" >&2
  exit 1
fi

case_file="$1"

jq -ce '
  .expected_manifest as $manifest
  | $manifest.change_surface as $surface
  | if ($surface | type) != "object" then
      error("missing change_surface")
    else
      (
        if ($surface.new_attack_surface or $surface.auth_change or $surface.external_integration) then
          ["5", "6", "7", "8", "9"]
        else
          []
        end
      )
      + (
        if ($surface.runtime_path_change or $surface.user_facing_operation) then
          ["10", "11", "12", "13", "14"]
        else
          []
        end
      )
      + (
        if ($surface.service_boundary_change or $surface.external_integration or $surface.api_change or $surface.data_format_change) then
          ["18", "19", "20"]
        else
          []
        end
      )
      + (
        if $manifest.task_classification == "docs" then
          ["21", "22"]
        else
          []
        end
      )
    end
' "$case_file"
