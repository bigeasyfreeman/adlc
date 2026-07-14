import importlib.util
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "skill" / "SKILL.src.md"
CONTEXT_PATH = ROOT / "skill" / "scripts" / "context.py"
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


def load_context_module():
    spec = importlib.util.spec_from_file_location("adlc_skill_context", CONTEXT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def parse_frontmatter(text):
    assert text.startswith("---\n")
    block, _ = text[4:].split("\n---\n", 1)
    return {
        line.split(":", 1)[0].strip(): line.split(":", 1)[1].strip()
        for line in block.splitlines()
        if ":" in line
    }


def test_skill_has_minimal_frontmatter_and_bounded_body():
    text = SKILL_PATH.read_text()
    frontmatter = parse_frontmatter(text)
    assert set(frontmatter) == {"name", "description"}
    assert frontmatter["name"] == "adlc"
    assert "ADLC" in frontmatter["description"]
    assert len(text.splitlines()) < 180


def test_skill_routes_exactly_eleven_commands_to_one_level_references():
    text = SKILL_PATH.read_text()
    routes = dict(
        re.findall(r"^\| `/(?:adlc )?([a-z]+)` \| `([^`]+)` \|$", text, re.MULTILINE)
    )
    assert set(routes) == set(COMMANDS)
    assert routes == {
        command: f"skill/reference/command-{command}.md" for command in COMMANDS
    }


def test_contract_contains_universal_safety_and_honesty_rules():
    text = SKILL_PATH.read_text().lower()
    required = (
        "one command reference",
        "never overwrite",
        "human approval",
        "evidence",
        "provider-neutral",
        "does not prove live provider invocation",
        "does not prove a complete adlc loop",
        "read-only",
    )
    for phrase in required:
        assert phrase in text


def test_contract_does_not_embed_provider_specific_paths_or_logic():
    text = SKILL_PATH.read_text().lower()
    forbidden = (".claude/", ".github/copilot", "gemini.md", "cursor/rules")
    assert not any(token in text for token in forbidden)


def test_router_defaults_ambiguous_requests_to_shape_and_selects_one_reference():
    context = load_context_module()
    assert context.route_command("Make this repository better.") == "shape"
    for command in COMMANDS:
        assert context.route_command(f"/adlc {command}") == command
        manifest = context.build_context_manifest(ROOT, command, max_files=1)
        assert manifest["selected_reference"] == f"skill/reference/command-{command}.md"
