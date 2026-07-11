"""Chain Manager hub (parity flip) — the shipped ``!chainmenu``
``_ChainMenuView`` (disbot/cogs/chain_cog.py @58040c6) at byte parity.

The shipped view was a plain session ``discord.ui.View`` send (never
anchored), hence ``session_lifecycle=True``: run-minted custom_ids
(``_mint_ephemeral`` → the Normalizer's ``<cid:N>``), no
``panel_anchors`` row, and NO nav row. goldens/chain/sweep_chainmenu
pins every byte: row 0 = ➕ Create Chain (green) / 🗑️ Delete Chain
(danger) / 📏 Set Limit (blurple) / 🚫 Clear Limit (grey), row 1 =
🔄 Refresh (grey) — emoji INSIDE the label strings (the shipped
``label=`` form) — under the blue "⛓️ Chain Manager" embed with the
state-dependent description ("No active chains in this server." /
the per-channel ``{mention} — word: `w`, limit: `n``` lines) and the
"Use buttons below to manage chains." footer literal.

The four buttons keep their G-10 modals (the shipped _CreateChainModal
/ _DeleteChainModal / _SetLimitModal / _ClearLimitModal quartet, each
with the 'Channel (mention/ID, blank = current)' field) — modal_ids
unchanged (compat-pinned). Ledgered deviation (no golden drives any
click): the shipped Refresh edited the message in place; the port
re-opens a fresh hub send (the projmoon edit-in-place class)."""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.outcomes import DeferMode
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
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
from sb.spec.refs import HandlerRef, PanelRef, is_registered, panel

__all__ = ["chain_hub_spec", "ensure_panel_refs", "install_chain_panels"]

#: the shipped footer literal (chain_cog build_embed set_footer) —
#: outside FooterMode's vocabulary, hence the renderer_override
#: (the channel/counting precedent).
_FOOTER = "Use buttons below to manage chains."

_CHANNEL_FIELD = ModalFieldSpec(
    field_id="channel", label="Channel (mention/ID, blank = current)",
    required=False, max_length=32)

CREATE_MODAL = ModalSpec(
    modal_id="chain.create_form",
    title="Create Chain",
    fields=(
        _CHANNEL_FIELD,
        ModalFieldSpec(field_id="word", label="Allowed word",
                       required=True, max_length=100),
    ),
    on_submit=HandlerRef("chain.create_route"),
)

DELETE_MODAL = ModalSpec(
    modal_id="chain.delete_form",
    title="Delete Chain",
    fields=(_CHANNEL_FIELD,),
    on_submit=HandlerRef("chain.delete_route"),
)

SET_LIMIT_MODAL = ModalSpec(
    modal_id="chain.set_limit_form",
    title="Set Word Limit",
    fields=(
        _CHANNEL_FIELD,
        # the shipped setlimit guard rejects <= 0 (removal is the Clear
        # Limit / !chain removelimit lane) — the field label promises
        # accordingly.
        ModalFieldSpec(field_id="limit", label="Word limit (> 0)",
                       required=True, max_length=6),
    ),
    on_submit=HandlerRef("chain.setlimit_route"),
)

CLEAR_LIMIT_MODAL = ModalSpec(
    modal_id="chain.clear_limit_form",
    title="Clear Word Limit",
    fields=(_CHANNEL_FIELD,),
    on_submit=HandlerRef("chain.removelimit_route"),
)


def chain_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="chain.hub",
        subsystem="chain",
        title="⛓️ Chain Manager",
        audience=Audience.INVOKER,
        # discord.Color.blue() — the shipped accent (build_embed).
        frame=EmbedFrameSpec(style_token="blue", footer_mode=FooterMode.NONE),
        body=(TextBlock(""),),
        actions=(
            # the shipped row-0 quartet — emoji INSIDE the labels, the
            # G-10 modal per button (the shipped send_modal callbacks).
            PanelActionSpec(
                action_id="chain_create", label="➕ Create Chain",
                style=ActionStyle.SUCCESS, audience_tier="staff",
                handler=HandlerRef("chain.create_route"),
                defer_mode=DeferMode.MODAL, modal=CREATE_MODAL,
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="chain_delete", label="🗑️ Delete Chain",
                style=ActionStyle.DANGER, audience_tier="staff",
                handler=HandlerRef("chain.delete_route"),
                defer_mode=DeferMode.MODAL, modal=DELETE_MODAL,
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="chain_set_limit", label="📏 Set Limit",
                style=ActionStyle.PRIMARY, audience_tier="staff",
                handler=HandlerRef("chain.setlimit_route"),
                defer_mode=DeferMode.MODAL, modal=SET_LIMIT_MODAL,
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="chain_clear_limit", label="🚫 Clear Limit",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                handler=HandlerRef("chain.removelimit_route"),
                defer_mode=DeferMode.MODAL, modal=CLEAR_LIMIT_MODAL,
                result_render=ResultRender.RESULT_CARD),
            # the shipped row-1 Refresh (edit-in-place lives as reopen).
            PanelActionSpec(
                action_id="chain_refresh", label="🔄 Refresh",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                handler=HandlerRef("chain.hub_refresh")),
        ),
        # the shipped view carried no nav row — the golden pins exactly
        # two component rows.
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("chain.render_hub"),
        justification=(
            "the shipped _ChainMenuView embed is state-dependent copy "
            "the grammar cannot express (build_embed: 'No active chains "
            "in this server.' vs the per-channel '{mention} — word: "
            "`w`, limit: `n`' lines over get_all_chain_channels) plus "
            "the footer literal 'Use buttons below to manage chains.' — "
            "outside FooterMode's vocabulary. The override delegates the "
            "COMPONENTS to render_panel (declared actions untouched) "
            "and composes the EMBED only (title, blue, description, "
            "footer). goldens/chain/sweep_chainmenu pins every byte."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("chain_create", "chain_delete", "chain_set_limit",
             "chain_clear_limit"),
            ("chain_refresh",),
        )),)),
    )


# --- renderer override --------------------------------------------------------------


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped state-dependent embed (see the spec
    justification)."""
    from sb.domain.chain import store
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    base = await render_panel(spec, ctx)
    rows = await store.get_all_chain_channels(int(ctx.guild_id or 0))
    if not rows:
        description = "No active chains in this server."
    else:
        lines = []
        for entry in rows:
            # shipped: ch.mention if resolvable else f"<#{id}>" — the
            # port renders the mention form directly.
            name = f"<#{entry['channel_id']}>"
            parts = []
            if entry.get("word"):
                parts.append(f"word: `{entry['word']}`")
            if entry.get("word_limit"):
                parts.append(f"limit: `{entry['word_limit']}`")
            lines.append(f"{name} — {', '.join(parts) or 'no restrictions'}")
        description = "\n".join(lines)
    embed = RenderedEmbed(
        title="⛓️ Chain Manager",
        description=description,
        footer=_FOOTER,
        style_token="blue")
    return _dc_replace(base, embed=embed)


def _register_handlers() -> None:
    from sb.kernel.interaction.handler_kit import Reply
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import handler

    if is_registered(HandlerRef("chain.render_hub")):
        return

    handler("chain.render_hub")(_render_hub)

    @handler("chain.hub_refresh")
    async def hub_refresh(req) -> Reply:
        from sb.kernel.panels.engine import open_panel

        await open_panel(PanelRef("chain.hub"), req)
        return Reply(SUCCESS, None)


@panel("chain.hub")
def _hub_factory() -> PanelSpec:
    return chain_hub_spec()


_register_handlers()


def install_chain_panels() -> PanelSpec:
    spec = chain_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P, panel as _panel

    if not is_registered(_P("chain.hub")):
        _panel("chain.hub")(_hub_factory)
    _register_handlers()
