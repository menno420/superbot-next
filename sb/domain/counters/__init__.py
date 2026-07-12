"""COUNTERS subsystem (band 2) — live member-count channel templates
(shipped services/counter_config.py render core; the rename effect rides
the channel-ops port when it arms)."""

from __future__ import annotations

__all__ = ["DEFAULT_TEMPLATES", "MAX_CHANNEL_NAME_LENGTH",
           "TEMPLATE_PRESETS", "render_counter_name", "render_counters"]

# shipped defaults, verbatim (services/counter_config.py)
DEFAULT_TEMPLATES = {
    "total": "👥 Members: {count}",
    "humans": "🧑 Humans: {count}",
    "bots": "🤖 Bots: {count}",
}

#: The shipped curated preset catalog (services/counter_config.py
#: ``TEMPLATE_PRESETS``, verbatim keys/labels) — ``(key, label,
#: total_template)`` triples: the ``!counterpreset`` list card renders
#: each preset's TOTAL-kind sample (goldens/counters/sweep_counterpreset
#: pins the bytes). The shipped catalog also carried the humans/bots
#: templates per preset; those ride the APPLY path (the audited
#: settings-pipeline write — a successor slice, see
#: sb/manifest/counters.py), so only the list-card fields port here.
TEMPLATE_PRESETS: tuple[tuple[str, str, str], ...] = (
    ("default", "Default — emoji + label", DEFAULT_TEMPLATES["total"]),
    ("minimal", "Minimal — label only, no emoji", "Members: {count}"),
    ("brackets", "Brackets — compact count in brackets", "Members [{count}]"),
    ("bullet", "Bullet — separator dot", "👥 Members • {count}"),
)

#: Discord's channel-name limit (services/counter_config.py).
MAX_CHANNEL_NAME_LENGTH = 100


def render_counter_name(template: str, count: int) -> str:
    """Render a counter channel name, ``{count}`` expanded +
    length-capped — shipped ``counter_config.render_counter_name``
    verbatim: plain ``str.replace`` (not ``str.format``) so a stray
    ``{`` in the template never raises, thousands-separated count,
    truncated to Discord's 100-char channel-name limit."""
    name = (template or "").replace("{count}", f"{count:,}")
    return name[:MAX_CHANNEL_NAME_LENGTH]


def render_counters(templates: dict[str, str], *, total: int, humans: int,
                    bots: int) -> dict[str, str]:
    counts = {"total": total, "humans": humans, "bots": bots}
    return {
        kind: render_counter_name(
            templates.get(kind) or DEFAULT_TEMPLATES[kind], counts[kind])
        for kind in ("total", "humans", "bots")
    }
