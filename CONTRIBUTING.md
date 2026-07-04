# Contributing to ADLC

Thanks for your interest in contributing to the Agentic Development Lifecycle.

## Adding a Skill

Skills are the primary extension point. Each skill is a markdown file that encodes domain expertise.

1. Create `skills/[name]/SKILL.md`
2. Follow this structure:

```markdown
# Skill: [Name]

> One-line description

## Trigger
When does this skill activate? Which DAG nodes use it?

## Input
What data does the skill receive? (JSON schema)

## Behavior
What does the skill do? Step by step.

## Output
What does the skill produce? (JSON schema)

## Quality Gates
Checklist of what must be true before the skill's output is accepted.
```

3. Add an entry to `skills/manifest.json`:
```json
{
  "name": "your-skill",
  "path": "skills/your-skill/SKILL.md",
  "contract_version": "1.0.0",
  "side_effect_profile": "read_only | mutating",
  "dag_nodes": ["which_nodes_use_this"]
}
```

4. Update the relevant agent config in `agents/` to include your skill in its `skills` list.

## Adding an Agent

Agents are thin configs. Keep them under 150 lines.

1. Create `agents/[name].md` with YAML frontmatter:
```yaml
---
name: your-agent
description: What this agent does
model: claude-sonnet-4-6
skills:
  - skill-one
  - skill-two
labels: [lgtm, revise]
---
```

2. Add the agent node to `WORKFLOW.dot`
3. Add edge routing with label conditions
4. Add the agent to `skills/manifest.json` agents section

## Modifying the Pipeline

1. Edit `WORKFLOW.dot` — add, remove, or rewire nodes
2. Update `WORKFLOW.md` — adjust configs if needed
3. Visualize: `dot -Tpng WORKFLOW.dot -o pipeline.png`
4. Update `README.md` if the pipeline structure changed

## Target Repo Conventions

ADLC treats every target repository as a standards source. Any ADLC change that
affects planning, decomposition, codegen, QA, review, or PR closeout must
preserve the target repo convention contract:

1. Build Briefs carry top-level `repo_conventions` and `product_vocabulary`.
2. Missing convention docs are represented explicitly with
   `repo_conventions.status = "none_found"` and
   `explicit_empty_marker = "no_conventions_found"`.
3. New or changed skills that touch target-repo work must consume
   `repo_conventions` where relevant instead of inventing local convention
   prompts.
4. Codegen context must carry every extracted rule and every banned vocabulary
   token into task packages.
5. Structural gates must not use file size, line count, or SLOC as a split or
   quality criterion.

## Process Artifact Storage

Build Brief drafts, approved briefs, eval outputs, audits, validation summaries,
goal prompts, and closeout packages are ADLC process artifacts. They must not be
added to target-repo diffs.

When adding or changing a skill that writes those materials, compute the storage
path with `bin/adlc process-artifact-path` and write the artifact under the
ADLC-side storage contract in `docs/specs/process-artifact-storage.md`. Target
repos may contain ignored transient state for a local run, but canonical process
artifacts stay keyed by target repo and task in the ADLC store.
6. PRs must run `bin/adlc pr-hygiene-scan` and keep ADLC goal prompts, Build
   Brief drafts, council scratch artifacts, and local paths out of target diffs.

## Code Style

- Agent configs: YAML frontmatter + concise markdown
- Skills: detailed, thorough, checklist-driven
- Schemas: JSON Schema draft-07
- DOT files: use shape conventions (box=agent, dashed=tool, component=fan-out, hexagon=human gate)

## Pull Requests

- One skill/agent per PR
- Include a brief description of what the skill/agent does and why
- If modifying the pipeline graph, include a screenshot of the new DAG
