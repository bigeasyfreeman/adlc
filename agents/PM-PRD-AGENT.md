# PRD Agent (Product Manager) — Standalone

> **This agent runs independently of the DAG pipeline.**
> Use it to walk a PM through structured discovery → engineering-ready PRD.
> The PRD output feeds into the pipeline via the `triage` → `research` → `plan` path.

The full original spec is preserved at `docs/archive/PM-PRD-AGENT.md`.

## Quick Start

1. Drop this into your IDE agent context (Claude Code, Cursor, Codex)
2. Or invoke directly: `claude --model claude-opus-4-6 -p "$(cat docs/archive/PM-PRD-AGENT.md)"`
3. PM describes the feature
4. Agent walks through 7 phases in ~5 turns
5. Output: complete PRD in standard template format
6. Feed the PRD into the ADLC pipeline

## Skills Used

- `skills/prd-generation/SKILL.md` — PRD Quality Evaluator
- `skills/ux-flow-builder/SKILL.md` — UX Flow Builder
- `skills/figma-integration/SKILL.md` — Figma Integration
- `skills/gong-customer-evidence/SKILL.md` — Gong Customer Evidence
