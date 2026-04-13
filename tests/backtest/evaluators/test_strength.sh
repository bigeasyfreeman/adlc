#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <case-json>" >&2
  exit 1
fi

case_file="$1"

jq -ce '
  if ((has("post_qa") | not) or (.post_qa == null)) then
    {"verdict": "n_a", "coverage": 0, "mutation_kill_rate": 0}
  else
    (.post_qa.coverage // null) as $coverage
    | (.post_qa.mutation_kill_rate // null) as $kill_rate
    | if ($coverage == null or $kill_rate == null) then
        {
          "verdict": "stuck",
          "coverage": ($coverage // 0),
          "mutation_kill_rate": ($kill_rate // 0)
        }
      elif (($coverage | type) != "number" or ($kill_rate | type) != "number") then
        error("post_qa coverage and mutation_kill_rate must be numeric")
      elif ($coverage >= 0.8 and $kill_rate >= 0.6) then
        {
          "verdict": "pass",
          "coverage": $coverage,
          "mutation_kill_rate": $kill_rate
        }
      else
        {
          "verdict": "weak",
          "coverage": $coverage,
          "mutation_kill_rate": $kill_rate
        }
      end
  end
' "$case_file"
