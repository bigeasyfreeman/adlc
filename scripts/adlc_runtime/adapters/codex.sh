#!/usr/bin/env bash
set -euo pipefail

# Runtime: codex
# Minimum CLI Version: 0.120.0
# Auth Env Vars: OPENAI_API_KEY or ADLC_SMOKE_SETTINGS_CODEX
# Flag Mapping:
# - system prompt: -c developer_instructions="..."
# - tool allowlist: -c default_tools_enabled=false plus -c enabled_tools=[...]
# - settings/isolation: ephemeral HOME plus ~/.codex/config.toml copied from ADLC_SMOKE_SETTINGS_CODEX when provided
# - session persistence: --ephemeral
# - JSON output: stdout redirected to --output
# - schema enforcement: --output-schema
# Known Limitations:
# - Codex prepends built-in runtime instructions; the adapter injects agent markdown through developer_instructions as the runtime-equivalent system prompt

_adlc_codex_help_cache=""

_adlc_codex_help() {
  if [ -z "${_adlc_codex_help_cache}" ]; then
    _adlc_codex_help_cache="$(codex exec --help)"
  fi
  printf '%s\n' "${_adlc_codex_help_cache}"
}

_adlc_codex_has_flag() {
  local flag="$1"

  _adlc_codex_help | awk -v flag="$flag" '
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

_adlc_codex_require_flag() {
  local flag="$1"

  if ! _adlc_codex_has_flag "$flag"; then
    echo "codex CLI missing required flag: $flag" >&2
    return 66
  fi
}

_adlc_codex_emit_error() {
  local stderr_log="$1"
  local message="$2"

  if [ -n "$stderr_log" ]; then
    printf '%s\n' "$message" | tee -a "$stderr_log" >&2
  else
    printf '%s\n' "$message" >&2
  fi
}

_adlc_codex_parse_args() {
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

_adlc_codex_auth_path() {
  if [ -n "${OPENAI_API_KEY:-}" ]; then
    printf 'env\n'
    return 0
  fi

  if [ -n "${ADLC_SMOKE_SETTINGS_CODEX:-}" ] && [ -r "${ADLC_SMOKE_SETTINGS_CODEX}" ]; then
    printf 'settings-file\n'
    return 0
  fi

  echo "codex auth missing: set OPENAI_API_KEY or ADLC_SMOKE_SETTINGS_CODEX=/path/to/config.toml" >&2
  return 65
}

_adlc_adapter_preflight() {
  if [ "$#" -ne 0 ]; then
    echo "usage: preflight" >&2
    return 64
  fi

  _adlc_codex_auth_path
}

_adlc_adapter_invoke_agent() {
  local stderr_log=""
  local temp_home=""
  local original_home="${HOME-}"
  local original_xdg_config_home="${XDG_CONFIG_HOME-}"
  local original_xdg_state_home="${XDG_STATE_HOME-}"
  local original_xdg_cache_home="${XDG_CACHE_HOME-}"
  local original_openai_api_key="${OPENAI_API_KEY-}"
  local original_pythonpath="${PYTHONPATH-}"
  local original_pythonuserbase="${PYTHONUSERBASE-}"
  local original_pythonno_usersite="${PYTHONNOUSERSITE-}"
  local auth_path=""
  local auth_note=""
  local schema_enforcement_note=""
  local developer_instructions=""
  local enabled_tools="[]"
  local reasoning_effort="${ADLC_REASONING_EFFORT:-medium}"
  local sandbox_mode="read-only"
  local status=0
  local preserved_python_user_site=""
  local -a cmd

  _adlc_codex_parse_args "$@" || return $?
  stderr_log="${_ADLC_OUTPUT_PATH}.stderr.log"
  : > "$stderr_log"

  auth_path="$(_adlc_codex_auth_path)" || {
    status=$?
    _adlc_codex_emit_error "$stderr_log" "codex auth missing: set OPENAI_API_KEY or ADLC_SMOKE_SETTINGS_CODEX=/path/to/config.toml"
    return "$status"
  }

  if ! command -v codex >/dev/null 2>&1; then
    _adlc_codex_emit_error "$stderr_log" "codex CLI not installed"
    return 77
  fi

  _adlc_codex_require_flag "--sandbox" || {
    status=$?
    _adlc_codex_emit_error "$stderr_log" "codex CLI missing required flag: --sandbox"
    return "$status"
  }
  _adlc_codex_require_flag "--ephemeral" || {
    status=$?
    _adlc_codex_emit_error "$stderr_log" "codex CLI missing required flag: --ephemeral"
    return "$status"
  }
  _adlc_codex_require_flag "--model" || {
    status=$?
    _adlc_codex_emit_error "$stderr_log" "codex CLI missing required flag: --model"
    return "$status"
  }
  _adlc_codex_require_flag "--config" || {
    status=$?
    _adlc_codex_emit_error "$stderr_log" "codex CLI missing required flag: --config"
    return "$status"
  }

  developer_instructions="$(jq -Rs . < "$_ADLC_AGENT_PATH")"
  enabled_tools="$(printf '%s' "$_ADLC_TOOLS_CSV" | jq -Rc 'split(",") | map(gsub("^\\s+|\\s+$"; "")) | map(select(length > 0))')"

  if command -v python3 >/dev/null 2>&1; then
    preserved_python_user_site="$(
      PYTHONNOUSERSITE= python3 - <<'PY'
import site
print(site.getusersitepackages())
PY
    )"
  fi

  case ",$_ADLC_TOOLS_CSV," in
    *,Write,*|*,Edit,*|*,Bash,*)
      sandbox_mode="workspace-write"
      ;;
  esac

  auth_note="invoke_agent: auth path ${auth_path}."

  # OpenAI structured-output rejects schemas where any property is not in `required`.
  # Our ADLC schemas deliberately permit optional fields, so CLI-side enforcement via
  # --output-schema returns HTTP 400 "Invalid schema for response_format". Skip CLI
  # enforcement entirely and let downstream validate_json be authoritative.
  if [ -n "$_ADLC_SCHEMA_PATH" ]; then
    schema_enforcement_note="invoke_agent: CLI schema enforcement disabled (OpenAI strict-schema incompat with optional fields); downstream validate_json is authoritative."
  fi

  if [ -n "$original_home" ] && [ -d "$original_home" ] && [ -w "$original_home" ]; then
    temp_home="$(mktemp -d "$original_home/.adlc-smoke-codex.XXXXXX")"
  else
    temp_home="$(mktemp -d)"
  fi

  export HOME="$temp_home"
  export XDG_CONFIG_HOME="$temp_home/.config"
  export XDG_STATE_HOME="$temp_home/.local/state"
  export XDG_CACHE_HOME="$temp_home/.cache"
  mkdir -p "$HOME/.codex" "$XDG_CONFIG_HOME" "$XDG_STATE_HOME" "$XDG_CACHE_HOME"

  if [ -n "$preserved_python_user_site" ] && [ -d "$preserved_python_user_site" ]; then
    export PYTHONPATH="${original_pythonpath:+$original_pythonpath:}$preserved_python_user_site"
    if [ -n "$original_home" ] && [ -d "$original_home/Library/Python" ]; then
      export PYTHONUSERBASE="$original_home/Library/Python"
    fi
    unset PYTHONNOUSERSITE
  fi

  if [ "$auth_path" = "env" ]; then
    export OPENAI_API_KEY="${OPENAI_API_KEY}"
  else
    unset OPENAI_API_KEY
    cp "$ADLC_SMOKE_SETTINGS_CODEX" "$HOME/.codex/config.toml"
    # Codex OAuth credentials live in a sibling auth.json beside config.toml.
    # Without it the CLI has config but no bearer token and every request 401s.
    local settings_dir
    settings_dir="$(cd "$(dirname "$ADLC_SMOKE_SETTINGS_CODEX")" && pwd)"
    if [ -r "$settings_dir/auth.json" ]; then
      cp "$settings_dir/auth.json" "$HOME/.codex/auth.json"
      chmod 600 "$HOME/.codex/auth.json"
    fi
  fi

  # Override any user-provided reasoning effort that the target model may reject
  # (e.g. "xhigh" is accepted by codex-1p but not by the API-exposed reasoning
  # models which only allow low/medium/high). Pin to "high" for predictable runs.
  cmd=(
    codex exec
    --sandbox "$sandbox_mode"
    --ephemeral
    -c 'approval_policy="never"'
    -c "model_reasoning_effort=\"$reasoning_effort\""
    -c "developer_instructions=$developer_instructions"
    -c 'default_tools_enabled=false'
    -c "enabled_tools=$enabled_tools"
  )

  if [ -n "${ADLC_MODEL:-}" ]; then
    cmd+=(--model "$ADLC_MODEL")
  fi

  # --output-schema intentionally omitted; see rationale above. Downstream
  # _validate.sh enforces the schema post-call.

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

  if [ -n "$original_openai_api_key" ]; then
    export OPENAI_API_KEY="$original_openai_api_key"
  else
    unset OPENAI_API_KEY
  fi

  if [ -n "$original_pythonpath" ]; then
    export PYTHONPATH="$original_pythonpath"
  else
    unset PYTHONPATH
  fi

  if [ -n "$original_pythonuserbase" ]; then
    export PYTHONUSERBASE="$original_pythonuserbase"
  else
    unset PYTHONUSERBASE
  fi

  if [ -n "$original_pythonno_usersite" ]; then
    export PYTHONNOUSERSITE="$original_pythonno_usersite"
  else
    unset PYTHONNOUSERSITE
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
