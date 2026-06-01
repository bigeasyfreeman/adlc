# ADLC — Agentic Development Lifecycle (Factory Platform)

This project uses the ADLC framework for AI-assisted development, adapted for the Factory platform.

## Pipeline

The ADLC pipeline converts PRDs into production code through a DAG of specialized agents:

```
Triage → Research → Plan ↔ Review → Code (parallel) → QA → Security → PR → Engineer Review
```

## Factory Concept Mapping

| ADLC Concept | Factory Equivalent | Location |
|---|---|---|
| Agent | Droid | `.factory/droids/` |
| Skill | Doc (injected knowledge) | `.factory/docs/skills/` |
| Subagent fan-out | Task tool (parallel dispatch) | Built-in |
| Instructions file | `AGENTS.md` | Project root |
| Model selection | `model: inherit` or explicit | Droid config |

## Droids

Droids are in `.factory/droids/`. Each is a YAML config that defines an ADLC pipeline agent:

- **adlc-triage** — Classify tasks, route to pipeline or escalate
- **adlc-researcher** — Deep codebase analysis + PRD cross-reference
- **adlc-planner** — PRD → Build Brief (spec/plan/tasks)
- **adlc-code-reviewer** — Quality and correctness review
- **adlc-coder** — Verifier-led execution per task class
- **adlc-fixer** — 4-phase systematic debugging

Additional agents (plan-reviewer, security-reviewer, pr-preparer) use the generic agent configs installed as droid markdown files.

## Skills

Skills are injected as docs in `.factory/docs/skills/`. Factory loads these automatically into the droid context when referenced. Each skill provides domain expertise following the ADLC skill contract:

- Trigger conditions (when the skill activates)
- Input schema (what data the skill receives)
- Behavior steps (what the skill does)
- Output schema (what the skill produces)
- Quality gates (acceptance criteria)

## Factory-Specific Conventions

### Model Selection

Factory uses the `inherit` model by default, which inherits the session's configured model. For agents requiring deep reasoning:

| Agent Tier | Model | Use For |
|---|---|---|
| Fast | `inherit` | triage, coder, fixer, pr-preparer |
| Deep | `claude-opus-4-6` | researcher, planner, plan-reviewer, security-reviewer, code-reviewer |

### Droid Inheritance

Factory droids use `model: inherit` to defer model selection to the runtime session. Override with an explicit model when an agent requires deep reasoning capability.

### Task Tool for Fan-Out

Factory's `Task` tool enables parallel subagent dispatch, mapping directly to ADLC's fan-out model:

```
# Fan-out: dispatch coding tasks in parallel
Task("adlc-coder", "Implement task 1: <context>")
Task("adlc-coder", "Implement task 2: <context>")
Task("adlc-coder", "Implement task 3: <context>")
# Fan-in: collect results at code review
```

Independent coding tasks should always be dispatched in parallel. Serial execution of independent tasks is a velocity failure.

### MCP Integration

Factory supports MCP (Model Context Protocol) servers for external tool integration. ADLC integration skills that use external services should configure MCP providers:

| Skill | Recommended MCP Server |
|---|---|
| jira-ticket-creation | Jira/Atlassian MCP |
| github-issue-creation | GitHub MCP (built-in) |
| confluence-decomposition | Atlassian MCP |
| slack-orchestration | Slack MCP |
| grafana-observability | Grafana MCP |

MCP servers are configured at the Factory workspace level, not per-droid.

### Skill Injection via Docs

Factory injects knowledge through `.factory/docs/`. ADLC skills installed here are available to all droids in the session:

```
.factory/docs/skills/
├── adlc-codebase-research.md
├── adlc-eval-council.md
├── adlc-tdd-enforcement.md
├── adlc-systematic-debugging.md
└── ...
```

## Usage

Invoke droids by name or let Factory route based on your task:

- "Research this codebase for building notifications" → adlc-researcher droid
- "Create a Build Brief from this PRD" → adlc-planner droid
- "Fix the failing tests from code review" → adlc-fixer droid
- "Review this code change" → adlc-code-reviewer droid

## Working Agreements

- Every acceptance criterion uses Given/When/Then format
- Every coding task must be self-contained (zero-read principle: all context inlined)
- Type 1 decisions (irreversible: data models, public APIs, auth) always escalate to human
- Type 2 decisions (reversible: implementation, internal APIs) decide and document rationale
- Agents emit structured labels: `lgtm`, `revise`, `escalate`, `pass`, `fail`
- Parallel tasks explicitly flagged — serial execution of independent tasks is a velocity failure
- No TODO/FIXME/PLACEHOLDER in shipped code
- Security review runs only when the applicability manifest marks a security-relevant surface active

## Build & Test

- Run tests after every code change
- TDD enforcement: RED → GREEN → REFACTOR per acceptance criterion
- Max 2 fix attempts before escalating
- Max 3 plan review iterations before escalating

## Labels

Labels drive DAG routing:

| Label | Meaning |
|---|---|
| `lgtm` | Approved, proceed to next node |
| `revise` | Back with findings |
| `escalate` | Human needed |
| `pass`/`fail` | Deterministic gate result |
| `fixed`/`stuck` | Fixer result |
| `blocked` | Council blocked, human decision required |
