"""The settings hub panel (band 1) — the generated settings-panel family's
front door (design-spec §4.2 "one generated settings-panel family").

`settings.hub` is a read-view v1: a FieldsBlock over the K7 declaration
registry (subsystem -> declared-setting count + persisted keys), one row
per subsystem, plus the per-subsystem generated panels from
sb.kernel.panels.projections.settings_panel_spec. Edit actions arrive with
the panel-action slice (successor work, D-0025) — the hub proves the
projection + navigation seams now.
"""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    NavigationSpec,
    PanelSpec,
    TextBlock,
)
from sb.spec.refs import ProviderRef, is_registered, panel, provider

__all__ = ["install_settings_panels", "settings_hub_spec"]

_HUB_PROVIDER = "settings.hub_index"


def _ensure_hub_provider() -> ProviderRef:
    ref = ProviderRef(_HUB_PROVIDER)
    if not is_registered(ref):
        @provider(_HUB_PROVIDER)
        async def hub_index(ctx: object):
            from sb.kernel import settings as ksettings

            by_subsystem: dict[str, int] = {}
            for decl in ksettings.iter_declarations():
                by_subsystem[decl.subsystem] = by_subsystem.get(decl.subsystem, 0) + 1
            if not by_subsystem:
                return (("no declared settings", "port bands declare as they land"),)
            return tuple(
                (subsystem, f"{count} declared setting(s)")
                for subsystem, count in sorted(by_subsystem.items())
            )
    return ref


def settings_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="settings.hub",
        subsystem="settings",
        title="Settings",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Per-subsystem configuration. Every value resolves "
                      "per-guild explicit → global explicit → default."),
            FieldsBlock(provider=_ensure_hub_provider()),
        ),
        navigation=NavigationSpec(),   # help slot + FOLLOW_PARENT home
    )


@panel("settings.hub")
def _hub_factory() -> PanelSpec:
    return settings_hub_spec()


def install_settings_panels() -> PanelSpec:
    """Register the hub with the panels registry (fences run here);
    composition-root/boot call. Idempotent for the identical spec."""
    spec = settings_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    """Idempotent re-arm of the panel + hub-provider refs."""
    from sb.spec.refs import PanelRef, is_registered, panel as _panel

    _ensure_hub_provider()
    if not is_registered(PanelRef("settings.hub")):
        _panel("settings.hub")(_hub_factory)
