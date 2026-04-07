# OWASP API Security Skill

> Threat analysis for API surfaces against OWASP API Security Top 10 (2023). Covers authorization, authentication, resource consumption, and business logic abuse for any exposed API endpoint.

## Trigger

Invoke when: a task creates or modifies API endpoints (MCP tools, HTTP routes, WebSocket handlers, gateway endpoints), API clients, or inter-service communication.

## Input Contract

```json
{
  "task_spec": "TaskSpec from Build Brief",
  "repo_map": "Cached codebase research output",
  "api_surface": ["list of endpoints/tools created or modified"],
  "auth_model": "description of authentication/authorization in use"
}
```

## OWASP API Security Top 10 (2023) Checklist

### API1: Broken Object Level Authorization (BOLA)

- [ ] Every API endpoint that accesses an object by ID enforces authorization
- [ ] Authorization checks use the authenticated user's context, not client-supplied role
- [ ] Object IDs are unpredictable (UUIDs, not sequential integers)
- [ ] Tests exist for unauthorized access to other users'/agents' objects

**Project-specific example:** Tool endpoints that accept `job_id`, `task_id` parameters must validate that the caller has access to that specific resource. In multi-instance mode, one instance must not access another's jobs without explicit cross-instance authorization.

### API2: Broken Authentication

- [ ] Authentication uses standard mechanisms (OAuth2, API keys with proper rotation)
- [ ] Tokens are validated on every request (not just at session start)
- [ ] Failed auth attempts are rate-limited and logged
- [ ] Token expiration and rotation are enforced

**Project-specific example:** Auth middleware (e.g., `src/mcp/auth.py`) must validate tokens on every tool call. Gateway WebSocket connections must authenticate on handshake. Backend APIs must reject unauthenticated callers.

### API3: Broken Object Property Level Authorization

- [ ] API responses only include properties the caller is authorized to see
- [ ] Write operations validate which fields the caller can modify (no mass assignment)
- [ ] Sensitive properties (tokens, internal state) are never exposed in API responses

**Project-specific example:** Status and job-view endpoints must not expose internal state (executor credentials, confidence internals) to unprivileged callers. Gateway responses to channel users must be filtered based on role.

### API4: Unrestricted Resource Consumption

- [ ] Rate limits per caller per endpoint
- [ ] Request payload size limits
- [ ] Pagination enforced on list endpoints (no unbounded queries)
- [ ] Timeout on all downstream calls
- [ ] Cost tracking for resource-intensive operations (LLM calls)

**Project-specific example:** Job dispatch endpoints must rate-limit job creation. Tracker adapters must handle pagination correctly (full-pagination bugs are resource consumption issues). LLM-backed endpoints must have token budgets.

### API5: Broken Function Level Authorization

- [ ] Admin-only functions are enforced server-side
- [ ] Role hierarchy is consistently applied across all endpoints
- [ ] Horizontal privilege escalation tested (user A accessing user B's admin functions)

**Project-specific example:** Tools like `cancel`, `retry`, and `merge` are admin-level operations. They must require elevated authorization. Gateways must distinguish between user roles (observer, operator, admin) and restrict tool access accordingly.

### API6: Unrestricted Access to Sensitive Business Flows

- [ ] Business-critical flows have anti-automation protections
- [ ] Rate limiting is business-context-aware (not just per-IP)
- [ ] Abuse scenarios are documented in failure modes

**Project-specific example:** The intake pipeline is a sensitive business flow -- automated issue spam could overwhelm the backend. The merge pipeline is another -- automated merge requests must respect confidence gates. A learning loop is a third -- rapid outcome injection could poison policy.

### API7: Server Side Request Forgery (SSRF)

- [ ] All URLs in API requests are validated against allowlists
- [ ] Internal network ranges are blocked for outbound fetches
- [ ] URL scheme is restricted (https only, no file://, no gopher://)

**Project-specific example:** Tracker adapters that fetch from external URLs (GitHub, Jira, Linear, Notion) must validate URLs. Webhook endpoints must not follow redirects to internal services.

### API8: Security Misconfiguration

- [ ] CORS is restrictive
- [ ] Error responses do not leak implementation details
- [ ] TLS enforced on all external-facing endpoints
- [ ] Unnecessary HTTP methods disabled
- [ ] Debug/development endpoints disabled in production

**Project-specific example:** Internal API servers must not expose error traces. Gateways must enforce TLS. Docker deployments must harden port exposure. Health endpoints (`/healthz`, `/readyz`) must not leak internal state.

### API9: Improper Inventory Management

- [ ] All API endpoints are documented
- [ ] Deprecated endpoints are removed (not just hidden)
- [ ] API versioning exists
- [ ] No shadow APIs (undocumented endpoints)

**Project-specific example:** Tools must be registered in a single catalog (e.g., `src/mcp/tools.py`). No endpoint should exist outside the registration system. The gateway tool catalog must match the backend's actual capabilities.

### API10: Unsafe Consumption of APIs

- [ ] Third-party API responses are validated and sanitized
- [ ] TLS is enforced for all outbound API calls
- [ ] Fallback behavior exists for third-party API failures
- [ ] Third-party API data is never trusted more than user input

**Project-specific example:** GitHub API responses, LLM API responses, and tracker API responses are all third-party data. HTTP clients must validate TLS. JSON responses must be schema-validated. An LLM call pattern with deterministic fallback is the mitigation for LLM API failures.

## Output Contract

```json
{
  "task_id": "string",
  "api_threat_assessment": {
    "API1_bola": { "risk": "HIGH|MEDIUM|LOW|N/A", "endpoints": [], "findings": [], "mitigations": [] },
    "API2_auth": { "...": "..." },
    "API3_property_authz": { "...": "..." },
    "API4_resource_consumption": { "...": "..." },
    "API5_function_authz": { "...": "..." },
    "API6_business_flow": { "...": "..." },
    "API7_ssrf": { "...": "..." },
    "API8_misconfiguration": { "...": "..." },
    "API9_inventory": { "...": "..." },
    "API10_unsafe_consumption": { "...": "..." }
  },
  "overall_risk": "HIGH|MEDIUM|LOW",
  "blocking_findings": [],
  "advisory_findings": []
}
```

## Quality Gates

- API1 (BOLA) and API2 (Auth) are applicable to every endpoint — never mark N/A for tasks that touch APIs
- API4 (Resource Consumption) is always applicable for LLM-backed endpoints
- HIGH risk findings block merge

## Framework Hardening Addendum

- **Contract versioning:** Require `contract_version` on request/response payloads; enforce compatibility before execution.
- **Schema validation:** Validate findings output against `docs/schemas/security-assessment.schema.json` and fail closed on mismatch.
- **Structured errors:** Return typed failure payloads (`schema_mismatch`, `unsupported_version`, `missing_context`) rather than partial assessments.
- **Read-only guarantee:** This skill is assessment-only and must not mutate downstream systems.

