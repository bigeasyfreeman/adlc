# Loop Engineering Strategy Review For ADLC

Date: 2026-06-09

## Research Basis

- User-provided loop-engineering article, including the claims that modern coding-agent loops need automations, worktrees, skills, plugins/connectors, subagents, durable memory, verification, and hard stops for iteration, no-progress, and budget.
- OpenAI Codex manual fetched locally on 2026-06-09, especially Goal mode, Automations, Worktrees, Agent Skills, MCP, Hooks, Memories, Subagents, and Plugins.
- Claude Code docs reviewed on 2026-06-09:
  - `https://code.claude.com/docs/en/goal`
  - `https://code.claude.com/docs/en/scheduled-tasks`
  - `https://code.claude.com/docs/en/worktrees`
  - `https://code.claude.com/docs/en/features-overview`
  - `https://code.claude.com/docs/en/hooks-guide`
- EveryInc Compound Engineering plugin reviewed on 2026-06-09:
  - `https://github.com/EveryInc/compound-engineering-plugin`
  - `https://github.com/EveryInc/compound-engineering-plugin/blob/main/plugins/compound-engineering/README.md`
- ReAct lineage checked against `https://arxiv.org/abs/2210.03629`.
- Local ADLC evidence reviewed:
  - `README.md`
  - `docs/research/compound-engineering-plugin-adlc-review.md`
  - `docs/build-briefs/compound-engineering-adlc-implementation.json`
  - `docs/build-briefs/loop-system-maturity-audit.json`
  - `docs/specs/loop-system-maturity-audit.md`
  - `docs/specs/token-budgets.md`
  - `docs/specs/pre-turn-check.md`
  - `docs/specs/cost-reporting.md`
  - `docs/schemas/loop-contract.schema.json`
  - `docs/schemas/loop-action.schema.json`
  - `docs/schemas/loop-maturity-report.schema.json`
  - `tests/fixtures/loop_maturity/`

## External Findings

The article's core pattern is valid: loop engineering is not just a better prompt. It is a control system that repeatedly lets an agent decide a next action from current state, observes the result, validates progress, and either continues, repairs, escalates, or stops.

The product primitives are real across Codex and Claude Code, though the names and packaging differ:

- schedule or heartbeat: Codex Automations; Claude `/loop`, scheduled tasks, hooks, cloud routines, or GitHub Actions
- isolated parallelism: Git worktrees and worktree-backed agent execution
- reusable instructions: skills as the reusable unit, plugins as the distribution unit
- real tool access: MCP/connectors and plugin-bundled integrations
- maker/checker separation: subagents, reviewer agents, stop hooks, and goal evaluators
- durable memory: checked-in state, workflow artifacts, local memories, session history, Linear/GitHub records, or repo docs

The article's caution is also valid. A loop without hard feedback is just unattended churn. A production loop needs:

- a clear win condition
- deterministic verification
- a separate checker where the maker is likely to self-grade
- a maximum iteration count
- no-progress detection
- token or dollar budget limits
- durable state outside one conversation
- human review for claims the system cannot prove

## ADLC Mapping

| Loop-engineering block | Article requirement | Current ADLC evidence | Verdict |
|---|---|---|---|
| Automation heartbeat | Recurring discovery, triage, PR babysitting, or feedback collection | `README.md` defines a nightly feedback loop; ADLC can be run through Codex Automations or Claude scheduled tasks, but scheduling itself is not a core ADLC runtime primitive | Concept integrated; product scheduling remains host-level |
| Worktrees | Parallel agents must not collide in one checkout | Compound-engineering research and Build Briefs already call for task/worktree isolation and sequential merge validation | Integrated as strategy; keep validating per slice |
| Skills | Reusable project knowledge and workflows should be invoked instead of pasted prompts | ADLC is skill-first across setup targets; planner, codegen, eval, systematic-debugging, learning-capture, learning-refresh, test-strength, and graph-research are existing skill surfaces | Integrated |
| Plugins/connectors | Loops should touch real tools through MCP/connectors rather than only the filesystem | ADLC ships runtime adapter targets and `bin/adlc mcp-tools`; optional integration skills cover Linear, GitHub, Slack, Grafana, Figma, Jira, Notion, Confluence, and CI/CD | Integrated enough for ADLC core; do not import CE plugin wholesale |
| Subagents / maker-checker split | The writer should not be the only checker | Eval Council, code-reviewer, test-strength-auditor, slop-judge, verifier-semantic-judge, and loop-maturity-audit provide separate review/evaluation surfaces | Integrated |
| Durable memory | Loop state must live outside chat | Graphify graph, Build Briefs, workflow state, task fingerprints, docs/solutions learning store, learning refresh, and maturity reports are durable repo artifacts | Integrated |
| Verification feedback | Real output must feed the next decision | Loop Contract, Loop Action, loop-test-selection, loop-action-validate, loop-maturity-audit, loop-test-result, and workflow-state progress/control fields encode this | Integrated for deterministic evidence paths |
| Cost control | Loops need iteration caps, no-progress detection, and token/dollar ceilings | Iteration caps and no-progress are in Loop Contract; token budgets, pre-turn checks, and cost reporting exist in separate specs | Partially integrated; next slice should bind budget guards into Loop Contract/report evidence |
| Slop control | Loops should not train the process to accept low-quality output | Slop Quality Gate, Eval Council, no-overclaim policy, test-strength, learning capture with verifier evidence, and human engineer review address this | Integrated, with human review still required |

## Strategy Verdict

ADLC already has the loop-engineering concept integrated in theory and materially implemented in framework surfaces. The right strategy is to keep ADLC as a stricter lifecycle and evidence framework rather than importing the Compound Engineering plugin or adopting a large slash-command surface.

The strongest local framing is:

1. Compound engineering is the memory and compounding layer: prior verified learnings, graph status, task refs, and resume fingerprints make each future run cheaper.
2. Loop-System Maturity is the control layer: an LLM may propose actions, but ADLC deterministically admits, rejects, escalates, and scores those actions.
3. Build Briefs are still the decomposition contract: loop metadata is an overlay activated only when a task delegates decisions, tool use, test selection, retry, repair, escalation, or autonomy claims to an LLM loop.
4. Human review remains the final production boundary: ADLC should keep claiming `assisted_loop` by default and only allow `self_autonomous` per workflow when the evidence supports it.

## Gap Before The Next Slice

The next implementation slice should not add another planner, another review stack, or a wholesale CE dependency. The highest-value missing integration is budget binding:

- Add a Loop Contract budget guard that references `docs/schemas/token-budget.schema.json`, `docs/specs/pre-turn-check.md`, and `docs/specs/cost-reporting.md`.
- Add maturity-report evidence for token/cost budget status.
- Treat missing budget evidence as a blocker for `self_autonomous` on LLM-backed loops, while allowing `assisted_loop` status to remain valid.
- Preserve backward compatibility: existing deterministic docs/lint/build-validation work should not need loop-budget fields unless it claims autonomous loop behavior.

Secondary follow-up:

- Add a small ADLC automation/runbook skill only if repeated scheduled ADLC work becomes common. The first version should wrap existing ADLC commands and host-level schedulers; it should not create a parallel ADLC scheduler.

## No-Overclaim Boundary

This review validates that the concept and strategy are integrated. It does not prove that every ADLC workflow is self-autonomous.

Current truthful claim:

- ADLC is an LLM-driven development lifecycle with deterministic control gates and assisted-loop maturity by default.
- ADLC can evaluate loop maturity for specific workflows through checked-in Loop Contracts, action envelopes, required-test evidence, workflow state, and maturity reports.
- ADLC should not claim global self-autonomy until budget guards, no-progress enforcement, evidence-backed test selection, and runtime action admission are proven across the specific workflow being claimed.
