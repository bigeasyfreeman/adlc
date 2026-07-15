#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

for path in \
  README.md LICENSE CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md GOVERNANCE.md CHANGELOG.md pyproject.toml \
  .github/CODEOWNERS \
  .github/workflows/ci.yml .github/PULL_REQUEST_TEMPLATE.md .github/dependabot.yml \
  .github/ISSUE_TEMPLATE/bug_report.yml .github/ISSUE_TEMPLATE/feature_request.yml \
  .github/ISSUE_TEMPLATE/config.yml; do
  test -s "$path" || { echo "missing public project file: $path" >&2; exit 1; }
done

repo_files=()
while IFS= read -r path; do
  [ -f "$path" ] && repo_files+=("$path")
done < <(git ls-files --cached --others --exclude-standard)

if rg --text -n -- '/(Users|home)/[A-Za-z0-9._-]+/' "${repo_files[@]}"; then
  echo "tracked developer-local absolute path found" >&2
  exit 1
fi

if rg --text -n -- '(sk-(ant-|proj-)?[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,})' "${repo_files[@]}"; then
  echo "tracked credential-like value found" >&2
  exit 1
fi

tracked_runtime_artifacts="$(printf '%s\n' "${repo_files[@]}" | grep -E '(^|/)(\.env($|\.)|credentials\.json|[^/]+\.(pem|key)|__pycache__|[^/]+\.pyc)$' || true)"
if [ -n "$tracked_runtime_artifacts" ]; then
  printf 'tracked runtime or credential artifacts found:\n%s\n' "$tracked_runtime_artifacts" >&2
  exit 1
fi

for path in "${repo_files[@]}"; do
  case "$path" in
    *.json) jq empty "$path" >/dev/null ;;
  esac
done

python3 tests/check_markdown_links.py
python3 scripts/render_support_matrix.py --check

test ! -e docs/adlc-v2-specification.md
test ! -e docs/adlc-v2-tickets.md
test ! -e TECH_DEBT_AUDIT.md

echo "public hygiene: pass"
