#!/usr/bin/env bash
set -euo pipefail

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "source tests/smoke/stages/_invoke.sh and call preflight or invoke_agent" >&2
  exit 64
fi

_adlc_smoke_supported_runtimes="claude codex cursor antigravity factory"
_adlc_smoke_loaded_runtime=""

_adlc_smoke_runtime() {
  printf '%s\n' "${ADLC_RUNTIME:-claude}"
}

_adlc_smoke_source_adapter() {
  local runtime adapter_path
  runtime="$(_adlc_smoke_runtime)"

  case "$runtime" in
    claude|codex|cursor|antigravity|factory) ;;
    *)
      echo "unsupported runtime: $runtime (supported: $_adlc_smoke_supported_runtimes)" >&2
      return 64
      ;;
  esac

  if [ "$_adlc_smoke_loaded_runtime" = "$runtime" ]; then
    return 0
  fi

  adapter_path="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/adapters/${runtime}.sh"
  if [ ! -r "$adapter_path" ]; then
    echo "smoke adapter missing: $adapter_path" >&2
    return 66
  fi

  unset -f _adlc_adapter_preflight 2>/dev/null || true
  unset -f _adlc_adapter_invoke_agent 2>/dev/null || true
  # shellcheck source=/dev/null
  source "$adapter_path"

  if ! declare -F _adlc_adapter_preflight >/dev/null 2>&1; then
    echo "smoke adapter missing function: _adlc_adapter_preflight ($runtime)" >&2
    return 66
  fi

  if ! declare -F _adlc_adapter_invoke_agent >/dev/null 2>&1; then
    echo "smoke adapter missing function: _adlc_adapter_invoke_agent ($runtime)" >&2
    return 66
  fi

  _adlc_smoke_loaded_runtime="$runtime"
}

preflight() {
  _adlc_smoke_source_adapter || return $?
  _adlc_adapter_preflight "$@"
}

invoke_agent() {
  _adlc_smoke_source_adapter || return $?
  _adlc_adapter_invoke_agent "$@"
}
