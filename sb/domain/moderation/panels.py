"""The moderation hub panel (band 2) — `modmenu`'s read-view v1 (the
band-1 hub pattern): policy snapshot + recent-history pointer; mutation
actions arrive with the panel-action slice (successor work)."""

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

__all__ = ["ensure_panel_refs", "moderation_hub_spec"]

_HUB_PROVIDER = "moderation.hub_policy"


def _ensure_hub_provider() -> ProviderRef:
    ref = ProviderRef(_HUB_PROVIDER)
    if not is_registered(ref):
        @provider(_HUB_PROVIDER)
        async def hub_policy(ctx: object):
            from sb.domain.moderation.service import load_policy

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            p = await load_policy(guild_id)
            return (
                ("Warn threshold",
                 f"{p.warn_threshold} → {p.warn_escalation_action} "
                 f"({p.warn_timeout_minutes}m timeout)"),
                ("Require reason", "on" if p.require_reason else "off"),
                ("DM on action",
                 f"{'on' if p.dm_on_action else 'off'} ({p.dm_actions})"),
                ("Ban message sweep", f"{p.ban_delete_message_days} day(s)"),
                ("Post-action cleanup",
                 f"{p.post_action_cleanup} "
                 f"(limit {p.post_action_cleanup_limit})"),
                ("Public log", p.public_log_actions),
            )
    return ref


def moderation_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="moderation.hub",
        subsystem="moderation",
        title="Moderation",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Warn / timeout / kick / ban lanes run through the "
                      "audited seam; policy below resolves per-guild → "
                      "global → shipped defaults."),
            FieldsBlock(provider=_ensure_hub_provider()),
        ),
        navigation=NavigationSpec(),
    )


@panel("moderation.hub")
def _hub_factory() -> PanelSpec:
    return moderation_hub_spec()


def install_moderation_panels() -> PanelSpec:
    spec = moderation_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef, is_registered as _is, panel as _panel

    _ensure_hub_provider()
    if not _is(PanelRef("moderation.hub")):
        _panel("moderation.hub")(_hub_factory)
