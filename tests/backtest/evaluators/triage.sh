#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <case-json>" >&2
  exit 1
fi

case_file="$1"

jq -ce '
  .expected_manifest.task_classification_confidence as $confidence
  | if ($confidence | type) != "number" then
      error("missing task_classification_confidence")
    elif $confidence >= 0.8 then
      {"label": "proceed", "confidence_band": "proceed"}
    elif $confidence >= 0.6 then
      {"label": "low_confidence", "confidence_band": "low_confidence"}
    else
      {"label": "escalate", "confidence_band": "escalate"}
    end
' "$case_file"
