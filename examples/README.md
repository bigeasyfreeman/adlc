# Examples

## example-prd.md

A complete example PRD for a User Notifications feature. Use this to test the ADLC pipeline:

```bash
# Step 1: Triage
claude --model claude-sonnet-4-6 -p "$(cat agents/triage.md)" < examples/example-prd.md

# Step 2: Research (point at your repo)
claude --model claude-opus-4-6 -p "$(cat agents/researcher.md)" \
  "PRD: $(cat examples/example-prd.md) REPO: /path/to/your/repo"

# Step 3: Plan
claude --model claude-opus-4-6 -p "$(cat agents/planner.md)" \
  "PRD: $(cat examples/example-prd.md) RESEARCH: [paste research output]"
```

## Custom Workflows

Copy `WORKFLOW.dot` and modify it for your use case:

```bash
# Minimal pipeline (skip security for internal tools)
# Edit WORKFLOW.dot: remove security node, route code_review → qa directly

# Bugfix pipeline (skip planning, go straight to code)
# Edit WORKFLOW.dot: triage → research → code → qa → pr_prep
```

Visualize your pipeline:
```bash
dot -Tpng WORKFLOW.dot -o pipeline.png
open pipeline.png
```
