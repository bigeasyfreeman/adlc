# Tool Pools Spec

## Policy
Default deny. Tools are explicitly allowed per phase based on registry metadata.

## Phase Pools
| Phase Group | Allowed Tool Families |
|---|---|
| Phase 0 Research | Codebase Research, Grafana baseline pull |
| Phase 1-7 Briefing | Build Brief analysis + Eval Council only (no external mutations) |
| Phase 8 Task Breakdown | Build Brief + Architecture analysis |
| Phase 9 Codegen | File read/write, tests, git local ops |
| Phase 10-11 Prep | Work-item emitter MCPs, document emitter MCPs, Scaffolding, QA, CI/CD |
| Phase 12+ Deploy/Operate | CI/CD deploy, Grafana provisioning, Incident Runbook, Slack |

## Enforcement
1. Resolve allowed list from `tool-registry` by current phase.
2. Reject out-of-phase invocation with `permission.denied` event.
3. Log denied attempts in permission audit trail.
