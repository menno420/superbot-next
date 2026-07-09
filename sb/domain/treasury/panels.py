"""The treasury panel (band 3) — the shipped `TreasuryView` made declarative
(the panel-action slice): **➕ Contribute** opens the shipped one-field modal
(G-10 `ModalSpec` — submit re-enters the frozen MODAL adapter and runs the
audited `treasury.contribute` op); **🔄 Refresh** re-reads and redraws.

Disbursing from the pool is intentionally NOT a panel button (shipped
posture, verbatim): an ordinary member's panel can only ever move their OWN
coins in — `!treasury grant` stays the manage_guild-gated command."""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.outcomes import DeferMode
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    ModalFieldSpec,
    ModalSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
    TextBlock,
)
from sb.spec.refs import PanelRef, ProviderRef, WorkflowRef, is_registered, panel, provider

__all__ = ["ensure_panel_refs", "install_treasury_panels", "treasury_hub_spec"]

_HUB_PROVIDER = "treasury.hub_overview"

CONTRIBUTE_MODAL = ModalSpec(
    modal_id="treasury.contribute_form",
    title="Contribute to the treasury",          # shipped modal title verbatim
    fields=(
        ModalFieldSpec(
            field_id="amount", label="Amount (coins)",
            placeholder="e.g. 100", required=True, max_length=12),
    ),
    on_submit=WorkflowRef("treasury.contribute"),
)


def _ensure_hub_provider() -> ProviderRef:
    ref = ProviderRef(_HUB_PROVIDER)
    if not is_registered(ref):
        @provider(_HUB_PROVIDER)
        async def hub_overview(ctx: object):
            from sb.domain.economy.store import get_coins
            from sb.domain.treasury.store import get_treasury

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            user_id = int(getattr(getattr(ctx, "actor", None), "user_id", 0)
                          or 0)
            balance = await get_treasury(guild_id)
            fields = [("Treasury", f"🏛️ **{balance:,}** 🪙 in the pool")]
            if user_id:
                wallet = await get_coins(user_id, guild_id)
                fields.append(("Your wallet", f"🪙 **{wallet:,}** 🪙"))
            fields.append(
                ("Disburse", "`!treasury grant @member <amount>` — "
                             "managers grant coins from the pool"))
            return tuple(fields)
    return ref


def treasury_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="treasury.hub",
        subsystem="treasury",
        title="🏛️ Server Treasury",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("The server's shared coin pool. Everyone can "
                      "**Contribute** their own coins to grow it; server "
                      "managers disburse from it with "
                      "`!treasury grant @member <amount>`."),
            FieldsBlock(provider=_ensure_hub_provider()),
        ),
        actions=(
            PanelActionSpec(
                action_id="contribute", label="Contribute", emoji="➕",
                style=ActionStyle.SUCCESS, audience_tier="user",
                defer_mode=DeferMode.MODAL,
                modal=CONTRIBUTE_MODAL,
                handler=WorkflowRef("treasury.contribute"),
                audit="economy.balance_changed"),
            PanelActionSpec(
                action_id="refresh", label="Refresh", emoji="🔄",
                audience_tier="user",
                handler=PanelRef("treasury.hub"),
                result_render=ResultRender.REFRESH_PANEL),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(("contribute", "refresh"),)),)),
    )


@panel("treasury.hub")
def _hub_factory() -> PanelSpec:
    return treasury_hub_spec()


def install_treasury_panels() -> PanelSpec:
    spec = treasury_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P, is_registered as _is, panel as _panel

    _ensure_hub_provider()
    if not _is(_P("treasury.hub")):
        _panel("treasury.hub")(_hub_factory)
