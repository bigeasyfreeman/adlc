# Bounded Directed Workflow Binding Contract

## Source of Truth

`WORKFLOW.md` is the execution binding contract for ADLC workflow runners.

Runners must consume these sections together:

- frontmatter `labels`
- frontmatter `iteration_limits`
- frontmatter `backends`
- the `Node -> Agent Mapping` table
- the `Tool Nodes` block

`WORKFLOW.dot` defines the graph topology and legal labeled transitions, including bounded retry back-edges. `WORKFLOW.md` defines how each node actually runs and caps retries.

## Binding Rules

1. Parse `WORKFLOW.dot` to discover node names and outgoing labels.
2. Resolve each node from `WORKFLOW.md`:
   - If the node appears in `Node -> Agent Mapping` with an agent path, run that agent config.
   - If the node appears as `*tool node*`, run the matching command from the `Tool Nodes` block.
   - If the node is a human gate, stop for human input.
3. Fail closed if an executable node appears in `WORKFLOW.dot` but has no execution binding in `WORKFLOW.md`.
4. For branching nodes, fail closed if an emitted label is missing from frontmatter `labels` or has no matching edge in `WORKFLOW.dot`.
5. Apply retry caps from `iteration_limits` by node name.
6. Resolve the runtime backend from `ADLC_RUNTIME` (default `claude`) against `WORKFLOW.md` frontmatter `backends`.

## Agent Nodes

Agent nodes are bound by the `Node -> Agent Mapping` table.

- The runner must load the exact markdown file listed in the table.
- The runner must honor the configured backend, model, and injected skills.
- The agent markdown and the corresponding output schema are authoritative across runtimes. Backend switching must not rewrite the agent contract.
- Labels emitted by branching agents must be valid for both the agent frontmatter and the workflow graph.
- Linear success nodes may emit `done` while following their sole unlabeled success edge.

`gen_tests` is an agent node bound to `agents/test-author.md`. It must not be routed to a shell command or tool stub.

## Tool Nodes

Tool nodes are deterministic command executions.

- The runner must execute the documented command body instead of inferring behavior from skill names.
- Tool nodes may consume skill outputs, but the execution mode is still command-based.
- Missing tool-node command bodies are a hard binding failure.

## Consistency Checks

Before execution, runners should verify:

- every executable node in `WORKFLOW.dot` is bound in `WORKFLOW.md`
- every edge label is listed in frontmatter `labels`
- every backend named in `ADLC_RUNTIME` exists in frontmatter `backends`
- every agent path exists on disk
- every tool node has a command block
- manifest `dag_node` and `dag_nodes` entries agree with workflow bindings

## Runtime Invocation Sources

- Smoke harness execution uses `tests/smoke/adapters/` as the source of truth for runtime-specific invocation logic.
- Production orchestration uses `WORKFLOW.md` frontmatter `backends` as the source of truth for backend commands and auth environment names.
- Runners must keep these two surfaces aligned: the adapter contract (`invoke_agent --agent --input --output --tools [--schema]`) is the canonical smoke shape, and `WORKFLOW.md` backends mirror that shape for production.
- Judge skills resolve `model_class` slots such as `fast_judge` and `deep_judge` through `skills/manifest.json` for the active runtime before the adapter executes the call.

## Retry Semantics

- Retry budgets are part of the binding contract, not agent discretion.
- `test_strength_retry` caps weak-test strengthening loops.
- Runners must not silently continue retrying after the configured budget is exhausted.

## Current Binding Notes

- `gen_tests` is an authoring agent stage.
- `test_strength` is an audit agent stage that runs after `qa` passes and before downstream delivery gates.
- If prose elsewhere describes an implicit stage, runners still bind only what `WORKFLOW.md` explicitly declares.
