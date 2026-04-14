#!/usr/bin/env bash
set -euo pipefail

# Runtime: factory
# Minimum CLI Version: unknown; Factory CLI is not installed on this machine
# Auth Env Vars: FACTORY_API_KEY
# Flag Mapping:
# - system prompt: unverified; requires a confirmed non-interactive prompt override in the Factory CLI
# - tool allowlist: unverified; requires a confirmed non-interactive tool grant surface
# - settings/isolation: unverified; requires a confirmed isolated config path or ephemeral mode
# - session persistence: unverified; requires a confirmed no-history or ephemeral mode
# - JSON output: unverified; requires a confirmed non-interactive raw-text mode
# - schema enforcement: unverified; rely on tests/smoke/stages/_validate.sh until the CLI surface is confirmed
# Known Limitations:
# - This adapter only validates auth and binary presence in the current environment; it exits 66 if Factory is installed but the invocation surface is still unverified

_adlc_factory_emit_error() {
  local stderr_log="$1"
  local message="$2"

  if [ -n "$stderr_log" ]; then
    printf '%s\n' "$message" | tee -a "$stderr_log" >&2
  else
    printf '%s\n' "$message" >&2
  fi
}

_adlc_factory_parse_args() {
  _ADLC_OUTPUT_PATH=""

  while [ "$#" -gt 0 ]; do
    case "$1" in
      --agent|--input|--output|--tools|--schema)
        [ "$#" -ge 2 ] || {
          echo "missing value for $1" >&2
          return 64
        }
        if [ "$1" = "--output" ]; then
          _ADLC_OUTPUT_PATH="$2"
        fi
        shift 2
        ;;
      *)
        echo "unknown argument: $1" >&2
        return 64
        ;;
    esac
  done
}

_adlc_factory_auth_path() {
  if [ -n "${FACTORY_API_KEY:-}" ]; then
    printf 'env\n'
    return 0
  fi

  echo "factory auth missing: set FACTORY_API_KEY" >&2
  return 65
}

_adlc_adapter_preflight() {
  if [ "$#" -ne 0 ]; then
    echo "usage: preflight" >&2
    return 64
  fi

  _adlc_factory_auth_path
}

_adlc_adapter_invoke_agent() {
  local stderr_log=""
  local status=0

  _adlc_factory_parse_args "$@" || return $?
  stderr_log="${_ADLC_OUTPUT_PATH}.stderr.log"
  : > "$stderr_log"

  _adlc_factory_auth_path >/dev/null || {
    status=$?
    _adlc_factory_emit_error "$stderr_log" "factory auth missing: set FACTORY_API_KEY"
    return "$status"
  }

  if ! command -v factory >/dev/null 2>&1; then
    _adlc_factory_emit_error "$stderr_log" "factory CLI not installed"
    return 77
  fi

  _adlc_factory_emit_error "$stderr_log" "factory CLI is installed, but this adapter does not have a verified non-interactive smoke invocation surface"
  return 66
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
