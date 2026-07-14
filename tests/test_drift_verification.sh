#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

if [ -d "$ROOT/.claude" ] || [ -f "$ROOT/CLAUDE.md" ]; then
  "$ROOT/setup.sh" verify-claude "$ROOT" >/dev/null
  echo "live root install verified"
fi

"$ROOT/setup.sh" claude "$TMP_ROOT" >/dev/null
"$ROOT/setup.sh" verify-claude "$TMP_ROOT" >/dev/null

mutated_agent="$TMP_ROOT/.claude/agents/planner.md"
printf '\n<!-- stale install fixture -->\n' >> "$mutated_agent"

set +e
stale_output="$($ROOT/setup.sh verify-claude "$TMP_ROOT" 2>&1)"
stale_status=$?
set -e

if [ "$stale_status" -eq 0 ] || ! printf '%s\n' "$stale_output" | grep -Fq 'digest mismatch: planner.md'; then
  echo "drift verification did not fail closed on planner.md" >&2
  exit 1
fi

echo "stale install detected: planner.md"
echo "remediation: ./setup.sh claude ."

"$ROOT/setup.sh" claude "$TMP_ROOT" >/dev/null
"$ROOT/setup.sh" verify-claude "$TMP_ROOT" >/dev/null
echo "fresh install verified"
