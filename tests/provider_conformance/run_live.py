#!/usr/bin/env python3
"""Explicit, bounded live Codex conformance runner for a disposable Fix repo."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/skill_behavior"))

from run import redact_payload  # noqa: E402

TIMEOUT_SECONDS = 300
PROMPT = """Use the installed $adlc skill for this bounded Fix task. The repository contains a failing arithmetic-mean test. First run the verifier to establish red, inspect only the relevant product code and test, make the smallest repair in app/calculator.py, then rerun the verifier to green. Do not edit tests, ADLC config, or any other file. Do not commit. Finish with a concise evidence summary."""


def _write_fixture(target: Path) -> None:
    (target / "app").mkdir(parents=True)
    (target / "tests").mkdir()
    (target / ".gitignore").write_text(".adlc/\n__pycache__/\n*.pyc\n", encoding="utf-8")
    (target / "app/__init__.py").write_text("", encoding="utf-8")
    (target / "app/calculator.py").write_text(
        "def average(values):\n    if not values:\n        return 0\n    return sum(values)\n",
        encoding="utf-8",
    )
    (target / "tests/test_calculator.py").write_text(
        "import unittest\nfrom app.calculator import average\n\n"
        "class CalculatorTests(unittest.TestCase):\n"
        "    def test_average(self):\n"
        "        self.assertEqual(average([2, 4, 6]), 4)\n\n"
        "if __name__ == '__main__':\n    unittest.main()\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.email", "adlc-live@example.invalid"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.name", "ADLC Live Harness"], cwd=target, check=True)
    subprocess.run(["git", "add", "."], cwd=target, check=True)
    subprocess.run(["git", "commit", "-qm", "red fixture"], cwd=target, check=True)


def _install_skill(target: Path) -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "scripts") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "adlc_runtime.install",
            "install",
            "--provider",
            "codex",
            "--target",
            str(target),
            "--source",
            str(ROOT / "skill"),
            "--source-version",
            "live-conformance",
        ],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [sys.executable, "-m", "adlc_runtime.install", "doctor", "--provider", "codex", "--target", str(target)],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _json_events(stdout: str) -> list[Dict[str, Any]]:
    events = []
    for line in stdout.splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _bounded_trace(events: Iterable[Mapping[str, Any]], workspace: Path) -> list[Dict[str, Any]]:
    trace = []
    for event in events:
        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        event_type = str(event.get("type", "unknown"))
        record: Dict[str, Any] = {"event": event_type}
        if item:
            record["item_type"] = str(item.get("type", "unknown"))
            if item.get("type") == "command_execution":
                record["command"] = str(item.get("command", ""))[:1000]
                record["exit_code"] = item.get("exit_code")
            elif item.get("type") == "agent_message":
                record["message"] = str(item.get("text", ""))[:1000]
        if event_type == "turn.completed" and isinstance(event.get("usage"), dict):
            record["usage"] = dict(event["usage"])
        trace.append(redact_payload(record, workspace))
    return trace[-80:]


def _usage(events: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    for event in reversed(list(events)):
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            return {
                key: int(event["usage"].get(key, 0))
                for key in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
            }
    return {key: 0 for key in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")}


def analyze_run(
    *,
    returncode: int,
    events: list[Mapping[str, Any]],
    target: Path,
    red_returncode: int,
    green_returncode: int,
) -> Dict[str, Any]:
    command_items = [
        event.get("item", {})
        for event in events
        if isinstance(event.get("item"), dict) and event["item"].get("type") == "command_execution"
    ]
    test_commands = [
        item
        for item in command_items
        if "unittest" in str(item.get("command", "")) or "pytest" in str(item.get("command", ""))
    ]
    test_exit_codes = [item.get("exit_code") for item in test_commands if isinstance(item.get("exit_code"), int)]
    provider_red_green = len(test_exit_codes) >= 2 and test_exit_codes[0] != 0 and test_exit_codes[-1] == 0
    changed = subprocess.run(
        ["git", "diff", "--name-only"], cwd=target, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    expected_code = "return sum(values) / len(values)"
    code_fixed = expected_code in (target / "app/calculator.py").read_text(encoding="utf-8")
    assertions = {
        "provider_exit": returncode == 0,
        "structured_trace": bool(events) and any(event.get("type") == "turn.completed" for event in events),
        "red_before": red_returncode != 0,
        "provider_test_trace": provider_red_green,
        "bounded_diff": changed == ["app/calculator.py"],
        "product_fix": code_fixed,
        "green_after": green_returncode == 0,
    }
    return {
        "status": "pass" if all(assertions.values()) else "fail",
        "assertions": assertions,
        "changed_paths": changed,
        "provider_test_command_count": len(test_commands),
        "provider_test_exit_codes": test_exit_codes,
    }


def _version() -> str:
    result = subprocess.run(["codex", "--version"], capture_output=True, text=True, check=True)
    return result.stdout.strip().replace("codex-cli ", "")


def run_once(model: str, run_index: int, output_dir: Path) -> Dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="adlc-live-fix-") as temporary:
        target = Path(temporary) / "target"
        target.mkdir()
        _write_fixture(target)
        _install_skill(target)
        red = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=target,
            capture_output=True,
            text=True,
            check=False,
        )
        command = [
            "codex",
            "exec",
            "-C",
            str(target),
            "--sandbox",
            "workspace-write",
            "--ephemeral",
            "--ignore-user-config",
            "--model",
            model,
            "--json",
            PROMPT,
        ]
        try:
            provider = subprocess.run(
                command,
                cwd=target,
                capture_output=True,
                text=True,
                check=False,
                timeout=TIMEOUT_SECONDS,
            )
            events = _json_events(provider.stdout)
            provider_returncode = provider.returncode
            provider_stderr = provider.stderr
        except subprocess.TimeoutExpired as error:
            events = _json_events(error.stdout or "") if isinstance(error.stdout, str) else []
            provider_returncode = 124
            provider_stderr = "provider timeout"
        green = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=target,
            capture_output=True,
            text=True,
            check=False,
        )
        analysis = analyze_run(
            returncode=provider_returncode,
            events=events,
            target=target,
            red_returncode=red.returncode,
            green_returncode=green.returncode,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        source_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        source_clean = not subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        trace = [
            {"event": "pre_provider_verifier", "status": "fail" if red.returncode else "pass"},
            *_bounded_trace(events, target),
            {"event": "post_provider_verifier", "status": "pass" if green.returncode == 0 else "fail"},
        ]
        failures = [name for name, passed in analysis["assertions"].items() if not passed]
        usage = _usage(events)
        overall = analysis["status"]
        adapter_path = ROOT / "scripts/adlc_runtime/adapters/codex.sh"
        report: Dict[str, Any] = {
            "contract_version": "1.0.0",
            "evidence_status": (
                "current_conformance"
                if overall == "pass" and source_clean
                else "candidate_conformance"
                if overall == "pass"
                else "failed_conformance"
            ),
            "runtime": "codex",
            "provider": "codex",
            "harness": "codex-cli-installed-skill",
            "model": model,
            "provider_version": _version(),
            "loop": "fix",
            "run_id": f"codex-fix-{source_commit[:12]}-{run_index}",
            "status": analysis["status"],
            "credential_status": "available",
            "dimensions": {
                "installation": "pass",
                "invocation": "pass" if analysis["assertions"]["structured_trace"] else "fail",
                "behavior": "pass" if all(analysis["assertions"][key] for key in ("red_before", "provider_test_trace", "bounded_diff", "product_fix", "green_after")) else "fail",
                "end_to_end": "pass" if analysis["status"] == "pass" else "fail",
            },
            "duration_ms": duration_ms,
            "cost": {"currency": "USD", "min": 0.0, "max": 0.0},
            "usage": usage,
            "trace": trace,
            "failures": failures,
            "source_commit": source_commit,
            "source_tree_clean": source_clean,
            "adapter": {
                "path": "scripts/adlc_runtime/adapters/codex.sh",
                "sha256": hashlib.sha256(adapter_path.read_bytes()).hexdigest(),
            },
            "fixture_sha256": hashlib.sha256((PROMPT + "\n" + model).encode("utf-8")).hexdigest(),
            "auth_path": "codex-account-session",
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "stages": [
                {"name": "install", "ok": True, "artifact": ".agents/skills/adlc", "duration_ms": 0},
                {"name": "provider_invocation", "ok": analysis["assertions"]["structured_trace"], "artifact": "trace", "duration_ms": duration_ms},
                {"name": "red_green_fix", "ok": analysis["status"] == "pass", "artifact": "app/calculator.py", "duration_ms": 0},
            ],
            "overall": overall,
            "cost_estimate_tokens": usage["input_tokens"] + usage["output_tokens"],
            "analysis": analysis,
            "stderr": redact_payload(provider_stderr[-2000:], target),
            "no_overclaim": "This run applies only to the named Codex CLI, model, installed skill, Fix fixture, commit, and date.",
            "limitations": [
                "Bundled-account execution does not expose a marginal USD charge, so cost is reported as zero with token usage retained.",
                "One disposable arithmetic Fix does not prove Build or Review loop conformance.",
            ],
        }
        report = redact_payload(report, target)
        schema = json.loads((ROOT / "docs/schemas/provider-conformance-report.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(report, schema)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{report['run_id']}.report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run explicit live Codex Fix conformance.")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output-dir", default=str(ROOT / "tests/provider_conformance/artifacts"))
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.repetitions < 1 or args.repetitions > 10:
        raise SystemExit("repetitions must be between 1 and 10")
    planned = {
        "provider": "codex",
        "model": args.model,
        "loop": "fix",
        "repetitions": args.repetitions,
        "timeout_seconds_per_run": TIMEOUT_SECONDS,
        "maximum_provider_calls": args.repetitions,
        "requires_explicit_execution": True,
    }
    if not args.execute:
        print(json.dumps(planned, indent=2, sort_keys=True) if args.json else planned)
        return 0
    if shutil.which("codex") is None:
        raise SystemExit("codex CLI is unavailable")
    reports = [run_once(args.model, index + 1, Path(args.output_dir)) for index in range(args.repetitions)]
    summary = {**planned, "status": "pass" if all(report["status"] == "pass" for report in reports) else "fail", "runs": reports}
    print(json.dumps(summary, indent=2, sort_keys=True) if args.json else summary)
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
