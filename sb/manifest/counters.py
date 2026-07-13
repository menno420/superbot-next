"""COUNTERS subsystem manifest (band 2) — live member-count channels
slice verbatim; the rename effect rides the channel-ops port."""

from __future__ import annotations

from sb.domain.counters import DEFAULT_TEMPLATES
from sb.domain.counters import panels as _panels
from sb.domain.operator_spine import ensure_hub, hub_spec
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef
from sb.spec.settings import Activation, BindingKind, BindingSpec, SettingSpec

_TITLE, _BLURB = "Server counters", ("Live member-count channels "
                                     "(total · humans · bots).")
ensure_hub("counters", _TITLE, _BLURB)

_SETTINGS = (
    SettingSpec(name="enabled", value_type=bool, default=False,
                settings_key="counters_enabled",
                activation=Activation.OFF_UNTIL_OPT_IN,
                hint="Master counters switch."),
    SettingSpec(name="total_template", value_type=str,
                default=DEFAULT_TEMPLATES["total"],
                settings_key="counters_total_template",
                hint="Total-members channel name template ({count})."),
    SettingSpec(name="humans_template", value_type=str,
                default=DEFAULT_TEMPLATES["humans"],
                settings_key="counters_humans_template",
                hint="Humans channel name template ({count})."),
    SettingSpec(name="bots_template", value_type=str,
                default=DEFAULT_TEMPLATES["bots"],
                settings_key="counters_bots_template",
                hint="Bots channel name template ({count})."),
    BindingSpec(name="total_channel", kind=BindingKind.CHANNEL,
                hint="Total-members counter channel.",
                legacy_settings_key_aliases=("counters_total_channel",)),
    BindingSpec(name="humans_channel", kind=BindingKind.CHANNEL,
                hint="Humans counter channel.",
                legacy_settings_key_aliases=("counters_humans_channel",)),
    BindingSpec(name="bots_channel", kind=BindingKind.CHANNEL,
                hint="Bots counter channel.",
                legacy_settings_key_aliases=("counters_bots_channel",)),
)

MANIFEST = SubsystemManifest(
    key="counters",
    version=1,
    commands=(
        # BOTH front doors render the shipped status card: prefix as a
        # public channel send, slash as the shipped ephemeral type-4
        # twin (slash+PanelRef resolves DeferMode.NONE; Audience.INVOKER
        # presents flags 64 on interaction surfaces).
        CommandSpec(name="counters", kind=CommandKind.BOTH,
                    route=PanelRef("counters.status"),
                    summary="Show the current server-counters policy "
                            "for this server.",
                    capability="counters"),
        # the shipped `!counterpreset [name]` split: no name lists the
        # curated catalog (goldens/counters/sweep_counterpreset pins the
        # card); a name APPLIES all three templates through the audited
        # settings.set_scalar lane (sb/domain/counters/panels.py
        # `_preset_view` — 2026-07-13 operator-hub edits A).
        CommandSpec(name="counterpreset", kind=CommandKind.PREFIX,
                    route=HandlerRef("counters.preset_view"),
                    summary="List or apply a counter name-template "
                            "preset.",
                    capability="counters"),
    ),
    panels=(hub_spec("counters", _TITLE, _BLURB), _panels.status_spec(),
            _panels.presets_spec()),
    settings=_SETTINGS,
    stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    ensure_hub("counters", _TITLE, _BLURB)
    _panels.ensure_panel_refs()


ENSURE_REFS = _ensure_refs
