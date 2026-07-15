#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_ROOT="$(mktemp -d)"
PASS=0
FAIL=0
trap 'rm -rf "$TMP_ROOT"' EXIT

assert() {
  local description="$1"
  shift
  if "$@"; then
    echo "  PASS $description"
    PASS=$((PASS + 1))
  else
    echo "  FAIL $description"
    FAIL=$((FAIL + 1))
  fi
}

count_files() {
  find "$1" -type f -name "$2" 2>/dev/null | wc -l | tr -d ' '
}

is_equal() {
  [ "$1" = "$2" ]
}

echo "ADLC canonical setup compatibility tests"

python3 "$ROOT/tests/check_legacy_surface_migration.py" \
  --ledger "$ROOT/docs/migration/legacy-surface-ledger.json"

assert "setup is executable" test -x "$ROOT/setup.sh"
assert "canonical source exists" test -f "$ROOT/skill/SKILL.src.md"
assert "dated migration guide exists" grep -Fq '2026-07-14' "$ROOT/docs/migration/legacy-surface-migration.md"

for platform in claude codex cursor antigravity factory; do
  target="$TMP_ROOT/$platform"
  mkdir -p "$target"
  "$ROOT/setup.sh" "$platform" "$target" >/dev/null 2>&1
  assert "$platform runtime wrapper" test -x "$target/.adlc/bin/adlc"
  assert "$platform health check" bash -c "'$target/.adlc/bin/adlc' health-check --json | jq -e '.summary.failed_required == 0' >/dev/null"
done

assert "Claude exposes one skill" is_equal "$(count_files "$TMP_ROOT/claude/.claude/skills" SKILL.md)" 1
assert "Claude public skill is adlc" test -f "$TMP_ROOT/claude/.claude/skills/adlc/SKILL.md"
assert "Claude exposes no peer agents" is_equal "$(count_files "$TMP_ROOT/claude/.claude/agents" '*.md')" 0
assert "Claude compatibility verification passes" "$ROOT/setup.sh" verify-claude "$TMP_ROOT/claude"

assert "Codex exposes one skill" is_equal "$(count_files "$TMP_ROOT/codex/.agents/skills" SKILL.md)" 1
assert "Codex public skill is adlc" test -f "$TMP_ROOT/codex/.agents/skills/adlc/SKILL.md"
assert "Codex instructions installed" test -f "$TMP_ROOT/codex/AGENTS.md"

assert "Cursor exposes one ADLC rule" is_equal "$(count_files "$TMP_ROOT/cursor/.cursor/rules" 'adlc*.mdc')" 1
assert "Cursor public rule is adlc" test -f "$TMP_ROOT/cursor/.cursor/rules/adlc.mdc"
assert "Cursor reference bundle is available" test -f "$TMP_ROOT/cursor/.adlc/provider-bundles/cursor/adlc/reference/command-build.md"
assert "Cursor compatibility ownership manifest exists" test -f "$TMP_ROOT/cursor/.adlc/compat-manifests/cursor.manifest"

assert "Antigravity exposes one skill" is_equal "$(count_files "$TMP_ROOT/antigravity/.agent/skills" SKILL.md)" 1
assert "Antigravity public skill is adlc" test -f "$TMP_ROOT/antigravity/.agent/skills/adlc/SKILL.md"
assert "Antigravity compatibility ownership manifest exists" test -f "$TMP_ROOT/antigravity/.adlc/compat-manifests/antigravity.manifest"

assert "Factory exposes one ADLC doc" is_equal "$(count_files "$TMP_ROOT/factory/.factory/docs/skills" 'adlc*.md')" 1
assert "Factory public doc is adlc" test -f "$TMP_ROOT/factory/.factory/docs/skills/adlc.md"
assert "Factory exposes no legacy droid markdown" is_equal "$(count_files "$TMP_ROOT/factory/.factory/droids" 'adlc-*.md')" 0
assert "Factory compatibility ownership manifest exists" test -f "$TMP_ROOT/factory/.adlc/compat-manifests/factory.manifest"

all_target="$TMP_ROOT/all"
mkdir -p "$all_target"
"$ROOT/setup.sh" all "$all_target" >/dev/null 2>&1
assert "all installs Claude canonical skill" test -f "$all_target/.claude/skills/adlc/SKILL.md"
assert "all installs Codex canonical skill" test -f "$all_target/.agents/skills/adlc/SKILL.md"
assert "all installs Cursor canonical rule" test -f "$all_target/.cursor/rules/adlc.mdc"
assert "all installs Antigravity canonical skill" test -f "$all_target/.agent/skills/adlc/SKILL.md"
assert "all installs Factory canonical doc" test -f "$all_target/.factory/docs/skills/adlc.md"
assert "all ends with canonical Factory instructions" grep -Fq '# ADLC — Factory' "$all_target/AGENTS.md"

"$ROOT/setup.sh" all "$all_target" >/dev/null 2>&1
assert "all is idempotent for Claude" is_equal "$(count_files "$all_target/.claude/skills" SKILL.md)" 1
assert "all is idempotent for Codex" is_equal "$(count_files "$all_target/.agents/skills" SKILL.md)" 1

migration_target="$TMP_ROOT/migration"
mkdir -p "$migration_target/.claude/skills/build-feature" "$migration_target/.claude/agents"
cp "$ROOT/skills/build-feature/SKILL.md" "$migration_target/.claude/skills/build-feature/SKILL.md"
cp "$ROOT/agents/planner.md" "$migration_target/.claude/agents/planner.md"
skill_hash="$(shasum -a 256 "$ROOT/skills/build-feature/SKILL.md" | awk '{print $1}')"
agent_hash="$(shasum -a 256 "$ROOT/agents/planner.md" | awk '{print $1}')"
printf '%s  build-feature\n' "$skill_hash" > "$migration_target/.claude/skills/.adlc-skill-manifest"
printf '%s  planner.md\n' "$agent_hash" > "$migration_target/.claude/agents/.adlc-agent-manifest"
"$ROOT/setup.sh" claude "$migration_target" >/dev/null 2>&1
assert "owned legacy peer skill is pruned" test ! -f "$migration_target/.claude/skills/build-feature/SKILL.md"
assert "owned legacy peer agent is pruned" test ! -f "$migration_target/.claude/agents/planner.md"
assert "migration installs canonical skill" test -f "$migration_target/.claude/skills/adlc/SKILL.md"

drift_target="$TMP_ROOT/drift"
mkdir -p "$drift_target/.claude/skills/build-feature"
cp "$ROOT/skills/build-feature/SKILL.md" "$drift_target/.claude/skills/build-feature/SKILL.md"
printf '%s  build-feature\n' "$skill_hash" > "$drift_target/.claude/skills/.adlc-skill-manifest"
printf '\nlocal user edit\n' >> "$drift_target/.claude/skills/build-feature/SKILL.md"
assert "changed legacy peer blocks destructive migration" bash -c "! '$ROOT/setup.sh' claude '$drift_target' >/dev/null 2>&1"
assert "changed legacy peer is preserved" grep -Fq 'local user edit' "$drift_target/.claude/skills/build-feature/SKILL.md"
assert "blocked preflight does not partially install canonical skill" test ! -e "$drift_target/.claude/skills/adlc"

cursor_migration="$TMP_ROOT/cursor-migration"
mkdir -p "$cursor_migration/.cursor/rules"
cp "$ROOT/skills/build-feature/SKILL.md" "$cursor_migration/.cursor/rules/adlc-build-feature.mdc"
cp "$ROOT/agents/planner.md" "$cursor_migration/.cursor/rules/adlc-agent-planner.mdc"
"$ROOT/setup.sh" cursor "$cursor_migration" >/dev/null 2>&1
assert "known Cursor peer skill is pruned" test ! -e "$cursor_migration/.cursor/rules/adlc-build-feature.mdc"
assert "known Cursor peer agent is pruned" test ! -e "$cursor_migration/.cursor/rules/adlc-agent-planner.mdc"

cursor_collision="$TMP_ROOT/cursor-collision"
mkdir -p "$cursor_collision/.cursor/rules"
printf 'unmanaged canonical rule\n' > "$cursor_collision/.cursor/rules/adlc.mdc"
assert "unmanaged Cursor canonical rule blocks install" bash -c "! '$ROOT/setup.sh' cursor '$cursor_collision' >/dev/null 2>&1"
assert "unmanaged Cursor canonical rule is preserved" grep -Fq 'unmanaged canonical rule' "$cursor_collision/.cursor/rules/adlc.mdc"

printf '\nlocal Cursor canonical edit\n' >> "$cursor_migration/.cursor/rules/adlc.mdc"
assert "drifted managed Cursor canonical rule blocks update" bash -c "! '$ROOT/setup.sh' cursor '$cursor_migration' >/dev/null 2>&1"
assert "drifted managed Cursor canonical rule is preserved" grep -Fq 'local Cursor canonical edit' "$cursor_migration/.cursor/rules/adlc.mdc"

antigravity_migration="$TMP_ROOT/antigravity-migration"
mkdir -p "$antigravity_migration"
cp "$ROOT/tests/fixtures/migration/antigravity-agents-pre-mig009.md" "$antigravity_migration/agents.md"
"$ROOT/setup.sh" antigravity "$antigravity_migration" >/dev/null 2>&1
assert "known legacy Antigravity agents.md is retired" test ! -e "$antigravity_migration/agents.md"

antigravity_drift="$TMP_ROOT/antigravity-drift"
mkdir -p "$antigravity_drift"
cp "$ROOT/tests/fixtures/migration/antigravity-agents-pre-mig009.md" "$antigravity_drift/agents.md"
printf '\nlocal Antigravity edit\n' >> "$antigravity_drift/agents.md"
assert "changed legacy Antigravity agents.md blocks migration" bash -c "! '$ROOT/setup.sh' antigravity '$antigravity_drift' >/dev/null 2>&1"
assert "changed legacy Antigravity agents.md is preserved" grep -Fq 'local Antigravity edit' "$antigravity_drift/agents.md"

antigravity_unknown="$TMP_ROOT/antigravity-unknown"
mkdir -p "$antigravity_unknown"
cp "$ROOT/platform/AGENTS.md" "$antigravity_unknown/agents.md"
assert "Codex-shaped agents.md without Codex ownership blocks Antigravity" bash -c "! '$ROOT/setup.sh' antigravity '$antigravity_unknown' >/dev/null 2>&1"
assert "unknown agents.md is preserved" test -f "$antigravity_unknown/agents.md"

antigravity_codex="$TMP_ROOT/antigravity-codex-coexistence"
mkdir -p "$antigravity_codex"
"$ROOT/setup.sh" codex "$antigravity_codex" >/dev/null 2>&1
"$ROOT/setup.sh" antigravity "$antigravity_codex" >/dev/null 2>&1
assert "manifest-proven Codex AGENTS instruction coexists with Antigravity" grep -Fq '# ADLC — Codex' "$antigravity_codex/AGENTS.md"

printf '\nlocal Antigravity canonical edit\n' >> "$antigravity_migration/.agent/skills/adlc/SKILL.md"
assert "drifted managed Antigravity canonical skill blocks update" bash -c "! '$ROOT/setup.sh' antigravity '$antigravity_migration' >/dev/null 2>&1"
assert "drifted managed Antigravity canonical skill is preserved" grep -Fq 'local Antigravity canonical edit' "$antigravity_migration/.agent/skills/adlc/SKILL.md"

factory_migration="$TMP_ROOT/factory-migration"
mkdir -p "$factory_migration/.factory/docs/skills" "$factory_migration/.factory/droids"
cp "$ROOT/skills/build-feature/SKILL.md" "$factory_migration/.factory/docs/skills/adlc-build-feature.md"
cp "$ROOT/agents/planner.md" "$factory_migration/.factory/droids/adlc-planner.md"
cp "$ROOT/platform/factory/droids/planner.yaml" "$factory_migration/.factory/droids/planner.yaml"
"$ROOT/setup.sh" factory "$factory_migration" >/dev/null 2>&1
assert "known Factory peer skill is pruned" test ! -e "$factory_migration/.factory/docs/skills/adlc-build-feature.md"
assert "known Factory peer agent is pruned" test ! -e "$factory_migration/.factory/droids/adlc-planner.md"
assert "known Factory native droid is pruned" test ! -e "$factory_migration/.factory/droids/planner.yaml"

printf '\nlocal Factory canonical edit\n' >> "$factory_migration/.factory/docs/skills/adlc.md"
assert "drifted managed Factory canonical doc blocks update" bash -c "! '$ROOT/setup.sh' factory '$factory_migration' >/dev/null 2>&1"
assert "drifted managed Factory canonical doc is preserved" grep -Fq 'local Factory canonical edit' "$factory_migration/.factory/docs/skills/adlc.md"

factory_collision="$TMP_ROOT/factory-collision"
mkdir -p "$factory_collision/.factory/docs/skills"
printf 'unmanaged Factory canonical doc\n' > "$factory_collision/.factory/docs/skills/adlc.md"
assert "unmanaged Factory canonical doc blocks install" bash -c "! '$ROOT/setup.sh' factory '$factory_collision' >/dev/null 2>&1"
assert "unmanaged Factory canonical doc is preserved" grep -Fq 'unmanaged Factory canonical doc' "$factory_collision/.factory/docs/skills/adlc.md"

assert "excluded execute-trade is not installed" bash -c "! rg -l 'name: execute-trade' '$all_target/.claude' '$all_target/.agents' '$all_target/.cursor' '$all_target/.agent' '$all_target/.factory' >/dev/null"
assert "excluded ship-content is not installed" bash -c "! rg -l 'name: ship-content' '$all_target/.claude' '$all_target/.agents' '$all_target/.cursor' '$all_target/.agent' '$all_target/.factory' >/dev/null"
assert "invalid platform fails" bash -c "! '$ROOT/setup.sh' banana '$TMP_ROOT' >/dev/null 2>&1"
assert "missing platform fails" bash -c "! '$ROOT/setup.sh' >/dev/null 2>&1"

echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
