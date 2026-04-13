#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0
TOTAL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

assert() {
  local desc="$1"
  local condition="$2"
  TOTAL=$((TOTAL + 1))
  if eval "$condition"; then
    echo -e "  ${GREEN}PASS${NC} $desc"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}FAIL${NC} $desc"
    FAIL=$((FAIL + 1))
  fi
}

echo "ADLC Contract Checks"
echo "Root: $ROOT"
echo ""

echo "--- JSON ---"
assert "applicability-manifest schema parses" "jq empty '$ROOT/docs/schemas/applicability-manifest.schema.json' >/dev/null 2>&1"
assert "build-brief schema parses" "jq empty '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null 2>&1"
assert "skills manifest parses" "jq empty '$ROOT/skills/manifest.json' >/dev/null 2>&1"
assert "applicability issue set parses" "jq empty '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null 2>&1"

echo ""
echo "--- Build Brief Contract ---"
assert "build brief requires applicability_manifest" "jq -e '.required | index(\"applicability_manifest\")' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema requires task_classification" "jq -e '.definitions.task.required | index(\"task_classification\")' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema requires verification_spec" "jq -e '.definitions.task.required | index(\"verification_spec\")' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "task schema keeps failure_modes required" "jq -e '.definitions.task.required | index(\"failure_modes\")' '$ROOT/docs/schemas/build-brief.schema.json' >/dev/null"
assert "change surface includes service_boundary_change" "jq -e '.properties.change_surface.required | index(\"service_boundary_change\")' '$ROOT/docs/schemas/applicability-manifest.schema.json' >/dev/null"

echo ""
echo "--- Prompt Contracts ---"
assert "triage emits task classification" "rg -q 'task_classification' '$ROOT/agents/triage.md'"
assert "planner references applicability manifest" "rg -q 'applicability_manifest' '$ROOT/agents/planner.md'"
assert "coder uses verification_spec" "rg -q 'verification_spec' '$ROOT/agents/coder.md'"
assert "verification discipline is task-class-aware" "rg -q 'build_validation|lint_cleanup' '$ROOT/skills/tdd-enforcement/SKILL.md'"
assert "codegen context consumes verification_spec" "rg -q 'verification_spec' '$ROOT/skills/codegen-context/SKILL.md'"
assert "DoD uses core baseline and overlays" "rg -q 'core baseline|overlay' '$ROOT/skills/definition-of-done/SKILL.md'"
assert "eval council checks applicability manifest" "rg -q 'applicability_manifest' '$ROOT/skills/eval-council/SKILL.md'"
assert "fix loop uses primary verifier wording" "rg -q 'primary verifier' '$ROOT/skills/fix-loop/SKILL.md'"
assert "JIRA ticket creation preserves verification contract" "rg -q 'Verification Contract|task_classification|verification_spec' '$ROOT/skills/jira-ticket-creation/SKILL.md'"
assert "Confluence decomposition respects applicability manifest" "rg -q 'applicability_manifest|active Build Brief sections' '$ROOT/skills/confluence-decomposition/SKILL.md'"

echo ""
echo "--- Activation Metadata ---"
assert "security-review has activation metadata" "jq -e '.skills[] | select(.name==\"security-review\") | .activation.consumes_manifest == true' '$ROOT/skills/manifest.json' >/dev/null"
assert "observability-contract has activation metadata" "jq -e '.skills[] | select(.name==\"observability-contract\") | .activation.mode == \"overlay\"' '$ROOT/skills/manifest.json' >/dev/null"
assert "definition-of-done declares core checks" "jq -e '.skills[] | select(.name==\"definition-of-done\") | (.activation.core_checks | length) > 0' '$ROOT/skills/manifest.json' >/dev/null"
assert "build-feature consumes manifest" "jq -e '.skills[] | select(.name==\"build-feature\") | .activation.consumes_manifest == true' '$ROOT/skills/manifest.json' >/dev/null"

echo ""
echo "--- Truthfulness ---"
assert "setup script does not hardcode 22 skills" "! rg -q '22 skills' '$ROOT/setup.sh'"
assert "platform CLAUDE doc does not hardcode 22 skills" "! rg -q '22 skills' '$ROOT/platform/CLAUDE.md'"
assert "platform AGENTS doc does not hardcode 22 skills" "! rg -q '22 injectable skills|22 skills' '$ROOT/platform/AGENTS.md'"
assert "setup test does not expect 22 skills" "! rg -q \"'22'|22 skills\" '$ROOT/tests/test_setup.sh'"
assert "README avoids stale headline inventory claim" "! rg -q '^11 agents\\. 34 skills\\.' '$ROOT/README.md'"
assert "platform CLAUDE doc avoids RED/GREEN/REFACTOR" "! rg -q 'RED/GREEN/REFACTOR' '$ROOT/platform/CLAUDE.md'"
assert "agents antigravity doc avoids RED/GREEN/REFACTOR" "! rg -q 'RED/GREEN/REFACTOR' '$ROOT/platform/agents-antigravity.md'"
assert "workflow diagram uses verifier-led wording" "rg -q 'Verifier-led execution|Tests / Reproducers / Failing Commands' '$ROOT/WORKFLOW.dot'"

echo ""
echo "--- Issue Benchmark ---"
assert "issue set contains five benchmark cases" "jq -e '.cases | length == 5' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "issue set covers build_validation" "jq -e '.cases[] | select(.expected_manifest.task_classification==\"build_validation\")' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "issue set covers lint_cleanup" "jq -e '.cases[] | select(.expected_manifest.task_classification==\"lint_cleanup\")' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "issue set covers bugfix" "jq -e '.cases[] | select(.expected_manifest.task_classification==\"bugfix\")' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "issue set covers feature" "jq -e '.cases[] | select(.expected_manifest.task_classification==\"feature\")' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "issue set covers security-sensitive work" "jq -e '.cases[] | select(.expected_manifest.task_classification==\"security\")' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "build validation suppresses security and observability" "jq -e '.cases[] | select(.id==\"CASE-001\") | (.expected_manifest.section_policy | any(.section_name==\"5_security_review\" and .status==\"suppressed\")) and (.expected_manifest.section_policy | any(.section_name==\"6_observability_slo\" and .status==\"suppressed\"))' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "lint cleanup uses command verifier" "jq -e '.cases[] | select(.id==\"CASE-002\") | .expected_manifest.verification_spec.primary_verifier.type == \"command\"' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "bugfix case flags contamination" "jq -e '.cases[] | select(.id==\"CASE-003\") | (.expected_manifest.contamination.flags | index(\"unsupported_claim\")) != null' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"
assert "security feature activates security review" "jq -e '.cases[] | select(.id==\"CASE-005\") | (.expected_manifest.section_policy | any(.section_name==\"5_security_review\" and .status==\"active\"))' '$ROOT/tests/fixtures/applicability-issue-set.json' >/dev/null"

echo ""
echo "═══════════════════════════════════════"
echo -e "Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}, $TOTAL total"
echo "═══════════════════════════════════════"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
