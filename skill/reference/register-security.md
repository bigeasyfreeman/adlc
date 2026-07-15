# Internal Security Pack Register

Load this register only when Harden, Build, or Review determines that the change affects a listed boundary. Apply only the matching rows; do not preload the legacy peer skills.

| Applicability signal | Migrated legacy sources | Bounded contract |
| --- | --- | --- |
| Authentication, authorization, tenant isolation, secrets, or untrusted input | `agentic-security`, `api-security`, `appsec-threat-model`, `security-review` | Identify assets, actors, trust boundaries, abuse cases, and enforceable mitigations. Verify deny paths as well as allow paths. |
| Model tools, retrieval, prompts, memory, or agent delegation | `llm-security`, `agentic-security` | Treat retrieved and tool-returned content as untrusted. Bound tools, validate arguments, prevent instruction/data confusion, and record approval gates. |
| Infrastructure, containers, clusters, IAM, or deployment credentials | `infra-security` | Check least privilege, isolation, secret handling, immutable provenance, rollback, and failure containment. |

Required output is evidence-backed findings with severity, affected path, exploit or failure precondition, remediation, and verifier. A checklist pass is not a security certification.

Source paths remain in `skills/` during the 0.x compatibility window. They are internal evidence and are not installed as public skills.
