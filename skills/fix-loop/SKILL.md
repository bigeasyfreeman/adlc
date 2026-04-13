---
name: fix-loop
description: "Autonomous error detection and repair pipeline. Runs parallel to Build Loop. Capture → Confirm → Investigate → Fix → Prove → Light Council → Deliver or Escalate."
---

# Fix Loop

## Overview

The Fix Loop runs in parallel with the Build Loop. It watches production for errors and autonomously repairs them. The Architect reviews fixes, not triages bugs.

## When to Use

- **Always running:** Monitors production/runtime continuously
- **Manual trigger:** When a specific error needs investigation
- **Fix Loop orchestration skill** chains this with TDD and council

## The Pipeline

```
Capture → Confirm → Investigate → Fix → Prove → [LIGHT COUNCIL] → Deliver PR
                                    ↑                                |
                                    └── Retry (max 3) ──────────────┘
                                                                     |
                                    Escalate (if 3 fails) ←─────────┘
```

### Step 1: Capture

Monitor for errors with full context:

| Source | What to Capture |
|--------|----------------|
| Error monitoring | Exceptions: type, message, stack trace, correlation ID |
| Health checks | Degraded/failed endpoints with response details |
| Test regressions | Tests that previously passed now failing |
| Performance anomalies | Latency spikes, throughput drops with timing data |
| Security alerts | Dependency vulnerabilities, suspicious access patterns |

**Domain adaptation:**
- **SWElfare:** Production errors, daemon failures, test regressions, CI failures
- **Ratatosk:** Trade execution failures, data feed errors, risk limit breaches, calibration drift
- **Magnus:** Publish failures, engagement anomalies, slop gate failures, platform API errors

### Step 2: Confirm

Filter noise from signal:

- **Deduplicate:** By error pattern (hash of normalized stack trace), not line number
- **Transient filter:** 1 occurrence = noise. 5 in 1 hour (configurable) = confirmed bug
- **External filter:** Errors from external dependencies (API outages, network) — logged, not investigated
- **Severity classify:** Critical (data loss/security/outage) / High (partial outage) / Medium (broken, workaround exists) / Low (cosmetic)

### Step 3: Investigate

Root cause analysis with codebase context:

1. Trace the call chain from error to origin
2. Check `git blame` and recent changes for related code
3. Build root cause hypothesis
4. Identify the minimal fix scope
5. Run STRIDE on the proposed fix (does the fix introduce new security concerns?)

### Step 4: Fix

Write the fix in isolation:

1. Create isolated worktree
2. Establish the primary verifier for the failure class:
   - existing bug: failing reproducer
   - build/CI regression: failing command or check
   - missing runtime behavior: focused behavioral test
3. Confirm the primary verifier fails before the fix
4. Write the minimal fix to make the primary verifier pass
5. Run the targeted regression suite and the relevant full validation set
6. Run linters (**LDD gate**)
7. Run security review only if the fix changes attack surface, auth, data handling, or external integrations
8. Run observability review only if the fix changes runtime paths, user-facing operations, or declared logging/alerting contracts

**If fix doesn't pass:** Retry with enriched context (failure reason from previous attempt). Max 3 retries.

### Step 5: Prove

Evidence package:
- Primary verifier evidence (fails before, passes after)
- Relevant regression and validation results
- Before/after comparison
- Root cause analysis document
- Overlay evidence when active (security, observability, performance)

### Step 6: Light Council

3 personas review (not full 6 — this is a fix, not a feature):

| Persona | Focus |
|---------|-------|
| **Skeptic** | Does this fix the root cause, or just the symptom? |
| **Operator** | Is the fix safe to deploy? Rollback plan? |
| **Security Auditor** | Does the fix introduce new security issues? |

Verdicts: APPROVED / REVISION REQUIRED (retry) / ESCALATE (human needed)

### Step 7: Deliver

PR with:
- Reproduction steps
- Root cause analysis
- Fix explanation
- Test evidence (reproduction test + full suite)
- Council verdict
- Severity classification
- Link to original error/alert

### Step 8: Escalate

If 3 fix attempts fail, create detailed issue with:
- Everything learned during investigation
- Root cause hypotheses tested and results
- Suggested next steps for human investigation
- Severity and impact assessment

## Configuration

```yaml
adlc:
  fix_loop:
    enabled: true
    confirmation_threshold: 5    # errors in window = confirmed
    confirmation_window_hours: 1
    max_fix_attempts: 3
    auto_escalate: true
    council_weight: light        # skeptic + operator + security_auditor
    security_auto_elevate: true  # security fixes → Critical risk tier
```

## Exit Criteria

- [ ] Root cause identified and documented
- [ ] Reproduction test exists and fails without fix
- [ ] Fix passes all tests + linters + security scan
- [ ] Light council approved
- [ ] PR delivered with full evidence package
- [ ] Pipeline audit log entry created
