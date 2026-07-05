#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
OUT_DIR="${1:-$(mktemp -d)}"
mkdir -p "$OUT_DIR"

feature_repo="$OUT_DIR/feature-repo-template"
claude_repo="$OUT_DIR/feature-repo-claude"
codex_repo="$OUT_DIR/feature-repo-codex"
mkdir -p "$feature_repo/config" "$feature_repo/src" "$feature_repo/tests/compat"

git -C "$feature_repo" init -q
git -C "$feature_repo" config user.email adlc@example.invalid
git -C "$feature_repo" config user.name "ADLC Test"

printf 'Published contract surface: config/control_config.v1.json follows additive v1 compatibility.\n' > "$feature_repo/CLAUDE.md"
printf '{"version":"1","threshold":1}\n' > "$feature_repo/config/control_config.v1.json"
cat > "$feature_repo/src/loader.py" <<'PY'
import json
from pathlib import Path

CONFIG_PATH = "config/control_config.v1.json"

def threshold(root="."):
    payload = json.loads((Path(root) / CONFIG_PATH).read_text())
    return int(payload["threshold"])
PY
cat > "$feature_repo/tests/test_feature.py" <<'PY'
from src.loader import threshold

assert threshold(".") >= 2
PY
cat > "$feature_repo/tests/run.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
python3 tests/test_feature.py
SH
chmod +x "$feature_repo/tests/run.sh"
printf 'round-trip evidence for config/control_config.v1.json\n' > "$feature_repo/tests/compat/control-config-v1.txt"
git -C "$feature_repo" add CLAUDE.md config/control_config.v1.json src/loader.py tests/run.sh tests/test_feature.py tests/compat/control-config-v1.txt
git -C "$feature_repo" commit -q -m init
git clone -q "$feature_repo" "$claude_repo"
git clone -q "$feature_repo" "$codex_repo"

"$ROOT/bin/adlc" contract-surface-inventory --workspace "$feature_repo" --output "$OUT_DIR/inventory.json" --json > "$OUT_DIR/inventory.stdout.json"
surface_id="$(jq -r '.surfaces[] | select(.path=="config/control_config.v1.json") | .id' "$OUT_DIR/inventory.json")"

jq --arg surface "$surface_id" '
  .brief_id = "CLARITY-HARDENING-FEATURE" |
  .epistemic_ledger = {
    "contract_version":"1.0.0",
    "entries":[
      {"id":"L-config","status":"KNOWN","claim":"config/control_config.v1.json is a versioned product contract surface","architecture_affecting":true,"sources":["CLAUDE.md","config/control_config.v1.json"],"disposition":"repo-evidence"},
      {"id":"L-threshold","status":"UNKNOWN","claim":"Whether the threshold feature should raise the v1 control config threshold","architecture_affecting":true,"sources":[],"disposition":"ask-user","related_blindspot_ids":["B-contract"]}
    ]
  } |
  .sections."18_blindspot_report" = {
    "contract_version":"1.0.0",
    "items":[{"id":"B-contract","category":"contract_surface","finding":"The feature touches config/control_config.v1.json, a versioned config contract.","source_refs":["CLAUDE.md","config/control_config.v1.json"],"ledger_entry_id":"L-threshold"}]
  } |
  .sections."19_clarity_interview" = {
    "contract_version":"1.0.0",
    "status":"blocked",
    "questions":[{
      "id":"Q-threshold-v1",
      "ledger_entry_id":"L-threshold",
      "question":"Should the v1 control config threshold be raised for this feature slice?",
      "architecture_impact":"high",
      "why_it_matters":"The threshold claim changes the versioned control_config.v1.json contract consumed by src/loader.py.",
      "what_changes":"The answer decides whether config/control_config.v1.json receives an additive threshold change and which compatibility evidence is required.",
      "conservative_default":"Keep the v1 threshold unchanged unless the human explicitly approves the additive threshold change."
    }]
  } |
  .sections."8_task_tickets"[0].task_id = "CLARITY_FEATURE_CONFIG" |
  .sections."8_task_tickets"[0].files_to_modify = ["config/control_config.v1.json","src/loader.py"] |
  .sections."8_task_tickets"[0].compatibility_contract = {
    "backward":"Additive v1 threshold change remains parseable by existing loader consumers.",
    "forward":"Unknown v1 fields remain ignored by current consumers.",
    "migration_or_rollout":"No migration required for additive v1 threshold change.",
    "surfaces":[$surface],
    "verification_predicates":[{"surface":$surface,"predicate":"tests/run.sh passes after config/control_config.v1.json threshold update","evidence_ref":"tests/compat/control-config-v1.txt"}]
  } |
  .sections."8_task_tickets"[0].compatibility_evidence_refs = ["tests/compat/control-config-v1.txt"]
' "$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json" > "$OUT_DIR/build-brief.json"

cat > "$OUT_DIR/answers.json" <<'JSON'
{"answers":[{"ledger_entry_id":"L-threshold","answer":"Raise the threshold to 2 for this feature slice.","answered_by":"human","answered_at":"2026-07-05T00:00:00Z"}]}
JSON

"$ROOT/bin/adlc" clarity-gate --build-brief "$OUT_DIR/build-brief.json" --answers "$OUT_DIR/answers.json" --output "$OUT_DIR/clarity-report.json" --json > "$OUT_DIR/clarity.stdout.json"
"$ROOT/bin/adlc" compatibility-evidence --build-brief "$OUT_DIR/build-brief.json" --inventory "$OUT_DIR/inventory.json" --output "$OUT_DIR/compatibility-report.json" --json > "$OUT_DIR/compatibility.stdout.json"
cat > "$OUT_DIR/deviation-report.json" <<'JSON'
{"contract_version":"1.0.0","status":"pass","brief_generator_defect_count":0,"issues":[]}
JSON

adapter_command='python3 - <<'"'"'PY'"'"'
import json
from pathlib import Path
path = Path("config/control_config.v1.json")
payload = json.loads(path.read_text())
payload["threshold"] = 2
path.write_text(json.dumps(payload, sort_keys=True) + "\n")
PY
./tests/run.sh
printf "feature slice completed\n" > harness-proof.txt'

"$ROOT/bin/adlc" execution-adapter --provider claude --model fixture --workdir "$claude_repo" --command "$adapter_command" --output "$OUT_DIR/claude-execution-report.json" --json > "$OUT_DIR/claude-execution.stdout.json"
"$ROOT/bin/adlc" execution-adapter --provider codex --model fixture --workdir "$codex_repo" --command "$adapter_command" --output "$OUT_DIR/codex-execution-report.json" --json > "$OUT_DIR/codex-execution.stdout.json"

"$ROOT/bin/adlc" run-report --provider claude --model fixture --runtime execution-adapter --run-id HARDENING-CLAUDE \
  --clarity-report "$OUT_DIR/clarity-report.json" \
  --deviation-report "$OUT_DIR/deviation-report.json" \
  --compatibility-report "$OUT_DIR/compatibility-report.json" \
  --execution-adapter-report "$OUT_DIR/claude-execution-report.json" \
  --output "$OUT_DIR/claude-run-report.json" --json > "$OUT_DIR/claude-run.stdout.json"

"$ROOT/bin/adlc" run-report --provider codex --model fixture --runtime execution-adapter --run-id HARDENING-CODEX \
  --clarity-report "$OUT_DIR/clarity-report.json" \
  --deviation-report "$OUT_DIR/deviation-report.json" \
  --compatibility-report "$OUT_DIR/compatibility-report.json" \
  --execution-adapter-report "$OUT_DIR/codex-execution-report.json" \
  --output "$OUT_DIR/codex-run-report.json" --json > "$OUT_DIR/codex-run.stdout.json"

python3 - "$OUT_DIR" <<'PY'
import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
reports = {
    "claude": json.loads((out / "claude-run-report.json").read_text()),
    "codex": json.loads((out / "codex-run-report.json").read_text()),
}
gate_names = sorted({gate["name"] for report in reports.values() for gate in report["gate_results"]})
comparison = {
    "contract_version": "1.0.0",
    "fixture": "clarity_hardening_feature_slice",
    "build_brief": str(out / "build-brief.json"),
    "status": "pass",
    "providers": {},
    "gate_comparison": [],
    "findings": [],
}
for provider, report in reports.items():
    comparison["providers"][provider] = {
        "status": report["status"],
        "brief_generator_defect_count": report["brief_generator_defect_count"],
        "run_report": str(out / f"{provider}-run-report.json"),
    }
for gate_name in gate_names:
    row = {"gate": gate_name}
    for provider, report in reports.items():
        statuses = [gate["status"] for gate in report["gate_results"] if gate["name"] == gate_name]
        row[provider] = statuses[0] if statuses else "missing"
    if len({row[provider] for provider in reports}) > 1:
        comparison["status"] = "finding"
        comparison["findings"].append({"gate": gate_name, "message": "Gate outcome differs between harnesses."})
    comparison["gate_comparison"].append(row)
(out / "dual-harness-comparison.json").write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n")
PY

printf '%s\n' "$OUT_DIR/dual-harness-comparison.json"
