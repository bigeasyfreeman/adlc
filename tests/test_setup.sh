#!/usr/bin/env bash
set -euo pipefail

# ADLC Setup Script Tests
# Usage: ./tests/test_setup.sh

ADLC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0
TOTAL=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

assert() {
  local desc="$1"
  local condition="$2"
  TOTAL=$((TOTAL + 1))
  if eval "$condition"; then
    echo -e "  ${GREEN}PASS${NC} $desc"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}FAIL${NC} $desc"
    FAIL=$((FAIL + 1))
  fi
}

assert_file_exists() {
  assert "$1" "[ -f '$2' ]"
}

assert_dir_exists() {
  assert "$1" "[ -d '$2' ]"
}

assert_file_contains() {
  assert "$1" "grep -q '$3' '$2' 2>/dev/null"
}

assert_file_count() {
  local desc="$1"
  local dir="$2"
  local pattern="$3"
  local expected="$4"
  local actual
  actual=$(find "$dir" -name "$pattern" 2>/dev/null | wc -l | tr -d ' ')
  assert "$desc (expected $expected, got $actual)" "[ '$actual' -eq '$expected' ]"
}

cleanup() {
  rm -rf "$TMPDIR"
}

# ═══════════════════════════════════════════════════
# Setup
# ═══════════════════════════════════════════════════

TMPDIR="$(mktemp -d)"
trap cleanup EXIT

echo "ADLC Setup Script Tests"
echo "Source: $ADLC_DIR"
echo "Temp:   $TMPDIR"
echo ""

# ═══════════════════════════════════════════════════
# Test 0: Preconditions
# ═══════════════════════════════════════════════════

echo "--- Preconditions ---"
assert_file_exists "setup.sh exists" "$ADLC_DIR/setup.sh"
assert "setup.sh is executable" "[ -x '$ADLC_DIR/setup.sh' ]"
assert_dir_exists "skills/ exists" "$ADLC_DIR/skills"
assert_dir_exists "agents/ exists" "$ADLC_DIR/agents"
assert_dir_exists "platform/ exists" "$ADLC_DIR/platform"

# Count source skills (directories with SKILL.md)
SKILL_COUNT=$(find "$ADLC_DIR/skills" -name "SKILL.md" | wc -l | tr -d ' ')
assert "22 skill SKILL.md files in source" "[ '$SKILL_COUNT' -eq '22' ]"

# Count source agents (excluding legacy pointers)
AGENT_COUNT=$(ls "$ADLC_DIR"/agents/*.md | grep -v 'ADLC-BUILD-BRIEF' | grep -v 'PM-PRD' | wc -l | tr -d ' ')
assert "9 agent configs in source" "[ '$AGENT_COUNT' -eq '9' ]"

echo ""

# ═══════════════════════════════════════════════════
# Test 1: Claude Code Installation
# ═══════════════════════════════════════════════════

echo "--- Claude Code ---"
TARGET="$TMPDIR/claude-test"
mkdir -p "$TARGET"
"$ADLC_DIR/setup.sh" claude "$TARGET" > /dev/null 2>&1

assert_dir_exists ".claude/skills/ created" "$TARGET/.claude/skills"
assert_dir_exists ".claude/agents/ created" "$TARGET/.claude/agents"
assert_file_count "22 skills installed" "$TARGET/.claude/skills" "SKILL.md" 22
assert_file_count "9 agents installed" "$TARGET/.claude/agents" "*.md" 9
assert_file_exists "CLAUDE.md created" "$TARGET/CLAUDE.md"

# Verify specific skills
assert_file_exists "codebase-research skill" "$TARGET/.claude/skills/codebase-research/SKILL.md"
assert_file_exists "eval-council skill" "$TARGET/.claude/skills/eval-council/SKILL.md"
assert_file_exists "figma-integration skill" "$TARGET/.claude/skills/figma-integration/SKILL.md"

# Verify specific agents
assert_file_exists "triage agent" "$TARGET/.claude/agents/triage.md"
assert_file_exists "researcher agent" "$TARGET/.claude/agents/researcher.md"
assert_file_exists "coder agent" "$TARGET/.claude/agents/coder.md"
assert_file_exists "security-reviewer agent" "$TARGET/.claude/agents/security-reviewer.md"

# Verify no legacy agents leaked
assert "No ADLC-BUILD-BRIEF-AGENT in agents" "[ ! -f '$TARGET/.claude/agents/ADLC-BUILD-BRIEF-AGENT.md' ]"
assert "No PM-PRD-AGENT in agents" "[ ! -f '$TARGET/.claude/agents/PM-PRD-AGENT.md' ]"

# Verify agent frontmatter
assert_file_contains "triage has model: sonnet" "$TARGET/.claude/agents/triage.md" "model: sonnet"
assert_file_contains "researcher has skills:" "$TARGET/.claude/agents/researcher.md" "codebase-research"
assert_file_contains "security-reviewer has 5 security skills" "$TARGET/.claude/agents/security-reviewer.md" "appsec-threat-model"

echo ""

# ═══════════════════════════════════════════════════
# Test 2: Codex Installation
# ═══════════════════════════════════════════════════

echo "--- Codex ---"
TARGET="$TMPDIR/codex-test"
mkdir -p "$TARGET"
"$ADLC_DIR/setup.sh" codex "$TARGET" > /dev/null 2>&1

assert_dir_exists ".agents/skills/ created" "$TARGET/.agents/skills"
assert_file_count "22 skills installed" "$TARGET/.agents/skills" "SKILL.md" 22
assert_file_exists "AGENTS.md created" "$TARGET/AGENTS.md"

# Verify AGENTS.md content
assert_file_contains "AGENTS.md has pipeline info" "$TARGET/AGENTS.md" "ADLC"
assert_file_contains "AGENTS.md has working agreements" "$TARGET/AGENTS.md" "Given/When/Then"

echo ""

# ═══════════════════════════════════════════════════
# Test 3: Cursor Installation
# ═══════════════════════════════════════════════════

echo "--- Cursor ---"
TARGET="$TMPDIR/cursor-test"
mkdir -p "$TARGET"
"$ADLC_DIR/setup.sh" cursor "$TARGET" > /dev/null 2>&1

assert_dir_exists ".cursor/rules/ created" "$TARGET/.cursor/rules"
SKILL_RULES=$(find "$TARGET/.cursor/rules" -name "adlc-*.mdc" ! -name "adlc-agent-*.mdc" | wc -l | tr -d ' ')
assert "22 skill rules installed (got $SKILL_RULES)" "[ '$SKILL_RULES' -eq '22' ]"

# Verify specific rule files
assert_file_exists "codebase-research rule" "$TARGET/.cursor/rules/adlc-codebase-research.mdc"
assert_file_exists "eval-council rule" "$TARGET/.cursor/rules/adlc-eval-council.mdc"

# Verify agent rules
AGENT_RULES=$(find "$TARGET/.cursor/rules" -name "adlc-agent-*.mdc" | wc -l | tr -d ' ')
assert "9 agent rules installed (got $AGENT_RULES)" "[ '$AGENT_RULES' -eq '9' ]"
assert_file_exists "triage agent rule" "$TARGET/.cursor/rules/adlc-agent-triage.mdc"

echo ""

# ═══════════════════════════════════════════════════
# Test 4: Antigravity Installation
# ═══════════════════════════════════════════════════

echo "--- Antigravity ---"
TARGET="$TMPDIR/antigravity-test"
mkdir -p "$TARGET"
"$ADLC_DIR/setup.sh" antigravity "$TARGET" > /dev/null 2>&1

assert_dir_exists ".agent/skills/ created" "$TARGET/.agent/skills"
assert_file_count "22 skills installed" "$TARGET/.agent/skills" "SKILL.md" 22
assert_file_exists "agents.md created" "$TARGET/agents.md"

# Verify agents.md has persona format
assert_file_contains "agents.md has Goal/Traits/Constraint" "$TARGET/agents.md" "Goal"
assert_file_contains "agents.md has 9 agents" "$TARGET/agents.md" "PR Preparer"

echo ""

# ═══════════════════════════════════════════════════
# Test 5: Factory Installation
# ═══════════════════════════════════════════════════

echo "--- Factory ---"
TARGET="$TMPDIR/factory-test"
mkdir -p "$TARGET"
"$ADLC_DIR/setup.sh" factory "$TARGET" > /dev/null 2>&1

assert_dir_exists ".factory/droids/ created" "$TARGET/.factory/droids"
assert_dir_exists ".factory/docs/ created" "$TARGET/.factory/docs"
assert_file_count "9 droids installed" "$TARGET/.factory/droids" "adlc-*.md" 9
assert_file_count "22 skill docs installed" "$TARGET/.factory/docs" "adlc-*.md" 22
assert_file_exists "AGENTS.md created" "$TARGET/AGENTS.md"

# Verify specific droids
assert_file_exists "triage droid" "$TARGET/.factory/droids/adlc-triage.md"
assert_file_exists "researcher droid" "$TARGET/.factory/droids/adlc-researcher.md"

echo ""

# ═══════════════════════════════════════════════════
# Test 6: 'all' Installation
# ═══════════════════════════════════════════════════

echo "--- All Platforms ---"
TARGET="$TMPDIR/all-test"
mkdir -p "$TARGET"
"$ADLC_DIR/setup.sh" all "$TARGET" > /dev/null 2>&1

assert_dir_exists "Claude: .claude/skills/" "$TARGET/.claude/skills"
assert_dir_exists "Claude: .claude/agents/" "$TARGET/.claude/agents"
assert_dir_exists "Codex: .agents/skills/" "$TARGET/.agents/skills"
assert_dir_exists "Cursor: .cursor/rules/" "$TARGET/.cursor/rules"
assert_dir_exists "Antigravity: .agent/skills/" "$TARGET/.agent/skills"
assert_dir_exists "Factory: .factory/droids/" "$TARGET/.factory/droids"
assert_dir_exists "Factory: .factory/docs/" "$TARGET/.factory/docs"

echo ""

# ═══════════════════════════════════════════════════
# Test 7: Idempotency (run twice, same result)
# ═══════════════════════════════════════════════════

echo "--- Idempotency ---"
TARGET="$TMPDIR/idempotent-test"
mkdir -p "$TARGET"
"$ADLC_DIR/setup.sh" claude "$TARGET" > /dev/null 2>&1
"$ADLC_DIR/setup.sh" claude "$TARGET" > /dev/null 2>&1

assert_file_count "Still 22 skills after double install" "$TARGET/.claude/skills" "SKILL.md" 22
assert_file_count "Still 9 agents after double install" "$TARGET/.claude/agents" "*.md" 9

echo ""

# ═══════════════════════════════════════════════════
# Test 8: Invalid platform
# ═══════════════════════════════════════════════════

echo "--- Error Handling ---"
assert "Invalid platform shows usage" "! '$ADLC_DIR/setup.sh' banana '$TMPDIR' > /dev/null 2>&1"
assert "No args shows usage" "! '$ADLC_DIR/setup.sh' > /dev/null 2>&1"

echo ""

# ═══════════════════════════════════════════════════
# Test 9: Skill Content Integrity
# ═══════════════════════════════════════════════════

echo "--- Content Integrity ---"
TARGET="$TMPDIR/integrity-test"
mkdir -p "$TARGET"
"$ADLC_DIR/setup.sh" claude "$TARGET" > /dev/null 2>&1

# Verify skills are not empty
for skill_dir in "$TARGET/.claude/skills"/*/; do
  skill_name="$(basename "$skill_dir")"
  size=$(wc -c < "$skill_dir/SKILL.md" | tr -d ' ')
  assert "$skill_name SKILL.md is non-empty ($size bytes)" "[ '$size' -gt '100' ]"
done

echo ""

# ═══════════════════════════════════════════════════
# Results
# ═══════════════════════════════════════════════════

echo "═══════════════════════════════════════"
echo -e "Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}, $TOTAL total"
echo "═══════════════════════════════════════"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
