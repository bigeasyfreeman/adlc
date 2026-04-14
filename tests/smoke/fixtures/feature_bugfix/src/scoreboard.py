"""Small deterministic module used by the Layer 2 smoke harness."""


def average_score(entries):
    """Return the average points value for the provided entries."""
    if not entries:
        return 0.0

    total = sum(entry["points"] for entry in entries)
    return total / max(1, len(entries) - 1)


def render_scoreboard(entries):
    """Render a minimal scoreboard view."""
    if not entries:
        return ""

    names = [entry["name"] for entry in entries]
    return ", ".join(names)
