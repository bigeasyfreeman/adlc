#!/usr/bin/env python3
"""Run the resumable live-Codex public Fix benchmark and validate its evidence."""

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
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/schemas/benchmark-report.schema.json"
RUN_REPORT_SCHEMA = ROOT / "docs/schemas/run-report.schema.json"
PUBLICATION_ATTESTATION_SCHEMA = ROOT / "docs/schemas/benchmark-publication-attestation.schema.json"
SECRET_PATTERN = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._~+/=-]{8,}|password\s*[=:]\s*[^\s\"']+|"
    r"(?:api|access|secret)[_-]?key\s*[=:]\s*[^\s\"']+)",
    re.IGNORECASE,
)
ABSOLUTE_PRIVATE_PATH = re.compile(r"/(?:Users/[^/]+|private/var/folders|var/folders)/")
PRIVATE_USER_HOME = re.compile(r"/Users/[^/\s\"'<>]+")
PRIVATE_TEMP_PATH = re.compile(r"/(?:private/)?var/folders/[^\s\"'<>]+")
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
DEFAULT_MODEL = "gpt-5.4"
DEFAULT_TOKEN_LIMIT = 750_000
APPROVAL_REF = "human:approved-complete-migration-process"


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
    fixture["prompt_file"] = path / fixture["prompt"]
    for key in ("starting_path", "prompt_file"):
        if not fixture[key].exists():
            raise BenchmarkError(f"fixture path missing: {fixture[key]}")
    return fixture


def codex_version() -> str:
    result = subprocess.run(["codex", "--version"], capture_output=True, text=True, check=False)
    if result.returncode:
        raise BenchmarkError("codex CLI is unavailable")
    return result.stdout.strip().replace("codex-cli ", "")


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
            "provider_version": "test",
            "model": DEFAULT_MODEL,
            "harness": "codex-cli-resumable-fix",
            "python": "3.9.0",
            "platform": "test",
        },
    }


def test_plan(runs: int) -> Dict[str, Any]:
    return build_plan(runs, 300)


def build_plan(runs: int, timeout_seconds: int) -> Dict[str, Any]:
    if not 3 <= runs <= 10:
        raise BenchmarkError("--runs must be between 3 and 10 for a public configuration")
    if not 1 <= timeout_seconds <= 600:
        raise BenchmarkError("--timeout must be between 1 and 600 seconds per provider turn")
    return {
        "runs": runs,
        "timeout_seconds_per_run": timeout_seconds,
        "token_limit_per_run": DEFAULT_TOKEN_LIMIT,
        "maximum_provider_calls": runs * 3,
        "projected_provider_cost": {"currency": "USD", "min": 0, "max": 0},
        "external_calls": True,
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
    tokens: int = 0,
    failure: Optional[str] = None,
) -> Dict[str, Any]:
    terminal = {"pass": "completed", "fail": "failed", "blocked": "blocked", "timeout": "timeout"}[status]
    invariant = {
        "terminal_class": terminal,
        "metrics": metrics,
        "changed_paths": ["src/invoice.py"],
        "provider_invoked": True,
        "resumed_same_session": metrics.get("resume_integrity"),
    }
    return {
        "attempt": attempt,
        "status": status,
        "terminal_class": terminal,
        "duration_ms": duration_ms,
        "cost": {"currency": "USD", "tokens": tokens, "min": 0, "max": 0},
        "metrics": metrics,
        "score": score_attempt(status, metrics, evidence_refs),
        "evidence_refs": list(evidence_refs),
        "redaction_status": "reviewed",
        "invariant_sha256": sha256_bytes(canonical_json(invariant)),
        "failure": failure,
    }


def spread(values: Iterable[float]) -> Dict[str, float]:
    sequence = list(values) or [0]
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
    return {
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
            "tokens": spread(item["cost"]["tokens"] for item in attempts),
            "provider_cost": spread(item["cost"]["max"] for item in attempts),
        },
        "replay": {
            "command": "python3 benchmarks/run.py --fixture examples/fix-demo --runs 3 --verify-replay --json",
            "verified": replay_verified,
            "matching_terminal_class": len(terminal_classes) == 1,
            "matching_invariants": len(invariants) == 1,
        },
        "redaction": {
            "status": "scanned",
            "scanner": "benchmark built-in credential and private-path scan v2",
            "secret_matches": 0,
            "absolute_paths_replaced": True,
        },
        "claims": [
            "The named live Codex Fix configuration preserved all attempts and reached the same terminal class.",
            "Each attempt used one persisted Codex session across the approval interruption and repair turn.",
            "Red-before-green, bounded scope, separate-session review, and completion-audit controls passed for the named fixture.",
        ],
        "limitations": [
            "Results apply only to the named fixture, source commit, product/provider/model versions, environment, harness, and execution date.",
            "Bundled-account execution exposes token usage but no marginal USD charge, so the observed provider-cost range is zero.",
        ],
        "no_overclaim": "This benchmark does not establish universal superiority, future model behavior, adoption, compliance, GA readiness, or autonomous code quality.",
    }


def redact(value: Any, replacements: Sequence[Tuple[str, str]]) -> Any:
    if isinstance(value, dict):
        return {key: redact(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, replacements) for item in value]
    if isinstance(value, str):
        for source, replacement in replacements:
            value = value.replace(source, replacement)
        value = PRIVATE_TEMP_PATH.sub("<PRIVATE_TEMP>", value)
        value = PRIVATE_USER_HOME.sub("<USER_HOME>", value)
        return value
    return value


def ensure_redacted(value: Any) -> None:
    serialized = json.dumps(value, sort_keys=True)
    secret = SECRET_PATTERN.search(serialized)
    if secret:
        raise BenchmarkError(f"secret-like content blocked by redaction scan: {secret.group(0)[:20]}...")
    private_path = ABSOLUTE_PRIVATE_PATH.search(serialized)
    if private_path:
        raise BenchmarkError(f"private absolute path blocked by redaction scan: {private_path.group(0)}")


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


def json_events(stdout: str) -> List[Dict[str, Any]]:
    events = []
    for line in stdout.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    return events


def event_thread_id(events: Sequence[Mapping[str, Any]]) -> str:
    for event in events:
        if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
            return str(event["thread_id"])
    raise BenchmarkError("Codex event stream did not expose a thread id")


def final_message(events: Sequence[Mapping[str, Any]]) -> str:
    messages = [
        str(event.get("item", {}).get("text", ""))
        for event in events
        if event.get("type") == "item.completed"
        and isinstance(event.get("item"), dict)
        and event["item"].get("type") == "agent_message"
    ]
    return messages[-1] if messages else ""


def token_usage(events: Sequence[Mapping[str, Any]]) -> int:
    return sum(
        int(event.get("usage", {}).get("input_tokens", 0)) + int(event.get("usage", {}).get("output_tokens", 0))
        for event in events
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict)
    )


def command_results(events: Sequence[Mapping[str, Any]]) -> List[Tuple[str, int]]:
    return [
        (str(event["item"].get("command", "")), int(event["item"]["exit_code"]))
        for event in events
        if event.get("type") == "item.completed"
        and isinstance(event.get("item"), dict)
        and event["item"].get("type") == "command_execution"
        and isinstance(event["item"].get("exit_code"), int)
    ]


def verifier_exit_codes(events: Sequence[Mapping[str, Any]], verifier: str) -> List[int]:
    """Exclude commands that only embed the verifier as completion-audit data."""
    return [
        code
        for command, code in command_results(events)
        if verifier in command and "completion-audit" not in command
    ]


def bounded_trace(events: Sequence[Mapping[str, Any]], replacements: Sequence[Tuple[str, str]]) -> List[Dict[str, Any]]:
    trace = []
    for event in events[-100:]:
        record: Dict[str, Any] = {"event": str(event.get("type", "unknown"))}
        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        if item:
            record["item_type"] = str(item.get("type", "unknown"))
            if item.get("type") == "command_execution":
                record["command"] = str(item.get("command", ""))[:1000]
                record["exit_code"] = item.get("exit_code")
            elif item.get("type") == "agent_message":
                record["message"] = str(item.get("text", ""))[:1500]
        if event.get("type") == "thread.started":
            record["thread_id"] = event.get("thread_id")
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            record["usage"] = dict(event["usage"])
        trace.append(redact(record, replacements))
    return trace


def artifact_refs(attempt: int) -> List[str]:
    prefix = f"runs/run-{attempt:03d}"
    names = [
        "install.json",
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


def runtime_metadata(fixture: Dict[str, Any], model: str) -> Dict[str, Any]:
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
            "provider_version": codex_version(),
            "model": model,
            "harness": "codex-cli-resumable-fix",
            "python": platform.python_version(),
            "platform": f"{platform.system()}-{platform.machine()}",
        },
    }


def execute_attempt(
    fixture: Dict[str, Any],
    attempt: int,
    output_root: Path,
    timeout: int,
    model: str,
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
        tokens = 0
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
            install_evidence = {
                "status": "pass",
                "fixture_starting_commit": starting_commit,
                "installed_commit": git_output(["rev-parse", "HEAD"], target),
                "doctor": health,
                "provider": "codex",
                "provider_version": codex_version(),
                "model": model,
            }
            write_json(run_dir / "install.json", install_evidence, replacements)

            verifier = fixture["verifier"].split()
            red_process = run_process(verifier, cwd=target, timeout=timeout, expected=(1,))
            red = {
                "status": "fail",
                "exit_code": red_process.returncode,
                "command": fixture["verifier"],
                "stdout": red_process.stdout,
                "stderr": red_process.stderr,
                "intended_failure": "Decimal('0.09') != Decimal('0.10')" in red_process.stderr,
            }
            if not red["intended_failure"]:
                raise BenchmarkError("pre-change verifier did not fail for the intended reconciliation defect")
            write_json(run_dir / "red.json", red, replacements)

            exact_prompt = fixture["prompt_file"].read_text(encoding="utf-8")
            interrupt_prompt = (
                "Use the installed $adlc skill for this bounded Fix task. This is the first turn of a resumable "
                f"benchmark. Run exactly `{fixture['verifier']}` to establish red; do not substitute another test "
                "command. Load the bounded Fix context, inspect only the "
                "relevant product code and tests, and diagnose the defect. Do not edit any file and do not commit. "
                "Stop at the mutation approval boundary and end your final message with the exact marker "
                "AWAITING_HUMAN_APPROVAL.\n\nExact user prompt:\n" + exact_prompt
            )
            interrupted_process = run_process(
                [
                    "codex",
                    "exec",
                    "-C",
                    str(target),
                    "--sandbox",
                    "workspace-write",
                    "--ignore-user-config",
                    "--model",
                    model,
                    "--json",
                    interrupt_prompt,
                ],
                cwd=target,
                timeout=timeout,
                expected=None,
            )
            interrupted_events = json_events(interrupted_process.stdout)
            executor_session = event_thread_id(interrupted_events)
            tokens += token_usage(interrupted_events)
            interrupted_diff = git_output(["status", "--porcelain", "--untracked-files=all"], target)
            interrupted = {
                "status": "awaiting_human",
                "session_id": executor_session,
                "prompt_sha256": sha256_bytes(interrupt_prompt.encode("utf-8")),
                "provider_exit_code": interrupted_process.returncode,
                "workspace_clean": not interrupted_diff,
                "approval_marker": "AWAITING_HUMAN_APPROVAL" in final_message(interrupted_events),
                "trace": bounded_trace(interrupted_events, replacements),
                "stderr": interrupted_process.stderr[-2000:],
            }
            write_json(run_dir / "interrupted.json", interrupted, replacements)
            if (
                interrupted["provider_exit_code"] != 0
                or not interrupted["workspace_clean"]
                or not interrupted["approval_marker"]
            ):
                raise BenchmarkError("the first Codex turn did not stop cleanly at the mutation approval boundary")

            resume_prompt = (
                f"Human approval is granted under {APPROVAL_REF}. Resume the same Fix task now. Apply the smallest "
                f"repair only in src/invoice.py, run exactly `{fixture['verifier']}` to green without substituting "
                "another test command, inspect the final diff, do not edit "
                "tests or ADLC files, and do not commit. End with the exact marker FIX_READY_FOR_REVIEW."
            )
            resumed_process = run_process(
                [
                    "codex",
                    "exec",
                    "resume",
                    "-c",
                    'sandbox_mode="workspace-write"',
                    "--ignore-user-config",
                    "--model",
                    model,
                    "--json",
                    executor_session,
                    resume_prompt,
                ],
                cwd=target,
                timeout=timeout,
                expected=None,
            )
            resumed_events = json_events(resumed_process.stdout)
            resumed_session = event_thread_id(resumed_events)
            tokens += token_usage(resumed_events)
            resumed = {
                "status": "completed",
                "session_id": resumed_session,
                "resumed_from_session_id": executor_session,
                "same_session": resumed_session == executor_session,
                "approval": {"decision": "approved", "approval_ref": APPROVAL_REF, "decided_by": "human"},
                "prompt_sha256": sha256_bytes(resume_prompt.encode("utf-8")),
                "provider_exit_code": resumed_process.returncode,
                "completion_marker": "FIX_READY_FOR_REVIEW" in final_message(resumed_events),
                "trace": bounded_trace(resumed_events, replacements),
                "stderr": resumed_process.stderr[-2000:],
            }
            write_json(run_dir / "resumed.json", resumed, replacements)
            if (
                resumed["provider_exit_code"] != 0
                or not resumed["same_session"]
                or not resumed["completion_marker"]
            ):
                raise BenchmarkError("Codex did not resume the same session through a completed Fix turn")

            changed = [line[3:] for line in git_output(["status", "--short"], target).splitlines() if line]
            scope_valid = sorted(changed) == sorted(fixture["allowed_product_changes"])
            if not scope_valid:
                raise BenchmarkError(f"out-of-scope product changes: {changed}")
            final_diff = git_output(["diff", "--unified=0", "--", *fixture["allowed_product_changes"]], target) + "\n"
            if not final_diff.strip():
                raise BenchmarkError("live Codex Fix produced no product diff")
            (run_dir / "final.diff").write_text(redact(final_diff, replacements), encoding="utf-8")
            ensure_redacted((run_dir / "final.diff").read_text(encoding="utf-8"))

            green_process = run_process(verifier, cwd=target, timeout=timeout)
            green = {
                "status": "pass",
                "exit_code": green_process.returncode,
                "command": fixture["verifier"],
                "stdout": green_process.stdout,
                "stderr": green_process.stderr,
            }
            write_json(run_dir / "green.json", green, replacements)
            provider_tests = command_results(interrupted_events) + command_results(resumed_events)
            provider_test_codes = [
                code
                for command, code in provider_tests
                if fixture["verifier"] in command and "completion-audit" not in command
            ]
            verifier_valid = provider_test_codes and provider_test_codes[0] != 0 and provider_test_codes[-1] == 0
            if not verifier_valid:
                raise BenchmarkError("live Codex trace does not contain the exact red-before-green verifier sequence")

            review_prompt = (
                "Independently review the current uncommitted Fix. Read only the product diff and affected tests, run "
                f"the exact verifier `{fixture['verifier']}`, and verify that only src/invoice.py changed and the "
                "allocation invariant is actually repaired. The harness, not this reviewer, runs completion-audit; "
                "do not invoke completion-audit, edit, or commit. End with "
                "INDEPENDENT_REVIEW_PASS only if every check passes; otherwise end with INDEPENDENT_REVIEW_FAIL."
            )
            review_process = run_process(
                [
                    "codex",
                    "exec",
                    "-C",
                    str(target),
                    "--sandbox",
                    "read-only",
                    "--ephemeral",
                    "--ignore-user-config",
                    "--model",
                    model,
                    "--json",
                    review_prompt,
                ],
                cwd=target,
                timeout=timeout,
                expected=None,
            )
            review_events = json_events(review_process.stdout)
            auditor_session = event_thread_id(review_events)
            tokens += token_usage(review_events)
            review_codes = verifier_exit_codes(review_events, fixture["verifier"])
            review_valid = (
                review_process.returncode == 0
                and auditor_session != executor_session
                and review_codes
                and review_codes[-1] == 0
                and "INDEPENDENT_REVIEW_PASS" in final_message(review_events)
                and sorted([line[3:] for line in git_output(["status", "--short"], target).splitlines() if line])
                == sorted(fixture["allowed_product_changes"])
            )
            review = {
                "status": "pass" if review_valid else "fail",
                "reviewer": "independent-codex-reviewer",
                "session_id": auditor_session,
                "executor_session_id": executor_session,
                "provider_exit_code": review_process.returncode,
                "verifier_exit_codes": review_codes,
                "changed_paths": changed,
                "product_diff_sha256": sha256_bytes(final_diff.encode("utf-8")),
                "trace": bounded_trace(review_events, replacements),
                "stderr": review_process.stderr[-2000:],
            }
            write_json(run_dir / "review.json", review, replacements)
            if not review_valid:
                raise BenchmarkError("separate-session independent Codex review did not pass")

            if tokens > DEFAULT_TOKEN_LIMIT:
                raise BenchmarkError(f"run token limit exceeded: {tokens} > {DEFAULT_TOKEN_LIMIT}")
            git_output(["add", *fixture["allowed_product_changes"]], target)
            git_output(["commit", "-qm", "Fix invoice discount reconciliation"], target)
            if git_output(["status", "--porcelain", "--untracked-files=all"], target):
                raise BenchmarkError("target is not clean and PR-ready")

            audit_plan = {
                "claims": [
                    {
                        "id": "FIX-GREEN",
                        "claim": "The invoice verifier passes after the live Codex fix.",
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
                "executor": {"identity": "live-codex-fix-executor", "session_id": executor_session},
                "auditor": {"identity": "live-codex-fix-auditor", "session_id": auditor_session},
                "evidence_refs": [f"runs/run-{attempt:03d}/interrupted.json", f"runs/run-{attempt:03d}/review.json"],
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
                        "live-codex-fix-executor",
                        "--auditor",
                        "live-codex-fix-auditor",
                        "--independence-evidence",
                        str(independence_path),
                        "--json",
                    ],
                    cwd=target,
                    timeout=timeout,
                ),
                "completion audit",
            )
            audit_valid = (
                audit.get("status") == "pass"
                and audit.get("independence", {}).get("executor_session_id") == executor_session
                and audit.get("independence", {}).get("auditor_session_id") == auditor_session
            )
            if not audit_valid:
                raise BenchmarkError("completion audit did not preserve the real executor/auditor session boundary")
            write_json(run_dir / "audit.json", audit, replacements)

            metrics = {
                "task_completion": True,
                "verifier_validity": verifier_valid and green_process.returncode == 0,
                "resume_integrity": resumed["same_session"] and interrupted["workspace_clean"],
                "claim_accuracy": audit_valid and review_valid,
                "scope_control": scope_valid,
                "human_decisions": 1,
            }
            run_report = {
                "contract_version": "1.0.0",
                "status": "pass",
                "run_id": f"public-fix-live-{attempt:03d}",
                "harness": {"provider": "codex", "model": model, "runtime": "codex-cli-resumable-fix"},
                "honesty_surface": {
                    "knowns": ["The live resumable Codex Fix controls passed for the pinned fixture."],
                    "ratified_assumptions": [],
                    "remaining_unknowns": ["Future model/provider versions may behave differently."],
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
                        "model": model,
                        "status": "pass",
                        "evidence_ref": f"runs/run-{attempt:03d}",
                        "exit_code": 0,
                    }
                ],
                "evidence_refs": artifact_refs(attempt)[:-1],
                "audit_surface": {
                    "reverified": ["red-before-green", "same-session resume", "scope", "completion claims"],
                    "taken_on_trust": [],
                },
                "process_artifacts_only": False,
            }
            validate_json(run_report, RUN_REPORT_SCHEMA, "run report")
            write_json(run_dir / "run-report.json", run_report, replacements)
            return attempt_record(
                attempt,
                "pass",
                metrics,
                artifact_refs(attempt),
                duration_ms=int((time.monotonic() - started) * 1000),
                tokens=tokens,
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
                tokens=tokens,
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
                tokens=tokens,
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
            {
                "attempt": index,
                "timeout_seconds_per_provider_turn": plan["timeout_seconds_per_run"],
                "provider_calls_max": 3,
                "token_limit": plan["token_limit_per_run"],
                "projected_cost_max": 0,
            }
            for index in range(1, plan["runs"] + 1)
        ],
        "warning": "This plan makes live Codex calls using the current CLI account; bundled-account marginal USD cost is unavailable.",
    }


def verify_published(report_path: Path) -> Dict[str, Any]:
    report_path = report_path.resolve()
    report = read_json(report_path)
    validate_json(report, SCHEMA, "published benchmark report")
    root = report_path.parent
    refs = [root / ref for attempt in report["attempts"] for ref in attempt["evidence_refs"]]
    missing = [str(path) for path in refs if not path.is_file()]
    if missing:
        raise BenchmarkError(f"published benchmark evidence refs are missing: {missing}")
    for path in [report_path, *refs]:
        ensure_redacted(path.read_text(encoding="utf-8", errors="replace"))
    if report["status"] != "pass" or not report["replay"]["verified"]:
        raise BenchmarkError("published benchmark report is not a verified pass")
    return {
        "contract_version": "1.0.0",
        "status": "pass",
        "report": str(report_path),
        "attempts": len(report["attempts"]),
        "evidence_refs": len(refs),
        "secret_matches": 0,
        "absolute_path_matches": 0,
    }


def resolve_published_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    if path != ROOT and ROOT.resolve() not in path.parents:
        raise BenchmarkError(f"published benchmark path escapes the repository: {value}")
    return path


def verify_published_bundle(attestation_path: Path) -> Dict[str, Any]:
    attestation_path = attestation_path.resolve()
    attestation = read_json(attestation_path)
    validate_json(attestation, PUBLICATION_ATTESTATION_SCHEMA, "benchmark publication attestation")
    ensure_redacted(attestation_path.read_text(encoding="utf-8", errors="replace"))

    reports: Dict[str, Dict[str, Any]] = {}
    report_paths: Dict[str, Path] = {}
    report_hashes: Dict[str, str] = {}
    evidence_paths = set()
    verification: Dict[str, Dict[str, Any]] = {}
    for key in ("primary_report", "independent_replay"):
        expected = attestation[key]
        report_path = resolve_published_path(expected["path"])
        if not report_path.is_file():
            raise BenchmarkError(f"attested benchmark report is missing: {expected['path']}")
        actual_hash = sha256_bytes(report_path.read_bytes())
        if actual_hash != expected["sha256"]:
            raise BenchmarkError(f"attested benchmark report hash mismatch: {expected['path']}")
        report = read_json(report_path)
        if len(report.get("attempts", [])) != expected["attempts"]:
            raise BenchmarkError(f"attested benchmark attempt count mismatch: {expected['path']}")
        reports[key] = report
        report_paths[key] = report_path
        report_hashes[key] = actual_hash
        verification[key] = verify_published(report_path)
        evidence_paths.add(report_path)
        evidence_paths.update(
            (report_path.parent / ref).resolve()
            for attempt in report["attempts"]
            for ref in attempt["evidence_refs"]
        )

    if report_paths["primary_report"] == report_paths["independent_replay"]:
        raise BenchmarkError("primary report and independent replay must be distinct paths")
    if report_hashes["primary_report"] == report_hashes["independent_replay"]:
        raise BenchmarkError("primary report and independent replay must be distinct artifacts")

    primary = reports["primary_report"]
    replay = reports["independent_replay"]
    for field in ("source_commit", "product_version", "fixture", "configuration", "plan"):
        if primary[field] != replay[field]:
            raise BenchmarkError(f"published benchmark reports diverge on {field}")
    if [attempt["status"] for attempt in primary["attempts"]] != [
        attempt["status"] for attempt in replay["attempts"]
    ]:
        raise BenchmarkError("published benchmark reports diverge on attempt statuses")
    if [attempt["terminal_class"] for attempt in primary["attempts"]] != [
        attempt["terminal_class"] for attempt in replay["attempts"]
    ]:
        raise BenchmarkError("published benchmark reports diverge on terminal classes")
    if [attempt["invariant_sha256"] for attempt in primary["attempts"]] != [
        attempt["invariant_sha256"] for attempt in replay["attempts"]
    ]:
        raise BenchmarkError("published benchmark reports diverge on calculated invariants")
    if len(evidence_paths) != attestation["redaction_review"]["files_reviewed"]:
        raise BenchmarkError("publication attestation file count does not match the evidence bundle")

    return {
        "contract_version": "1.0.0",
        "status": "pass",
        "attestation": str(attestation_path),
        "reports": 2,
        "attempts": sum(len(report["attempts"]) for report in reports.values()),
        "evidence_files": len(evidence_paths),
        "same_fixture": True,
        "same_configuration": True,
        "matching_terminal_class": True,
        "matching_invariants": True,
        "secret_matches": 0,
        "absolute_path_matches": 0,
        "report_verification": verification,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=300, help="seconds per provider turn")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--verify-replay", action="store_true")
    parser.add_argument("--verify-published", type=Path)
    parser.add_argument("--verify-published-bundle", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.verify_published_bundle:
            payload = verify_published_bundle(args.verify_published_bundle)
            exit_code = 0
        elif args.verify_published:
            payload = verify_published(args.verify_published)
            exit_code = 0
        else:
            fixture = load_fixture(args.fixture)
            actual_start = compute_starting_commit(fixture)
            if actual_start != fixture["starting_commit"]:
                raise BenchmarkError(
                    f"fixture starting commit is not pinned: expected {fixture['starting_commit']}, computed {actual_start}"
                )
            plan = build_plan(args.runs, args.timeout)
            metadata = runtime_metadata(fixture, args.model)
            if args.plan:
                payload = plan_payload(metadata, plan)
                exit_code = 0
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
                attempts = [
                    execute_attempt(fixture, index, output_root, args.timeout, args.model)
                    for index in range(1, args.runs + 1)
                ]
                payload = build_report(metadata, plan, attempts)
                validate_json(payload, SCHEMA, "benchmark report")
                write_json(output_root / "benchmark-report.json", payload, [])
                exit_code = 0 if payload["status"] == "pass" and (not args.verify_replay or payload["replay"]["verified"]) else 1
                if temporary_output is not None:
                    temporary_output.cleanup()
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"benchmark {payload['status']}")
        return exit_code
    except BenchmarkError as exc:
        error = {"status": "fail", "error": str(exc)}
        if args.json:
            print(json.dumps(error, indent=2, sort_keys=True))
        else:
            print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
