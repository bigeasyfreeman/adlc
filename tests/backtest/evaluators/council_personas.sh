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
        "core": ["skeptic", "executioner", "first_principles"],
        "overlays": (
          (
            if ($surface.service_boundary_change or $surface.external_integration or $surface.api_change or $surface.data_format_change) then
              ["architect"]
            else
              []
            end
          )
          + (
            if ($surface.runtime_path_change or $surface.user_facing_operation) then
              ["operator"]
            else
              []
            end
          )
        )
      }
    end
' "$case_file"
