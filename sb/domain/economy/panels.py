"""The economy hub panel (band 3) — `economymenu`/`/economy`'s read-view v1
(the band-1/2 hub pattern): loop status + catalogue snapshot; the shipped
Daily/Work/Shop/... button actions arrive with the panel-action slice
(successor work, like every hub so far)."""

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

__all__ = ["economy_hub_spec", "ensure_panel_refs", "install_economy_panels"]

_HUB_PROVIDER = "economy.hub_overview"


def _ensure_hub_provider() -> ProviderRef:
    ref = ProviderRef(_HUB_PROVIDER)
    if not is_registered(ref):
        @provider(_HUB_PROVIDER)
        async def hub_overview(ctx: object):
            from sb.domain.economy import catalogue, service, store

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            user_id = int(getattr(ctx, "user_id", 0) or
                          getattr(getattr(ctx, "actor", None), "user_id", 0)
                          or 0)
            fields = [
                ("Jobs", f"{len(catalogue.JOBS)} jobs across 4 tiers — "
                         f"`!work <job>` (1h cooldown)"),
                ("Shop", ", ".join(
                    f"{d['emoji']} {name} ({d['price']:,})"
                    for name, d in catalogue.SHOP_ITEMS.items())),
                ("Daily", "`!daily` — streaks shift the reward odds upward"),
            ]
            if user_id:
                coins = await store.get_coins(user_id, guild_id)
                row = await store.read_economy(user_id, guild_id)
                fields.insert(0, ("Your wallet",
                                  f"🪙 {coins:,} · 🔥 streak "
                                  f"{row.get('daily_streak', 0)}"))
            log_channel = await service.bound_log_channel(guild_id)
            fields.append(("Log channel",
                           f"<#{log_channel}>" if log_channel
                           else "*(unbound — `!setlogchannel #channel`)*"))
            return tuple(fields)
    return ref


def economy_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="economy.hub",
        subsystem="economy",
        title="Economy",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Daily rewards, jobs, the item shop, and transfers — "
                      "every coin movement rides the audited seam and the "
                      "economy_audit_log money trail."),
            FieldsBlock(provider=_ensure_hub_provider()),
        ),
        navigation=NavigationSpec(),
    )


@panel("economy.hub")
def _hub_factory() -> PanelSpec:
    return economy_hub_spec()


def install_economy_panels() -> PanelSpec:
    spec = economy_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef, is_registered as _is, panel as _panel

    _ensure_hub_provider()
    if not _is(PanelRef("economy.hub")):
        _panel("economy.hub")(_hub_factory)
