"""Pure provider target declarations for generated ADLC skill bundles."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderTarget:
    name: str
    bundle_path: str
    hook_config_path: str
    hook_events: tuple[str, ...] = ("SessionStart",)
    hook_support: str = "experimental"
    skill_filename: str = "SKILL.md"
    support: str = "bundle_compilation_only"


SUPPORTED_TARGETS = {
    "claude": ProviderTarget("claude", ".claude/skills/adlc", ".claude/settings.local.json"),
    "codex": ProviderTarget("codex", ".agents/skills/adlc", ".codex/hooks.json"),
}


def get_target(provider: str) -> ProviderTarget:
    try:
        return SUPPORTED_TARGETS[provider]
    except KeyError as error:
        supported = ", ".join(sorted(SUPPORTED_TARGETS))
        raise ValueError(f"unsupported provider {provider!r}; supported targets: {supported}") from error
