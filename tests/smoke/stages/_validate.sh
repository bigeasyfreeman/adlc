#!/usr/bin/env bash
set -euo pipefail

# Validation order:
# 1. `jq empty` for JSON parse checks
# 2. `python3 -m jsonschema` when the Python jsonschema module is installed
# 3. `ajv validate` when ajv-cli is installed

validate_json() {
  if [ "$#" -ne 2 ]; then
    echo "usage: validate_json <file> <schema_path>" >&2
    return 64
  fi

  local file_path="$1"
  local schema_path="$2"

  jq empty "$file_path" >/dev/null

  if python3 -c 'import jsonschema' >/dev/null 2>&1; then
    python3 -m jsonschema -i "$file_path" "$schema_path"
    return 0
  fi

  if command -v ajv >/dev/null 2>&1; then
    ajv validate -s "$schema_path" -d "$file_path"
    return 0
  fi

  echo "No JSON Schema validator is installed. Install python package 'jsonschema' or ajv-cli." >&2
  return 77
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  validate_json "$@"
fi
