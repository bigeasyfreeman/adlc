# ADLC Build Brief Agent (Legacy — Archived)

> **This monolithic agent has been decomposed into the DAG pipeline.**
> The full original spec is preserved at `docs/archive/ADLC-BUILD-BRIEF-AGENT.md`.

## New Architecture

The Build Brief Agent's 12 phases are now individual nodes in `WORKFLOW.dot`:

| Old Phase | New Node | Agent Config |
|-----------|----------|-------------|
| Phase 0: Inputs + Research | `research` | `agents/researcher.md` |
| Phases 1-8: Brief Generation | `plan` | `agents/planner.md` |
| Eval Council | `plan_review` | `agents/plan-reviewer.md` |
| Phase 9: Codegen | `code` (fan-out) | `agents/coder.md` |
| Phase 10: Verification | `code_review` + `qa` | `agents/code-reviewer.md` |
| Phase 11: Security | `security` | `agents/security-reviewer.md` |
| Phase 12: Deploy | `pr_prep` → `engineer_review` | `agents/pr-preparer.md` |

See `WORKFLOW.dot` for the complete pipeline graph.
See `WORKFLOW.md` for agent configuration and skill injection.
