#!/usr/bin/env bash
set -euo pipefail

# ADLC Setup — Install skills and agents into your AI coding tool
# Usage: ./setup.sh <platform> [target-repo-path]
#
# Platforms: claude | codex | cursor | antigravity | factory | all
# If target-repo-path is omitted, installs to current directory.

ADLC_DIR="$(cd "$(dirname "$0")" && pwd)"
PLATFORM="${1:-}"
TARGET="${2:-.}"
TARGET="$(cd "$TARGET" && pwd)"

count_source_skills() {
  find "$ADLC_DIR/skills" -mindepth 2 -maxdepth 2 -type f -name SKILL.md | wc -l | tr -d ' '
}

count_installable_agents() {
  find "$ADLC_DIR/agents" -maxdepth 1 -type f -name "*.md" \
    ! -name "ADLC-BUILD-BRIEF-AGENT.md" \
    ! -name "PM-PRD-AGENT.md" | wc -l | tr -d ' '
}

SOURCE_SKILL_COUNT="$(count_source_skills)"
INSTALLABLE_AGENT_COUNT="$(count_installable_agents)"

usage() {
  echo "ADLC Setup — Install into your AI coding tool"
  echo ""
  echo "Usage: ./setup.sh <platform> [target-repo-path]"
  echo ""
  echo "Platforms:"
  echo "  claude        → .claude/skills/ + .claude/agents/"
  echo "  codex         → .agents/skills/ + AGENTS.md"
  echo "  cursor        → .cursor/rules/"
  echo "  antigravity   → .agent/skills/ + agents.md"
  echo "  factory       → .factory/droids/ + .factory/docs/skills/"
  echo "  all           → Install for all platforms"
  echo ""
  echo "Examples:"
  echo "  ./setup.sh claude              # Install to current dir for Claude Code"
  echo "  ./setup.sh codex ~/my-project  # Install to ~/my-project for Codex"
  echo "  ./setup.sh all .               # Install for all platforms"
  exit 1
}

[ -z "$PLATFORM" ] && usage

install_runtime() {
  local bin_dir="$TARGET/.adlc/bin"
  mkdir -p "$bin_dir"
  cat > "$bin_dir/adlc" <<SH
#!/usr/bin/env bash
set -euo pipefail
export ADLC_ROOT="$ADLC_DIR"
exec "$ADLC_DIR/bin/adlc" "\$@"
SH
  chmod +x "$bin_dir/adlc"
  echo "  ✓ ADLC runtime wrapper installed to .adlc/bin/adlc"
}

sync_skills() {
  local dest="$1"
  echo "  Syncing $SOURCE_SKILL_COUNT skills → $dest"
  mkdir -p "$dest"
  for skill_dir in "$ADLC_DIR"/skills/*/; do
    skill_name="$(basename "$skill_dir")"
    mkdir -p "$dest/$skill_name"
    cp "$skill_dir/SKILL.md" "$dest/$skill_name/SKILL.md"
  done
  echo "  ✓ $SOURCE_SKILL_COUNT skills installed"
}

install_claude() {
  echo "→ Claude Code"

  # Skills
  sync_skills "$TARGET/.claude/skills"

  # Agents (subagents)
  mkdir -p "$TARGET/.claude/agents"
  for agent in "$ADLC_DIR"/agents/*.md; do
    name="$(basename "$agent")"
    # Skip non-installable top-level reference docs
    [[ "$name" == "ADLC-BUILD-BRIEF-AGENT.md" ]] && continue
    [[ "$name" == "PM-PRD-AGENT.md" ]] && continue
    cp "$agent" "$TARGET/.claude/agents/$name"
  done
  echo "  ✓ $INSTALLABLE_AGENT_COUNT installable agents installed to .claude/agents/"

  # CLAUDE.md instructions
  cp "$ADLC_DIR/platform/CLAUDE.md" "$TARGET/CLAUDE.md"

  # Workflow files
  cp "$ADLC_DIR/WORKFLOW.dot" "$TARGET/.claude/WORKFLOW.dot"

  echo "  ✓ Claude Code setup complete"
}

install_codex() {
  echo "→ Codex (OpenAI)"

  # Skills
  sync_skills "$TARGET/.agents/skills"

  # AGENTS.md instructions
  cp "$ADLC_DIR/platform/AGENTS.md" "$TARGET/AGENTS.md"

  echo "  ✓ Codex setup complete"
}

install_cursor() {
  echo "→ Cursor"

  # Rules (skills as .mdc files)
  mkdir -p "$TARGET/.cursor/rules"
  for skill_dir in "$ADLC_DIR"/skills/*/; do
    skill_name="$(basename "$skill_dir")"
    # Convert SKILL.md to .mdc format
    # Cursor uses description + globs in frontmatter
    cp "$skill_dir/SKILL.md" "$TARGET/.cursor/rules/adlc-${skill_name}.mdc"
  done
  echo "  ✓ $SOURCE_SKILL_COUNT skills installed as .cursor/rules/*.mdc"

  # Agent rules
  for agent in "$ADLC_DIR"/agents/*.md; do
    name="$(basename "$agent" .md)"
    [[ "$name" == "ADLC-BUILD-BRIEF-AGENT" ]] && continue
    [[ "$name" == "PM-PRD-AGENT" ]] && continue
    cp "$agent" "$TARGET/.cursor/rules/adlc-agent-${name}.mdc"
  done
  echo "  ✓ $INSTALLABLE_AGENT_COUNT installable agent rules installed"

  echo "  ✓ Cursor setup complete"
}

install_antigravity() {
  echo "→ Antigravity"

  # Skills
  sync_skills "$TARGET/.agent/skills"

  # agents.md (persona definitions)
  if [ -f "$ADLC_DIR/platform/agents-antigravity.md" ]; then
    cp "$ADLC_DIR/platform/agents-antigravity.md" "$TARGET/agents.md"
  fi

  echo "  ✓ Antigravity setup complete"
}

install_factory() {
  echo "→ Factory"

  # Droid YAML configs (Factory-native droid definitions)
  mkdir -p "$TARGET/.factory/droids"
  local droid_count=0
  if [ -d "$ADLC_DIR/platform/factory/droids" ]; then
    for droid in "$ADLC_DIR"/platform/factory/droids/*.yaml; do
      [ -f "$droid" ] || continue
      cp "$droid" "$TARGET/.factory/droids/$(basename "$droid")"
      droid_count=$((droid_count + 1))
    done
  fi
  echo "  ✓ $droid_count droid configs installed to .factory/droids/"

  # Agent markdown files as droids (for agents without YAML configs)
  for agent in "$ADLC_DIR"/agents/*.md; do
    name="$(basename "$agent" .md)"
    [[ "$name" == "ADLC-BUILD-BRIEF-AGENT" ]] && continue
    [[ "$name" == "PM-PRD-AGENT" ]] && continue
    cp "$agent" "$TARGET/.factory/droids/adlc-${name}.md"
  done
  echo "  ✓ $INSTALLABLE_AGENT_COUNT agent configs installed to .factory/droids/"

  # Skills as docs (Factory's doc injection path)
  mkdir -p "$TARGET/.factory/docs/skills"
  for skill_dir in "$ADLC_DIR"/skills/*/; do
    skill_name="$(basename "$skill_dir")"
    cp "$skill_dir/SKILL.md" "$TARGET/.factory/docs/skills/adlc-${skill_name}.md"
  done
  echo "  ✓ $SOURCE_SKILL_COUNT skill docs installed to .factory/docs/skills/"

  # AGENTS.md (Factory-specific platform instructions)
  if [ -f "$ADLC_DIR/platform/factory/AGENTS.md" ]; then
    cp "$ADLC_DIR/platform/factory/AGENTS.md" "$TARGET/AGENTS.md"
  else
    cp "$ADLC_DIR/platform/AGENTS.md" "$TARGET/AGENTS.md"
  fi

  # MCP server hints
  echo "  ℹ  Recommended MCP servers for full integration skill support:"
  echo "     - GitHub MCP (built-in) for github-issue-creation"
  echo "     - Atlassian MCP for jira-ticket-creation, confluence-decomposition"
  echo "     - Slack MCP for slack-orchestration"
  echo "     - Grafana MCP for grafana-observability"

  echo "  ✓ Factory setup complete"
}

echo "ADLC Setup"
echo "Source: $ADLC_DIR"
echo "Target: $TARGET"
echo ""

case "$PLATFORM" in
  claude)       install_claude ;;
  codex)        install_codex ;;
  cursor)       install_cursor ;;
  antigravity)  install_antigravity ;;
  factory)      install_factory ;;
  all)
    install_claude
    install_codex
    install_cursor
    install_antigravity
    install_factory
    ;;
  *) usage ;;
esac

install_runtime

echo ""
echo "Done. See README.md for usage instructions."
