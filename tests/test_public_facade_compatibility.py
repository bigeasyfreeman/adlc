from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from adlc_runtime import cli  # noqa: E402
from adlc_runtime.metadata import COMMAND_METADATA, LOW_LEVEL_COMPATIBILITY, PUBLIC_OPERATION_METADATA, SCHEMA_ALIASES  # noqa: E402


def run_cli(*args):
    return subprocess.run([str(ROOT / "bin" / "adlc"), *args], cwd=ROOT, text=True, capture_output=True, check=False)


def test_public_schemas_and_low_level_compatibility_metadata_are_registered():
    assert SCHEMA_ALIASES["public-operation"].endswith("public-operation.schema.json")
    assert SCHEMA_ALIASES["public-operation-result"].endswith("public-operation-result.schema.json")
    assert len(PUBLIC_OPERATION_METADATA) == 11
    assert LOW_LEVEL_COMPATIBILITY["status"] == {
        "deprecated": False,
        "replacement": "public-operation",
        "retained_through": "0.x",
    }


def test_existing_status_command_output_is_unchanged(tmp_path):
    state = cli.new_workflow_state("BRIEF-COMPAT", tmp_path, phase="triage")
    state_path = tmp_path / ".adlc" / "workflow_state.json"
    cli.save_workflow_state(state_path, state)
    before = state_path.read_bytes()
    legacy = run_cli("status", "--workspace", str(tmp_path), "--state", str(state_path), "--json")
    assert legacy.returncode == 0, legacy.stderr
    assert json.loads(legacy.stdout)["read_only"] is True
    assert state_path.read_bytes() == before


def test_public_operation_cli_is_additive_and_schema_valid(tmp_path):
    request_path = tmp_path / "doctor.json"
    request_path.write_text(json.dumps({
        "contract_version": "1.0.0",
        "operation": "doctor",
        "experimental": True,
        "allow_mutation": False,
        "human_approved": False,
        "arguments": {},
    }), encoding="utf-8")
    result = run_cli("public-operation", "--input", str(request_path), "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["operation"] == "doctor"
    assert payload["status"] == "completed"
    assert payload["compatibility"]["support"] == "experimental"
    assert payload["compatibility"]["low_level_commands"] == [{
        "name": "health-check",
        "deprecated": False,
        "replacement": "public-operation",
        "retained_through": "0.x",
    }]
    assert not cli.validate_artifact_payload(cli.resolve_schema("public-operation-result"), payload)


def test_public_operation_is_exposed_through_mcp_with_the_request_schema():
    tool = next(item for item in cli.mcp_tools() if item["name"] == COMMAND_METADATA["public-operation"]["mcp_name"])
    assert tool["inputSchema"]["properties"]["operation"]["enum"] == list(PUBLIC_OPERATION_METADATA)
    response = cli.call_tool("adlc_public_operation", {
        "contract_version": "1.0.0",
        "operation": "doctor",
        "experimental": True,
        "allow_mutation": False,
        "human_approved": False,
        "arguments": {},
    })
    assert response["isError"] is False
    assert response["structuredContent"]["operation"] == "doctor"


def test_wrapper_preserves_external_pythonpath_and_existing_help():
    env = dict(os.environ, PYTHONPATH="sentinel")
    result = subprocess.run([str(ROOT / "bin" / "adlc"), "--help"], cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    assert result.returncode == 0
    assert "public-operation" in result.stdout
    assert "status" in result.stdout
    assert "resume-workflow" in result.stdout
