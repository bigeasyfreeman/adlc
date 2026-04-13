---
name: observability-contract
description: "Logging mandate with applicability-aware activation: structured error, audit, and general logging are required only when the task introduces a runtime path, service boundary, or user-facing operation. Triggers at Phase 1 (specification) and Phase 5 (verification)."
---

# Observability Contract

## Overview

Every feature or change with an active observability surface must include structured logging. This is a mandatory deliverable for those tasks, not an afterthought. If it's not logged, it didn't happen.

## When to Use

- **Phase 1 (specification):** Generate observability contract per task when the applicability manifest marks a runtime or user-facing surface active
- **Phase 5 (verification):** Verify logging is present per active contract — AST scan for required log statements
- **Manual:** When auditing observability coverage of existing code

## Applicability Contract

Before generating the logging contract, record the observability applicability decision:

| Field | Purpose |
|-------|---------|
| `observability_applicability.status` | `active` or `not_applicable` |
| `observability_applicability.reason` | Concrete reason tied to task class or repo evidence |
| `observability_applicability.trigger_fields` | Which manifest fields activated or suppressed the overlay |
| `observability_applicability.manifest_ref` | Pointer to the upstream applicability manifest entry |

If the status is `not_applicable`, do not invent error, audit, or general logging requirements for that task. Record the suppression and move on.

## The Three Log Types

All three are mandatory for every active observability task.

### Error Logging

**What:** Exception context at every failure point.

**Required fields:**
- Exception type and message
- Stack trace
- Input state that caused the failure
- Correlation ID (for tracing across services)
- Upstream caller context
- Timestamp (ISO8601)

**Format:** Structured JSON, ERROR level.

**Rule:** Every public function that can fail MUST have error logging.

```python
# GOOD
try:
    result = process_order(order_id)
except ProcessingError as e:
    logger.error(
        "order.processing_failed",
        extra={
            "order_id": order_id,
            "error": str(e),
            "correlation_id": ctx.correlation_id,
            "input_state": {"status": order.status, "amount": order.amount},
        },
        exc_info=True,
    )
    raise

# BAD — silent failure
try:
    result = process_order(order_id)
except ProcessingError:
    pass
```

### Audit Logging

**What:** State changes — who did what, when, and what changed.

**Required fields:**
- Actor (who or what triggered the change)
- Action (what changed)
- Timestamp (ISO8601)
- From-state (previous value)
- To-state (new value)
- Correlation ID

**Format:** Structured JSON, INFO level. **Immutable append-only.**

**Rule:** Every state mutation MUST have an audit log entry.

```python
# GOOD
logger.info(
    "order.status_changed",
    extra={
        "order_id": order_id,
        "actor": current_user.id,
        "from_state": "pending",
        "to_state": "approved",
        "correlation_id": ctx.correlation_id,
    },
)

# BAD — state changed with no record
order.status = "approved"
db.commit()
```

### General Logging

**What:** Operational metrics, health signals, debug breadcrumbs.

**Required fields:**
- Metric name or signal type
- Value
- Timestamp
- Context (what was happening)

**Format:** Structured JSON, configurable level (DEBUG/INFO).

**Rule:** Every external API call MUST log request/response metadata (NOT bodies — PII risk). Health-critical operations MUST log timing.

```python
# GOOD
start = time.monotonic()
response = httpx.get(url, headers=headers)
logger.info(
    "external_api.call",
    extra={
        "url": url,
        "method": "GET",
        "status_code": response.status_code,
        "duration_ms": (time.monotonic() - start) * 1000,
        "correlation_id": ctx.correlation_id,
    },
)
```

## Correlation IDs

Correlation IDs MUST propagate across service boundaries. Every request gets a correlation ID at the entry point. All downstream calls include it. All log entries include it.

This enables: tracing a single request through the entire system, linking error logs to audit logs to general logs.

## Pipeline Observability

The ADLC pipeline itself emits structured audit logs at every phase. This pipeline-level observability is separate from task-level overlay activation:

```json
{
  "pipeline_run_id": "uuid",
  "phase": 0,
  "phase_name": "prd_agent",
  "started_at": "ISO8601",
  "completed_at": "ISO8601",
  "duration_ms": 1234,
  "tokens_consumed": 5678,
  "outcome": "success",
  "details": {},
  "errors": []
}
```

## Verification (Phase 5)

AST-based scan checks:
- [ ] Error logging present at all try/except blocks for active observability tasks
- [ ] Audit logging present at all state mutation points for active observability tasks
- [ ] External API calls have request/response logging for active observability tasks
- [ ] Correlation IDs propagated (present in log calls)
- [ ] Log format is structured JSON (not print statements or unstructured strings)
- [ ] No PII in log payloads (no request/response bodies, no user data)

## Domain Adaptation

**SWElfare:** Error=daemon failures/API errors, Audit=job state changes/config changes, General=phase timing/token usage/health checks

**Ratatosk:** Error=trade execution failures/data feed errors, Audit=trade decisions/position changes/calibration updates, General=market data freshness/API latency/experiment metrics

**Magnus:** Error=publish failures/API errors, Audit=editorial decisions/content state changes/voice profile updates, General=engagement metrics/slop scores/pipeline throughput

## Common Rationalizations

| Excuse | Rebuttal |
|--------|---------|
| "Logging adds overhead" | Structured logging overhead is microseconds. Debugging without logs costs hours. |
| "We'll add logging when something breaks" | By then you've lost the context you need to diagnose it. |
| "The error message is enough" | Error messages without context (input state, correlation ID) are nearly useless. |
| "Audit logs are only for compliance" | Audit logs are how you understand what your system actually did. |
