"""Consent-gated, deterministic provider hook rendering and execution."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from adlc_runtime import cli
from adlc_runtime.provider_targets import get_target

MAX_INPUT_BYTES = 65_536
MAX_OUTPUT_CHARS = 4_096
HOOK_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class HookDefinition:
    key: str
    native_event: str
    argv: tuple[str, ...]
    tool_name: str
    action: str
    phase: str
    permission_tier: str
    side_effect_profile: str


HOOK_DEFINITIONS = {
    "session_start": HookDefinition(
        key="session_start",
        native_event="SessionStart",
        argv=("-m", "adlc_runtime.hooks", "check"),
        tool_name="adlc-provider-hook-doctor",
        action="verify_managed_bundle",
        phase="research",
        permission_tier="unrestricted",
        side_effect_profile="read_only",
    )
}

_SECRET_PATTERNS = (
    re.compile(r"(?i)(token|password|secret|api[_-]?key)(\s*[=:]\s*)([^\s\"']+)"),
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._~+\-/=]{8,})"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
)


def completed_process(returncode: int, stdout: str, stderr: str) -> subprocess.CompletedProcess[str]:
    """Build a CompletedProcess for callers and focused tests."""

    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def _runtime_argv(provider: str, event: str, target: Path, executable: str) -> tuple[str, ...]:
    return (
        executable,
        "-m",
        "adlc_runtime.hooks",
        "run",
        "--provider",
        provider,
        "--event",
        event,
        "--target",
        str(target.resolve()),
    )


def _tool_registry(definition: HookDefinition) -> Dict[str, Any]:
    return {
        "version": "1.0.0",
        "default_policy": "deny",
        "tools": [
            {
                "name": definition.tool_name,
                "description": "Read-only integrity check for an explicitly enabled ADLC provider bundle.",
                "inputSchema": {},
                "side_effect_profile": definition.side_effect_profile,
                "permission_tier": definition.permission_tier,
                "available_phases": [definition.phase],
            }
        ],
    }


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def render_hook_artifacts(provider: str, target: Path, executable: str) -> Dict[str, bytes]:
    """Purely render provider-native config and its admission registry."""

    definition = HOOK_DEFINITIONS["session_start"]
    provider_target = get_target(provider)
    if definition.native_event not in provider_target.hook_events:
        raise ValueError(f"provider {provider!r} does not support event {definition.native_event!r}")
    argv = _runtime_argv(provider, definition.key, target, executable)
    if provider == "claude":
        handler = {
            "type": "command",
            "command": argv[0],
            "args": list(argv[1:]),
            "timeout": HOOK_TIMEOUT_SECONDS,
            "statusMessage": "Checking ADLC bundle integrity",
        }
    elif provider == "codex":
        handler = {
            "type": "command",
            "command": shlex.join(argv),
            "timeout": HOOK_TIMEOUT_SECONDS,
        }
    else:
        raise ValueError(f"unsupported provider {provider!r}")
    config = {"hooks": {definition.native_event: [{"hooks": [handler]}]}}
    registry_path = f".adlc/hooks/{provider}/tool-registry.json"
    return {
        provider_target.hook_config_path: _json_bytes(config),
        registry_path: _json_bytes(_tool_registry(definition)),
    }


def parse_hook_input(raw: bytes) -> Dict[str, Any]:
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("provider hook input is too large")
    try:
        payload = json.loads(raw.decode("utf-8")) if raw.strip() else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("provider hook input must be one UTF-8 JSON object") from error
    if not isinstance(payload, dict):
        raise ValueError("provider hook input must be one JSON object")
    return payload


def validate_hook_input(event: str, target: Path, payload: Mapping[str, Any]) -> None:
    definition = HOOK_DEFINITIONS.get(event)
    if definition is None:
        raise ValueError(f"unsupported hook event: {event}")
    if payload.get("hook_event_name") != definition.native_event:
        raise ValueError("provider hook event mismatch")
    cwd = payload.get("cwd")
    if not isinstance(cwd, str):
        raise ValueError("provider hook cwd is required")
    supplied = Path(cwd)
    if not supplied.is_absolute() or supplied.resolve() != target.resolve():
        raise ValueError("provider hook cwd does not match the installed target")


def _redact(value: str) -> str:
    redacted = value[:MAX_OUTPUT_CHARS]
    redacted = _SECRET_PATTERNS[0].sub(r"\1\2[REDACTED]", redacted)
    redacted = _SECRET_PATTERNS[1].sub(r"\1[REDACTED]", redacted)
    return _SECRET_PATTERNS[2].sub("[REDACTED]", redacted)


def run_hook_payload(provider: str, event: str, target: Path, payload: Mapping[str, Any]) -> Dict[str, Any]:
    target = target.resolve()
    validate_hook_input(event, target, payload)
    definition = HOOK_DEFINITIONS[event]
    registry = target / ".adlc" / "hooks" / provider / "tool-registry.json"
    exit_code, admission = cli.action_admit_payload(
        tool_registry_path=registry,
        tool_name=definition.tool_name,
        action=definition.action,
        phase=definition.phase,
        allow_mutation=False,
        human_approved=False,
    )
    if exit_code or admission.get("status") != "admitted":
        return {
            "status": "denied",
            "stop_reason": admission.get("stop_reason") or "permission_denied",
            "system_message": "ADLC policy denied the provider hook before execution.",
            "admission": admission,
        }
    command = [sys.executable, *definition.argv, "--provider", provider, "--target", str(target)]
    try:
        result = subprocess.run(
            command,
            cwd=target,
            capture_output=True,
            text=True,
            timeout=HOOK_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "stop_reason": "timeout",
            "system_message": f"ADLC provider hook timed out after {HOOK_TIMEOUT_SECONDS} seconds.",
            "admission": admission,
        }
    stdout = _redact(result.stdout or "")
    stderr = _redact(result.stderr or "")
    try:
        detail = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        detail = {"stdout": stdout}
    status = "pass" if result.returncode == 0 else "failed"
    return {
        "status": status,
        "stop_reason": None if status == "pass" else "integrity_check_failed",
        "system_message": "ADLC provider bundle integrity check passed." if status == "pass" else "ADLC provider bundle integrity check failed.",
        "admission": admission,
        "detail": detail,
        **({"stderr": stderr} if stderr else {}),
        "no_overclaim": "This hook checks managed bundle integrity; it does not prove provider behavior.",
    }


def _check(provider: str, target: Path) -> int:
    from adlc_runtime import install

    report = install.doctor(target, provider)
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("status") == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m adlc_runtime.hooks")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--provider", required=True, choices=("claude", "codex"))
    run.add_argument("--event", required=True, choices=tuple(HOOK_DEFINITIONS))
    run.add_argument("--target", required=True)
    check = commands.add_parser("check")
    check.add_argument("--provider", required=True, choices=("claude", "codex"))
    check.add_argument("--target", required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = Path(args.target)
    if args.command == "check":
        return _check(args.provider, target)
    try:
        payload = parse_hook_input(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        report = run_hook_payload(args.provider, args.event, target, payload)
    except (ValueError, OSError) as error:
        report = {"status": "failed", "stop_reason": "invalid_input", "system_message": str(error)}
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
