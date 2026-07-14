# Bounded Directed Workflow Binding Contract

## Source of Truth

The executable contract is split across machine-readable files:

- `WORKFLOW.dot` defines topology, legal edge labels, and per-edge `max_retries` caps.
- `skills/manifest.json` binds agent names, prompts, skills, and runtime model maps to `dag_node` values.
- `scripts/adlc_runtime/adapters/{runtime}.sh` defines runtime invocation and authentication behavior.
- `scripts/adlc_runtime/cli.py` binds deterministic tool-node implementations and output schemas.

`WORKFLOW.md` explains this contract for humans. It is not parsed as configuration.

## Binding Rules

1. Parse `WORKFLOW.dot` to discover node names and outgoing labels.
2. Resolve agent nodes by matching `skills/manifest.json` `dag_node` values; resolve tool nodes through the runtime's explicit tool-node dispatch table; stop at human gates.
3. Fail closed if an executable node has no manifest agent or tool-node implementation.
4. For branching nodes, fail closed if the emitted label has no matching edge in `WORKFLOW.dot`.
5. Increment the persisted counter for the traversed edge and stop when its DOT `max_retries` cap is exhausted.
6. Resolve `ADLC_RUNTIME` (default `claude`) to an executable adapter file under `scripts/adlc_runtime/adapters/`.

## Agent Nodes

Agent nodes are bound by `skills/manifest.json`. The mapping table in `WORKFLOW.md` is a readable projection of that manifest.

- The runner must load the exact markdown file listed in the table.
- The runner must honor the configured backend, model, and injected skills.
- The agent markdown and the corresponding output schema are authoritative across runtimes. Backend switching must not rewrite the agent contract.
- Labels emitted by branching agents must match an outgoing workflow edge after their artifact passes schema validation.
- Linear success nodes may emit `done` while following their sole unlabeled success edge.

`gen_tests` is an agent node bound to `agents/test-author.md`. It must not be routed to a shell command or tool stub.

## Tool Nodes

Tool nodes are deterministic command executions.

- The runner must execute the explicit CLI implementation instead of inferring behavior from skill names.
- Tool nodes may consume skill outputs, but the execution mode is still command-based.
- Missing tool-node command bodies are a hard binding failure.
- Tool-node outputs must validate against `docs/schemas/tool-node-result.schema.json`.
- Dry-run tool-node execution emits a `planned` artifact and must not mark the phase complete.
- Mutating tool-node execution must use action admission before writing project files or learning entries.

## Consistency Checks

Before execution, runners should verify:

- every executable node in `WORKFLOW.dot` has a manifest agent or tool-node implementation
- every branching output label has a matching edge
- every supported `ADLC_RUNTIME` has an executable adapter
- every agent path exists on disk
- every executable tool node has a CLI/MCP binding and emits a phase artifact
- manifest `dag_node` and `dag_nodes` entries agree with workflow bindings

## Runtime Invocation Sources

- Production and smoke execution use `scripts/adlc_runtime/adapters/` as the single source of truth for runtime-specific invocation logic.
- Production orchestration uses the selected adapter as the source of truth for backend commands and auth environment names.
- Runners must keep the adapter contract (`invoke_agent --agent --input --output --tools [--schema]`) aligned across all supported adapters.
- Judge skills resolve `model_class` slots such as `fast_judge` and `deep_judge` through `skills/manifest.json` for the active runtime before the adapter executes the call.

## Retry Semantics

- Retry budgets are part of the binding contract, not agent discretion.
- `max_retries` on the matching DOT edge caps each retry route, including weak-test strengthening loops.
- Runners must not silently continue retrying after the configured budget is exhausted.

## Current Binding Notes

- `gen_tests` is an authoring agent stage.
- `test_strength` is an audit agent stage that runs after `qa` passes and before downstream delivery gates.
- The `security` workflow node is owned by `agents/security-reviewer.md`; `security-review` supplies the STRIDE contract at planning and review surfaces, while the five domain skills supply the node's specialized checks.
- If prose elsewhere describes an implicit stage, runners still bind only what the executable sources above declare.
