# Internal Release Pack Register

Load this register only for Build, Review, Harden, or Ship when the change affects delivery, operations, or release readiness.

| Applicability signal | Migrated legacy sources | Bounded contract |
| --- | --- | --- |
| CI workflow, build artifact, deployment, Helm, or Argo CD change | `ci-cd-pipeline`, `helm-argocd-deployment` | Pin inputs, preserve provenance, validate the rendered artifact, define promotion and rollback, and observe the real release gate. |
| Runtime behavior, dashboards, alerts, or operational ownership | `grafana-observability`, `observability-contract`, `incident-runbook` | Define useful signals, thresholds, owners, failure modes, and a tested response or rollback path. |
| PR preparation, documentation handoff, or post-change drift | `drift-maintenance` | Compare declared and actual state, keep reviewer scope bounded, and report unresolved external gates honestly. |

Publishing, merging, releasing, deploying, or communicating externally always requires explicit authority. `ship-content` is not loaded or installed; use `command-ship.md` for the product-safe release contract.
