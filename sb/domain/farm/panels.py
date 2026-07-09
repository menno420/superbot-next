"""Farm panel (band 6) — the shipped farm view made declarative: settled
status provider + Collect / Buy Hen / Upgrade Coop actions over the
audited K7 lanes."""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
    TextBlock,
)
from sb.spec.refs import PanelRef, ProviderRef, WorkflowRef, is_registered, panel, provider

__all__ = ["ensure_panel_refs", "farm_hub_spec", "install_farm_panels"]

_STATUS_PROVIDER = "farm.hub_status"


def _ensure_status_provider() -> ProviderRef:
    ref = ProviderRef(_STATUS_PROVIDER)
    if not is_registered(ref):
        @provider(_STATUS_PROVIDER)
        async def hub_status(ctx: object):
            import datetime as dt

            from sb.domain.farm import core, store

            uid = int(getattr(getattr(ctx, "actor", None), "user_id", 0)
                      or 0)
            gid = int(getattr(ctx, "guild_id", 0) or 0)
            now = int(dt.datetime.now(tz=dt.timezone.utc).timestamp())
            chickens, eggs, ts, coop = await store.get_farm(uid, gid)
            settled = core.settle(
                core.FarmState(chickens, eggs, ts or now, coop), now)
            cap = core.coop_capacity(settled.coop_level)
            return (
                ("Coop", core.egg_bar(settled.eggs, cap)),
                ("Flock", f"🐔 **{settled.chickens}** hen(s) — "
                          f"{core.lay_rate_per_hour(settled.chickens)} "
                          f"eggs/hour"),
                ("Next hen", f"**{core.chicken_price(settled.chickens)}** "
                             "🪙"),
                ("Coop upgrade",
                 f"**{core.coop_upgrade_price(settled.coop_level)}** 🪙 "
                 f"(level {settled.coop_level}/{core.MAX_COOP_LEVEL})"),
            )
    return ref


def farm_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="farm.hub",
        subsystem="farm",
        title="🐔 Chicken Farm",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Your idle farm — hens lay eggs while you're away. "
                      "Collect eggs for coins, buy hens to lay faster, "
                      "and upgrade the coop to hold more."),
            FieldsBlock(provider=_ensure_status_provider()),
        ),
        actions=(
            PanelActionSpec(
                action_id="farm_collect", label="Collect", emoji="🥚",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=WorkflowRef("farm.collect"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="farm_buy_hen", label="Buy Hen", emoji="🐔",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=WorkflowRef("farm.buy_chicken"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="farm_upgrade_coop", label="Upgrade Coop",
                emoji="🏠", style=ActionStyle.PRIMARY,
                audience_tier="user",
                handler=WorkflowRef("farm.upgrade_coop"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="farm_refresh", label="Refresh", emoji="🔄",
                audience_tier="user", handler=PanelRef("farm.hub"),
                result_render=ResultRender.REFRESH_PANEL),
        ),
        navigation=NavigationSpec(parent=PanelRef("games.world")),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("farm_collect", "farm_buy_hen", "farm_upgrade_coop",
             "farm_refresh"),)),)),
    )


@panel("farm.hub")
def _hub_factory() -> PanelSpec:
    return farm_hub_spec()


def install_farm_panels() -> PanelSpec:
    spec = farm_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P, panel as _panel

    _ensure_status_provider()
    if not is_registered(_P("farm.hub")):
        _panel("farm.hub")(_hub_factory)
