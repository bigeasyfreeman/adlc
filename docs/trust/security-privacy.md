# Security and privacy

ADLC constrains agent actions; it is not a security certification.

## Boundaries

- Tool actions pass deterministic admission before mutation.
- Review, status, and doctor are read-only contracts.
- External writes, privileged access, destructive recovery, publish, merge, release, deploy, and paid execution require explicit approval.
- Provider hooks are opt-in, least-privilege, fail-closed, locally logged, and bounded by the [hook threat model](https://github.com/bigeasyfreeman/adlc/blob/v0.9.1/docs/security/provider-hooks-threat-model.md).
- Credentials stay in provider-approved local stores or environment variables and must not enter Git, prompts, reports, or examples.
- Telemetry is off by default. ADLC does not require a hosted control plane.

## Data handling

Target-repository content is read locally by ADLC and may be sent to the coding-agent provider selected by the operator. Provider retention, model training, regional processing, and account controls are outside ADLC; review those terms before use with sensitive code. Redact evidence before publication.

Report vulnerabilities privately through the [security policy](https://github.com/bigeasyfreeman/adlc/blob/v0.9.1/SECURITY.md).

`doc_honesty_section`: These are design and validation boundaries, not proof that ADLC or a provider is vulnerability-free.

`no_overclaim`: ADLC does not claim compliance certification, sandbox completeness, or universal prompt-injection resistance.

`limitations`: Operator credentials, provider infrastructure, target dependencies, and deployment environments remain external trust domains.
