# Runtime Decomposition Plan

Status: design only. This document does not decompose `scripts/adlc_runtime/cli.py`; every code move remains gated on human approval of the boundary map.

## Boundary Map

The proposed boundaries follow owned behavior, not line count:

1. `artifacts.py`: schema resolution, artifact validation, and process-artifact paths.
2. `workflow.py`: workflow state, transitions, phase planning, resume, and deterministic tool-node execution.
3. `gates.py`: clarity, compatibility, minimalism, completion, convention, and hygiene evaluators.
4. `queue.py`: queue lifecycle, worktree admission, and cleanup planning.
5. `loops.py`: loop contracts, budgets, actions, maturity, library, and meta-harness planning.
6. `execution.py`: runtime adapters, context packages, external execution reports, and goal-prompt generation.
7. `emitters.py`: normalized work-item payloads and provider synchronization.
8. `cli.py`: argument parsing and command-to-domain dispatch only.

## Per-Slice Dependency Direction

Each extracted module may depend on small shared types and filesystem helpers, but domain modules must not import `cli.py`. `cli.py` imports domain command functions. Gates may consume artifact and workflow data but must not mutate queue or emitter state. Execution may consume artifacts and context packages but must not call emitters. Queue and emitters share normalized identifiers through a small neutral contract, never through each other.

Land slices independently in this order: artifacts, emitters, queue, loops, gates, execution, workflow, then thin the parser. For each slice, first add characterization tests around the existing public command, move one cohesive command family without changing its CLI shape, and delete the old definitions only after parity passes. No slice requires the next slice to compile or pass.

## Dispatch Ownership

`cli.py` owns parser construction, help text, argument normalization, and final exit-code rendering. Each domain module owns payload construction and its command handler. `metadata.py` remains the declarative registry for schema aliases, MCP names, runtime lists, and default tool grants. The `bin/adlc` wrapper remains unchanged.

## Escalation Points

- Human approval is required before accepting or changing this boundary map.
- Escalate any proposed public flag, JSON field, exit-code, or MCP-name change.
- Escalate a circular dependency, a slice that cannot land independently, or a move requiring cross-domain state mutation.
- Escalate any plan to replace behavior while moving it; decomposition slices are behavior-preserving only.
- Security review remains required before moving external execution and goal-prompt code.

## Per-Slice Verification Command Sequence

Run this exact safety net after every slice:

```bash
bash tests/test_adlc_cli.sh
bash tests/test_adlc_contracts.sh
bash tests/test_setup.sh
bin/adlc ci --json
```

The historical brief called these the 957-assertion suites. Assertion totals are expected to grow; green command results, not a frozen count, are the migration contract. Add focused import-direction and command-parity tests with each extraction before relying on the full suite.

## Reversibility

Each slice is a standalone move commit with no schema or command change. Reverting that commit restores the prior location. The final parser-thinning slice happens only after all extracted modules have stable focused tests.
