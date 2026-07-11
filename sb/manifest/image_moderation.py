"""IMAGE_MODERATION subsystem manifest (band 2) — the shipped settings
slice verbatim. The master switch carries external_side_effects=True
(provider image scans) — the §4.4 privacy gate AS GRAMMAR (the fence's
own canonical example). The scan engine arms with the message band +
provider keys."""

from __future__ import annotations

from sb.domain.image_moderation import panels as _panels
from sb.domain.operator_spine import ensure_hub, hub_spec
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import PanelRef
from sb.spec.settings import Activation, SettingSpec

_TITLE, _BLURB = "Image moderation", ("Provider-scored image screening "
                                      "(sexual/violence/harassment/hate).")
ensure_hub("image_moderation", _TITLE, _BLURB)

_CATEGORIES = tuple(
    SettingSpec(name=f"{category}_enabled", value_type=bool, default=False,
                settings_key=f"image_moderation_{category}_enabled",
                activation=Activation.OFF_UNTIL_OPT_IN,
                hint=f"Screen the {category} category.")
    for category in ("sexual", "violence", "harassment", "hate")
)

_SETTINGS = (
    SettingSpec(name="enabled", value_type=bool, default=False,
                settings_key="image_moderation_enabled",
                activation=Activation.OFF_UNTIL_OPT_IN,
                external_side_effects=True,
                hint="Master switch — images leave the guild for scoring."),
) + _CATEGORIES + (
    SettingSpec(name="threshold_percent", value_type=int, default=80,
                settings_key="image_moderation_threshold_percent",
                bounds=(1, 100), hint="Score threshold to act."),
    SettingSpec(name="exempt_roles", value_type=str, default="",
                settings_key="image_moderation_exempt_roles",
                hint="Comma list of exempt role ids."),
    SettingSpec(name="exempt_channels", value_type=str, default="",
                settings_key="image_moderation_exempt_channels",
                hint="Comma list of exempt channel ids."),
)

MANIFEST = SubsystemManifest(
    key="image_moderation",
    version=1,
    commands=(
        CommandSpec(name="imagemod", kind=CommandKind.PREFIX,
                    route=PanelRef("image_moderation.status"),
                    summary="Show the current image-moderation policy "
                            "for this server.",
                    capability="image_moderation"),
    ),
    panels=(hub_spec("image_moderation", _TITLE, _BLURB),
            _panels.status_spec()),
    settings=_SETTINGS,
    stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    ensure_hub("image_moderation", _TITLE, _BLURB)
    _panels.ensure_panel_refs()


ENSURE_REFS = _ensure_refs
