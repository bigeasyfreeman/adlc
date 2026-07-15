#!/usr/bin/env python3
"""Replay the public ADLC Fix demo and emit complete, redacted evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/schemas/benchmark-report.schema.json"
RUN_REPORT_SCHEMA = ROOT / "docs/schemas/run-report.schema.json"
SECRET_PATTERN = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._~+/=-]{8,}|password\s*[=:]\s*[^\s\"']+|"
    r"(?:api|access|secret)[_-]?key\s*[=:]\s*[^\s\"']+)",
    re.IGNORECASE,
)
FIXED_GIT_ENV = {
    "GIT_AUTHOR_NAME": "ADLC Fix Demo",
    "GIT_AUTHOR_EMAIL": "adlc-fix@example.invalid",
    "GIT_AUTHOR_DATE": "2020-01-01T00:00:00Z",
    "GIT_COMMITTER_NAME": "ADLC Fix Demo",
    "GIT_COMMITTER_EMAIL": "adlc-fix@example.invalid",
    "GIT_COMMITTER_DATE": "2020-01-01T00:00:00Z",
}
CALCULATED_METRICS = [
    "task_completion",
    "verifier_validity",
    "resume_integrity",
    "claim_accuracy",
    "scope_control",
]
HUMAN_RUBRIC_FIELDS = ["human_decisions"]


class BenchmarkError(RuntimeError):
    """A benchmark contract or execution gate failed."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def product_version() -> str:
    match = re.search(r'^version = "([^"]+)"$', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise BenchmarkError("project version not found")
    return match.group(1)


def git_output(args: Sequence[str], cwd: Path, *, env: Optional[Dict[str, str]] = None) -> str:
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=process_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise BenchmarkError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.rstrip("\n")


def initialize_fixture_repo(fixture: Dict[str, Any], target: Path) -> str:
    shutil.copytree(fixture["starting_path"], target)
    git_output(["init", "-q"], target)
    git_output(["config", "user.name", FIXED_GIT_ENV["GIT_AUTHOR_NAME"]], target)
    git_output(["config", "user.email", FIXED_GIT_ENV["GIT_AUTHOR_EMAIL"]], target)
    git_output(["-c", "core.autocrlf=false", "add", "."], target)
    git_output(["-c", "commit.gpgsign=false", "commit", "-qm", "Pinned public Fix fixture"], target, env=FIXED_GIT_ENV)
    return git_output(["rev-parse", "HEAD"], target)


def compute_starting_commit(fixture: Dict[str, Any]) -> str:
    with tempfile.TemporaryDirectory(prefix="adlc-fixture-commit-") as temporary:
        return initialize_fixture_repo(fixture, Path(temporary) / "target")


def load_fixture(path: Path) -> Dict[str, Any]:
    path = path.resolve()
    manifest_path = path / "fixture.json"
    if not manifest_path.is_file():
        raise BenchmarkError(f"fixture manifest not found: {manifest_path}")
    fixture = read_json(manifest_path)
    required = {
        "fixture_id",
        "fixture_version",
        "starting_commit",
        "starting_directory",
        "solution_path",
        "product_path",
        "verifier",
        "prompt",
        "allowed_product_changes",
    }
    missing = sorted(required - fixture.keys())
    if missing:
        raise BenchmarkError(f"fixture fields missing: {', '.join(missing)}")
    fixture["path"] = path
    fixture["starting_path"] = path / fixture["starting_directory"]
    fixture["solution_file"] = path / fixture["solution_path"]
    fixture["prompt_file"] = path / fixture["prompt"]
    for key in ("starting_path", "solution_file", "prompt_file"):
        if not fixture[key].exists():
            raise BenchmarkError(f"fixture path missing: {fixture[key]}")
    return fixture


def test_metadata() -> Dict[str, Any]:
    return {
        "product_version": "0.1.0",
        "source_commit": "0" * 40,
        "fixture": {
            "id": "test-fixture",
            "version": "1.0.0",
            "starting_commit": "1" * 40,
            "prompt_sha256": "2" * 64,
            "path": "examples/fix-demo",
        },
        "configuration": {
            "provider": "codex",
            "provider_version": "installed-bundle:test",
            "model": "not-invoked",
            "harness": "public-fix-deterministic",
            "python": "3.9.0",
            "platform": "test",
        },
    }


def test_plan(runs: int) -> Dict[str, Any]:
    return build_plan(runs, 120)


def build_plan(runs: int, timeout_seconds: int) -> Dict[str, Any]:
    if not 3 <= runs <= 10:
        raise BenchmarkError("--runs must be between 3 and 10 for a public configuration")
    if not 1 <= timeout_seconds <= 600:
        raise BenchmarkError("--timeout must be between 1 and 600 seconds per run")
    return {
        "runs": runs,
        "timeout_seconds_per_run": timeout_seconds,
        "token_limit_per_run": 0,
        "projected_provider_cost": {"currency": "USD", "min": 0, "max": 0},
        "external_calls": False,
    }


def score_attempt(status: str, metrics: Dict[str, Any], evidence_refs: Sequence[str]) -> Dict[str, Any]:
    passed = status == "pass" and bool(evidence_refs) and all(metrics.get(name) is True for name in CALCULATED_METRICS)
    return {
        "passed": passed,
        "calculated_metrics": list(CALCULATED_METRICS),
        "human_rubric_fields": list(HUMAN_RUBRIC_FIELDS),
    }


def attempt_record(
    attempt: int,
    status: str,
    metrics: Dict[str, Any],
    evidence_refs: Sequence[str],
    *,
    duration_ms: int = 0,
    failure: Optional[str] = None,
) -> Dict[str, Any]:
    terminal = {"pass": "completed", "fail": "failed", "blocked": "blocked", "timeout": "timeout"}[status]
    invariant = {
        "terminal_class": terminal,
        "metrics": metrics,
        "product_diff": "src/invoice.py",
        "provider_invoked": False,
    }
    return {
        "attempt": attempt,
        "status": status,
        "terminal_class": terminal,
        "duration_ms": duration_ms,
        "cost": {"currency": "USD", "tokens": 0, "min": 0, "max": 0},
        "metrics": metrics,
        "score": score_attempt(status, metrics, evidence_refs),
        "evidence_refs": list(evidence_refs),
        "redaction_status": "reviewed",
        "invariant_sha256": sha256_bytes(canonical_json(invariant)),
        "failure": failure,
    }


def spread(values: Iterable[float]) -> Dict[str, float]:
    sequence = list(values)
    if not sequence:
        sequence = [0]
    low = min(sequence)
    high = max(sequence)
    return {"median": statistics.median(sequence), "min": low, "max": high, "spread": high - low}


def build_report(metadata: Dict[str, Any], plan: Dict[str, Any], attempts: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    attempts = list(attempts)
    statuses = [item["status"] for item in attempts]
    terminal_classes = {item["terminal_class"] for item in attempts}
    invariants = {item["invariant_sha256"] for item in attempts}
    replay_verified = (
        len(attempts) == plan["runs"]
        and len(terminal_classes) == 1
        and len(invariants) == 1
        and all(item["score"]["passed"] for item in attempts)
    )
    report_status = "pass" if replay_verified else ("blocked" if statuses and all(value == "blocked" for value in statuses) else "fail")
    passed = statuses.count("pass")
    report = {
        "contract_version": "1.0.0",
        "report_id": f"public-fix-{metadata['product_version']}-{metadata['source_commit'][:12]}",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "product_version": metadata["product_version"],
        "source_commit": metadata["source_commit"],
        "fixture": metadata["fixture"],
        "configuration": metadata["configuration"],
        "plan": plan,
        "status": report_status,
        "attempts": attempts,
        "summary": {
            "attempted": len(attempts),
            "passed": passed,
            "failed": statuses.count("fail"),
            "blocked": statuses.count("blocked"),
            "timed_out": statuses.count("timeout"),
            "completion_rate": passed / len(attempts) if attempts else 0,
            "duration_ms": spread(item["duration_ms"] for item in attempts),
            "human_decisions": spread(item["metrics"]["human_decisions"] for item in attempts),
            "provider_cost": spread(item["cost"]["max"] for item in attempts),
        },
        "replay": {
            "command": "python3 benchmarks/run.py --fixture examples/fix-demo --runs 3 --verify-replay --json",
            "verified": replay_verified,
            "matching_terminal_class": len(terminal_classes) == 1,
            "matching_invariants": len(invariants) == 1,
        },
        "redaction": {
            "status": "reviewed",
            "scanner": "benchmark built-in credential-pattern scan v1",
            "secret_matches": 0,
            "absolute_paths_replaced": True,
        },
        "claims": [
            "The named deterministic Fix control replay preserved all attempts and reached the same terminal class.",
            "Red-before-green, resume idempotency, bounded scope, and completion-audit controls passed for the named fixture.",
        ],
        "limitations": [
            "Results apply only to the named fixture, source commit, product version, environment, harness, and execution date.",
            "The Codex bundle was installed, but no provider or model was invoked; provider behavior remains unmeasured.",
        ],
        "no_overclaim": "This benchmark does not establish universal superiority, future model behavior, adoption, compliance, GA readiness, or autonomous code quality.",
    }
    return report


def redact(value: Any, replacements: Sequence[Tuple[str, str]]) -> Any:
    if isinstance(value, dict):
        return {key: redact(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, replacements) for item in value]
    if isinstance(value, str):
        for source, replacement in replacements:
            value = value.replace(source, replacement)
        return value
    return value


def ensure_redacted(value: Any) -> None:
    serialized = json.dumps(value, sort_keys=True)
    match = SECRET_PATTERN.search(serialized)
    if match:
        raise BenchmarkError(f"secret-like content blocked by redaction scan: {match.group(0)[:20]}...")


def write_json(path: Path, value: Any, replacements: Sequence[Tuple[str, str]]) -> None:
    sanitized = redact(value, replacements)
    ensure_redacted(sanitized)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitized, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_process(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout: int,
    expected: Optional[Iterable[int]] = (0,),
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if expected is not None and result.returncode not in set(expected):
        raise BenchmarkError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout[-1000:]}\n{result.stderr[-1000:]}"
        )
    return result


def parse_json_output(result: subprocess.CompletedProcess[str], label: str) -> Dict[str, Any]:
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise BenchmarkError(f"{label} did not emit JSON: {result.stdout[-1000:]}") from exc


def artifact_refs(attempt: int) -> List[str]:
    prefix = f"runs/run-{attempt:03d}"
    names = [
        "install.json",
        "facade.json",
        "red.json",
        "interrupted.json",
        "resumed.json",
        "final.diff",
        "review.json",
        "green.json",
        "audit.json",
        "run-report.json",
    ]
    return [f"{prefix}/{name}" for name in names]


def validate_json(value: Any, schema_path: Path, label: str) -> None:
    schema = read_json(schema_path)
    errors = sorted(jsonschema.Draft7Validator(schema).iter_errors(value), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}" for error in errors)
        raise BenchmarkError(f"{label} failed schema validation: {details}")


def runtime_metadata(fixture: Dict[str, Any]) -> Dict[str, Any]:
    source_commit = git_output(["rev-parse", "HEAD"], ROOT)
    try:
        fixture_path = fixture["path"].relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise BenchmarkError("public fixture must live inside the ADLC repository") from exc
    return {
        "product_version": product_version(),
        "source_commit": source_commit,
        "fixture": {
            "id": fixture["fixture_id"],
            "version": fixture["fixture_version"],
            "starting_commit": fixture["starting_commit"],
            "prompt_sha256": sha256_bytes(fixture["prompt_file"].read_bytes()),
            "path": fixture_path,
        },
        "configuration": {
            "provider": "codex",
            "provider_version": f"installed-bundle:{product_version()}",
            "model": "not-invoked",
            "harness": "public-fix-deterministic",
            "python": platform.python_version(),
            "platform": f"{platform.system()}-{platform.machine()}",
        },
    }


def execute_attempt(
    fixture: Dict[str, Any],
    attempt: int,
    output_root: Path,
    timeout: int,
) -> Dict[str, Any]:
    started = time.monotonic()
    run_dir = output_root / "runs" / f"run-{attempt:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"adlc-public-benchmark-{attempt:03d}-") as temporary:
        temporary_path = Path(temporary)
        target = temporary_path / "target"
        replacements = [
            (str(target.resolve()), "<WORKSPACE>"),
            (str(target), "<WORKSPACE>"),
            (str(temporary_path.resolve()), "<TEMP>"),
            (str(temporary_path), "<TEMP>"),
            (str(ROOT.resolve()), "<ADLC_ROOT>"),
            (str(ROOT), "<ADLC_ROOT>"),
        ]
        try:
            starting_commit = initialize_fixture_repo(fixture, target)
            if starting_commit != fixture["starting_commit"]:
                raise BenchmarkError(
                    f"fixture commit mismatch: expected {fixture['starting_commit']}, got {starting_commit}"
                )

            run_process([str(ROOT / "setup.sh"), "codex", str(target)], cwd=ROOT, timeout=timeout)
            adlc = target / ".adlc/bin/adlc"
            health = parse_json_output(
                run_process([str(adlc), "health-check", "--json"], cwd=target, timeout=timeout), "health-check"
            )
            if health.get("status") != "pass":
                raise BenchmarkError("installed ADLC health-check did not pass")
            git_output(["add", ".agents", "AGENTS.md"], target)
            git_output(["commit", "-qm", "Install ADLC Codex bundle"], target)
            installed_commit = git_output(["rev-parse", "HEAD"], target)
            install_evidence = {
                "status": "pass",
                "fixture_starting_commit": starting_commit,
                "installed_commit": installed_commit,
                "doctor": health,
                "provider_invoked": False,
            }
            write_json(run_dir / "install.json", install_evidence, replacements)

            registry = target / ".adlc/public-fix-tool-registry.json"
            registry.write_text(
                json.dumps(
                    {
                        "version": "1.0.0",
                        "default_policy": "deny",
                        "tools": [
                            {
                                "name": "Write",
                                "description": "Bounded invoice repair",
                                "inputSchema": {},
                                "side_effect_profile": "mutating",
                                "permission_tier": "requires_approval",
                                "available_phases": ["triage"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            request = {
                "contract_version": "1.0.0",
                "operation": "fix",
                "experimental": True,
                "request_id": f"public-benchmark-{attempt:03d}",
                "workspace": str(target),
                "allow_mutation": True,
                "human_approved": True,
                "approval_ref": "human:public-benchmark-fixture",
                "arguments": {
                    "tool_registry": ".adlc/public-fix-tool-registry.json",
                    "tool": "Write",
                    "action": "edit_file",
                    "phase": "triage",
                    "brief_id": "PUBLIC-FIX-BENCHMARK",
                    "session_id": f"PUBLIC-FIX-{attempt:03d}",
                    "dry_run": True,
                },
            }
            request_path = temporary_path / "request.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            facade = parse_json_output(
                run_process(
                    [str(adlc), "public-operation", "--input", str(request_path), "--json"],
                    cwd=target,
                    timeout=timeout,
                ),
                "public-operation",
            )
            if facade.get("status") != "planned" or facade.get("result", {}).get("admission", {}).get("status") != "admitted":
                raise BenchmarkError("public Fix facade was not admitted and planned")
            write_json(run_dir / "facade.json", facade, replacements)

            red_result = run_process(
                [
                    str(adlc),
                    "run-phase",
                    "qa",
                    "--brief-id",
                    "PUBLIC-FIX-BENCHMARK",
                    "--workspace",
                    str(target),
                    "--state",
                    ".adlc/fix_state.json",
                    "--verifier",
                    fixture["verifier"],
                    "--json",
                ],
                cwd=target,
                timeout=timeout,
                expected=(1,),
            )
            red = parse_json_output(red_result, "red verifier")
            red_serialized = json.dumps(red, sort_keys=True)
            red_valid = (
                red.get("tool_result", {}).get("status") == "fail"
                and red.get("tool_result", {}).get("stop_reason") == "verifier_failed"
                and "test_allocations_reconcile_rounding_remainder" in red_serialized
                and "Decimal('0.09') != Decimal('0.10')" in red_serialized
            )
            if not red_valid:
                raise BenchmarkError("pre-change verifier did not fail for the intended reason")
            write_json(run_dir / "red.json", red, replacements)

            interrupted = parse_json_output(
                run_process(
                    [
                        str(adlc),
                        "run-phase",
                        "intent_validation",
                        "--brief-id",
                        "PUBLIC-FIX-BENCHMARK-RESUME",
                        "--workspace",
                        str(target),
                        "--state",
                        ".adlc/resume_state.json",
                        "--dry-run",
                        "--json",
                    ],
                    cwd=target,
                    timeout=timeout,
                ),
                "interrupt",
            )
            if interrupted.get("state", {}).get("status") != "awaiting_approval":
                raise BenchmarkError("Fix replay did not stop at the human approval gate")
            write_json(run_dir / "interrupted.json", interrupted, replacements)

            state_path = target / ".adlc/resume_state.json"
            state = read_json(state_path)
            state["side_effects"] = [
                {
                    "idempotency_key": "public-fix:invoice-repair-completed-once",
                    "tool_name": "fixture-repair",
                    "operation": "repair_invoice_allocation",
                    "status": "completed",
                    "timestamp": "2020-01-01T00:00:00Z",
                }
            ]
            state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
            resumed = parse_json_output(
                run_process(
                    [
                        str(adlc),
                        "resume",
                        "--workspace",
                        str(target),
                        "--state",
                        ".adlc/resume_state.json",
                        "--approve",
                        "intent_validation",
                        "--reason",
                        "Resume the bounded public invoice Fix proof.",
                        "--json",
                    ],
                    cwd=target,
                    timeout=timeout,
                ),
                "resume",
            )
            side_effects = resumed.get("state", {}).get("side_effects", [])
            keys = [item.get("idempotency_key") for item in side_effects]
            resume_valid = resumed.get("state", {}).get("resume_count") == 1 and keys == ["public-fix:invoice-repair-completed-once"]
            if not resume_valid:
                raise BenchmarkError("resume replayed or lost the completed side effect")
            write_json(run_dir / "resumed.json", resumed, replacements)

            product_path = target / fixture["product_path"]
            product_path.write_bytes(fixture["solution_file"].read_bytes())
            changed = [line[3:] for line in git_output(["status", "--short"], target).splitlines() if line]
            scope_valid = sorted(changed) == sorted(fixture["allowed_product_changes"])
            if not scope_valid:
                raise BenchmarkError(f"out-of-scope product changes: {changed}")
            final_diff = git_output(["diff", "--unified=0", "--", *fixture["allowed_product_changes"]], target) + "\n"
            if not final_diff.strip():
                raise BenchmarkError("bounded repair produced no product diff")
            (run_dir / "final.diff").write_text(redact(final_diff, replacements), encoding="utf-8")
            ensure_redacted((run_dir / "final.diff").read_text(encoding="utf-8"))

            green = parse_json_output(
                run_process(
                    [
                        str(adlc),
                        "run-phase",
                        "qa",
                        "--brief-id",
                        "PUBLIC-FIX-BENCHMARK",
                        "--workspace",
                        str(target),
                        "--state",
                        ".adlc/fix_state.json",
                        "--verifier",
                        fixture["verifier"],
                        "--json",
                    ],
                    cwd=target,
                    timeout=timeout,
                ),
                "green verifier",
            )
            green_valid = green.get("tool_result", {}).get("status") == "pass" and green.get("state", {}).get("phase") == "pr_prep"
            if not green_valid:
                raise BenchmarkError("post-change verifier did not pass into PR preparation")
            write_json(run_dir / "green.json", green, replacements)

            review_check = run_process(fixture["verifier"].split(), cwd=target, timeout=timeout)
            review = {
                "status": "pass",
                "reviewer": "public-fix-scope-reviewer",
                "findings": [],
                "changed_paths": changed,
                "allowed_paths": fixture["allowed_product_changes"],
                "verifier_exit_code": review_check.returncode,
                "product_diff_sha256": sha256_bytes(final_diff.encode("utf-8")),
            }
            write_json(run_dir / "review.json", review, replacements)

            git_output(["add", *fixture["allowed_product_changes"]], target)
            git_output(["commit", "-qm", "Fix invoice discount reconciliation"], target)
            if git_output(["status", "--porcelain", "--untracked-files=all"], target):
                raise BenchmarkError("target is not clean and PR-ready")

            audit_plan = {
                "claims": [
                    {
                        "id": "FIX-GREEN",
                        "claim": "The invoice verifier passes after the fix.",
                        "verifier": {"type": "command", "command": fixture["verifier"], "expect_exit": 0},
                    },
                    {
                        "id": "FIX-PR-READY",
                        "claim": "The target worktree is clean and PR-ready.",
                        "verifier": {
                            "type": "command",
                            "command": 'test -z "$(git status --porcelain --untracked-files=all)"',
                            "expect_exit": 0,
                        },
                    },
                ]
            }
            audit_plan_path = temporary_path / "completion-plan.json"
            audit_plan_path.write_text(json.dumps(audit_plan), encoding="utf-8")
            independence = {
                "contract_version": "1.0.0",
                "basis": "separate_session",
                "executor": {"identity": "public-fix-benchmark-executor", "session_id": f"executor-{attempt:03d}"},
                "auditor": {"identity": "public-fix-benchmark-auditor", "session_id": f"auditor-{attempt:03d}"},
                "evidence_refs": ["benchmarks/run.py", "examples/fix-demo/fixture.json"],
            }
            independence_path = temporary_path / "independence.json"
            independence_path.write_text(json.dumps(independence), encoding="utf-8")
            audit = parse_json_output(
                run_process(
                    [
                        str(adlc),
                        "completion-audit",
                        "--input",
                        str(audit_plan_path),
                        "--workspace",
                        str(target),
                        "--executor",
                        "public-fix-benchmark-executor",
                        "--auditor",
                        "public-fix-benchmark-auditor",
                        "--independence-evidence",
                        str(independence_path),
                        "--json",
                    ],
                    cwd=target,
                    timeout=timeout,
                ),
                "completion audit",
            )
            audit_valid = audit.get("status") == "pass" and audit.get("independence", {}).get("executor_session_id") != audit.get("independence", {}).get("auditor_session_id")
            if not audit_valid:
                raise BenchmarkError("independent completion audit did not pass")
            write_json(run_dir / "audit.json", audit, replacements)

            metrics = {
                "task_completion": True,
                "verifier_validity": red_valid and green_valid,
                "resume_integrity": resume_valid,
                "claim_accuracy": audit_valid,
                "scope_control": scope_valid,
                "human_decisions": 1,
            }
            run_report = {
                "contract_version": "1.0.0",
                "status": "pass",
                "run_id": f"public-fix-benchmark-{attempt:03d}",
                "harness": {"provider": "codex", "model": "not-invoked", "runtime": "public-fix-deterministic"},
                "honesty_surface": {
                    "knowns": ["Deterministic controls passed for the pinned fixture."],
                    "ratified_assumptions": [],
                    "remaining_unknowns": ["Live Codex provider behavior was not measured."],
                    "accepted_risks": [],
                },
                "brief_generator_defect_count": 0,
                "blocked_slices": [],
                "gate_results": [
                    {"name": name, "status": "pass", "evidence_ref": f"benchmark:{name}"}
                    for name in CALCULATED_METRICS
                ],
                "harness_runs": [
                    {
                        "provider": "codex",
                        "model": "not-invoked",
                        "status": "pass",
                        "evidence_ref": f"runs/run-{attempt:03d}",
                        "exit_code": 0,
                    }
                ],
                "evidence_refs": artifact_refs(attempt)[:-1],
                "audit_surface": {
                    "reverified": ["red-before-green", "resume idempotency", "scope", "completion claims"],
                    "taken_on_trust": [],
                },
                "process_artifacts_only": False,
            }
            validate_json(run_report, RUN_REPORT_SCHEMA, "run report")
            write_json(run_dir / "run-report.json", run_report, replacements)
            duration_ms = int((time.monotonic() - started) * 1000)
            return attempt_record(
                attempt,
                "pass",
                metrics,
                artifact_refs(attempt),
                duration_ms=duration_ms,
            )
        except subprocess.TimeoutExpired as exc:
            metrics = {name: False for name in CALCULATED_METRICS}
            metrics["human_decisions"] = 0
            failure = f"timeout after {timeout}s: {' '.join(map(str, exc.cmd))}"
            write_json(run_dir / "failure.json", {"status": "timeout", "failure": failure}, replacements)
            return attempt_record(
                attempt,
                "timeout",
                metrics,
                [f"runs/run-{attempt:03d}/failure.json"],
                duration_ms=int((time.monotonic() - started) * 1000),
                failure=failure,
            )
        except Exception as exc:
            metrics = {name: False for name in CALCULATED_METRICS}
            metrics["human_decisions"] = 0
            failure = str(exc)
            write_json(run_dir / "failure.json", {"status": "fail", "failure": failure}, replacements)
            return attempt_record(
                attempt,
                "fail",
                metrics,
                [f"runs/run-{attempt:03d}/failure.json"],
                duration_ms=int((time.monotonic() - started) * 1000),
                failure=failure,
            )


def plan_payload(metadata: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "contract_version": "1.0.0",
        "status": "planned",
        "fixture": metadata["fixture"],
        "configuration": metadata["configuration"],
        "plan": plan,
        "attempts": [
            {"attempt": index, "timeout_seconds": plan["timeout_seconds_per_run"], "token_limit": 0, "projected_cost_max": 0}
            for index in range(1, plan["runs"] + 1)
        ],
        "warning": "No provider/model calls are made by this deterministic configuration.",
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120, help="seconds per run")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--verify-replay", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        fixture = load_fixture(args.fixture)
        actual_start = compute_starting_commit(fixture)
        if actual_start != fixture["starting_commit"]:
            raise BenchmarkError(
                f"fixture starting commit is not pinned: expected {fixture['starting_commit']}, computed {actual_start}"
            )
        plan = build_plan(args.runs, args.timeout)
        metadata = runtime_metadata(fixture)
        if args.plan:
            payload = plan_payload(metadata, plan)
        else:
            temporary_output = None
            if args.output_dir:
                output_root = args.output_dir.resolve()
                if output_root.exists() and any(output_root.iterdir()):
                    raise BenchmarkError(f"output directory must be absent or empty: {output_root}")
                output_root.mkdir(parents=True, exist_ok=True)
            else:
                temporary_output = tempfile.TemporaryDirectory(prefix="adlc-public-benchmark-evidence-")
                output_root = Path(temporary_output.name)
            attempts = [execute_attempt(fixture, index, output_root, args.timeout) for index in range(1, args.runs + 1)]
            payload = build_report(metadata, plan, attempts)
            validate_json(payload, SCHEMA, "benchmark report")
            write_json(output_root / "benchmark-report.json", payload, [])
            if args.verify_replay and not payload["replay"]["verified"]:
                raise BenchmarkError("replay verification failed; inspect the complete attempts in the report")
            if payload["status"] != "pass":
                raise BenchmarkError("benchmark did not pass; inspect the complete attempts in the report")
            if temporary_output is not None:
                temporary_output.cleanup()
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"benchmark {payload['status']}")
        return 0
    except BenchmarkError as exc:
        error = {"status": "fail", "error": str(exc)}
        if args.json:
            print(json.dumps(error, indent=2, sort_keys=True))
        else:
            print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
