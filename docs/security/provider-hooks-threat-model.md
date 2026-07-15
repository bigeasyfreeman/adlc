# Provider Hooks Threat Model

## Scope and Security Claim

ADLC can render an optional provider-native `SessionStart` hook for Claude Code and Codex. The hook performs one deterministic, read-only managed-bundle integrity check after ADLC action admission. Hooks are disabled by default, make no model calls, request no new permissions, and do not establish that a provider invoked or obeyed the hook.

## Trust Boundaries

1. The operator trusts the local ADLC package and explicitly installed provider bundle.
2. The provider supplies event JSON and launches the configured local process with the user's permissions. Provider input is untrusted.
3. ADLC owns only the paths listed and digested in the provider install manifest.
4. ADLC action admission is authoritative for the tool, action, phase, side-effect profile, and tier.
5. Provider-native trust remains separate. Codex project hooks require the provider's project trust/review flow; ADLC consent cannot bypass it. Claude Code applies its own settings precedence and hook controls.

## Supported Mapping

| Native event | ADLC event | Fixed action | Tier | Side effects |
| --- | --- | --- | --- | --- |
| `SessionStart` | `session_start` | `adlc-provider-hook-doctor:verify_managed_bundle` | `unrestricted` | `read_only` |

The canonical definition is an immutable argument tuple. Claude Code receives its native executable-plus-arguments form. Codex currently accepts a command string, so ADLC renders the already-fixed argument vector with shell quoting; no provider value is interpolated into it.

## Threats and Controls

| Threat | Control | Failure behavior |
| --- | --- | --- |
| Hooks enabled without informed consent | Plan is read-only and displays paths/digests; enable requires its exact deterministic consent hash | No files written |
| Unmanaged config overwritten | Existing file, final symlink, or symlink ancestor is rejected | Collision remains untouched |
| Shell injection through event content, workspace, or path | Event content is data only; workspace must be the exact absolute installed target; execution uses a fixed argument vector | Input rejected before admission |
| Permission bypass | Every definition names a registry tool/action and calls action admission before subprocess execution | Denied/escalated actions never execute |
| Malicious or oversized provider input | UTF-8 JSON object only, bounded to 64 KiB, exact native event and workspace validation | Visible `invalid_input` failure |
| Hanging command | Five-second subprocess timeout | Visible `timeout` failure |
| Secret-bearing diagnostic output | Output is capped and token/password/secret/API-key/Bearer patterns are redacted | Only bounded redacted detail returned |
| Hook or admission-registry tampering | Manifest records every hook artifact digest; doctor, disable, update, and uninstall validate them | Destructive lifecycle operation refused |
| Partial lifecycle mutation | Enable rolls back created files on failure; disable tombstones files until manifest update succeeds | Prior managed state restored where possible |
| Provider trust confusion | Documentation and plan warning state that hooks run with user permissions and provider trust is separate | Operator must complete provider-native review |
| Capability creep | Supported events are an explicit closed mapping; current command is read-only, offline, and model-free | Unknown event/provider rejected |

## Residual Risks and Limitations

- A compromised local ADLC installation or Python interpreter is outside this control's trust boundary.
- Providers execute hooks with the user's permissions; OS sandboxing and provider-native policy remain the outer controls.
- Redaction is defense in depth, not a guarantee for every possible secret encoding. The command is intentionally designed not to read or emit secrets.
- A hostile process racing filesystem checks with path replacement may exceed application-level protections; operators should not install into an attacker-writable workspace.
- Codex command-hook syntax currently uses a reviewed command string because that provider surface does not expose a native argument array. ADLC keeps its source definition as an argument tuple and quotes the fixed rendering.
- Hook success proves only that ADLC admission and the local integrity check passed at that time. It does not prove later provider behavior or full runtime correctness.

## Security Review Checklist

- Hooks remain disabled on install and update unless already explicitly enabled.
- Plan and enable consent references match exactly.
- No event value reaches command construction.
- All commands have action-admission mappings.
- Renderer performs no writes or subprocess execution.
- Timeout, denial, redaction, malicious input, collision, symlink, drift, disable, and uninstall tests pass.
- No unresolved high- or critical-severity finding remains before merge.
