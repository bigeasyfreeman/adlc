#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

if [ -f "$ROOT/.adlc/install-manifests/claude.json" ]; then
  PYTHONPATH="$ROOT/scripts${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -m adlc_runtime.install doctor --provider claude --target "$ROOT" >/dev/null
  echo "live root canonical install verified"
fi

"$ROOT/setup.sh" claude "$TMP_ROOT" >/dev/null
"$ROOT/setup.sh" verify-claude "$TMP_ROOT" >/dev/null

mutated="$TMP_ROOT/.claude/skills/adlc/SKILL.md"
printf '\n<!-- stale canonical install fixture -->\n' >> "$mutated"

set +e
stale_output="$($ROOT/setup.sh verify-claude "$TMP_ROOT" 2>&1)"
stale_status=$?
set -e

if [ "$stale_status" -eq 0 ]; then
  echo "drift verification did not fail closed on canonical SKILL.md" >&2
  exit 1
fi

if ! printf '%s\n' "$stale_output" | grep -Eq 'SKILL.md|canonical|blocked'; then
  echo "drift verification did not identify the canonical install" >&2
  printf '%s\n' "$stale_output" >&2
  exit 1
fi

echo "stale canonical install detected: .claude/skills/adlc/SKILL.md"
echo "remediation: adlc-skill update --provider claude --target ."

PYTHONPATH="$ROOT/scripts${PYTHONPATH:+:$PYTHONPATH}" \
  python3 -m adlc_runtime.install rollback --provider claude --target "$TMP_ROOT" >/dev/null 2>&1 && {
    echo "unexpected rollback availability on initial install" >&2
    exit 1
  } || true

# A drifted managed install must not be overwritten by the compatibility path.
set +e
repair_output="$($ROOT/setup.sh claude "$TMP_ROOT" 2>&1)"
repair_status=$?
set -e
if [ "$repair_status" -eq 0 ] || ! grep -Fq 'managed files drifted' <<<"$repair_output"; then
  echo "compatibility update did not refuse drifted canonical content" >&2
  exit 1
fi

echo "drifted canonical install preserved for explicit reconciliation"
