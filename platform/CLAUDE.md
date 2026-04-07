# ADLC — Agentic Development Lifecycle

This project uses the ADLC framework for AI-assisted development.

## Pipeline

The ADLC pipeline converts PRDs into production code through a DAG of specialized agents:

```
Triage → Research → Plan ↔ Review → Code (parallel) → QA → Security → PR → Engineer Review
```

## Agents

Agents are in `.claude/agents/`. Each is a subagent with preloaded skills:

- **triage** — Classify tasks, route to pipeline or escalate
- **researcher** — Deep codebase analysis + PRD cross-reference
- **planner** — PRD → Build Brief (spec/plan/tasks)
- **plan-reviewer** — 6-persona Eval Council validation
- **coder** — TDD per task (RED/GREEN/REFACTOR)
- **code-reviewer** — Quality and correctness review
- **fixer** — 4-phase systematic debugging
- **security-reviewer** — 5 OWASP domain assessment
- **pr-preparer** — Assemble final PR package

## Skills

22 skills are in `.claude/skills/`. They inject domain expertise into agents automatically.

## Usage

Invoke agents by name or let Claude select the right one based on your task:
- "Research this codebase for building notifications" → researcher agent
- "Create a Build Brief from this PRD" → planner agent
- "Review this Build Brief" → plan-reviewer agent (Eval Council)

## Conventions

- Every acceptance criterion uses Given/When/Then format
- Every task must be self-contained (zero-read principle)
- Type 1 decisions (irreversible) always escalate to human
- Label-based routing: agents emit `lgtm`/`revise`/`escalate`
