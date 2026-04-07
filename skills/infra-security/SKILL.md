# OWASP Kubernetes / Infrastructure Security Skill

> Threat analysis for container and infrastructure deployments against OWASP Kubernetes Top 10 (2025). Covers workload hardening, RBAC, secrets management, network segmentation, and cloud lateral movement.

## Trigger

Invoke when: a task involves Dockerfiles, docker-compose, Kubernetes manifests, Helm charts, CI/CD pipelines, deployment scripts, systemd/launchd services, infrastructure-as-code, or cloud configuration.

## Input Contract

```json
{
  "task_spec": "TaskSpec from Build Brief",
  "repo_map": "Cached codebase research output",
  "deployment_artifacts": ["list of infra files created or modified"],
  "target_environment": "docker | k8s | systemd | launchd | cloud"
}
```

## OWASP Kubernetes Top 10 (2025) Checklist

Applicable to both Kubernetes deployments and Docker/container deployments. Items marked [K8s-only] can be skipped for Docker-only deployments.

### K01: Insecure Workload Configurations

- [ ] Containers run as non-root user (`USER` directive in Dockerfile)
- [ ] No `--privileged` flag (common failure: sandboxing tools fail in privileged Docker)
- [ ] Capabilities dropped (`--cap-drop=ALL`, add back only what's needed)
- [ ] Read-only root filesystem where possible
- [ ] Resource limits set (CPU, memory) — no unbounded containers
- [ ] No host PID/network/IPC namespace sharing unless required
- [ ] Security context enforced (seccomp profiles, AppArmor/SELinux)

**Project-specific example:** Dockerfiles must run services as a non-root user. If your executor needs specific capabilities (e.g., for sandboxing), document exactly which ones and drop all others. Resource limits must prevent a runaway process from consuming the host.

### K02: Overly Permissive Authorization [K8s-only]

- [ ] No cluster-admin bindings for application workloads
- [ ] RBAC follows least privilege — no wildcard verbs or resources
- [ ] Service account tokens not auto-mounted unless needed
- [ ] Role bindings scoped to namespace, not cluster

**Project-specific example:** If deployed to K8s, backend service pods need read access to their own namespace only. Internal API server pods need network access to the backend but not to the K8s API. Gateway/edge pods need external network but not internal cluster access.

### K03: Secrets Management Failures

- [ ] No secrets in environment variables (use mounted volumes or external vault)
- [ ] No secrets in Docker images or git history
- [ ] Secrets encrypted at rest (etcd encryption for K8s, vault for Docker)
- [ ] Secret rotation mechanism exists
- [ ] Base64 is NOT encryption — K8s secrets need additional protection

**Project-specific example:** If your project has an in-app vault (e.g., `security/vault.py`, `security/credential_gateway.py`), use it. For infrastructure: API keys must not be in `docker-compose.yml` or `.env` committed to git. K8s secrets must use external-secrets-operator or similar. Project config files must not contain credentials.

### K04: Lack of Cluster-Level Policy Enforcement [K8s-only]

- [ ] Pod Security Standards enforced (restricted baseline minimum)
- [ ] Admission controller deployed (OPA/Gatekeeper or Kyverno)
- [ ] Network policies deployed as code
- [ ] Resource quotas per namespace

**Project-specific example:** If deployed to K8s, enforce restricted pod security. If executor pods need a specific exception for sandboxing capabilities, this must be the ONLY exception, explicitly documented.

### K05: Missing Network Segmentation

- [ ] Default-deny network policy (no pod-to-pod unless explicitly allowed)
- [ ] Daemon and MCP server on internal network only
- [ ] Gateway on DMZ / edge network with restricted backend access
- [ ] Database/state store not directly accessible from external network
- [ ] Service mesh mTLS for inter-service communication (if applicable)

**Project-specific example:** For Docker: backend services, internal APIs, and state stores should be on an internal Docker network. Only the gateway/edge service should have port exposure. For K8s: NetworkPolicies must restrict gateway-to-backend (API only), backend-to-executor (task dispatch only), and block executor-to-state-store access.

### K06: Overly Exposed Components

- [ ] API server / daemon management port not publicly accessible
- [ ] Health/readiness endpoints do not leak internal state
- [ ] Debug/profiling endpoints disabled in production
- [ ] Container ports limited to what's needed

**Project-specific example:** Internal API servers must listen on internal-only ports. The gateway/edge service is the only public-facing port. Health endpoints (`/healthz`) must return only status, not configuration or state details.

### K07: Misconfigured and Vulnerable Components

- [ ] Base images are minimal (distroless or alpine)
- [ ] Base images are regularly updated for security patches
- [ ] Container scanning in CI (Trivy, Grype, or similar)
- [ ] Ingress controller is current and properly configured
- [ ] TLS termination at ingress, not in application

**Project-specific example:** Dockerfiles that install runtimes, CLIs, and agent binaries expand the attack surface. Pin versions. Scan the built image. The `apt-get install` step must not leave package caches in the image.

### K08: Cluster-to-Cloud Lateral Movement [K8s-only]

- [ ] IMDS v2 enforced (blocks metadata service exploitation)
- [ ] Workload identity used instead of node-level IAM roles
- [ ] Cloud IAM scope is minimum required per workload
- [ ] Network policies block access to cloud metadata endpoints (169.254.169.254)

**Project-specific example:** If deployed in cloud K8s, executor pods must NOT have access to cloud metadata. A compromised executor (running arbitrary code) could pivot to cloud credentials via IMDS.

### K09: Broken Authentication Mechanisms

- [ ] Anonymous access disabled
- [ ] Client certificate rotation automated
- [ ] Short-lived tokens preferred over long-lived
- [ ] All inter-service auth events logged

**Project-specific example:** Internal API servers must require authentication. Gateways must authenticate WebSocket connections. In multi-instance mode, cross-instance communication must use mutual TLS or signed tokens.

### K10: Inadequate Logging and Monitoring

- [ ] Container stdout/stderr captured and forwarded to log aggregator
- [ ] API audit logging enabled (who called what, when, from where)
- [ ] Runtime anomaly detection (unexpected process execution, file access)
- [ ] Resource usage monitoring with alerting
- [ ] Log retention policy defined

**Project-specific example:** Structured logging output (e.g., structlog) must produce JSON for log aggregation. Application-level audit trails complement container-level logging. Container logs must capture executor subprocess output. Alerting must exist for: executor timeout spikes, gate failures, anomalies, and auth failures.

## Output Contract

```json
{
  "task_id": "string",
  "infra_threat_assessment": {
    "K01_workload_config": { "risk": "HIGH|MEDIUM|LOW|N/A", "findings": [], "mitigations": [] },
    "K02_authorization": { "...": "..." },
    "K03_secrets": { "...": "..." },
    "K04_policy_enforcement": { "...": "..." },
    "K05_network_segmentation": { "...": "..." },
    "K06_exposed_components": { "...": "..." },
    "K07_vulnerable_components": { "...": "..." },
    "K08_lateral_movement": { "...": "..." },
    "K09_authentication": { "...": "..." },
    "K10_logging_monitoring": { "...": "..." }
  },
  "target_environment": "docker | k8s | systemd | launchd",
  "overall_risk": "HIGH|MEDIUM|LOW",
  "blocking_findings": [],
  "advisory_findings": []
}
```

## Quality Gates

- K01 (Workload Config) and K03 (Secrets) are ALWAYS applicable — never mark N/A
- K05 (Network Segmentation) is applicable for any multi-container deployment
- HIGH risk findings block merge
- Any use of `--privileged`, root user, or host namespace sharing is an automatic HIGH finding requiring explicit justification

## Framework Hardening Addendum

- **Contract versioning:** Security assessment contracts require `contract_version` and semver compatibility enforcement.
- **Schema validation:** Validate outputs against `docs/schemas/security-assessment.schema.json`; reject invalid structures before downstream use.
- **Structured errors:** Emit deterministic failure categories (`unsupported_scope`, `missing_repo_map`, `schema_mismatch`).
- **Read-only guarantee:** Analysis-only mode; no mutating operations during security review.

