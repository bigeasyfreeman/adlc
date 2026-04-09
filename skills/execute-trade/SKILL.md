---
name: execute-trade
description: "Orchestration skill for Ratatosk trade execution. Thesis → Council → Risk Check → Execute → Audit → Report. End-to-end trade lifecycle."
---

# Execute Trade (Orchestration — Ratatosk)

## Overview

Chains the ADLC Build Loop adapted for investment operations. From market signal to executed trade with full audit trail.

## When to Use

- Ratatosk has identified a trade opportunity
- Trade thesis is ready for evaluation
- End-to-end trade execution pipeline

## The Sequence

```
Step 1: Trade Thesis (structured from market signal)
Step 2: STRIDE on trade execution
Step 3: Eval Council (HEAVY — investment-adapted)
Step 4: Risk Gate (HARD — position/drawdown/budget limits)
Step 5: Execute Trade (exchange API)
Step 6: Audit Log
Step 7: Stop Slop on report
Step 8: Report (Telegram)
Step 9: Feedback capture (post-settlement)
```

### Step 1: Trade Thesis
- **Skill:** `trade-thesis` (Ratatosk domain PRD)
- Structure signal into: market context, conviction rationale (quantified), risk parameters, exit criteria, position sizing
- Reject ambiguous signals (no vague directional calls)

### Step 2: Security Review
- **Skill:** `security-review` (STRIDE mode — trade execution)
- Spoofing: order spoofing, fake signals
- Tampering: parameter modification
- Repudiation: decision audit trail
- Info Disclosure: API key/position exposure
- DoS: exchange rate limiting
- Elevation: unauthorized mode escalation

### Step 3: Eval Council — Full
- **Skill:** `eval-council` (HEAVY — 6 investment-adapted personas)
- Architect (Portfolio Strategy): Portfolio fit, correlation risk, concentration
- Skeptic (Bearish Thesis): Bear case, thesis inversion, what if wrong?
- Operator (Execution Feasibility): Liquidity, slippage, timing, market hours
- Executioner (Agent Capability): All parameters specified? Can agent execute?
- Security Auditor (Funds Safety): API exposure, position sanity, mode authorization
- First Principles (Thesis Soundness): Data-driven? Edge identified? Sound reasoning?

### Step 4: Risk Gate (HARD)
This is a non-negotiable automated gate. No human override for limit breaches.

| Check | Limit | Action on Breach |
|-------|-------|-----------------|
| Position size | Per-strategy max | BLOCK trade |
| Portfolio concentration | Max % in single asset | BLOCK trade |
| Daily drawdown | Max daily loss limit | BLOCK all trading |
| Budget | Remaining budget check | BLOCK trade |
| Calibration | Strategy calibration score | Reduce size or BLOCK |

### Step 5: Execute Trade
- Place order via exchange API
- Capture: order ID, entry price, size, timing, exchange, order type
- Set exit criteria (stop loss, take profit, time-based exit)

### Step 6: Audit Log
Full structured audit entry:
```json
{
  "pipeline_run_id": "uuid",
  "trade_id": "...",
  "thesis_summary": "...",
  "council_verdict": "approved",
  "risk_gate": "passed",
  "entry": { "price": 0, "size": 0, "time": "ISO8601", "exchange": "..." },
  "exit_criteria": { "stop_loss": 0, "take_profit": 0, "time_exit": "ISO8601" },
  "stride_summary": "...",
  "calibration_score": 0
}
```

### Step 7: Stop Slop
- **Skill:** `stop-slop` (content mode on trade summary)
- Score the trade report on 5 dimensions
- Threshold: 35/50

### Step 8: Report
- Deliver via Telegram
- Include: trade summary, thesis, risk parameters, council verdict

### Step 9: Feedback Capture (Post-Settlement)
- After trade settles: predicted P&L vs actual
- Classify: thesis error, timing error, sizing error, execution error
- Feed into calibration and experiment loop
- Update signal weighting based on outcome

## Escalation

| Trigger | Action |
|---------|--------|
| Risk limit breach | Immediate notification to Eric |
| Council BLOCKED verdict | Trade cancelled, thesis logged for review |
| Execution failure | Fix loop triggered, position check initiated |
| Loss exceeds 2x expected | Post-mortem triggered, calibration review |
