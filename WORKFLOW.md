---
# ADLC Workflow Configuration
# This file defines agents, backends, routing, and retry caps for the bounded directed workflow.

workflow: WORKFLOW.dot

backends:
  claude:
    command: "tests/smoke/adapters/claude.sh invoke_agent --agent {{ agent_path | shellquote }} --input {{ input_path | shellquote }} --output {{ output_path | shellquote }} --tools {{ tools_csv | shellquote }} {{ schema_arg }}"
    env:
      ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY}"
      ADLC_SMOKE_SETTINGS: "${ADLC_SMOKE_SETTINGS}"
  codex:
    command: "tests/smoke/adapters/codex.sh invoke_agent --agent {{ agent_path | shellquote }} --input {{ input_path | shellquote }} --output {{ output_path | shellquote }} --tools {{ tools_csv | shellquote }} {{ schema_arg }}"
    env:
      OPENAI_API_KEY: "${OPENAI_API_KEY}"
      ADLC_SMOKE_SETTINGS_CODEX: "${ADLC_SMOKE_SETTINGS_CODEX}"
  cursor:
    command: "tests/smoke/adapters/cursor.sh invoke_agent --agent {{ agent_path | shellquote }} --input {{ input_path | shellquote }} --output {{ output_path | shellquote }} --tools {{ tools_csv | shellquote }} {{ schema_arg }}"
    env:
      CURSOR_API_KEY: "${CURSOR_API_KEY}"
  antigravity:
    command: "tests/smoke/adapters/antigravity.sh invoke_agent --agent {{ agent_path | shellquote }} --input {{ input_path | shellquote }} --output {{ output_path | shellquote }} --tools {{ tools_csv | shellquote }} {{ schema_arg }}"
    env:
      ADLC_RUNTIME_SESSION: "${ADLC_RUNTIME_SESSION}"
  factory:
    command: "tests/smoke/adapters/factory.sh invoke_agent --agent {{ agent_path | shellquote }} --input {{ input_path | shellquote }} --output {{ output_path | shellquote }} --tools {{ tools_csv | shellquote }} {{ schema_arg }}"
    env:
      FACTORY_API_KEY: "${FACTORY_API_KEY}"
    # Factory-specific notes:
    #   Fan-out: Factory's Task tool enables parallel subagent dispatch.
    #     Independent coding tasks dispatch via Task("adlc-coder", "<context>")
    #     and converge at code review. Maps directly to ADLC's fan-out model.
    #   Model mapping:
    #     - Fast agents (triage, coder, fixer, pr-preparer): model: inherit
    #       Inherits the session model (typically Sonnet-tier).
    #     - Deep agents (researcher, planner, plan-reviewer, security-reviewer,
    #       code-reviewer): model: claude-opus-4-6 for deep reasoning.
    #   Skills: Installed to .factory/docs/skills/ and auto-injected into droid context.
    #   Droids: YAML configs in .factory/droids/ define agent capabilities and tool access.
    #   MCP: External integrations (Jira, Slack, Grafana) use MCP servers configured
    #     at the workspace level, not per-droid.

default_backend: claude

concurrency:
  max_concurrent_agents: 8
  max_fan_out: 6

iteration_limits:
  plan_review: 3          # Eval Council max loops
  intent_validation: 3    # Human narrative gate max revisions before escalate
  code_review: 3          # Code review max loops
  fixer: 2                # Fix attempts before escalate
  test_strength_retry: 2  # Weak-test strengthening attempts before escalate
  qa_retry: 2             # CI retry before escalate

labels:
  - lgtm                  # Approved, proceed to next node
  - revise                # Send back for revision
  - escalate              # Human intervention needed
  - low_confidence        # Triage confidence requires extra research before planning
  - blocked               # Cannot proceed, critical issue
  - pass                  # Deterministic gate passed
  - fail                  # Deterministic gate failed
  - weak                  # Test-strength audit failed thresholds
  - proceed               # Triage approved or deterministic preflight complete
  - unclear               # Triage cannot classify
  - fixed                 # Fixer resolved the issue
  - stuck                 # Fixer cannot resolve
  - approve               # Engineer approved
  - skipped               # Conditional deterministic node had no work
---

# ADLC Pipeline Configuration

## Agents

Each agent is a thin config: model + prompt template + injected skills.
Agent prompts live in `agents/{name}.md`. Skills are synced into the workspace before execution.
Set `ADLC_RUNTIME` to select a backend at orchestration time. The `Backend` column in the table below records the Claude default used when `ADLC_RUNTIME` is unset.
Judge skills resolve their `fast_judge` and `deep_judge` slots through `skills/manifest.json` and the adapter-backed backend binding, not by hardcoded runtime names inside the skill docs.

### Node → Agent Mapping

| DAG Node | Agent | Backend | Model | Skills Injected |
|----------|-------|---------|-------|-----------------|
| `triage` | `agents/triage.md` | claude | claude-sonnet-4-6 | — |
| `compound_preflight` | *tool node* | — | — | compound context preflight |
| `research` | `agents/researcher.md` | claude | claude-opus-4-6 | graph-research, codebase-research, paved-road-registry, dark-code-audit, grafana-observability |
| `plan` | `agents/planner.md` | claude | claude-opus-4-6 | graph-research, codegen-context, architecture-pattern, reuse-analysis, paved-road-registry, context-layers |
| `plan_review` | `agents/plan-reviewer.md` | claude | claude-opus-4-6 | eval-council |
| `intent_validation` | *human gate* | — | — | — |
| `scaffold` | *tool node* | — | — | architecture-pattern |
| `gen_tests` | `agents/test-author.md` | claude | claude-sonnet-4-6 | spec-to-tests, tdd-enforcement, qa-test-data |
| `context_assembly` | *tool node* | — | — | codegen-context |
| `code` | `agents/coder.md` | claude | claude-sonnet-4-6 | tdd-enforcement, systematic-debugging |
| `code_review` | `agents/code-reviewer.md` | claude | claude-opus-4-6 | eval-council, graph-research, paved-road-registry, comprehension-gate |
| `security` | `agents/security-reviewer.md` | claude | claude-opus-4-6 | appsec-threat-model, llm-security, agentic-security, api-security, infra-security |
| `qa` | *tool node* | — | — | — |
| `test_strength` | `agents/test-strength-auditor.md` | claude | claude-sonnet-4-6 | test-strength |
| `slop_gate` | *tool node* | — | — | stop-slop |
| `fixer` | `agents/fixer.md` | claude | claude-sonnet-4-6 | systematic-debugging |
| `pr_prep` | `agents/pr-preparer.md` | claude | claude-sonnet-4-6 | learning-capture |
| `learning_capture` | *tool node* | — | — | learning-capture |
| `engineer_review` | *human gate* | — | — | — |

`security`, `test_strength`, and `slop_gate` are conditional overlays. A runner
enters them only when the applicability manifest or task-level surface evidence
activates the corresponding surface. Inactive overlays are skipped rather than
converted into boilerplate work.

### Intent Validation (Human Gate)

After `plan_review` approves the Build Brief and BEFORE `scaffold` or any codegen
work begins, the human (founder or designated approver) validates intent and
impact. This gate is the literal implementation of "state intent and impact" and
"don't let AI make decisions" — the human decides; ADLC executes.

Human inputs (one short paragraph or four short answers):

- **Intent:** "This Build Brief exists to <X>"
- **Impact:** "When shipped, the user can <Y>"
- **Routing:** confirm product slice / Initiative
- **Kill / keep / split decision**

Human outputs:

- `approved` → proceed to `scaffold`. The approved Intent and Impact populate `narrative_contract.feature` and `narrative_contract.value` in the Build Brief. The `why` and `goal` fields are derived from PRD plus the human's impact statement by the planner.
- `revise` (with feedback) → back to `plan` (max 3 revisions per `intent_validation` iteration limit)
- `rejected` → escalate

Cost: ~5 minutes per Build Brief. Prevents 20+ hours of wasted codegen on misdirected briefs.

Backward compatibility: existing workflows that do not include `intent_validation` continue to run (treated as auto-approved with a deprecation warning). New emissions at `contract_version >= 1.1.x` require `narrative_contract.human_validated_at`; emitters must refuse mutation and return `missing_intent_validation` if the field is absent.

### Tool Nodes (Deterministic — No LLM)

Tool nodes run shell commands. They are cheap, fast, and reliable. Overlay nodes
run only when the Build Brief `applicability_manifest` or task surface marks the
surface active; otherwise the runner follows the skip/no-op edge shown in
`WORKFLOW.dot`.

```yaml
compound_preflight:
  command: |
    bin/adlc run-phase compound_preflight --workspace "${WORKSPACE:-.}" ${BUILD_BRIEF:+--build-brief "$BUILD_BRIEF"} --json
    # Emits schema-backed compact learning_refs, verifier_refs, task_refs, and explicit no-op reasons.

scaffold:
  command: |
    bin/adlc run-phase scaffold --workspace "${WORKSPACE:-.}" --build-brief "${BUILD_BRIEF:?}" --dry-run --json
    # Write mode requires --allow-mutation, --tool-registry, and action admission.

context_assembly:
  command: |
    bin/adlc run-phase context_assembly --workspace "${WORKSPACE:-.}" --build-brief "${BUILD_BRIEF:?}" --json
    # Emits per-task context packages with queue, worktree, tracker, verifier, and contract refs.

qa:
  command: |
    bin/adlc run-phase qa --workspace "${WORKSPACE:-.}" --json
    # Verifier commands come from --verifier, Build Brief verification_spec, or TEST_COMMAND/LINT_COMMAND/BUILD_COMMAND.

slop_gate:
  command: |
    bin/adlc run-phase slop_gate --workspace "${WORKSPACE:-.}" --build-brief "${BUILD_BRIEF:?}" --json

learning_capture:
  command: |
    bin/adlc run-phase learning_capture --workspace "${WORKSPACE:-.}" ${PR_PREP_OUTPUT:+--input "$PR_PREP_OUTPUT"} --json
    # Write mode requires verified reusable learning candidates, redaction evidence, action admission, and validation.
```

### Fan-Out Configuration

The `code` node fans out across tasks. Each task gets:
- Its own assembled context (from `context_assembly`)
- Its own workspace branch
- TDD enforcement: RED → GREEN → REFACTOR per G/W/T criterion

```yaml
code:
  fan_out_by: tasks              # Split by task tickets
  max_parallel: 6                # Concurrent coding agents
  fan_in: code_review            # Converge at code review
  success_criteria: all          # All tasks must succeed (vs "any")
```

## Workspace Isolation

Each pipeline run gets:
- Fresh repo clone or worktree
- Skills synced to `.claude/skills/` (digest-based, idempotent)
- `.adlc/` directory for pipeline state, artifacts, thread history
- Clean git state before each attempt

## Skill Injection

### Claude Code Native (Recommended)

Agent configs use Claude Code's native `skills:` frontmatter field. Skills listed in the frontmatter are injected into the agent's context at startup — no auto-discovery, no searching. The knowledge is there from the first turn.

```yaml
# agents/researcher.md
---
name: researcher
model: opus
skills:
  - codebase-research       # Injected at startup
  - grafana-observability    # Injected at startup
---
```

**Two patterns for skills + subagents:**

1. **Subagent preloads Skills** (what ADLC agents do) — The `skills:` field in agent frontmatter injects skill content directly. The agent is the actor; skills are its reference material.

2. **Skill delegates to Subagent** (`context: fork`) — For heavy skills that should run in isolation. Add `context: fork` and `agent: Explore` to a skill's frontmatter to spawn a subagent that runs the skill and returns only a summary.

### Manual Injection (Any Backend)

Skills are synced from `skills/` into the workspace before agent execution:

```
skills/{name}/SKILL.md  →  ${WORKSPACE}/.claude/skills/{name}/SKILL.md
                        →  ${WORKSPACE}/.codex/skills/{name}/SKILL.md
```

Sync is digest-based (SHA256). Only changed skills are copied.
Skills are excluded from git via `.git/info/exclude`.
