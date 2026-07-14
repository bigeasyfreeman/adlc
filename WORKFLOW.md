# ADLC Workflow Reference

`WORKFLOW.dot` and `skills/manifest.json` are the machine-readable sources of
truth. Runtime adapters are selected by `ADLC_RUNTIME`; retry caps live as
`max_retries` edge metadata in the DOT graph and are enforced in persisted
workflow state. This file is explanatory and is not parsed as configuration.

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
    bin/adlc paved-road-patterns --json
    bin/adlc module-plan-check --build-brief "${BUILD_BRIEF:?}" --json
    bin/adlc run-phase context_assembly --workspace "${WORKSPACE:-.}" --build-brief "${BUILD_BRIEF:?}" --json
    # Emits per-task context packages with queue, worktree, tracker, verifier, effective module_plan, task_sizing, minimality_contract, registered pattern exemplars, repo_conventions, product_vocabulary, honesty_contract, performance_envelope, and contract refs.

qa:
  command: |
    bin/adlc run-phase qa --workspace "${WORKSPACE:-.}" --json
    # Verifier commands come from --verifier, Build Brief verification_spec, or TEST_COMMAND/LINT_COMMAND/BUILD_COMMAND.
    # Target-repo structural checks run with bin/adlc convention-scan when repo_conventions.status == extracted.

slop_gate:
  command: |
    bin/adlc run-phase slop_gate --workspace "${WORKSPACE:-.}" --build-brief "${BUILD_BRIEF:?}" --json

learning_capture:
  command: |
    bin/adlc run-phase learning_capture --workspace "${WORKSPACE:-.}" ${PR_PREP_OUTPUT:+--input "$PR_PREP_OUTPUT"} --json
    # Write mode requires verified reusable learning candidates, redaction evidence, action admission, and validation.
```

PR closeout also runs `bin/adlc pr-hygiene-scan` before publish. The scan blocks
goal prompts, Build Brief drafts, council scratch artifacts, absolute local
paths, banned internal vocabulary, removed target-repo gates, and undocumented
stacked PR bases.

Process artifacts are stored outside target-repo diffs. Writers compute the
canonical ADLC-side path with `bin/adlc process-artifact-path`, keyed by target
repo, task, run, and artifact type. Build Briefs, eval outputs, audits,
validation summaries, and closeout packages reference that path instead of
adding planning files to product commits.

### Fan-Out Configuration

The `code` node fans out across tasks. Each task gets:
- Its own assembled context (from `context_assembly`)
- Its own workspace branch
- TDD enforcement: RED → GREEN → REFACTOR per G/W/T criterion
- Target repo `repo_conventions` and `product_vocabulary` inlined into its context package

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
- `.adlc/` directory for transient pipeline state and thread history
- ADLC-side process artifact storage for briefs, eval outputs, audits, validation summaries, and closeout packages
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
                        →  ${WORKSPACE}/.agents/skills/{name}/SKILL.md
```

Sync is digest-based (SHA256). Only changed skills are copied. Each managed
skill destination writes `.adlc-skill-manifest`; later installs prune skills
recorded in that manifest if they disappear from the ADLC source tree, while
leaving unmanaged local skills alone.
Run `./setup.sh verify-claude ${WORKSPACE}` during Claude closeout to check
installed skill digests without mutating the target workspace.
Skills are excluded from git via `.git/info/exclude`.
