import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "migration" / "legacy-surface-ledger.json"
SKILL = ROOT / "skill" / "SKILL.src.md"
COMMANDS = (
    "init",
    "shape",
    "build",
    "fix",
    "review",
    "harden",
    "ship",
    "status",
    "resume",
    "doctor",
    "learn",
)
REQUIRED_HEADINGS = (
    "Purpose",
    "Preconditions",
    "Example",
    "Procedure",
    "Outputs",
    "Stop states",
    "Side effects",
    "Approval points",
    "Compatibility map",
    "Troubleshooting",
    "Honesty",
)


def reference_path(command):
    return ROOT / "skill" / "reference" / f"command-{command}.md"


def test_every_public_command_has_one_concise_complete_reference():
    skill_text = SKILL.read_text()
    routes = re.findall(
        r"^\| `/(?:adlc )?([a-z]+)` \| `([^`]+)` \|$", skill_text, re.MULTILINE
    )
    assert [command for command, _ in routes] == list(COMMANDS)
    assert len({path for _, path in routes}) == len(COMMANDS)

    for command, relative in routes:
        path = ROOT / relative
        text = path.read_text()
        assert path == reference_path(command)
        assert text.startswith(f"# `/adlc {command}`\n")
        assert len(text.splitlines()) <= 80
        for heading in REQUIRED_HEADINGS:
            assert f"## {heading}" in text
        assert "doc_honesty_section:" in text
        assert "no_overclaim:" in text
        assert "limitations:" in text


def test_ledger_maps_all_commands_to_real_kernel_and_legacy_surfaces():
    ledger = json.loads(LEDGER.read_text())
    mappings = {item["command"]: item for item in ledger["command_mappings"]}
    assert set(mappings) == set(COMMANDS)

    help_text = subprocess.run(
        [str(ROOT / "bin" / "adlc"), "--help"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    ledger_surfaces = ledger["surfaces"]
    for command, mapping in mappings.items():
        expected_reference = f"skill/reference/command-{command}.md"
        assert mapping["reference"] == expected_reference
        assert reference_path(command).is_file()
        assert mapping["kernel_commands"]
        for kernel_command in mapping["kernel_commands"]:
            assert kernel_command.startswith("bin/adlc ")
            assert kernel_command.split()[1] in help_text
        assert mapping["schema_refs"]
        assert mapping["deterministic_checks"]
        for schema_ref in mapping["schema_refs"]:
            assert (ROOT / schema_ref).is_file()
        assert isinstance(mapping["workflow_phases"], list)
        expected_legacy = sorted(
            surface["path"]
            for surface in ledger_surfaces
            if surface.get("replacement") == expected_reference
        )
        assert sorted(mapping["legacy_surfaces"]) == expected_legacy


def test_review_is_read_only_and_ship_stops_for_approval():
    review = reference_path("review").read_text().lower()
    ship = reference_path("ship").read_text().lower()
    assert "read-only" in review
    assert "do not edit" in review
    assert "separate `/adlc fix`" in review
    assert "stop before" in ship
    assert "human approval" in ship


def test_fix_refuses_skip_tests_and_requires_reproduction_first():
    fix = reference_path("fix").read_text().lower()
    reproduce = fix.index("reproduce")
    mutate = fix.index("smallest repair")
    assert reproduce < mutate
    assert "skip tests" in fix
    assert "stop" in fix[fix.index("skip tests") :]


def test_skill_no_longer_marks_command_references_pending():
    text = SKILL.read_text().lower()
    assert "command references land in the next migration" not in text
    assert "reference_status` is `pending" not in text
