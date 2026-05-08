# Agent-Native CLI + MCP Wrapper Build Brief

## ADLC Mode

`prd_and_decompose`

## Production Target

Expose ADLC's existing machine-readable contracts through a small local CLI and MCP stdio wrapper so another agent can quickly discover agents, inspect workflow phases, validate artifacts, manage workflow state, run phases through existing adapters, and prepare normalized work-item emitter payloads.

## Scope Lock

In scope:

- `bin/adlc list-agents --json`
- `bin/adlc list-phases --json`
- `bin/adlc validate-artifact --schema <alias> --input <path> --json`
- `bin/adlc run --brief-id <id> --workspace <path> --dry-run --json`
- `bin/adlc run-phase <phase> --workspace <path> --dry-run --json`
- `bin/adlc resume-workflow --workspace <path> --json`
- `bin/adlc emit-work-items --target <linear|github|jira> --build-brief <path> --dry-run --json`
- `bin/adlc mcp-tools --json`
- `bin/adlc mcp-serve` with `initialize`, `tools/list`, and `tools/call`
- deterministic CLI and contract tests

Out of scope for this slice:

- deterministic implementations for every tool node (`scaffold`, `context_assembly`, `qa`, `slop_gate`)
- provider-specific SDK clients for Linear/GitHub/JIRA
- package publishing

## Existing Primitives Reused

- `skills/manifest.json` for agent discovery
- `WORKFLOW.dot` for workflow node and edge discovery
- `docs/schemas/*.schema.json` for artifact validation
- `docs/specs/emitter-contract.md` for normalized work-item emitter integration
- `tests/test_adlc_contracts.sh` as the deterministic regression gate

## Tasks

| Task ID | Artifact Type | Objective | Verification |
|---|---|---|---|
| ADLC-CLI-001 | implementation_task | Add repo-native CLI commands for agent discovery, phase discovery, and schema validation. | `tests/test_adlc_cli.sh` |
| ADLC-WF-001 | implementation_task | Add workflow state creation, dry-run phase transitions, runtime adapter invocation hooks, and resume inspection. | `tests/test_adlc_cli.sh` workflow section |
| ADLC-EMIT-001 | implementation_task | Add normalized Linear/GitHub/JIRA work-item payload generation with explicit local provider mutation hooks. | `tests/test_adlc_cli.sh` emitter section |
| ADLC-MCP-001 | implementation_task | Add MCP stdio wrapper for discovery, validation, workflow, resume, and emitter tools. | `tests/test_adlc_cli.sh` MCP section |
| ADLC-VAL-001 | validation_task | Prove the wrapper is agent-native enough for a downstream orchestrator to consume without hand-reading docs. | `tests/test_adlc_contracts.sh` and `tests/test_setup.sh` |

## Compatibility Contract

Backward compatibility: existing setup, smoke, and contract tests keep their current invocation paths.

Forward compatibility: the CLI stays thin and delegates to the existing manifest, workflow, schemas, adapter contracts, and local provider hooks so richer orchestration can be layered on without rewriting the contracts.

Migration or rollout: no migration. The CLI is additive and local-only.

## Definition of Done

- `tests/test_adlc_cli.sh` passes.
- `tests/test_adlc_contracts.sh` passes.
- `tests/test_setup.sh` passes.
- `git diff --check` passes.
- MCP tools expose discovery, validation, workflow, resume, and dry-run emitter operations.
- External mutation requires explicit `--allow-mutation` and a local `--provider-command`.

## Production Readiness Finding

This slice validates that ADLC is agent-native at the discovery, validation, state-transition, phase-runner, resume, and work-item-emitter layers. It does not yet validate a fully autonomous production run across every deterministic tool node and every external provider, because provider-specific adapters and full tool-node implementations remain future work.
