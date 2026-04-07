# OWASP AppSec Threat Model Skill

> Systematic application security analysis against OWASP Top 10 (2021). Produces per-component threat assessments with concrete mitigations tied to the codebase.

## Trigger

Invoke when: a Build Brief task touches authentication, authorization, data handling, user input processing, external API consumption, session management, or deployment configuration. Also invoke on any task flagged `security-relevant` by the Eval Council.

## Input Contract

```json
{
  "task_spec": "TaskSpec from Build Brief",
  "repo_map": "Cached codebase research output",
  "affected_files": ["list of files this task creates or modifies"],
  "integration_wiring": "upstream/downstream from task spec"
}
```

## OWASP Top 10 (2021) Checklist

The skill evaluates each task against all 10 categories. Categories not applicable to the task are marked N/A with justification.

### A01: Broken Access Control

- [ ] Every endpoint/function enforces authorization (not just authentication)
- [ ] Server-side access control — never rely on client-side checks
- [ ] Deny by default — new endpoints start with no access
- [ ] CORS is restrictive, not permissive
- [ ] Directory listing disabled; metadata files (.git, .env) not served
- [ ] Rate-limit access control APIs to slow credential stuffing
- [ ] JWT tokens invalidated on logout; stateless tokens have short TTL
- [ ] Log and alert on access control failures

**Project-specific example:** Tool endpoints must enforce role-based access. Backend APIs must not expose admin operations without token verification. Gateway/channel adapters must verify sender identity before dispatching.

### A02: Cryptographic Failures

- [ ] Classify data processed by this task (PII, credentials, tokens, repo content)
- [ ] Sensitive data encrypted at rest (AES-256-GCM via vault)
- [ ] Sensitive data encrypted in transit (TLS 1.2+ enforced)
- [ ] No deprecated algorithms (MD5, SHA1 for security, DES, RC4)
- [ ] No hardcoded keys, secrets, or connection strings in source
- [ ] Password storage uses bcrypt/scrypt/argon2 with salt (if applicable)
- [ ] Key rotation mechanism exists for any stored secrets

**Project-specific example:** A credential gateway should handle all secret injection. State stores must not contain plaintext tokens. LLM API keys must flow through a vault, never env vars in code.

### A03: Injection

- [ ] All user/external input is validated and sanitized
- [ ] Parameterized queries for any database operations (no string concatenation)
- [ ] Context-aware output encoding (HTML, JS, SQL, OS command, LDAP)
- [ ] LIMIT clauses on queries to prevent mass data exfiltration
- [ ] OS command execution uses allowlists, not blocklists
- [ ] Structured logging — log messages never interpolate user input unsanitized

**Project-specific example:** Issue tracker bodies are untrusted input -- they may flow into LLM prompts and must be sanitized. Executor prompts must escape any user-supplied content. Tool parameters must be schema-validated before dispatch.

### A04: Insecure Design

- [ ] Threat model exists for this component (you're reading it)
- [ ] Security controls are designed in, not bolted on
- [ ] Failure modes include security failure scenarios
- [ ] Rate limiting and resource limits are part of the design
- [ ] Separation of privilege — no single component has full access

**Project-specific example:** Pipeline designs must enforce gate separation. No single agent should have both read and write access to production systems. Multi-perspective validation (e.g., an Eval Council) before action is a security design pattern.

### A05: Security Misconfiguration

- [ ] No default credentials anywhere in config or code
- [ ] Unnecessary features/endpoints/services are disabled
- [ ] Error handling does not expose stack traces or internal details
- [ ] Security headers set (if HTTP: HSTS, X-Content-Type, X-Frame-Options, CSP)
- [ ] Cloud/container permissions follow least privilege

**Project-specific example:** Project config files must not contain secrets. Docker deployment must not use `--privileged`. Internal API servers must not expose debug endpoints in production. Default merge policy must be restrictive.

### A06: Vulnerable and Outdated Components

- [ ] All dependencies pinned to specific versions
- [ ] No known CVEs in current dependency tree
- [ ] Dependency update mechanism exists (Dependabot, Renovate, or manual process)
- [ ] Unused dependencies removed
- [ ] Components sourced from official/trusted registries only

**Project-specific example:** `pyproject.toml` dependencies must specify minimum versions. `package.json` must use a lockfile. LLM provider SDKs must be current.

### A07: Identification and Authentication Failures

- [ ] Authentication uses established frameworks (not custom crypto)
- [ ] MFA supported where applicable
- [ ] Session tokens are cryptographically random with sufficient entropy
- [ ] Failed login attempts are rate-limited and logged
- [ ] Password/token storage follows current NIST guidance (800-63b)
- [ ] Session invalidation on logout/timeout

**Project-specific example:** Auth tokens must be cryptographically generated. Device pairing must enforce approval flow. Backend APIs must reject unauthenticated requests.

### A08: Software and Data Integrity Failures

- [ ] CI/CD pipeline has integrity checks (signed commits, protected branches)
- [ ] Dependencies verified by checksum or signature
- [ ] Deserialization of untrusted data is avoided or sandboxed
- [ ] Auto-update mechanisms verify signatures before applying

**Project-specific example:** If your system processes its own PRs (self-development), PR governance validation must not be bypassable. Executor output must be treated as untrusted (code review gates). Learning systems must validate data integrity before updating policy.

### A09: Security Logging and Monitoring Failures

- [ ] All authentication events logged (success and failure)
- [ ] All access control failures logged
- [ ] All input validation failures logged
- [ ] Logs include sufficient context for incident response (timestamp, user, action, resource)
- [ ] Logs do NOT contain sensitive data (tokens, passwords, PII)
- [ ] Alerting exists for anomalous patterns

**Project-specific example:** Structured log events must cover all gate decisions, executor invocations, merge actions, and learning updates. An audit trail (e.g., journal writer) is essential. Secret redaction must apply to all log sinks.

### A10: Server-Side Request Forgery (SSRF)

- [ ] All user-supplied URLs are validated against an allowlist
- [ ] HTTP redirects are not blindly followed
- [ ] Internal network ranges (169.254.x.x, 10.x.x.x, etc.) are blocked for outbound requests
- [ ] Raw responses from fetched URLs are not returned to users

**Project-specific example:** Tracker adapters and webhook endpoints must validate all URLs. Gateways must not proxy arbitrary URLs from channel messages. LLM tool-use responses that contain URLs must be validated before fetch.

## Output Contract

```json
{
  "task_id": "string",
  "threat_assessment": {
    "A01_access_control": { "applicable": true, "risk": "HIGH|MEDIUM|LOW|N/A", "findings": [], "mitigations": [] },
    "A02_crypto": { "applicable": true, "risk": "...", "findings": [], "mitigations": [] },
    "A03_injection": { "...": "..." },
    "A04_insecure_design": { "...": "..." },
    "A05_misconfiguration": { "...": "..." },
    "A06_vulnerable_components": { "...": "..." },
    "A07_auth_failures": { "...": "..." },
    "A08_integrity_failures": { "...": "..." },
    "A09_logging_monitoring": { "...": "..." },
    "A10_ssrf": { "...": "..." }
  },
  "overall_risk": "HIGH|MEDIUM|LOW",
  "blocking_findings": ["findings that must be resolved before merge"],
  "advisory_findings": ["findings to address in follow-up tickets"]
}
```

## Quality Gates

- Every applicable OWASP category must have at least one specific finding or explicit N/A justification
- HIGH risk findings are blocking — task cannot pass Eval Council without mitigation
- MEDIUM risk findings require a mitigation plan (can be follow-up ticket)
- All mitigations must reference specific code locations, not generic advice

## Framework Hardening Addendum

- **Contract versioning:** Input and output contracts include `contract_version` with semver rules from `docs/specs/skill-contract-versioning.md`.
- **Schema validation:** Validate threat-model outputs against `docs/schemas/security-assessment.schema.json` before publishing to downstream consumers.
- **Stop reasons:** On blocking conditions, emit structured stop reasons from `docs/specs/stop-reasons.md` for deterministic pipeline behavior.
- **Read-only guarantee:** This skill performs analysis only; no external side effects are permitted.

