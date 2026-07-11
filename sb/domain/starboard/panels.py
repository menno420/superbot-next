"""Starboard config panel (the `_unmapped` starboard-family re-home) —
the shipped ``!starboard panel`` ``StarboardConfigPanel``
(disbot/views/starboard/config_panel.py, BaseView) at byte parity.

The shipped view was a timeout-bound session view (BaseView family,
author-locked, NO nav row), hence ``session_lifecycle=True``: run-minted
custom_ids (``_mint_ephemeral`` → the Normalizer's ``<cid:N>``), no
``panel_anchors`` row. goldens/starboard/sweep_starboard_panel pins every
byte of the OFF state: the two type-8 channel pickers ("Set the
hall-of-fame channel…" row 0 + "Toggle an ignored channel…" row 1), the
row-2 button trio (✏️ Threshold blurple / ⭐ Self-star grey / 🚫 Disable
red — emoji INSIDE the label strings), and the gold "⭐ Starboard config"
embed with the off-state description and the "Pick a channel below to
toggle its ignore state." footer.

State model (the shipped ``build_embed``): configured+enabled ⇒ the
Channel/Threshold/Self-stars description lines; else the off-state copy;
a non-empty ignore list adds the "🚫 Ignored channels" mentions field.
The COMPONENT SET is static across both states (every control is
decorator-declared on the shipped view) — the override only composes the
embed, never drops components.

Deliberate under-port notes (no golden drives any click): the shipped
view EDITED itself in place on every mutation (`_rerender`); the port
re-opens a fresh send (the projmoon edit-in-place deviation class,
ledgered). The ✏️ Threshold button opened a ``discord.ui.Modal`` — the
modal-driven ingress (D-0063's class); it lands as an honest pending
terminal until that slice ships.
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    SelectorKind,
    SelectorSpec,
    TextBlock,
)
from sb.spec.refs import HandlerRef, PanelRef, is_registered, panel

__all__ = [
    "CONFIG_PANEL_ID",
    "config_panel_spec",
    "ensure_panel_refs",
    "install_starboard_panels",
]

CONFIG_PANEL_ID = "starboard.config"

#: the shipped footer literal (config_panel.build_embed set_footer) —
#: outside FooterMode's vocabulary, hence the renderer_override (the
#: counting-hub precedent).
_FOOTER = "Pick a channel below to toggle its ignore state."

#: the shipped off-state description, verbatim —
#: goldens/starboard/sweep_starboard_panel pins every byte.
_DESC_OFF = ("Starboard is **off**. Pick a hall-of-fame channel below to "
             "turn it on (default threshold **3**, then tap "
             "**✏️ Threshold** to change).")


def config_panel_spec() -> PanelSpec:
    return PanelSpec(
        panel_id=CONFIG_PANEL_ID,
        subsystem="starboard",
        title="⭐ Starboard config",
        # the shipped view was author-locked (BaseView family).
        audience=Audience.INVOKER,
        # STAR_COLOR = discord.Color.gold() — the shipped accent
        # (config_panel.build_embed); STYLE_TOKEN_COLORS "gold" 15844367.
        frame=EmbedFrameSpec(style_token="gold", footer_mode=FooterMode.NONE),
        body=(TextBlock(""),),
        selectors=(
            # _ChannelPick — set the hall-of-fame channel (native
            # ChannelSelect, wire type 8; the golden pins channel_types
            # [0] + required false), row 0.
            SelectorSpec(
                selector_id="starboard_pick_channel",
                kind=SelectorKind.CHANNEL,
                placeholder="Set the hall-of-fame channel…",
                on_select=HandlerRef("starboard.panel_pick_channel"),
                audience_tier="staff"),
            # _IgnorePick — toggle a channel's ignore state, row 1.
            SelectorSpec(
                selector_id="starboard_toggle_ignore",
                kind=SelectorKind.CHANNEL,
                placeholder="Toggle an ignored channel…",
                on_select=HandlerRef("starboard.panel_toggle_ignore"),
                audience_tier="staff"),
        ),
        actions=(
            # the shipped row-2 trio — emoji INSIDE the label strings
            # (config_panel used @discord.ui.button(label="✏️ Threshold")
            # etc., never the separate emoji= field; the golden pins
            # label-only wire bytes).
            PanelActionSpec(
                action_id="starboard_threshold", label="✏️ Threshold",
                style=ActionStyle.PRIMARY, audience_tier="staff",
                handler=HandlerRef("starboard.panel_threshold")),
            PanelActionSpec(
                action_id="starboard_selfstar", label="⭐ Self-star",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                handler=HandlerRef("starboard.panel_selfstar")),
            PanelActionSpec(
                action_id="starboard_disable", label="🚫 Disable",
                style=ActionStyle.DANGER, audience_tier="staff",
                handler=HandlerRef("starboard.panel_disable")),
        ),
        # the shipped view carried NO nav row — the golden pins exactly
        # three component rows.
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("starboard.render_config"),
        justification=(
            "the shipped StarboardConfigPanel embed is state-keyed "
            "(config_panel.build_embed): the DESCRIPTION swaps between "
            "the configured Channel/Threshold/Self-stars lines and the "
            "off-state copy, a non-empty ignore list ADDS the "
            "'🚫 Ignored channels' mentions field, and the FOOTER is the "
            "shipped literal outside FooterMode's vocabulary ('Pick a "
            "channel below to toggle its ignore state.'). The override "
            "delegates to render_panel for the COMPONENTS (all bytes "
            "from the spec; the shipped component set is static across "
            "states) and composes only the EMBED. goldens/starboard/"
            "sweep_starboard_panel pins every off-state byte."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("starboard_pick_channel",),
            ("starboard_toggle_ignore",),
            ("starboard_threshold", "starboard_selfstar",
             "starboard_disable"),
        )),)),
    )


# --- renderer override --------------------------------------------------------------


async def _render_config(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped state-keyed embed assembly (see the
    spec justification)."""
    from sb.domain.starboard import service
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    base = await render_panel(spec, ctx)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    settings = await service.get_settings(gid)
    ignored = await service.list_ignore_channels(gid)

    if settings and settings["enabled"]:
        # the shipped configured branch (config_panel.build_embed) — the
        # oracle resolved the channel and fell back to the raw id in
        # backticks; the port renders the mention form (the resolver
        # fallback is an unpinned degradation corner).
        description = (
            f"**Channel:** <#{int(settings['channel_id'])}>\n"
            f"**Threshold:** {settings['emoji']} ≥ "
            f"**{settings['threshold']}**\n"
            f"**Self-stars:** "
            f"{'counted' if settings['self_star'] else 'ignored'}")
    else:
        description = _DESC_OFF

    fields: tuple[tuple, ...] = ()
    if ignored:
        # the shipped ignored-channels field (mentions joined, 1024 cap).
        mentions = ", ".join(f"<#{cid}>" for cid in ignored)[:1024]
        fields = (("🚫 Ignored channels", mentions, False),)

    embed = RenderedEmbed(
        title="⭐ Starboard config",
        description=description,
        fields=fields,
        footer=_FOOTER,
        style_token="gold")
    return _dc_replace(base, embed=embed)


# --- panel handlers -----------------------------------------------------------------


async def _reopen(req):
    """Fresh config-panel send (the shipped view edited in place — the
    ledgered projmoon deviation class; no golden pins any click)."""
    from sb.kernel.interaction.handler_kit import Reply
    from sb.kernel.panels.engine import open_panel
    from sb.spec.outcomes import SUCCESS

    await open_panel(PanelRef(CONFIG_PANEL_ID), req)
    return Reply(SUCCESS, None)


def _picked_channel(req) -> int:
    """First picked value as a channel id (native ChannelSelect values)."""
    values = tuple(req.args.get("values", ()) or ())
    if not values:
        return 0
    text = str(values[0]).strip().strip("<#>")
    return int(text) if text.isdigit() else 0


def _register_handlers() -> None:
    from sb.kernel.interaction.handler_kit import (
        Reply,
        ctx_from_request as _ctx_from_req,
    )
    from sb.spec.outcomes import BLOCKED, SUCCESS
    from sb.spec.refs import WorkflowRef, handler

    if is_registered(HandlerRef("starboard.render_config")):
        return

    handler("starboard.render_config")(_render_config)

    async def _run_op(req, op_key: str, params: dict) -> Reply | None:
        from sb.kernel.workflow import engine

        result = await engine.run(WorkflowRef(op_key),
                                  _ctx_from_req(req, params))
        if result.outcome != SUCCESS:
            return Reply(result.outcome, result.user_message)
        return None

    @handler("starboard.panel_pick_channel")
    async def panel_pick_channel(req) -> Reply:
        """_ChannelPick: configure the picked hall-of-fame channel — the
        shipped callback ran starboard_service.configure preserving the
        existing threshold/emoji (or the 3/⭐ defaults)."""
        from sb.domain.starboard import service

        picked = _picked_channel(req)
        if not picked:
            return await _reopen(req)
        settings = await service.get_settings(int(req.guild_id or 0))
        params = {
            "channel_id": picked,
            "threshold": int(settings["threshold"]) if settings else 3,
            "emoji": str(settings["emoji"]) if settings else "⭐",
        }
        failed = await _run_op(req, "starboard.configure", params)
        if failed is not None:
            return failed
        return await _reopen(req)

    @handler("starboard.panel_toggle_ignore")
    async def panel_toggle_ignore(req) -> Reply:
        """_IgnorePick: toggle the picked channel's ignore state (the
        shipped add-or-remove branch over the current list)."""
        from sb.domain.starboard import service

        picked = _picked_channel(req)
        if not picked:
            return await _reopen(req)
        ignored = await service.list_ignore_channels(int(req.guild_id or 0))
        op = ("starboard.ignore_remove" if picked in ignored
              else "starboard.ignore_add")
        failed = await _run_op(req, op, {"channel_id": picked})
        if failed is not None:
            return failed
        return await _reopen(req)

    @handler("starboard.panel_selfstar")
    async def panel_selfstar(req) -> Reply:
        """⭐ Self-star: the shipped toggle — ``new = not (settings and
        settings['self_star'])`` (config_panel.selfstar_btn verbatim)."""
        from sb.domain.starboard import service

        settings = await service.get_settings(int(req.guild_id or 0))
        new_value = not (settings and settings["self_star"])
        failed = await _run_op(req, "starboard.set_self_star",
                               {"self_star": new_value})
        if failed is not None:
            return failed
        return await _reopen(req)

    @handler("starboard.panel_disable")
    async def panel_disable(req) -> Reply:
        """🚫 Disable: the shipped disable lane (starboard.disable — the
        pure-UPDATE flip + unconditional audit)."""
        failed = await _run_op(req, "starboard.disable", {})
        if failed is not None:
            return failed
        return await _reopen(req)

    @handler("starboard.panel_threshold")
    async def panel_threshold(req) -> Reply:
        """✏️ Threshold — the shipped button opened a discord.ui.Modal
        (config_panel.threshold_btn): the modal-driven ingress (D-0063's
        class). Honest pending terminal until that slice ships; the
        threshold is settable today via `!starboard #channel <n>`."""
        return Reply(BLOCKED, "ℹ️ This starboard control is not ported "
                              "yet — set the threshold with "
                              "`!starboard #channel <n>` meanwhile.")


@panel(CONFIG_PANEL_ID)
def _config_factory() -> PanelSpec:
    return config_panel_spec()


_register_handlers()


def install_starboard_panels() -> tuple[PanelSpec, ...]:
    out = []
    for spec in (config_panel_spec(),):
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P, panel as _panel

    if not is_registered(_P(CONFIG_PANEL_ID)):
        _panel(CONFIG_PANEL_ID)(_config_factory)
    _register_handlers()
