# ADLC — Agentic Development Lifecycle

This project uses the ADLC framework for AI-assisted development.

## Pipeline

The ADLC pipeline converts PRDs into production code through a DAG of specialized agents:

```
Triage → Graph Research → Plan ↔ Review → Code (parallel) → Comprehension Gate → QA → Security → PR → Engineer Review
```

## Agents

Agents are in `.claude/agents/`. Each is a subagent with preloaded skills:

- **triage** — Classify tasks, route to pipeline or escalate
- **researcher** — Graph-backed codebase analysis + PRD cross-reference + dark-code risk notes
- **planner** — PRD → Build Brief (spec/plan/tasks/context artifacts)
- **plan-reviewer** — 6-persona Eval Council validation
- **coder** — verifier-led execution per task class
- **code-reviewer** — Quality, correctness, and comprehension review
- **fixer** — 4-phase systematic debugging
- **security-reviewer** — 5 OWASP domain assessment
- **pr-preparer** — Assemble final PR package

## Skills

Skills are in `.claude/skills/`. They inject domain expertise into agents automatically.

## Usage

Invoke agents by name or let Claude select the right one based on your task:
- "Research this codebase for building notifications" → researcher agent
- "Create a Build Brief from this PRD" → planner agent
- "Review this Build Brief" → plan-reviewer agent (Eval Council)
- "Review this diff for comprehension and blast radius" → code-reviewer agent

## Conventions

- Every acceptance criterion uses Given/When/Then format
- Every task must be self-contained (zero-read principle)
- Use Graphify before broad source search when `graphify-out/` exists; use Beads only for task memory and blockers
- Medium+ blast-radius changes require comprehension evidence before shipping
- Type 1 decisions (irreversible) always escalate to human
- Label-based routing: agents emit `lgtm`/`revise`/`escalate`
