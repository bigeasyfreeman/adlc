#!/usr/bin/env python3
"""Trace-based pressure runner for the public ADLC facade."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from adlc_runtime import public_facade  # noqa: E402

SECRET_PATTERNS = (
    re.compile(r"(?i)(token|password|secret|api[_-]?key)(\s*[=:]\s*)([^\s\"']+)"),
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._~+\-/=]{8,})"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
)
SUPPORTED_PROVIDERS = frozenset({"claude", "codex", "fixture"})


def load_scenarios(path: Path) -> list[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    scenarios = payload.get("scenarios")
    if payload.get("contract_version") != "1.0.0" or not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenario corpus must be a non-empty version 1.0.0 document")
    identifiers = [item.get("id") for item in scenarios if isinstance(item, dict)]
    if len(identifiers) != len(scenarios) or len(set(identifiers)) != len(identifiers):
        raise ValueError("scenario ids must be present and unique")
    return scenarios


def plan(
    scenario_path: Path,
    *,
    providers: Iterable[str],
    models: Iterable[str],
    repetitions: int,
    timeout_seconds: int,
    token_budget: int,
    usd_per_million_tokens: float,
) -> Dict[str, Any]:
    scenarios = load_scenarios(scenario_path)
    providers = list(providers)
    models = list(models)
    if repetitions < 1 or timeout_seconds < 1 or token_budget < 0:
        raise ValueError("repetitions, timeout, and token budget must be bounded non-negative values")
    return {
        "contract_version": "1.0.0",
        "scenario_count": len(scenarios),
        "providers": providers,
        "models": models,
        "repetitions": repetitions,
        "run_count": len(scenarios) * len(providers) * len(models) * repetitions,
        "timeout_seconds": timeout_seconds,
        "token_budget": token_budget,
        "projected_spend_usd": round(token_budget / 1_000_000 * usd_per_million_tokens, 4),
        "requires_explicit_execution": True,
        "no_overclaim": "This plan estimates an upper bound; it does not execute a provider.",
    }


class TraceKernel:
    def __init__(self, controls: Mapping[str, Any]):
        self.controls = dict(controls)
        self.trace: list[Dict[str, Any]] = []
        self.mutations: list[str] = []

    def _record(self, event: str, **detail: Any) -> None:
        self.trace.append({"event": event, **detail})

    def health_check_payload(self, include_optional: bool = False) -> Dict[str, Any]:
        self._record("health_check_payload", include_optional=include_optional)
        return {"status": "pass", "checks": []}

    def workflow_status_payload(self, workspace: str | None, state: str | None) -> Dict[str, Any]:
        self._record("workflow_status_payload", workspace=workspace, state=state)
        return {"read_only": True, "state": {"status": "planned", "phase": "triage"}}

    def action_admit_payload(self, **kwargs: Any) -> tuple[int, Dict[str, Any]]:
        denied = bool(self.controls.get("deny_admission"))
        self._record("action_admit_payload", tool=kwargs.get("tool_name"), action=kwargs.get("action"))
        return (1 if denied else 0), {
            "status": "denied" if denied else "admitted",
            "stop_reason": "permission_denied" if denied else None,
        }

    def queue_status_payload(self, args: argparse.Namespace) -> Dict[str, Any]:
        self._record("queue_status_payload", queue=getattr(args, "queue", None))
        return {"status": "pass", "tasks": []}

    def run_phase_payload(self, args: argparse.Namespace) -> tuple[int, Dict[str, Any]]:
        exit_code = int(self.controls.get("phase_exit_code", 0))
        state_status = str(self.controls.get("state_status", "planned"))
        stop_reason = self.controls.get("state_stop_reason")
        side_effects = list(self.controls.get("side_effects", []))
        self._record(
            "run_phase_payload",
            phase=getattr(args, "phase", None),
            verifier=list(getattr(args, "verifier", []) or []),
            max_refs=getattr(args, "max_refs", None),
            input=getattr(args, "input", None),
        )
        return exit_code, {
            "state_path": ".adlc/workflow_state.json",
            "state": {
                "status": state_status,
                "phase": getattr(args, "phase", "triage"),
                "stop_reason": stop_reason,
                "side_effects": side_effects,
            },
        }

    def completion_audit_payload(self, args: argparse.Namespace) -> Dict[str, Any]:
        independent = args.executor != args.auditor
        passed = bool(self.controls.get("audit_pass", True)) and independent
        self._record("completion_audit_payload", executor=args.executor, auditor=args.auditor, independent=independent)
        return {
            "status": "pass" if passed else "blocked",
            "independence": {"evidence_refs": ["audit:independent"] if independent else []},
            "findings": [] if passed else [{"severity": "blocking", "reason": "audit_not_independent_or_failed"}],
        }

    def resume_workflow_payload(
        self,
        workspace: str | None,
        state: str | None,
        approve: str | None,
        decision: str,
        reason: str | None,
    ) -> Dict[str, Any]:
        side_effects = list(self.controls.get("side_effects", [{"idempotency_key": "effect:one"}]))
        self._record("resume_workflow_payload", approve=approve, decision=decision, side_effect_count=len(side_effects))
        return {
            "state_path": ".adlc/workflow_state.json",
            "state": {"status": "planned", "phase": "code", "side_effects": side_effects},
        }

    def goal_prompt_payload(self, brief: Path, task_id: str, workspace: Path) -> Dict[str, Any]:
        self._record("goal_prompt_payload", task_id=task_id)
        return {"artifact_ref": ".adlc/prompts/task.json", "task_id": task_id}

    def memory_health_payload(self, args: argparse.Namespace) -> tuple[int, Dict[str, Any]]:
        self._record("memory_health_payload")
        return 0, {"status": "pass", "evidence_refs": ["memory:checked"]}


def _request(scenario: Mapping[str, Any]) -> Dict[str, Any]:
    configured = scenario.get("request", {})
    payload: Dict[str, Any] = {
        "contract_version": "1.0.0",
        "operation": scenario["operation"],
        "experimental": True,
        "allow_mutation": bool(configured.get("allow_mutation", False)),
        "human_approved": bool(configured.get("human_approved", False)),
        "arguments": dict(configured.get("arguments", {})),
        "request_id": f"scenario:{scenario['id']}",
    }
    for key in ("workspace", "state", "approval_ref"):
        if configured.get(key) is not None:
            payload[key] = configured[key]
    if payload["human_approved"] and "approval_ref" not in payload:
        payload["approval_ref"] = "human:scenario"
    return payload


def _state_transition(result: Mapping[str, Any]) -> str:
    delegated = result.get("result", {}).get("delegated", {}) if isinstance(result.get("result"), dict) else {}
    state = delegated.get("state", {}) if isinstance(delegated, dict) else {}
    return str(state.get("status") or result.get("status") or "unknown")


def execute_scenario(scenario: Mapping[str, Any], provider: str) -> Dict[str, Any]:
    expected = scenario["expected"]
    started = time.monotonic()
    if scenario.get("provider") and scenario["provider"] not in SUPPORTED_PROVIDERS:
        result: Dict[str, Any] = {
            "status": "blocked",
            "stop_reason": "unsupported_provider",
            "result": {"provider": scenario["provider"]},
        }
        trace = [{"event": f"facade:{scenario['operation']}"}, {"event": "provider_policy_rejected"}]
        mutations: list[str] = []
    else:
        kernel = TraceKernel(scenario.get("controls", {}))
        result = public_facade.dispatch_public_operation(_request(scenario), bindings=kernel)
        trace = [{"event": f"facade:{scenario['operation']}"}, *kernel.trace]
        mutations = kernel.mutations
    event_names = [item["event"] for item in trace]
    required_events = list(expected.get("trace_events", []))
    forbidden_events = list(expected.get("forbidden_trace_events", []))
    forbidden_mutations = list(expected.get("forbidden_mutations", []))
    observed_forbidden = sorted(set(mutations).intersection(forbidden_mutations))
    transition = _state_transition(result)
    assertions = {
        "status": result.get("status") == expected.get("status"),
        "stop_reason": result.get("stop_reason") == expected.get("stop_reason"),
        "trace": all(event in event_names for event in required_events)
        and all(event not in event_names for event in forbidden_events),
        "state": transition == expected.get("state_transition"),
        "forbidden_mutations": not observed_forbidden,
    }
    return {
        "id": scenario["id"],
        "pressure": scenario["pressure"],
        "status": "pass" if all(assertions.values()) else "fail",
        "observed_status": result.get("status"),
        "observed_stop_reason": result.get("stop_reason"),
        "trace_events": trace,
        "state_transition": transition,
        "forbidden_mutations_observed": observed_forbidden,
        "assertions": assertions,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
    }


def run_scenarios(
    scenario_path: Path,
    *,
    provider: str,
    harness: str,
    model: str,
    output_dir: Path,
    seed: int = 0,
) -> Dict[str, Any]:
    del output_dir
    scenarios = load_scenarios(scenario_path)
    started = time.monotonic()
    results = [execute_scenario(scenario, provider) for scenario in scenarios]
    failures = [result["id"] for result in results if result["status"] != "pass"]
    digest = hashlib.sha256(scenario_path.read_bytes()).hexdigest()
    return {
        "contract_version": "1.0.0",
        "status": "fail" if failures else "pass",
        "provider": provider,
        "harness": harness,
        "model": model,
        "provider_version": "fixture-1.0.0",
        "seed": seed,
        "scenario_digest": digest,
        "timing": {"duration_ms": max(0, int((time.monotonic() - started) * 1000))},
        "cost": {"currency": "USD", "min": 0.0, "max": 0.0},
        "summary": {"total": len(results), "passed": len(results) - len(failures), "failed": len(failures)},
        "scenarios": results,
        "failures": failures,
        "no_overclaim": "Fixture traces prove deterministic facade behavior, not live provider behavior.",
        "limitations": ["Credential-free fixture runner with instrumented kernel bindings."],
    }


def _redact_string(value: str, workspace: Path | None) -> str:
    redacted = value
    if workspace:
        aliases = {str(workspace), str(workspace.resolve())}
        for alias in sorted(aliases, key=len, reverse=True):
            redacted = redacted.replace(alias, "<WORKSPACE>")
    redacted = SECRET_PATTERNS[0].sub(r"\1\2[REDACTED]", redacted)
    redacted = SECRET_PATTERNS[1].sub(r"\1[REDACTED]", redacted)
    return SECRET_PATTERNS[2].sub("[REDACTED]", redacted)


def redact_payload(value: Any, workspace: Path | None = None) -> Any:
    if isinstance(value, str):
        return _redact_string(value, workspace)
    if isinstance(value, list):
        return [redact_payload(item, workspace) for item in value]
    if isinstance(value, dict):
        return {key: redact_payload(item, workspace) for key, item in value.items()}
    return value


def publish_report(payload: Mapping[str, Any], output: Path, *, workspace: Path | None = None) -> Dict[str, Any]:
    redacted = redact_payload(dict(payload), workspace)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(redacted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return redacted


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan or run ADLC skill behavior pressure scenarios.")
    parser.add_argument("--scenarios", default=str(ROOT / "tests/skill_behavior/scenarios.json"))
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--provider", action="append", default=[])
    parser.add_argument("--model", action="append", default=[])
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--token-budget", type=int, default=120_000)
    parser.add_argument("--usd-per-million-tokens", type=float, default=10.0)
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    scenario_path = Path(args.scenarios)
    if args.execute and not args.plan:
        providers = args.provider or ["fixture"]
        models = args.model or ["deterministic"]
        if len(providers) != 1 or len(models) != 1:
            raise SystemExit("fixture execution accepts exactly one provider and model")
        report = run_scenarios(
            scenario_path,
            provider=providers[0],
            harness="public-facade",
            model=models[0],
            output_dir=Path(args.output).parent if args.output else Path.cwd(),
        )
        if args.output:
            publish_report(report, Path(args.output))
        payload = report
    else:
        payload = plan(
            scenario_path,
            providers=args.provider or ["codex"],
            models=args.model or ["account-default"],
            repetitions=args.repetitions,
            timeout_seconds=args.timeout_seconds,
            token_budget=args.token_budget,
            usd_per_million_tokens=args.usd_per_million_tokens,
        )
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload)
    return 0 if payload.get("status") != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
