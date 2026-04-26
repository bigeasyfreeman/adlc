#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR_ROOT="$(mktemp -d)"
PASS=0
FAIL=0
TOTAL=0

cleanup() {
  rm -rf "$TMPDIR_ROOT"
}

trap cleanup EXIT

dummy_agent="$TMPDIR_ROOT/agent.md"
dummy_input="$TMPDIR_ROOT/input.json"
dummy_output="$TMPDIR_ROOT/output.json"

cat > "$dummy_agent" <<'EOF'
## Output Contract
Return JSON.
EOF

printf '{}\n' > "$dummy_input"

assert_case() {
  local description="$1"
  local expected_rc="$2"
  local expected_pattern="$3"
  shift 3

  local output_file="$TMPDIR_ROOT/assert.$TOTAL.log"
  local rc=0

  TOTAL=$((TOTAL + 1))
  set +e
  "$@" >"$output_file" 2>&1
  rc=$?
  set -e

  if [ "$rc" -eq "$expected_rc" ] && {
    if [ -n "$expected_pattern" ]; then
      rg -q "$expected_pattern" "$output_file"
    else
      [ ! -s "$output_file" ]
    fi
  }; then
    printf 'PASS %s\n' "$description"
    PASS=$((PASS + 1))
  else
    printf 'FAIL %s\n' "$description" >&2
    printf '  expected rc=%s pattern=%s\n' "$expected_rc" "$expected_pattern" >&2
    printf '  actual rc=%s\n' "$rc" >&2
    sed 's/^/  /' "$output_file" >&2 || true
    FAIL=$((FAIL + 1))
  fi
}

assert_sourceable() {
  local runtime="$1"
  local adapter="$ROOT/tests/smoke/adapters/${runtime}.sh"

  assert_case \
    "${runtime} adapter sources cleanly" \
    0 \
    "" \
    env -i PATH="/usr/bin:/bin" /bin/bash -c 'source "$1"' bash "$adapter"
}

assert_auth_missing() {
  local runtime="$1"
  local adapter="$ROOT/tests/smoke/adapters/${runtime}.sh"
  local pattern="$2"

  assert_case \
    "${runtime} invoke_agent without auth exits 65" \
    65 \
    "$pattern" \
    env -i PATH="/usr/bin:/bin" /bin/bash "$adapter" invoke_agent \
      --agent "$dummy_agent" \
      --input "$dummy_input" \
      --output "$dummy_output" \
      --tools ""
}

assert_missing_output() {
  local runtime="$1"
  local adapter="$ROOT/tests/smoke/adapters/${runtime}.sh"

  assert_case \
    "${runtime} invoke_agent without output exits 64" \
    64 \
    'usage: invoke_agent --agent <path> --input <path> --output <path>' \
    env -i PATH="/usr/bin:/bin" /bin/bash "$adapter" invoke_agent \
      --agent "$dummy_agent" \
      --input "$dummy_input" \
      --tools ""
}

assert_cli_missing() {
  local runtime="$1"
  local adapter="$ROOT/tests/smoke/adapters/${runtime}.sh"
  local env_name="$2"
  local env_value="$3"
  local pattern="$4"

  assert_case \
    "${runtime} invoke_agent with auth but hidden CLI exits 77" \
    77 \
    "$pattern" \
    env -i PATH="/usr/bin:/bin" "$env_name=$env_value" /bin/bash "$adapter" invoke_agent \
      --agent "$dummy_agent" \
      --input "$dummy_input" \
      --output "$dummy_output" \
      --tools ""
}

for runtime in claude codex cursor antigravity factory; do
  assert_sourceable "$runtime"
done

assert_auth_missing claude 'smoke auth missing: set ANTHROPIC_API_KEY or ADLC_SMOKE_SETTINGS=/path/to/settings.json'
assert_auth_missing codex 'codex auth missing: set OPENAI_API_KEY or ADLC_SMOKE_SETTINGS_CODEX=/path/to/config.toml'
assert_auth_missing cursor 'cursor auth missing: set CURSOR_API_KEY or install the cursor CLI with native auth configured'
assert_auth_missing antigravity 'antigravity auth missing: set GOOGLE_API_KEY or GEMINI_API_KEY'
assert_auth_missing factory 'factory auth missing: set FACTORY_API_KEY'

assert_missing_output cursor
assert_missing_output antigravity
assert_missing_output factory

assert_cli_missing claude ANTHROPIC_API_KEY dummy 'claude CLI is not installed'
assert_cli_missing codex OPENAI_API_KEY dummy 'codex CLI not installed'
assert_cli_missing cursor CURSOR_API_KEY dummy 'cursor CLI not installed'
assert_cli_missing antigravity GOOGLE_API_KEY dummy 'antigravity CLI not installed'
assert_cli_missing factory FACTORY_API_KEY dummy 'factory CLI not installed'

printf 'Results: %s passed, %s failed, %s total\n' "$PASS" "$FAIL" "$TOTAL"

[ "$FAIL" -eq 0 ]
