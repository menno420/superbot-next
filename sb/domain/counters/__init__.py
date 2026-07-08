"""COUNTERS subsystem (band 2) — live member-count channel templates
(shipped services/counter_service.py render core; the rename effect rides
the channel-ops port when it arms)."""

from __future__ import annotations

__all__ = ["DEFAULT_TEMPLATES", "render_counters"]

# shipped defaults, verbatim (services/counter_config.py)
DEFAULT_TEMPLATES = {
    "total": "👥 Members: {count}",
    "humans": "🧑 Humans: {count}",
    "bots": "🤖 Bots: {count}",
}


def render_counters(templates: dict[str, str], *, total: int, humans: int,
                    bots: int) -> dict[str, str]:
    counts = {"total": total, "humans": humans, "bots": bots}
    return {
        kind: (templates.get(kind) or DEFAULT_TEMPLATES[kind]).replace(
            "{count}", str(counts[kind]))
        for kind in ("total", "humans", "bots")
    }
