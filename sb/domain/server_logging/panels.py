"""The logging hub panel (band 2) — `!logging`'s read-view v1."""

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

__all__ = ["ensure_panel_refs", "logging_hub_spec"]

_HUB_PROVIDER = "logging.hub_status"


def _ensure_hub_provider() -> ProviderRef:
    ref = ProviderRef(_HUB_PROVIDER)
    if not is_registered(ref):
        @provider(_HUB_PROVIDER)
        async def hub_status(ctx: object):
            from sb.domain.server_logging import service

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            config = await service.load_config(guild_id)
            mod = await service.bound_channel(guild_id, "mod")
            categories = [c for c, on in
                          sorted(config.category_enabled.items()) if on]
            return (
                ("Enabled", "🟢 on" if config.enabled else "⚪ off"),
                ("Mod channel", f"<#{mod}>" if mod else "*(unset)*"),
                ("Routing", f"`{config.routing}`"),
                ("Categories",
                 ", ".join(categories) if categories else "*(none)*"),
            )
    return ref


def logging_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="logging.hub",
        subsystem="logging",
        title="Server logging",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Operator log routing: `!logging status` / `enable` / "
                      "`set <slot> #channel` / `routes` / `test`."),
            FieldsBlock(provider=_ensure_hub_provider()),
        ),
        navigation=NavigationSpec(),
    )


@panel("logging.hub")
def _hub_factory() -> PanelSpec:
    return logging_hub_spec()


def install_logging_panels() -> PanelSpec:
    spec = logging_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef, is_registered as _is, panel as _panel

    _ensure_hub_provider()
    if not _is(PanelRef("logging.hub")):
        _panel("logging.hub")(_hub_factory)
