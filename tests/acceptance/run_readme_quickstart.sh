#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

grep -Fq 'bash tests/acceptance/run_readme_quickstart.sh' README.md
grep -Fq '/adlc fix the failing average calculation.' README.md
python3 scripts/render_support_matrix.py --check

echo "README quick start: replaying isolated deterministic Fix"
bash tests/acceptance/run_public_fix_loop.sh

echo "README quick start: pass"
echo "limitation: the fixture installs the Codex layout but does not invoke a live provider"
