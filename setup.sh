#!/usr/bin/env bash
set -euo pipefail

# ADLC Setup compatibility wrapper.
# MIGRATION NOTICE (2026-07-14): legacy peer skills and agents are retained as
# internal source packs, but default installs expose only the canonical `adlc`
# skill. Prefer `adlc-skill install` for Claude Code and Codex lifecycle control.

ADLC_DIR="$(cd "$(dirname "$0")" && pwd)"
PLATFORM="${1:-}"
TARGET="${2:-.}"
TARGET="$(cd "$TARGET" && pwd)"
INSTALL_RUNTIME=1
LEGACY_ANTIGRAVITY_AGENTS_SHA256="fdc6fb623030d6f1fa09eaf1a7a15598713699243101b5caa3cec35bb8bcf010"

usage() {
  echo "ADLC Setup — install the canonical ADLC skill"
  echo ""
  echo "Usage: ./setup.sh <platform> [target-repo-path]"
  echo ""
  echo "Platforms: claude | codex | cursor | antigravity | factory | all | verify-claude"
  echo ""
  echo "Migration (2026-07-14): default installs now expose one public skill: adlc."
  echo "Legacy peer skills and agents remain in the ADLC source tree as internal packs."
  exit 1
}

[ -n "$PLATFORM" ] || usage
echo "MIGRATION NOTICE (2026-07-14): setup.sh now installs only the canonical adlc skill; prefer adlc-skill for transactional Claude Code and Codex installs." >&2

skill_digest() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    python3 - "$1" <<'PY'
import hashlib
import pathlib
import sys
print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())
PY
  fi
}

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

# A pre-MIG009 setup manifest is proof that setup.sh owned the listed path. We
# remove only byte-identical managed files; drift blocks migration so user work
# is never silently deleted.
preflight_manifest_prune() {
  local manifest="$1"
  local base="$2"
  local suffix="$3"
  [ -f "$manifest" ] || return 0
  local recorded_hash name path actual_hash
  while read -r recorded_hash name; do
    [ -n "$name" ] || continue
    path="$base/$name$suffix"
    [ -e "$path" ] || continue
    actual_hash="$(skill_digest "$path")"
    if [ "$actual_hash" != "$recorded_hash" ]; then
      echo "  ✗ legacy managed path has local changes: ${path#$TARGET/}" >&2
      echo "    Move or reconcile it, then rerun setup.sh; nothing will be pruned." >&2
      return 1
    fi
  done < "$manifest"
}

prune_manifest_paths() {
  local manifest="$1"
  local base="$2"
  local suffix="$3"
  [ -f "$manifest" ] || return 0
  local _recorded_hash name path
  while read -r _recorded_hash name; do
    [ -n "$name" ] || continue
    path="$base/$name$suffix"
    if [ -e "$path" ]; then
      rm -f "$path"
      if [ "$suffix" = "/SKILL.md" ]; then
        rmdir "$base/$name" 2>/dev/null || true
      fi
    fi
  done < "$manifest"
  rm -f "$manifest"
}

preflight_known_legacy_files() {
  local layout="$1"
  local source path name
  case "$layout" in
    cursor)
      for source in "$ADLC_DIR"/skills/*/SKILL.md; do
        name="$(basename "$(dirname "$source")")"
        path="$TARGET/.cursor/rules/adlc-$name.mdc"
        [ ! -e "$path" ] || [ "$(skill_digest "$path")" = "$(skill_digest "$source")" ] || {
          echo "  ✗ legacy Cursor rule has local changes: ${path#$TARGET/}" >&2; return 1;
        }
      done
      for source in "$ADLC_DIR"/agents/*.md; do
        name="$(basename "$source" .md)"
        path="$TARGET/.cursor/rules/adlc-agent-$name.mdc"
        [ ! -e "$path" ] || [ "$(skill_digest "$path")" = "$(skill_digest "$source")" ] || {
          echo "  ✗ legacy Cursor agent rule has local changes: ${path#$TARGET/}" >&2; return 1;
        }
      done
      ;;
    factory)
      for source in "$ADLC_DIR"/skills/*/SKILL.md; do
        name="$(basename "$(dirname "$source")")"
        path="$TARGET/.factory/docs/skills/adlc-$name.md"
        [ ! -e "$path" ] || [ "$(skill_digest "$path")" = "$(skill_digest "$source")" ] || {
          echo "  ✗ legacy Factory skill doc has local changes: ${path#$TARGET/}" >&2; return 1;
        }
      done
      for source in "$ADLC_DIR"/agents/*.md; do
        name="$(basename "$source" .md)"
        path="$TARGET/.factory/droids/adlc-$name.md"
        [ ! -e "$path" ] || [ "$(skill_digest "$path")" = "$(skill_digest "$source")" ] || {
          echo "  ✗ legacy Factory droid has local changes: ${path#$TARGET/}" >&2; return 1;
        }
      done
      for source in "$ADLC_DIR"/platform/factory/droids/*.yaml; do
        [ -f "$source" ] || continue
        path="$TARGET/.factory/droids/$(basename "$source")"
        [ ! -e "$path" ] || [ "$(skill_digest "$path")" = "$(skill_digest "$source")" ] || {
          echo "  ✗ legacy Factory droid has local changes: ${path#$TARGET/}" >&2; return 1;
        }
      done
      ;;
  esac
}

prune_known_legacy_files() {
  local layout="$1"
  local source path name
  case "$layout" in
    cursor)
      for source in "$ADLC_DIR"/skills/*/SKILL.md; do
        name="$(basename "$(dirname "$source")")"
        path="$TARGET/.cursor/rules/adlc-$name.mdc"
        [ ! -e "$path" ] || rm -f "$path"
      done
      for source in "$ADLC_DIR"/agents/*.md; do
        name="$(basename "$source" .md)"
        path="$TARGET/.cursor/rules/adlc-agent-$name.mdc"
        [ ! -e "$path" ] || rm -f "$path"
      done
      ;;
    factory)
      for source in "$ADLC_DIR"/skills/*/SKILL.md; do
        name="$(basename "$(dirname "$source")")"
        path="$TARGET/.factory/docs/skills/adlc-$name.md"
        [ ! -e "$path" ] || rm -f "$path"
      done
      for source in "$ADLC_DIR"/agents/*.md; do
        name="$(basename "$source" .md)"
        path="$TARGET/.factory/droids/adlc-$name.md"
        [ ! -e "$path" ] || rm -f "$path"
      done
      for source in "$ADLC_DIR"/platform/factory/droids/*.yaml; do
        [ -f "$source" ] || continue
        path="$TARGET/.factory/droids/$(basename "$source")"
        [ ! -e "$path" ] || rm -f "$path"
      done
      ;;
  esac
}

lifecycle_public_skill() {
  local provider="$1"
  local skill_root agent_root operation
  case "$provider" in
    claude) skill_root="$TARGET/.claude/skills"; agent_root="$TARGET/.claude/agents" ;;
    codex) skill_root="$TARGET/.agents/skills"; agent_root="" ;;
  esac
  preflight_manifest_prune "$skill_root/.adlc-skill-manifest" "$skill_root" "/SKILL.md"
  if [ -n "$agent_root" ]; then
    preflight_manifest_prune "$agent_root/.adlc-agent-manifest" "$agent_root" ""
  fi
  operation=install
  [ ! -f "$TARGET/.adlc/install-manifests/$provider.json" ] || operation=update
  local lifecycle_output
  if ! lifecycle_output="$(PYTHONPATH="$ADLC_DIR/scripts${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -m adlc_runtime.install "$operation" \
      --provider "$provider" --target "$TARGET" --source "$ADLC_DIR/skill" \
      --source-version "setup-compat-2026-07-14")"; then
    printf '%s\n' "$lifecycle_output" >&2
    return 1
  fi
  prune_manifest_paths "$skill_root/.adlc-skill-manifest" "$skill_root" "/SKILL.md"
  if [ -n "$agent_root" ]; then
    prune_manifest_paths "$agent_root/.adlc-agent-manifest" "$agent_root" ""
    rmdir "$agent_root" 2>/dev/null || true
  fi
  echo "  ✓ one canonical adlc skill installed"
}

compile_compat_bundle() {
  local output="$1"
  local temp
  temp="$(mktemp -d)"
  PYTHONPATH="$ADLC_DIR/scripts${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -m adlc_runtime.install compile --provider claude \
      --source "$ADLC_DIR/skill" --output "$temp" >/dev/null
  mkdir -p "$(dirname "$output")"
  rm -rf "$output"
  cp -R "$temp/claude/adlc" "$output"
  rm -rf "$temp"
}

compat_manifest_path() {
  printf '%s/.adlc/compat-manifests/%s.manifest\n' "$TARGET" "$1"
}

preflight_compat_install() {
  local provider="$1"
  shift
  local manifest path relative recorded_hash actual_hash actual_count=0 recorded_count=0
  manifest="$(compat_manifest_path "$provider")"
  if [ ! -f "$manifest" ]; then
    for path in "$@"; do
      if [ -e "$path" ] || [ -L "$path" ]; then
        echo "  ✗ unmanaged canonical $provider path already exists: ${path#$TARGET/}" >&2
        echo "    Move it or adopt it explicitly before rerunning setup.sh." >&2
        return 1
      fi
    done
    return 0
  fi
  while read -r recorded_hash relative; do
    [ -n "$relative" ] || continue
    path="$TARGET/$relative"
    if [ ! -f "$path" ]; then
      echo "  ✗ managed canonical $provider path is missing: $relative" >&2
      return 1
    fi
    actual_hash="$(skill_digest "$path")"
    if [ "$actual_hash" != "$recorded_hash" ]; then
      echo "  ✗ managed canonical $provider path has drifted: $relative" >&2
      echo "    Reconcile it before rerunning setup.sh; local content was not overwritten." >&2
      return 1
    fi
    recorded_count=$((recorded_count + 1))
  done < "$manifest"
  for path in "$@"; do
    if [ -f "$path" ]; then
      actual_count=$((actual_count + 1))
    elif [ -d "$path" ]; then
      actual_count=$((actual_count + $(find "$path" -type f | wc -l | tr -d ' ')))
    fi
  done
  if [ "$actual_count" -ne "$recorded_count" ]; then
    echo "  ✗ managed canonical $provider surface contains untracked files" >&2
    echo "    Reconcile it before rerunning setup.sh; local content was not overwritten." >&2
    return 1
  fi
}

write_compat_manifest() {
  local provider="$1"
  shift
  local manifest temporary path file relative
  manifest="$(compat_manifest_path "$provider")"
  mkdir -p "$(dirname "$manifest")"
  temporary="$manifest.tmp"
  : > "$temporary"
  for path in "$@"; do
    if [ -f "$path" ]; then
      relative="${path#$TARGET/}"
      printf '%s  %s\n' "$(skill_digest "$path")" "$relative" >> "$temporary"
    elif [ -d "$path" ]; then
      while IFS= read -r file; do
        relative="${file#$TARGET/}"
        printf '%s  %s\n' "$(skill_digest "$file")" "$relative" >> "$temporary"
      done < <(find "$path" -type f | sort)
    fi
  done
  sort -o "$temporary" "$temporary"
  mv "$temporary" "$manifest"
}

preflight_legacy_antigravity_agents() {
  local path="$TARGET/agents.md"
  local actual_hash codex_hash
  [ -e "$path" ] || return 0
  actual_hash="$(skill_digest "$path")"
  codex_hash="$(skill_digest "$ADLC_DIR/platform/AGENTS.md")"
  if [ "$actual_hash" = "$LEGACY_ANTIGRAVITY_AGENTS_SHA256" ]; then
    return 0
  fi
  if [ "$actual_hash" = "$codex_hash" ] \
    && [ -f "$TARGET/.adlc/install-manifests/codex.json" ] \
    && [ -f "$TARGET/.agents/skills/adlc/SKILL.md" ]; then
    return 0
  fi
  echo "  ✗ legacy Antigravity agents.md has local changes or unknown ownership: agents.md" >&2
  echo "    Move or reconcile it before rerunning setup.sh; it was not deleted." >&2
  return 1
}

prune_legacy_antigravity_agents() {
  local path="$TARGET/agents.md"
  [ ! -e "$path" ] || [ "$(skill_digest "$path")" != "$LEGACY_ANTIGRAVITY_AGENTS_SHA256" ] || rm -f "$path"
}

install_claude() {
  echo "→ Claude Code"
  lifecycle_public_skill claude
  cp "$ADLC_DIR/platform/CLAUDE.md" "$TARGET/CLAUDE.md"
  mkdir -p "$TARGET/.claude"
  cp "$ADLC_DIR/WORKFLOW.dot" "$TARGET/.claude/WORKFLOW.dot"
}

install_codex() {
  echo "→ Codex"
  lifecycle_public_skill codex
  cp "$ADLC_DIR/platform/AGENTS.md" "$TARGET/AGENTS.md"
}

install_cursor() {
  echo "→ Cursor"
  preflight_known_legacy_files cursor
  preflight_compat_install cursor \
    "$TARGET/.adlc/provider-bundles/cursor/adlc" \
    "$TARGET/.cursor/rules/adlc.mdc"
  compile_compat_bundle "$TARGET/.adlc/provider-bundles/cursor/adlc"
  mkdir -p "$TARGET/.cursor/rules"
  cp "$TARGET/.adlc/provider-bundles/cursor/adlc/SKILL.md" "$TARGET/.cursor/rules/adlc.mdc"
  prune_known_legacy_files cursor
  write_compat_manifest cursor \
    "$TARGET/.adlc/provider-bundles/cursor/adlc" \
    "$TARGET/.cursor/rules/adlc.mdc"
  echo "  ✓ one canonical adlc rule installed"
}

install_antigravity() {
  echo "→ Antigravity"
  preflight_manifest_prune "$TARGET/.agent/skills/.adlc-skill-manifest" "$TARGET/.agent/skills" "/SKILL.md"
  preflight_legacy_antigravity_agents
  preflight_compat_install antigravity "$TARGET/.agent/skills/adlc"
  compile_compat_bundle "$TARGET/.agent/skills/adlc"
  prune_manifest_paths "$TARGET/.agent/skills/.adlc-skill-manifest" "$TARGET/.agent/skills" "/SKILL.md"
  prune_legacy_antigravity_agents
  write_compat_manifest antigravity "$TARGET/.agent/skills/adlc"
  echo "  ✓ one canonical adlc skill installed"
}

install_factory() {
  echo "→ Factory"
  preflight_known_legacy_files factory
  preflight_compat_install factory \
    "$TARGET/.adlc/provider-bundles/factory/adlc" \
    "$TARGET/.factory/docs/skills/adlc.md"
  compile_compat_bundle "$TARGET/.adlc/provider-bundles/factory/adlc"
  mkdir -p "$TARGET/.factory/docs/skills"
  cp "$TARGET/.adlc/provider-bundles/factory/adlc/SKILL.md" "$TARGET/.factory/docs/skills/adlc.md"
  prune_known_legacy_files factory
  if [ -f "$ADLC_DIR/platform/factory/AGENTS.md" ]; then
    cp "$ADLC_DIR/platform/factory/AGENTS.md" "$TARGET/AGENTS.md"
  else
    cp "$ADLC_DIR/platform/AGENTS.md" "$TARGET/AGENTS.md"
  fi
  write_compat_manifest factory \
    "$TARGET/.adlc/provider-bundles/factory/adlc" \
    "$TARGET/.factory/docs/skills/adlc.md"
  echo "  ✓ one canonical adlc document installed"
}

verify_claude() {
  INSTALL_RUNTIME=0
  PYTHONPATH="$ADLC_DIR/scripts${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -m adlc_runtime.install doctor --provider claude --target "$TARGET" >/dev/null
  [ -f "$TARGET/.claude/skills/adlc/SKILL.md" ]
  [ "$(find "$TARGET/.claude/skills" -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l | tr -d ' ')" -eq 1 ]
  [ ! -d "$TARGET/.claude/agents" ] || [ -z "$(find "$TARGET/.claude/agents" -type f -name '*.md' -print -quit)" ]
  echo "  ✓ canonical Claude Code install verified"
}

echo "ADLC Setup"
echo "Source: $ADLC_DIR"
echo "Target: $TARGET"
echo ""

case "$PLATFORM" in
  claude) install_claude ;;
  codex) install_codex ;;
  cursor) install_cursor ;;
  antigravity) install_antigravity ;;
  factory) install_factory ;;
  verify-claude) verify_claude ;;
  all)
    install_claude
    install_codex
    install_cursor
    install_antigravity
    install_factory
    ;;
  *) usage ;;
esac

if [ "$INSTALL_RUNTIME" -eq 1 ]; then
  install_runtime
fi

echo ""
echo "Done. Use /adlc <command>; see skill/reference/ for the dated migration map."
