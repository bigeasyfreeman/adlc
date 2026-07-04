#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP_PARENT="${ADLC_ACCEPTANCE_TMPDIR:-${TMPDIR:-/tmp}}"
TMP_ROOT="$(mktemp -d "$TMP_PARENT/adlc-os12-acceptance.XXXXXX")"
TARGET="$TMP_ROOT/target"
REPORT_OUT="${ADLC_OS12_ACCEPTANCE_REPORT:-}"

cleanup() {
  local status=$?
  if [ "$status" -eq 0 ] && [ "${ADLC_ACCEPTANCE_KEEP_TMP:-0}" != "1" ]; then
    rm -rf "$TMP_ROOT"
  else
    printf 'OS-12 acceptance temp retained: %s\n' "$TMP_ROOT" >&2
  fi
}
trap cleanup EXIT

step() {
  printf '  %s\n' "$1"
}

require() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$name" >&2
    exit 2
  fi
}

require git
require jq
require python3

echo "ADLC OS-12 Acceptance"
echo "Root:   $ROOT"
echo "Target: $TARGET"
echo ""

step "Create a purpose-built target repo with interralis-style conventions"
mkdir -p "$TARGET/src" "$TARGET/tests" "$TARGET/.adlc"
cat > "$TARGET/.gitignore" <<'EOF'
.adlc/
__pycache__/
*.pyc
EOF
cat > "$TARGET/CLAUDE.md" <<'EOF'
# OS-12 Fixture Repo

## Code conventions

- **One responsibility per file**, stated in the first line of the module doc-comment.
- **The coordinator file is a thin coordinator, never a worker.**
- **Pure core, impure shell.** Side effects live only in an impure shell.
- **Catch-all modules are forbidden.** Split miscellaneous helpers by responsibility.
EOF
cat > "$TARGET/README.md" <<'EOF'
# OS-12 Fixture Repo

Tiny target used by ADLC's OS-12 acceptance harness.
EOF
git -C "$TARGET" init -q
git -C "$TARGET" config user.email adlc@example.invalid
git -C "$TARGET" config user.name ADLC
git -C "$TARGET" add .
git -C "$TARGET" commit -qm init

step "Use the repo ADLC runtime for the provider-free Build Brief loop"
ADLC="$ROOT/bin/adlc"
"$ADLC" health-check --json | jq -e '.status == "pass"' >/dev/null

step "Extract target repo conventions for the Build Brief"
"$ADLC" repo-conventions \
  --workspace "$TARGET" \
  --output "$TARGET/.adlc/repo_conventions.json" \
  --json > "$TMP_ROOT/repo_conventions.json"
jq -e '
  .status == "extracted" and
  (.sources | length) == 1 and
  any(.rules[]; .rule | test("One responsibility per file")) and
  any(.rules[]; .rule | test("Pure core"))
' "$TMP_ROOT/repo_conventions.json" >/dev/null

step "Create a schema-valid Build Brief with module_plan, honesty, performance, and sizing"
BRIEF="$TARGET/.adlc/os12_build_brief.json"
python3 - "$ROOT/tests/smoke/fixtures/feature_bugfix/.adlc/build_brief.json" "$TMP_ROOT/repo_conventions.json" "$BRIEF" <<'PY'
import json
import sys
from copy import deepcopy
from pathlib import Path

base_path, conventions_path, out_path = map(Path, sys.argv[1:])
brief = json.loads(base_path.read_text())
repo_conventions = json.loads(conventions_path.read_text())

brief["brief_id"] = "OS12-END-TO-END-ACCEPTANCE"
brief["prd_id"] = "OS12"
brief["repo_conventions"] = repo_conventions
brief["product_vocabulary"] = {
    "status": "defined",
    "mappings": [
        {
            "internal": "HMETA_INTERNAL",
            "product": "user-facing acceptance artifact",
            "applies_to": ["PR title", "PR body", "target diff"],
        }
    ],
    "banned_tokens": ["HMETA_INTERNAL"],
}
brief["enterprise_readiness_contract"] = {
    "production_grade_target": "Prove a one-shot target change can be scoped by Build Brief contracts without human structural fix prompts.",
    "backward_compatibility": "The fixture repo keeps its initial docs and installed ADLC wrapper intact.",
    "forward_compatibility": "The generated score module is decomposed into stable pure and impure-shell files.",
    "failure_mode_coverage": [
        "Architecture test fails before the module files exist.",
        "Convention scan catches flat multi-domain files.",
        "PR hygiene catches process artifacts and banned internal tokens.",
        "Task sizing catches split-required oversized work.",
    ],
    "definition_of_done": [
        "Build Brief validates and emits ready work items.",
        "Context assembly includes repo conventions, module_plan, honesty, performance, task_sizing, and minimality.",
        "One-shot generated code passes architecture, convention, QA, and PR hygiene gates.",
    ],
    "validation_tasks": ["OS12_VALIDATE_ACCEPTANCE"],
    "compliance_posture": "Provider-free fixture; no external data or secrets.",
}

implementation_task = {
    "artifact_type": "implementation_task",
    "task_id": "OS12_SCORE_MODULE",
    "title": "Add right-sized score summary module",
    "objective": "Create a score summary module whose structure is fully prescribed before codegen.",
    "task_classification": "feature",
    "decision_contract": {
        "type1_decision": False,
        "status": "not_applicable",
        "owner": "os12-acceptance",
        "deadline": "not_applicable",
        "blocks_implementation": False,
        "resolution": "No Type 1 decision is required for the fixture module.",
    },
    "scope": [
        "Create the src/scores directory module exactly as described by module_plan.",
        "Write the architecture test before production files.",
        "Keep filesystem side effects isolated to the impure shell file.",
    ],
    "out_of_scope": [
        "External providers, network access, databases, or generated process artifacts in the target diff.",
        "Any manual structural prescription after context assembly.",
    ],
    "dependencies": [],
    "acceptance_criteria": [
        {
            "id": "AC-OS12_STRUCTURE",
            "given": "the Build Brief module_plan lists the score module files",
            "when": "one-shot codegen writes the target diff",
            "then": "every planned file exists with one responsibility and pure/impure placement intact",
            "measurable_post_condition": "python3 -m unittest tests.test_scores_architecture -v passes",
        },
        {
            "id": "AC-OS12_GATES",
            "given": "the target diff contains only score module code and tests",
            "when": "convention, QA, and PR hygiene gates run",
            "then": "all gates pass without waivers",
            "measurable_post_condition": "convention-scan, run-phase qa, and pr-hygiene-scan return pass",
        },
    ],
    "anti_slop_rules": [
        "No support/helpers/util/common files.",
        "No file-size or line-count criteria.",
        "No checked-in Build Briefs, eval reports, or closeout artifacts in the target diff.",
    ],
    "tech_debt_boundaries": {
        "prerequisite_debt": "none",
        "deferred_debt": "none",
        "deferral_safety": "The fixture module is isolated and fully covered by architecture tests.",
    },
    "compatibility_contract": {
        "backward": "Do not modify the target repo's existing README or installed ADLC wrapper.",
        "forward": "Keep score collection, projection, and type responsibilities split for future extension.",
        "migration_or_rollout": "No rollout is required for the provider-free fixture.",
    },
    "implementation_notes": [
        "Write tests/test_scores_architecture.py before production files.",
        "Use only files listed in module_plan.",
        "Keep std::fs usage in src/scores/impure_shell.rs.",
    ],
    "verification_spec": {
        "primary_verifier": {
            "type": "command",
            "target": "python3 -m unittest discover -s tests -v",
            "expected_pre_change": "fail",
            "expected_post_change": "pass",
            "rationale": "The fixture is accepted only when structure, purity placement, and contract tests pass.",
            "target_files": [
                "src/scores/mod.rs",
                "src/scores/types.rs",
                "src/scores/project.rs",
                "src/scores/impure_shell.rs",
                "tests/test_scores_architecture.py",
                "tests/test_scores_contract.py",
            ],
            "expected_failure_mode": "planned score module files are missing before codegen",
        },
        "secondary_verifiers": [],
        "must_fail_before_change": True,
        "must_be_deterministic": True,
        "scope_note": "The verifier covers only the OS-12 fixture module and tests.",
    },
    "evidence_responsibilities": [
        "Capture the pre-change architecture failure.",
        "Capture context assembly containing module_plan, honesty, performance, task_sizing, and minimality.",
        "Capture passing convention, QA, and PR hygiene outputs.",
        "Capture negative controls for flat file, process artifact, banned token, and split-required task.",
    ],
    "definition_of_done": [
        "All module_plan files exist.",
        "Pure files contain no filesystem/process/env/db/network side effects.",
        "The impure shell file owns filesystem reads.",
        "python3 -m unittest discover -s tests -v passes.",
        "No human-authored structural fix prompt is needed.",
    ],
    "failure_modes": [
        "HIGH: A broad module file would bypass one-shot structure; mitigation: architecture test plus convention-scan negative control.",
        "HIGH: Process artifacts could leak into the target diff; mitigation: pr-hygiene-scan negative control.",
    ],
    "contracts": [
        "src/scores/mod.rs remains a thin coordinator.",
        "src/scores/project.rs remains pure projection logic.",
        "src/scores/impure_shell.rs contains filesystem effects.",
    ],
    "observability": [
        "The OS-12 artifact trail records every gate output path.",
    ],
    "tests": [
        "tests/test_scores_architecture.py",
        "tests/test_scores_contract.py",
    ],
    "security_impact": [],
    "bpe_classification": "type_2",
    "owner": "os12-acceptance",
    "files_to_modify": [],
    "files_to_create": [
        "src/scores/mod.rs",
        "src/scores/types.rs",
        "src/scores/project.rs",
        "src/scores/impure_shell.rs",
        "tests/test_scores_architecture.py",
        "tests/test_scores_contract.py",
    ],
    "reference_impl": "pattern:module_plan:src/scores",
    "module_plan": {
        "applicability": "required",
        "reason": "The task creates a new score directory module and must prescribe structure before codegen.",
        "files": [
            {"path": "src/scores/mod.rs", "responsibility": "Score module coordinator", "purity": "pure", "capabilities": ["none"]},
            {"path": "src/scores/types.rs", "responsibility": "Score event types", "purity": "pure", "capabilities": ["none"]},
            {"path": "src/scores/project.rs", "responsibility": "Score summary projection", "purity": "pure", "capabilities": ["compute"]},
            {"path": "src/scores/impure_shell.rs", "responsibility": "Score event loading shell", "purity": "impure", "capabilities": ["fs", "parse"]},
            {"path": "tests/test_scores_architecture.py", "responsibility": "Score architecture contract", "purity": "impure", "capabilities": ["test", "fs"]},
            {"path": "tests/test_scores_contract.py", "responsibility": "Score behavior contract", "purity": "impure", "capabilities": ["test", "fs"]},
        ],
        "architecture_test": {
            "test_path": "tests/test_scores_architecture.py",
            "command": "python3 -m unittest tests.test_scores_architecture -v",
            "assertions": [
                "Every planned source file exists.",
                "Coordinator file has no function bodies.",
                "Pure files contain no filesystem/process/env/db/network side effects.",
                "No module-doc first line uses 'and'.",
            ],
            "write_first": True,
        },
    },
    "task_sizing": {
        "applicability": "required",
        "reason": "The score module is one coherent module_plan file-set.",
        "basis": ["module_plan", "coherent_file_set"],
        "change_surface": {
            "surface_kind": "coherent_file_set",
            "primary_module": "src/scores",
            "touched_modules": ["src/scores"],
            "touched_files": [
                "src/scores/mod.rs",
                "src/scores/types.rs",
                "src/scores/project.rs",
                "src/scores/impure_shell.rs",
                "tests/test_scores_architecture.py",
                "tests/test_scores_contract.py",
            ],
            "coherence": "All files implement and verify one planned score summary module.",
        },
        "split_decision": {
            "required": False,
            "rationale": "The required module_plan describes one coherent directory module file-set.",
        },
    },
    "minimality_contract": {
        "rung": "minimum_code",
        "decision": "Build only the planned score module files without new dependency or extra abstraction.",
    },
    "work_item_metadata": {
        "area": "acceptance",
        "area_label": "acceptance",
        "phase_label": "coding",
        "target_project": "os12",
        "labels": ["os12", "acceptance"],
        "external_refs": ["OS-12"],
    },
    "honesty_contract": {
        "applicability": "not_applicable",
        "reason": "Pure internal fixture with no external claims.",
    },
    "performance_envelope": {
        "applicability": "required",
        "reason": "Score projection touches a data path over score events.",
        "expected_input_scale": [
            {"name": "score_events", "expected": "<=100", "worst_case": "<=1000", "unit": "events"}
        ],
        "hot_paths": [
            {
                "operation": "summarize_scores",
                "file": "src/scores/project.rs",
                "complexity": "O(n)",
                "rationale": "Each score event is visited once.",
            }
        ],
        "benchmark_required": False,
    },
}

validation_task = deepcopy(implementation_task)
validation_task.update({
    "artifact_type": "validation_task",
    "task_id": "OS12_VALIDATE_ACCEPTANCE",
    "title": "Validate OS-12 acceptance artifact trail",
    "objective": "Verify the OS-12 generated reports, gates, negative controls, and artifact trail.",
    "task_classification": "build_validation",
    "dependencies": ["OS12_SCORE_MODULE"],
    "scope": ["Run all OS-12 acceptance verifiers and gate checks."],
    "out_of_scope": ["Changing generated source files."],
    "implementation_notes": ["Validation-only task; inspect generated reports without target source edits."],
    "files_to_create": [],
    "files_to_modify": [],
    "reference_impl": "tests/acceptance/run_os12_acceptance.sh",
    "module_plan": {
        "applicability": "not_applicable",
        "reason": "Validation-only task with no module structure changes.",
    },
    "task_sizing": {
        "applicability": "not_applicable",
        "reason": "validation-only no implementation/change surface.",
    },
    "honesty_contract": {
        "applicability": "not_applicable",
        "reason": "Validation-only task with no external claims.",
    },
    "performance_envelope": {
        "applicability": "not_applicable",
        "reason": "Validation-only task with no data path.",
    },
    "minimality_contract": {
        "rung": "reuse_existing",
        "decision": "Run existing OS-12 validation gates without adding implementation scope.",
    },
})
validation_task["verification_spec"] = {
    "primary_verifier": {
        "type": "command",
        "target": "bash tests/acceptance/run_os12_acceptance.sh",
        "expected_pre_change": "fail",
        "expected_post_change": "pass",
        "rationale": "The OS-12 acceptance harness is the validation artifact.",
        "target_files": ["tests/acceptance/run_os12_acceptance.sh"],
        "expected_failure_mode": "acceptance gate reports the named failing control",
    },
    "secondary_verifiers": [],
    "must_fail_before_change": False,
    "must_be_deterministic": True,
    "scope_note": "Validation task records the artifact trail and negative controls.",
}

brief["sections"]["1_context"] = "OS-12 proves the upgraded ADLC loop against a purpose-built target repo carrying interralis-style conventions."
brief["sections"]["7_execution_plan"] = "Extract repo conventions; validate the Build Brief and module plan; emit right-sized work items; assemble context; write the architecture test first, then one-shot code; run gates and negative controls."
brief["sections"]["8_task_tickets"] = [implementation_task, validation_task]

Path(out_path).write_text(json.dumps(brief, indent=2) + "\n", encoding="utf-8")
PY

"$ADLC" validate-artifact --schema build-brief --input "$BRIEF" --json > "$TMP_ROOT/brief_validation.json"
jq -e '.valid == true' "$TMP_ROOT/brief_validation.json" >/dev/null
"$ADLC" repo-conventions-check --workspace "$TARGET" --build-brief "$BRIEF" --json > "$TMP_ROOT/repo_conventions_check.json"
jq -e '.status == "pass"' "$TMP_ROOT/repo_conventions_check.json" >/dev/null
"$ADLC" module-plan-check --build-brief "$BRIEF" --json > "$TMP_ROOT/module_plan_check.json"
jq -e '.status == "pass" and any(.tasks[]; .task_id == "OS12_SCORE_MODULE" and .module_plan_applicability == "required")' \
  "$TMP_ROOT/module_plan_check.json" >/dev/null
"$ADLC" ponytail-admit --build-brief "$BRIEF" --json > "$TMP_ROOT/ponytail_admission.json"
jq -e '.status == "pass" and all(.tasks[]; (.minimality_contract | keys | sort) == ["decision", "rung"])' \
  "$TMP_ROOT/ponytail_admission.json" >/dev/null

step "Emit right-sized work items and assemble codegen context"
"$ADLC" emit-work-items \
  --target github \
  --build-brief "$BRIEF" \
  --workspace "$TARGET" \
  --dry-run \
  --require-ready \
  --json > "$TMP_ROOT/work_items.json"
jq -e '
  .readiness_report.status == "ready" and
  any(.artifacts[]; .id == "OS12_SCORE_MODULE" and .module_plan.applicability == "required" and .task_sizing.change_surface.surface_kind == "coherent_file_set") and
  any(.artifacts[]; .id == "OS12_SCORE_MODULE" and .minimality_contract.rung == "minimum_code") and
  any(.artifacts[]; .id == "OS12_VALIDATE_ACCEPTANCE" and .task_sizing.applicability == "not_applicable")
' "$TMP_ROOT/work_items.json" >/dev/null
"$ADLC" run-phase context_assembly \
  --brief-id OS12 \
  --workspace "$TARGET" \
  --build-brief "$BRIEF" \
  --json > "$TMP_ROOT/context_assembly.json"
jq -e '
  .tool_result.status == "pass" and
  any(.tool_result.outputs.context_packages[];
    .task_id == "OS12_SCORE_MODULE" and
    .constraints.repo_conventions.status == "extracted" and
    .constraints.module_plan.applicability == "required" and
    .constraints.task_sizing.change_surface.surface_kind == "coherent_file_set" and
    .constraints.minimality_contract.rung == "minimum_code" and
    .constraints.performance_envelope.applicability == "required" and
    .constraints.honesty_contract.applicability == "not_applicable"
  )
' "$TMP_ROOT/context_assembly.json" >/dev/null

step "Write the architecture test first and capture its pre-code failure"
cat > "$TARGET/tests/test_scores_architecture.py" <<'PY'
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLANNED_SOURCE_FILES = [
    "src/scores/mod.rs",
    "src/scores/types.rs",
    "src/scores/project.rs",
    "src/scores/impure_shell.rs",
]
PURE_FILES = [
    "src/scores/mod.rs",
    "src/scores/types.rs",
    "src/scores/project.rs",
]
FORBIDDEN_SIDE_EFFECTS = ("std::fs", "std::process", "std::env", "reqwest", "rusqlite")


class ScoreArchitectureTests(unittest.TestCase):
    def test_planned_files_exist(self):
        for relative in PLANNED_SOURCE_FILES:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_module_doc_first_lines_are_single_responsibility(self):
        for relative in PLANNED_SOURCE_FILES:
            first = (ROOT / relative).read_text(encoding="utf-8").splitlines()[0]
            self.assertTrue(first.startswith("//! "), relative)
            self.assertIsNone(re.search(r"\band\b", first, flags=re.IGNORECASE), relative)

    def test_coordinator_has_no_worker_function_body(self):
        source = (ROOT / "src/scores/mod.rs").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"(?m)^\s*(pub\s+)?fn\s+\w+\s*\([^)]*\)\s*(?:->\s*[^{]+)?\{", source))

    def test_pure_files_have_no_side_effects(self):
        for relative in PURE_FILES:
            source = (ROOT / relative).read_text(encoding="utf-8")
            for token in FORBIDDEN_SIDE_EFFECTS:
                self.assertNotIn(token, source, relative)


if __name__ == "__main__":
    unittest.main()
PY
if python3 -m unittest tests.test_scores_architecture -v > "$TMP_ROOT/pre_code_architecture.txt" 2>&1; then
  printf 'Expected architecture test to fail before production files exist.\n' >&2
  exit 1
fi

step "Run one-shot codegen from the context package without manual structural prompts"
mkdir -p "$TARGET/src/scores"
cat > "$TARGET/src/scores/mod.rs" <<'RS'
//! Score module coordinator
pub mod types;
pub mod project;
pub mod impure_shell;
RS
cat > "$TARGET/src/scores/types.rs" <<'RS'
//! Score event types
#[derive(Clone, Debug, PartialEq)]
pub struct ScoreEvent {
    pub label: String,
    pub points: i64,
}
RS
cat > "$TARGET/src/scores/project.rs" <<'RS'
//! Score summary projection
use super::types::ScoreEvent;

#[derive(Clone, Debug, PartialEq)]
pub struct ScoreSummary {
    pub count: usize,
    pub total: i64,
}

pub fn summarize_scores(events: &[ScoreEvent]) -> ScoreSummary {
    let total = events.iter().map(|event| event.points).sum();
    ScoreSummary { count: events.len(), total }
}
RS
cat > "$TARGET/src/scores/impure_shell.rs" <<'RS'
//! Score event loading shell
use std::fs;

pub fn load_score_text(path: &str) -> std::io::Result<String> {
    fs::read_to_string(path)
}
RS
cat > "$TARGET/tests/test_scores_contract.py" <<'PY'
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ScoreContractTests(unittest.TestCase):
    def test_projection_is_linear_and_deterministic(self):
        source = (ROOT / "src/scores/project.rs").read_text(encoding="utf-8")
        self.assertIn("events.iter().map", source)
        self.assertIn("ScoreSummary { count: events.len(), total }", source)

    def test_impure_shell_owns_file_read(self):
        shell = (ROOT / "src/scores/impure_shell.rs").read_text(encoding="utf-8")
        pure = (ROOT / "src/scores/project.rs").read_text(encoding="utf-8")
        self.assertIn("fs::read_to_string", shell)
        self.assertNotIn("std::fs", pure)


if __name__ == "__main__":
    unittest.main()
PY
git -C "$TARGET" add -N src tests

step "Run good-path gates and prove target PR diff is code/tests only"
"$ADLC" convention-scan \
  --workspace "$TARGET" \
  --build-brief "$BRIEF" \
  --json > "$TMP_ROOT/convention_scan_pass.json"
jq -e '.status == "pass" and (.summary.checked_files >= 4)' "$TMP_ROOT/convention_scan_pass.json" >/dev/null
"$ADLC" run-phase qa \
  --brief-id OS12 \
  --workspace "$TARGET" \
  --verifier 'python3 -m unittest discover -s tests -v' \
  --json > "$TMP_ROOT/qa_pass.json"
jq -e '.tool_result.status == "pass" and .state.phase == "pr_prep"' "$TMP_ROOT/qa_pass.json" >/dev/null
git -C "$TARGET" diff --name-only HEAD > "$TMP_ROOT/diff_files.txt"
jq -R -s 'split("\n")[:-1] | all(.[]; startswith("src/") or startswith("tests/"))' "$TMP_ROOT/diff_files.txt" |
  jq -e '. == true' >/dev/null
git -C "$TARGET" diff --no-ext-diff HEAD > "$TMP_ROOT/target.diff"
"$ADLC" pr-hygiene-scan \
  --workspace "$TARGET" \
  --build-brief "$BRIEF" \
  --diff-file "$TMP_ROOT/target.diff" \
  --base-branch main \
  --default-branch main \
  --title "OS-12 fixture score module" \
  --body "Provider-free fixture PR with code and tests only." \
  --json > "$TMP_ROOT/pr_hygiene_pass.json"
jq -e '.status == "pass" and .summary.issues == 0' "$TMP_ROOT/pr_hygiene_pass.json" >/dev/null

step "Run negative controls for flat file, process artifact, banned token, and oversized task"
cat > "$TARGET/src/scores/support.rs" <<'RS'
//! Reads and projects score events
use std::fs;

pub fn helper(path: &str) -> std::io::Result<String> {
    fs::read_to_string(path)
}
RS
if "$ADLC" convention-scan \
  --workspace "$TARGET" \
  --build-brief "$BRIEF" \
  --file src/scores/support.rs \
  --json > "$TMP_ROOT/negative_flat_file.json"; then
  printf 'Expected flat multi-domain file to be blocked by convention-scan.\n' >&2
  exit 1
fi
jq -e '
  .status == "blocked" and
  any(.issues[]; .rule == "module_doc_multiple_jobs") and
  any(.issues[]; .rule == "side_effect_without_impure_shell")
' "$TMP_ROOT/negative_flat_file.json" >/dev/null
rm "$TARGET/src/scores/support.rs"

cat > "$TMP_ROOT/negative_process_artifact.diff" <<'EOF'
diff --git a/docs/build-briefs/os12.json b/docs/build-briefs/os12.json
new file mode 100644
--- /dev/null
+++ b/docs/build-briefs/os12.json
@@ -0,0 +1 @@
+{"brief_id":"OS12"}
EOF
if "$ADLC" pr-hygiene-scan \
  --workspace "$TARGET" \
  --build-brief "$BRIEF" \
  --diff-file "$TMP_ROOT/negative_process_artifact.diff" \
  --base-branch main \
  --default-branch main \
  --title "OS-12 fixture" \
  --body "Process artifact control." \
  --json > "$TMP_ROOT/negative_process_artifact.json"; then
  printf 'Expected process artifact diff to be blocked by pr-hygiene-scan.\n' >&2
  exit 1
fi
jq -e '.status == "blocked" and any(.issues[]; .rule == "pipeline_artifact_in_pr")' \
  "$TMP_ROOT/negative_process_artifact.json" >/dev/null

cat > "$TMP_ROOT/negative_banned_token.diff" <<'EOF'
diff --git a/src/scores/project.rs b/src/scores/project.rs
--- a/src/scores/project.rs
+++ b/src/scores/project.rs
@@ -1 +1,2 @@
 //! Score summary projection
+// HMETA_INTERNAL must not appear in target PRs.
EOF
if "$ADLC" pr-hygiene-scan \
  --workspace "$TARGET" \
  --build-brief "$BRIEF" \
  --diff-file "$TMP_ROOT/negative_banned_token.diff" \
  --base-branch main \
  --default-branch main \
  --title "OS-12 fixture" \
  --body "Banned token control." \
  --json > "$TMP_ROOT/negative_banned_token.json"; then
  printf 'Expected banned token diff to be blocked by pr-hygiene-scan.\n' >&2
  exit 1
fi
jq -e '.status == "blocked" and any(.issues[]; .rule == "banned_internal_token")' \
  "$TMP_ROOT/negative_banned_token.json" >/dev/null

python3 - "$BRIEF" "$TMP_ROOT/oversized_brief.json" <<'PY'
import json
import sys
from pathlib import Path

brief = json.loads(Path(sys.argv[1]).read_text())
task = brief["sections"]["8_task_tickets"][0]
task["task_sizing"]["reason"] = "Negative control: score, payment, and reporting modules are too broad for one ready task."
task["task_sizing"]["change_surface"] = {
    "surface_kind": "atomic_cross_module",
    "primary_module": "score-payment-reporting",
    "touched_modules": ["src/scores", "src/payments", "src/reporting"],
    "touched_files": ["src/scores/mod.rs", "src/payments/mod.rs", "src/reporting/mod.rs"],
    "coherence": "Negative control deliberately spans unrelated modules.",
}
task["task_sizing"]["split_decision"] = {
    "required": True,
    "rationale": "Score, payment, and reporting work are separate responsibilities.",
    "proposed_splits": [
        {
            "title": "Score module",
            "module_or_file_set": "src/scores",
            "reason": "Owns score summaries.",
            "files": ["src/scores/mod.rs"],
        },
        {
            "title": "Payment module",
            "module_or_file_set": "src/payments",
            "reason": "Owns payment behavior.",
            "files": ["src/payments/mod.rs"],
        },
        {
            "title": "Reporting module",
            "module_or_file_set": "src/reporting",
            "reason": "Owns reporting behavior.",
            "files": ["src/reporting/mod.rs"],
        },
    ],
}
task["task_sizing"]["atomic_work_reason"] = "Negative control intentionally marks a broad surface so readiness must still block."
Path(sys.argv[2]).write_text(json.dumps(brief, indent=2) + "\n", encoding="utf-8")
PY
"$ADLC" emit-work-items \
  --target github \
  --build-brief "$TMP_ROOT/oversized_brief.json" \
  --workspace "$TARGET" \
  --dry-run \
  --json > "$TMP_ROOT/negative_oversized_task.json"
jq -e '
  .readiness_report.status == "blocked" and
  any(.readiness_report.issues[]; .rule == "task_sizing_split_required" and (.message | contains("Score module")))
' "$TMP_ROOT/negative_oversized_task.json" >/dev/null
if "$ADLC" emit-work-items \
  --target github \
  --build-brief "$TMP_ROOT/oversized_brief.json" \
  --workspace "$TARGET" \
  --dry-run \
  --require-ready \
  --json >/dev/null 2>&1; then
  printf 'Expected --require-ready to reject the split-required oversized task.\n' >&2
  exit 1
fi

step "Write the OS-12 artifact trail"
jq -n \
  --arg brief "$BRIEF" \
  --arg work_items "$TMP_ROOT/work_items.json" \
  --arg context "$TMP_ROOT/context_assembly.json" \
  --arg target_diff "$TMP_ROOT/target.diff" \
  --arg repo_conventions "$TMP_ROOT/repo_conventions.json" \
  --arg module_plan "$TMP_ROOT/module_plan_check.json" \
  --arg convention_pass "$TMP_ROOT/convention_scan_pass.json" \
  --arg qa_pass "$TMP_ROOT/qa_pass.json" \
  --arg hygiene_pass "$TMP_ROOT/pr_hygiene_pass.json" \
  --arg flat "$TMP_ROOT/negative_flat_file.json" \
  --arg artifact "$TMP_ROOT/negative_process_artifact.json" \
  --arg banned "$TMP_ROOT/negative_banned_token.json" \
  --arg oversized "$TMP_ROOT/negative_oversized_task.json" \
  '{
    status: "pass",
    target_repo: "purpose-built fixture with interralis-style CLAUDE.md conventions",
    run_iterations: 1,
    manual_structural_fix_prompts: 0,
    resulting_pr_diff: {
      path: $target_diff,
      allowed_surfaces: ["src/", "tests/"],
      process_artifacts_in_diff: false
    },
    artifacts: {
      brief: $brief,
      work_items: $work_items,
      context_assembly: $context
    },
    gates: {
      repo_conventions: $repo_conventions,
      module_plan: $module_plan,
      convention_scan: $convention_pass,
      qa: $qa_pass,
      pr_hygiene: $hygiene_pass
    },
    negative_controls: {
      flat_multi_domain_file: {gate: "convention-scan", report: $flat},
      process_artifact: {gate: "pr-hygiene-scan", report: $artifact},
      banned_token: {gate: "pr-hygiene-scan", report: $banned},
      oversized_task: {gate: "emit-work-items readiness", report: $oversized}
    }
  }' > "$TMP_ROOT/artifact_trail.json"

if [ -n "$REPORT_OUT" ]; then
  mkdir -p "$(dirname "$REPORT_OUT")"
  cp "$TMP_ROOT/artifact_trail.json" "$REPORT_OUT"
  printf 'OS-12 artifact trail copied to: %s\n' "$REPORT_OUT"
else
  printf 'OS-12 artifact trail: %s\n' "$TMP_ROOT/artifact_trail.json"
fi

echo ""
echo "OS-12 acceptance passed."
