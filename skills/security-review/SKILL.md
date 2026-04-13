---
name: security-review
description: "Security analysis with applicability-aware activation: STRIDE threat modeling only when the task introduces attack surface, trust-boundary, auth, data, or external-integration change; OWASP Top 10 vulnerability scanning per-diff post-execution (Phase 5)."
---

# Security Review

## Overview

Every task gets a security decision. Active security surfaces get a STRIDE overlay; inactive surfaces get an explicit `not_applicable` reason. This is not optional, not a separate review — it is baked into the ADLC pipeline at two critical points.

## When to Use

- **STRIDE mode:** Phase 1 (Build Brief) — threat model tasks whose applicability manifest marks security active
- **OWASP mode:** Phase 5 (Post-Execution) — scan diffs that touch executable code, dependencies, or security-sensitive config before merge
- **Manual:** Any time security posture of a change needs evaluation
- **Fix Loop:** Security fixes auto-elevate to Critical risk tier

## Applicability Gate

Before generating a STRIDE table, record the security applicability decision:

| Field | Purpose |
|-------|---------|
| `security_applicability.status` | `active` or `not_applicable` |
| `security_applicability.reason` | Concrete reason tied to task class or repo evidence |
| `security_applicability.trigger_fields` | Which manifest fields activated or suppressed the overlay |
| `security_applicability.manifest_ref` | Pointer to the upstream applicability manifest entry |

If the status is `not_applicable`, do not invent a STRIDE table. Record the suppression and move on.

## Mode 1: STRIDE Threat Modeling

Run during brief generation when the security overlay is active. Per task, analyze all six STRIDE categories:

| Threat | Key Question | What to Look For |
|--------|-------------|-----------------|
| **S**poofing | Can an attacker impersonate a legitimate actor? | Missing auth, weak identity verification, token theft vectors |
| **T**ampering | Can data be modified in transit or at rest? | Missing integrity checks, unsigned data, mutable shared state |
| **R**epudiation | Can actions be denied without evidence? | Missing audit logging, unsigned transactions, no correlation IDs |
| **I**nformation Disclosure | Can sensitive data leak? | PII in logs, verbose errors, missing encryption, exposed internals |
| **D**enial of Service | Can availability be degraded? | Missing rate limiting, unbounded queries, resource exhaustion paths |
| **E**levation of Privilege | Can an actor gain unauthorized access? | Missing authz checks, privilege escalation, role confusion |

### Risk Rating Scale

| Rating | Definition | Action |
|--------|-----------|--------|
| **Low** | Minimal impact, unlikely exploitation | Document, address in future work |
| **Medium** | Moderate impact or moderate likelihood | Mitigate in this task |
| **High** | Significant impact or high likelihood | Must mitigate before execution. Blocks pipeline. |
| **Critical** | Data breach, full compromise, or safety risk | Blocks pipeline. Requires human review. |

### Output Format

Per task in the brief:

```markdown
### STRIDE Threat Model — [Task Title]

| Threat | Analysis | Risk | Mitigation Required |
|--------|----------|------|-------------------|
| Spoofing | [analysis] | L/M/H/C | [mitigation or N/A] |
| Tampering | [analysis] | L/M/H/C | [mitigation or N/A] |
| Repudiation | [analysis] | L/M/H/C | [mitigation or N/A] |
| Information Disclosure | [analysis] | L/M/H/C | [mitigation or N/A] |
| Denial of Service | [analysis] | L/M/H/C | [mitigation or N/A] |
| Elevation of Privilege | [analysis] | L/M/H/C | [mitigation or N/A] |
```

Mitigations marked "Required" become the **Security Contract** in the codegen context — the executor MUST implement them.

### Domain Adaptation

**SWElfare (Software Engineering):**
- Spoofing: auth bypass, session hijacking, API key impersonation
- Tampering: input mutation, SQL injection, request forgery
- Repudiation: missing audit logs, unsigned commits
- Info Disclosure: PII in logs, stack traces in responses, hardcoded secrets
- DoS: unbounded pagination, missing rate limits, resource-intensive queries
- Elevation: missing RBAC checks, privilege escalation via API

**Ratatosk (Investment Operations):**
- Spoofing: order spoofing, fake market signals, impersonated data feeds
- Tampering: position size tampering, limit modification, order parameter injection
- Repudiation: trade decision denial, missing trade rationale logging
- Info Disclosure: API key leakage, position disclosure, strategy leakage
- DoS: exchange rate limiting, data feed outages, compute exhaustion during experiments
- Elevation: unauthorized autonomous mode escalation, bypassing risk gates

**Magnus (Content Operations):**
- Spoofing: voice impersonation, unauthorized brand representation
- Tampering: content tampering post-draft, unauthorized editorial changes
- Repudiation: authorship denial, attribution issues
- Info Disclosure: PII in content, confidential business info, client details
- DoS: publish flooding, platform rate limits, API abuse
- Elevation: unauthorized tone override, bypassing editorial controls, slop gate bypass

## Mode 2: OWASP Top 10 Scanning

Run on every diff at Phase 5 (Post-Execution Quality Gate).

| # | Vulnerability | Detection Patterns |
|---|--------------|-------------------|
| A01 | Broken Access Control | Missing auth decorators near routes, direct object references without ownership check, missing RBAC |
| A02 | Cryptographic Failures | md5/sha1 usage, hardcoded secrets (API_KEY=, SECRET=, PASSWORD= in literals), missing encryption at rest |
| A03 | Injection | f-strings/%-format in SQL, os.system/subprocess with string concat, eval/exec, template injection |
| A04 | Insecure Design | Missing rate limiting on endpoints, no trust boundary validation, missing input size limits |
| A05 | Security Misconfiguration | DEBUG=True in production, verbose error responses, default credentials, unnecessary features enabled |
| A06 | Vulnerable Components | Known CVEs in dependencies (requires external scanning tool integration) |
| A07 | Auth Failures | Hardcoded passwords, missing password complexity, weak session management, missing MFA |
| A08 | Data Integrity Failures | pickle.loads, yaml.load without SafeLoader, missing signature verification, insecure deserialization |
| A09 | Logging Failures | except blocks without logging, missing security event logging, insufficient audit trail |
| A10 | SSRF | requests.get/post with user-controlled URLs, unvalidated redirect targets, internal network access |

### Severity Classification

| Severity | Definition | Pipeline Action |
|----------|-----------|----------------|
| **Info** | Best practice suggestion | Log, no block |
| **Low** | Minor issue, limited exploitability | Log, no block |
| **Medium** | Moderate risk, requires attention | Log, flag for review |
| **High** | Significant vulnerability | **BLOCKS pipeline** |
| **Critical** | Active exploitation risk, data breach potential | **BLOCKS pipeline**, requires human review |

### Output Format

```json
{
  "findings": [
    {
      "category": "A03",
      "category_name": "Injection",
      "severity": "high",
      "file_path": "src/api/users.py",
      "line_number": 42,
      "description": "SQL query constructed with f-string using user input",
      "remediation": "Use parameterized queries via SQLAlchemy or psycopg2 params"
    }
  ],
  "has_blocking_findings": true,
  "severity_level": "high",
  "summary": "OWASP scan: 1 high finding(s)."
}
```

## Common Rationalizations

| Excuse | Rebuttal |
|--------|---------|
| "This is an internal API, no one will attack it" | Internal APIs get compromised via lateral movement. STRIDE applies regardless. |
| "We'll add auth later" | Auth is structural. Retrofitting it is 10x harder and 100x riskier. |
| "The input is trusted" | Trust boundaries must be explicit and documented. If it crosses a boundary, validate. |
| "It's just a prototype" | Prototypes become production. Security debt compounds faster than tech debt. |
| "STRIDE is overkill for this change" | The analysis takes 2 minutes. A breach costs months. Always analyze. |

## Verification

- [ ] Every security-active task has a STRIDE threat model with all 6 categories analyzed
- [ ] Every High/Critical threat has a documented mitigation
- [ ] Mitigations are specific (not "add authentication" — specify WHERE and HOW)
- [ ] Security Auditor council persona has reviewed the threat model
- [ ] OWASP scan ran on the diff with zero High/Critical findings
- [ ] Security-specific tests exist for each STRIDE mitigation (TDD integration)
