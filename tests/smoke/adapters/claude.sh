#!/usr/bin/env bash
set -euo pipefail

# Runtime: claude
# Minimum CLI Version: 2.1.105
# Auth Env Vars: ANTHROPIC_API_KEY or ADLC_SMOKE_SETTINGS
# Flag Mapping:
# - system prompt: --system-prompt
# - tool allowlist: --allowed-tools and --tools
# - settings/isolation: --bare, --settings, ephemeral HOME
# - session persistence: --no-session-persistence
# - JSON output: stdout redirected to --output, optional --output-format json
# - schema enforcement: --json-schema with --output-format json
# Known Limitations:
# - bare mode ignores OAuth and keychain auth; the adapter requires ANTHROPIC_API_KEY or ADLC_SMOKE_SETTINGS with apiKeyHelper

_adlc_claude_help_cache=""

_adlc_claude_help() {
  if [ -z "${_adlc_claude_help_cache}" ]; then
    _adlc_claude_help_cache="$(claude --help)"
  fi
  printf '%s\n' "${_adlc_claude_help_cache}"
}

_adlc_claude_has_flag() {
  local flag="$1"

  _adlc_claude_help | awk -v flag="$flag" '
    /^[[:space:]]*-/ {
      line = $0
      sub(/^[[:space:]]*/, "", line)
      split(line, cols, /[[:space:]][[:space:]]+/)
      options = cols[1]
      gsub(/,/, " ", options)
      count = split(options, parts, /[[:space:]]+/)
      for (i = 1; i <= count; i++) {
        if (parts[i] == flag) {
          found = 1
        }
      }
    }
    END {
      exit(found ? 0 : 1)
    }
  '
}

_adlc_claude_require_flag() {
  local flag="$1"

  if ! _adlc_claude_has_flag "$flag"; then
    echo "claude CLI missing required flag: $flag" >&2
    return 66
  fi
}

_adlc_claude_emit_error() {
  local stderr_log="$1"
  local message="$2"

  if [ -n "$stderr_log" ]; then
    printf '%s\n' "$message" | tee -a "$stderr_log" >&2
  else
    printf '%s\n' "$message" >&2
  fi
}

_adlc_claude_parse_args() {
  _ADLC_AGENT_PATH=""
  _ADLC_INPUT_PATH=""
  _ADLC_OUTPUT_PATH=""
  _ADLC_TOOLS_CSV=""
  _ADLC_SCHEMA_PATH=""

  while [ "$#" -gt 0 ]; do
    case "$1" in
      --agent)
        [ "$#" -ge 2 ] || {
          echo "missing value for --agent" >&2
          return 64
        }
        _ADLC_AGENT_PATH="$2"
        shift 2
        ;;
      --input)
        [ "$#" -ge 2 ] || {
          echo "missing value for --input" >&2
          return 64
        }
        _ADLC_INPUT_PATH="$2"
        shift 2
        ;;
      --output)
        [ "$#" -ge 2 ] || {
          echo "missing value for --output" >&2
          return 64
        }
        _ADLC_OUTPUT_PATH="$2"
        shift 2
        ;;
      --tools)
        [ "$#" -ge 2 ] || {
          echo "missing value for --tools" >&2
          return 64
        }
        _ADLC_TOOLS_CSV="$2"
        shift 2
        ;;
      --schema)
        [ "$#" -ge 2 ] || {
          echo "missing value for --schema" >&2
          return 64
        }
        _ADLC_SCHEMA_PATH="$2"
        shift 2
        ;;
      *)
        echo "unknown argument: $1" >&2
        return 64
        ;;
    esac
  done

  if [ -z "$_ADLC_AGENT_PATH" ] || [ -z "$_ADLC_INPUT_PATH" ] || [ -z "$_ADLC_OUTPUT_PATH" ]; then
    echo "usage: invoke_agent --agent <path> --input <path> --output <path> --tools <csv> [--schema <path>]" >&2
    return 64
  fi
}

_adlc_claude_auth_path() {
  if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    printf 'env\n'
    return 0
  fi

  if [ -n "${ADLC_SMOKE_SETTINGS:-}" ] && [ -r "${ADLC_SMOKE_SETTINGS}" ]; then
    printf 'settings-file\n'
    return 0
  fi

  echo "smoke auth missing: set ANTHROPIC_API_KEY or ADLC_SMOKE_SETTINGS=/path/to/settings.json" >&2
  return 65
}

_adlc_adapter_preflight() {
  if [ "$#" -ne 0 ]; then
    echo "usage: preflight" >&2
    return 64
  fi

  _adlc_claude_auth_path
}

_adlc_adapter_invoke_agent() {
  local stderr_log=""
  local temp_home=""
  local original_home="${HOME-}"
  local original_xdg_config_home="${XDG_CONFIG_HOME-}"
  local original_xdg_state_home="${XDG_STATE_HOME-}"
  local original_xdg_cache_home="${XDG_CACHE_HOME-}"
  local original_claude_simple="${CLAUDE_CODE_SIMPLE-}"
  local original_anthropic_api_key="${ANTHROPIC_API_KEY-}"
  local auth_path=""
  local auth_note=""
  local settings_arg="/dev/null"
  local system_prompt=""
  local json_schema=""
  local schema_enforcement_note=""
  local status=0
  local -a cmd
  local -a missing_schema_flags=()

  _adlc_claude_parse_args "$@" || return $?
  stderr_log="${_ADLC_OUTPUT_PATH}.stderr.log"
  : > "$stderr_log"

  auth_path="$(_adlc_claude_auth_path)" || {
    status=$?
    _adlc_claude_emit_error "$stderr_log" "smoke auth missing: set ANTHROPIC_API_KEY or ADLC_SMOKE_SETTINGS=/path/to/settings.json"
    return "$status"
  }

  if ! command -v claude >/dev/null 2>&1; then
    _adlc_claude_emit_error "$stderr_log" "claude CLI is not installed"
    return 77
  fi

  _adlc_claude_require_flag "--settings" || {
    status=$?
    _adlc_claude_emit_error "$stderr_log" "claude CLI missing required flag: --settings"
    return "$status"
  }
  _adlc_claude_require_flag "--bare" || {
    status=$?
    _adlc_claude_emit_error "$stderr_log" "claude CLI missing required flag: --bare"
    return "$status"
  }
  _adlc_claude_require_flag "--permission-mode" || {
    status=$?
    _adlc_claude_emit_error "$stderr_log" "claude CLI missing required flag: --permission-mode"
    return "$status"
  }
  _adlc_claude_require_flag "--allowedTools" || {
    status=$?
    _adlc_claude_emit_error "$stderr_log" "claude CLI missing required flag: --allowedTools"
    return "$status"
  }
  _adlc_claude_require_flag "--tools" || {
    status=$?
    _adlc_claude_emit_error "$stderr_log" "claude CLI missing required flag: --tools"
    return "$status"
  }
  _adlc_claude_require_flag "--model" || {
    status=$?
    _adlc_claude_emit_error "$stderr_log" "claude CLI missing required flag: --model"
    return "$status"
  }
  _adlc_claude_require_flag "--no-session-persistence" || {
    status=$?
    _adlc_claude_emit_error "$stderr_log" "claude CLI missing required flag: --no-session-persistence"
    return "$status"
  }
  _adlc_claude_require_flag "--system-prompt" || {
    status=$?
    _adlc_claude_emit_error "$stderr_log" "claude CLI missing required flag: --system-prompt"
    return "$status"
  }

  system_prompt="$(cat "$_ADLC_AGENT_PATH")"

  if [ "$auth_path" = "settings-file" ]; then
    settings_arg="$ADLC_SMOKE_SETTINGS"
  fi

  auth_note="invoke_agent: auth path ${auth_path}."

  if [ -n "$_ADLC_SCHEMA_PATH" ]; then
    if _adlc_claude_has_flag "--json-schema"; then
      :
    else
      missing_schema_flags+=("--json-schema")
    fi

    if _adlc_claude_has_flag "--output-format"; then
      :
    else
      missing_schema_flags+=("--output-format")
    fi

    if [ "${#missing_schema_flags[@]}" -eq 0 ]; then
      json_schema="$(jq -c . "$_ADLC_SCHEMA_PATH")"
      schema_enforcement_note="invoke_agent: enabling CLI schema enforcement with --output-format json and --json-schema; downstream validate_json remains authoritative."
    else
      schema_enforcement_note="invoke_agent: skipping CLI schema enforcement because claude CLI lacks ${missing_schema_flags[*]}; downstream validate_json remains authoritative."
    fi
  fi

  temp_home="$(mktemp -d)"

  export HOME="$temp_home"
  export XDG_CONFIG_HOME="$temp_home/.config"
  export XDG_STATE_HOME="$temp_home/.local/state"
  export XDG_CACHE_HOME="$temp_home/.cache"
  export CLAUDE_CODE_SIMPLE=1
  mkdir -p "$XDG_CONFIG_HOME" "$XDG_STATE_HOME" "$XDG_CACHE_HOME"

  if [ "$auth_path" = "env" ]; then
    export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"
  else
    unset ANTHROPIC_API_KEY
  fi

  cmd=(
    claude
    --bare
    --settings "$settings_arg"
    --no-session-persistence
    --permission-mode bypassPermissions
    --allowed-tools "$_ADLC_TOOLS_CSV"
    --tools "$_ADLC_TOOLS_CSV"
    --print
  )

  if [ -n "${ADLC_MODEL:-}" ]; then
    cmd+=(--model "$ADLC_MODEL")
  fi

  cmd+=(--system-prompt "$system_prompt")

  if [ -n "$json_schema" ]; then
    cmd+=(--output-format json --json-schema "$json_schema")
  fi

  printf '%s\n' "$auth_note" >> "$stderr_log"
  if [ -n "$schema_enforcement_note" ]; then
    printf '%s\n' "$schema_enforcement_note" >> "$stderr_log"
  fi

  if < "$_ADLC_INPUT_PATH" "${cmd[@]}" > "$_ADLC_OUTPUT_PATH" 2>> "$stderr_log"; then
    status=0
  else
    status=$?
  fi

  if [ -n "$original_home" ]; then
    export HOME="$original_home"
  else
    unset HOME
  fi

  if [ -n "$original_xdg_config_home" ]; then
    export XDG_CONFIG_HOME="$original_xdg_config_home"
  else
    unset XDG_CONFIG_HOME
  fi

  if [ -n "$original_xdg_state_home" ]; then
    export XDG_STATE_HOME="$original_xdg_state_home"
  else
    unset XDG_STATE_HOME
  fi

  if [ -n "$original_xdg_cache_home" ]; then
    export XDG_CACHE_HOME="$original_xdg_cache_home"
  else
    unset XDG_CACHE_HOME
  fi

  if [ -n "$original_claude_simple" ]; then
    export CLAUDE_CODE_SIMPLE="$original_claude_simple"
  else
    unset CLAUDE_CODE_SIMPLE
  fi

  if [ -n "$original_anthropic_api_key" ]; then
    export ANTHROPIC_API_KEY="$original_anthropic_api_key"
  else
    unset ANTHROPIC_API_KEY
  fi

  rm -rf "$temp_home"
  return "$status"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  case "${1:-}" in
    preflight)
      shift
      _adlc_adapter_preflight "$@"
      ;;
    invoke_agent)
      shift
      _adlc_adapter_invoke_agent "$@"
      ;;
    *)
      echo "usage: $0 {preflight|invoke_agent} ..." >&2
      exit 64
      ;;
  esac
fi
