# Permission Tiers Spec

## Tiers
- `unrestricted`: read-only tools (research, evidence lookup, baseline pulls)
- `requires_approval`: mutating non-destructive actions (JIRA create, Confluence create, scaffold writes, git branch)
- `requires_escalation`: destructive/high-risk actions (deploy to production, irreversible migrations, flag kill-switches)

## Decision Flow
1. Resolve tool tier from registry metadata.
2. Apply policy for current phase and actor.
3. If unresolved Type 1 decision exists, block mutating/destructive actions.
4. Persist decision in permission logs and audit trail.

## Minimum Enforcement
- no tier metadata => deny tool
- no decision record => deny execution
- escalation approvals must include approver identity and rationale

## Provider Hooks

Provider hooks are an opt-in transport for a small set of ADLC actions; they are not a separate permission system.

- A managed provider installation starts with hooks disabled.
- `adlc-skill hooks-plan` renders the exact files and content digests without writing them.
- `adlc-skill hooks-enable` requires the exact `sha256:` consent reference from that plan. Consent to one rendered diff does not authorize a later or different diff.
- Each supported native event maps to one fixed argument vector, one registered tool/action pair, and one permission tier. Provider input never becomes a command, argument, path, tier, or action.
- The hook runner calls action admission before execution. A denied or escalated decision stops the command.
- The initial `SessionStart` hook is `read_only` and `unrestricted`; it only runs the managed-bundle integrity doctor with a bounded timeout and redacted output.
- Hook enablement does not grant mutation, destructive access, model calls, network access, or any permission beyond the invoking user's existing provider process.
- ADLC consent does not replace provider-native project trust. Codex may require a separate project-hook trust review, and Claude Code applies its own settings and hook policy.
- `adlc-skill hooks-disable` and uninstall remove only digest-matching ADLC-owned files. Drift or unmanaged collisions fail closed.

See [Provider Hooks Threat Model](../security/provider-hooks-threat-model.md) for trust boundaries and abuse cases.
