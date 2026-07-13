"""COUNTERS subsystem (band 2) — live member-count channel templates
(shipped services/counter_config.py render core; the rename effect rides
the channel-ops port when it arms)."""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["DEFAULT_TEMPLATES", "MAX_CHANNEL_NAME_LENGTH",
           "TEMPLATE_PRESETS", "TEMPLATE_SETTING_BY_KIND", "CounterPreset",
           "get_preset", "preset_setting_writes", "render_counter_name",
           "render_counters"]

# shipped defaults, verbatim (services/counter_config.py)
DEFAULT_TEMPLATES = {
    "total": "👥 Members: {count}",
    "humans": "🧑 Humans: {count}",
    "bots": "🤖 Bots: {count}",
}


@dataclass(frozen=True)
class CounterPreset:
    """One curated set of ``{count}`` templates (one per counter kind) —
    the shipped ``counter_config.CounterPreset``, verbatim fields."""

    key: str
    label: str
    templates: dict[str, str] = field(default_factory=dict)

    def template_for(self, kind: str) -> str:
        """Template for ``kind``, falling back to the canonical default
        (the shipped ``_DEFAULT_TEMPLATE_BY_KIND`` fallback)."""
        return self.templates.get(kind, DEFAULT_TEMPLATES[kind])


#: The shipped curated preset catalog (services/counter_config.py
#: ``TEMPLATE_PRESETS``, verbatim keys/labels/templates — all three kinds
#: per preset; the ``default`` preset is byte-identical to the canonical
#: defaults above). The ``!counterpreset`` list card renders each
#: preset's TOTAL-kind sample (goldens/counters/sweep_counterpreset pins
#: the bytes); the APPLY path writes all three through the audited
#: settings lane (sb/domain/counters/panels.py `_preset_view`).
TEMPLATE_PRESETS: tuple[CounterPreset, ...] = (
    CounterPreset(key="default", label="Default — emoji + label",
                  templates=dict(DEFAULT_TEMPLATES)),
    CounterPreset(key="minimal", label="Minimal — label only, no emoji",
                  templates={"total": "Members: {count}",
                             "humans": "Humans: {count}",
                             "bots": "Bots: {count}"}),
    CounterPreset(key="brackets", label="Brackets — compact count in brackets",
                  templates={"total": "Members [{count}]",
                             "humans": "Humans [{count}]",
                             "bots": "Bots [{count}]"}),
    CounterPreset(key="bullet", label="Bullet — separator dot",
                  templates={"total": "👥 Members • {count}",
                             "humans": "🧑 Humans • {count}",
                             "bots": "🤖 Bots • {count}"}),
)

#: lookup keyed by preset key — built once (the catalog is immutable).
_PRESETS_BY_KEY: dict[str, CounterPreset] = {p.key: p for p in TEMPLATE_PRESETS}


def get_preset(key: str) -> CounterPreset | None:
    """The :class:`CounterPreset` for ``key`` (case-insensitive), or None
    — shipped ``counter_config.get_preset`` verbatim."""
    return _PRESETS_BY_KEY.get(key.strip().lower())


#: the declared ``SettingSpec.name`` per kind (sb/manifest/counters.py
#: ``_SETTINGS`` — the shipped ``TEMPLATE_SETTING_BY_KIND`` twin).
TEMPLATE_SETTING_BY_KIND: dict[str, str] = {
    "total": "total_template",
    "humans": "humans_template",
    "bots": "bots_template",
}


def preset_setting_writes(preset: CounterPreset) -> tuple[tuple[str, str], ...]:
    """The ``(setting_name, template)`` writes that apply ``preset`` —
    shipped ``counter_config.preset_setting_writes`` verbatim (kind
    order; the apply path feeds each pair through the audited settings
    lane so coercion, validation, audit and the capability check all
    run)."""
    return tuple(
        (TEMPLATE_SETTING_BY_KIND[kind], preset.template_for(kind))
        for kind in ("total", "humans", "bots"))

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
