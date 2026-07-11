"""The treasury panel (band 3, parity flip) — the shipped `TreasuryView`
made declarative (the panel-action slice), byte-for-byte as
parity/goldens/treasury/sweep_treasury.json pins it: **➕ Contribute** opens
the shipped one-field modal (G-10 `ModalSpec` — submit re-enters the frozen
MODAL adapter and runs the audited `treasury.contribute` op); **🔄 Refresh**
re-reads and redraws.

Disbursing from the pool is intentionally NOT a panel button (shipped
posture, verbatim): an ordinary member's panel can only ever move their OWN
coins in — `!treasury grant` stays the manage_guild-gated command.

The shipped view (`disbot/cogs/treasury_cog.py` `TreasuryView`) was
ctx-bound and timeout-based (view-local button decorators, no persistent
custom_ids) — `session_lifecycle=True`, run-minted `<cid:1>`/`<cid:2>` ids
(the cleanup words-manager precedent), no nav row (`show_help=False,
show_home=False` — the shipped view carried ONLY its own two buttons), no
`panel_anchors` row (the golden's db_delta carries none)."""

from __future__ import annotations

from dataclasses import replace as _dc_replace

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
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    WorkflowRef,
    handler,
    is_registered,
    panel,
    provider,
)

__all__ = ["ensure_panel_refs", "install_treasury_panels", "treasury_hub_spec"]

#: the shipped footer literal (TreasuryView.embed set_footer) — outside
#: FooterMode's none/subsystem/provenance vocabulary, hence the
#: renderer_override below (the cleanup-hub precedent).
_HUB_FOOTER = "➕ Contribute · 🔄 Refresh"

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
            return tuple(fields)
    return ref


def treasury_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="treasury.hub",
        subsystem="treasury",
        title="🏛️ Server Treasury",
        audience=Audience.INVOKER,
        # the shipped accent — discord.Color.gold() (ECONOMY_COLOR token).
        frame=EmbedFrameSpec(style_token="gold", footer_mode=FooterMode.NONE),
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
        # the shipped TreasuryView carried ONLY its own two buttons (no nav
        # row; timeout session view) — the golden pins exactly ONE component
        # row; the never-strand fence takes the session-view exemption (the
        # cleanup words-manager precedent).
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("treasury.render_hub"),
        justification=(
            "the shipped panel footer is the literal '➕ Contribute · 🔄 "
            "Refresh' (disbot/cogs/treasury_cog.py TreasuryView set_footer) "
            "— outside FooterMode's none/subsystem/provenance vocabulary — "
            "and both fields render inline=True (the shipped add_field "
            "calls) — outside the grammar's vocabulary (2-tuple fields "
            "render inline=False). parity/goldens/treasury/"
            "sweep_treasury.json pins both bytes (the cleanup-hub "
            "precedent). The override delegates to the grammar renderer "
            "and adjusts ONLY those two surfaces; body, fields, actions "
            "and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(("contribute", "refresh"),)),)),
    )


@handler("treasury.render_hub")
async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the two shipped adjustments (see justification):
    the footer literal and both fields rendered inline."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    fields = tuple((f[0], f[1], True) for f in rendered.embed.fields)
    return _dc_replace(
        rendered,
        embed=_dc_replace(rendered.embed, footer=_HUB_FOOTER, fields=fields))


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
    if not is_registered(HandlerRef("treasury.render_hub")):
        handler("treasury.render_hub")(_render_hub)
    if not _is(_P("treasury.hub")):
        _panel("treasury.hub")(_hub_factory)
