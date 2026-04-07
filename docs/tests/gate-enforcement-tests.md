# Gate Enforcement Invariant Tests

## Harness Setup
- Use deterministic brief fixture and deterministic Eval Council verdict fixtures.
- Mock gate inputs/outputs only; do not use live systems.
- Validate gate outcomes through checkpoint progression and terminal stop reasons.

## Test Cases
| Test ID | Scenario | Steps (Deterministic Fixture) | Pass Criteria | Fail Criteria |
|---|---|---|---|---|
| GATE-01 | Eval Council FAIL blocks progression | Set `phase_2_eval_council` verdict to FAIL after max revisions. | No checkpoint beyond Phase 2 is created; terminal event uses `stop_reason=council_blocked`. | Pipeline enters Phase 3+ after FAIL verdict. |
| GATE-02 | Deploy gate enforces pre-deploy evidence | Set `phase_12_deploy_gate` input with missing latest council verdict link. | Deploy gate remains closed and run is blocked. | Deploy gate opens without required evidence links. |
| GATE-03 | Engineer review is required before completion | Simulate all machine gates pass but engineer review fixture is `rejected`. | Terminal event uses `stop_reason=engineer_rejected`; no `completed` terminal status. | Pipeline emits `completed` without engineer approval. |
| GATE-04 | Security HIGH finding blocks merge path | Provide Phase 7 security fixture with unresolved HIGH finding. | Gate status remains blocked until finding resolved and rerun passes. | Pipeline proceeds to deploy gate with unresolved HIGH finding. |
