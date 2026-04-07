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
  echo "  factory       → .factory/droids/"
  echo "  all           → Install for all platforms"
  echo ""
  echo "Examples:"
  echo "  ./setup.sh claude              # Install to current dir for Claude Code"
  echo "  ./setup.sh codex ~/my-project  # Install to ~/my-project for Codex"
  echo "  ./setup.sh all .               # Install for all platforms"
  exit 1
}

[ -z "$PLATFORM" ] && usage

sync_skills() {
  local dest="$1"
  echo "  Syncing 22 skills → $dest"
  mkdir -p "$dest"
  for skill_dir in "$ADLC_DIR"/skills/*/; do
    skill_name="$(basename "$skill_dir")"
    mkdir -p "$dest/$skill_name"
    cp "$skill_dir/SKILL.md" "$dest/$skill_name/SKILL.md"
  done
  echo "  ✓ 22 skills installed"
}

install_claude() {
  echo "→ Claude Code"

  # Skills
  sync_skills "$TARGET/.claude/skills"

  # Agents (subagents)
  mkdir -p "$TARGET/.claude/agents"
  for agent in "$ADLC_DIR"/agents/*.md; do
    name="$(basename "$agent")"
    # Skip legacy pointers
    [[ "$name" == "ADLC-BUILD-BRIEF-AGENT.md" ]] && continue
    [[ "$name" == "PM-PRD-AGENT.md" ]] && continue
    cp "$agent" "$TARGET/.claude/agents/$name"
  done
  echo "  ✓ 9 agents installed to .claude/agents/"

  # CLAUDE.md instructions
  cp "$ADLC_DIR/platform/CLAUDE.md" "$TARGET/CLAUDE.md" 2>/dev/null || \
    cp "$ADLC_DIR/platform/instructions.md" "$TARGET/CLAUDE.md" 2>/dev/null || true

  # Workflow files
  cp "$ADLC_DIR/WORKFLOW.dot" "$TARGET/.claude/WORKFLOW.dot" 2>/dev/null || true

  echo "  ✓ Claude Code setup complete"
}

install_codex() {
  echo "→ Codex (OpenAI)"

  # Skills
  sync_skills "$TARGET/.agents/skills"

  # AGENTS.md instructions
  cp "$ADLC_DIR/platform/AGENTS.md" "$TARGET/AGENTS.md" 2>/dev/null || \
    cp "$ADLC_DIR/platform/instructions.md" "$TARGET/AGENTS.md" 2>/dev/null || true

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
  echo "  ✓ 22 skills installed as .cursor/rules/*.mdc"

  # Agent rules
  for agent in "$ADLC_DIR"/agents/*.md; do
    name="$(basename "$agent" .md)"
    [[ "$name" == "ADLC-BUILD-BRIEF-AGENT" ]] && continue
    [[ "$name" == "PM-PRD-AGENT" ]] && continue
    cp "$agent" "$TARGET/.cursor/rules/adlc-agent-${name}.mdc"
  done
  echo "  ✓ 9 agent rules installed"

  echo "  ✓ Cursor setup complete"
}

install_antigravity() {
  echo "→ Antigravity (Google)"

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

  # Droids (agents as .md files in .factory/droids/)
  mkdir -p "$TARGET/.factory/droids"
  for agent in "$ADLC_DIR"/agents/*.md; do
    name="$(basename "$agent" .md)"
    [[ "$name" == "ADLC-BUILD-BRIEF-AGENT" ]] && continue
    [[ "$name" == "PM-PRD-AGENT" ]] && continue
    cp "$agent" "$TARGET/.factory/droids/adlc-${name}.md"
  done
  echo "  ✓ 9 droids installed to .factory/droids/"

  # Skills as approved docs
  mkdir -p "$TARGET/.factory/docs"
  for skill_dir in "$ADLC_DIR"/skills/*/; do
    skill_name="$(basename "$skill_dir")"
    cp "$skill_dir/SKILL.md" "$TARGET/.factory/docs/adlc-${skill_name}.md"
  done
  echo "  ✓ 22 skill docs installed to .factory/docs/"

  # AGENTS.md
  cp "$ADLC_DIR/platform/AGENTS.md" "$TARGET/AGENTS.md" 2>/dev/null || true

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

echo ""
echo "Done. See README.md for usage instructions."
