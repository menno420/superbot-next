"""Counting Manager hub (parity flip) — the shipped ``!countingmenu``
``_CountingHubView`` (disbot/views/counting/hub_panel.py @58040c6) at
byte parity.

The shipped view was a timeout-bound session view (``HubView`` family,
author-locked root panel — Help attaches Back externally, so NO nav
row), hence ``session_lifecycle=True``: run-minted custom_ids
(``_mint_ephemeral`` → the Normalizer's ``<cid:N>``), no
``panel_anchors`` row. goldens/counting/sweep_countingmenu pins every
byte of the INACTIVE state: the type-8 channel picker ("Select a
channel to manage…"), the 9-mode enable select (labels
``mode.capitalize()``, "Enable counting here — pick a mode…"), the
"🔄 Refresh" grey button, the blue "🔢 Counting Manager" embed with the
"is not an active counting channel" copy and the "Select a channel
above to manage it." footer.

State model (the shipped ``_rebuild``/``build_embed`` pair): the view
manages ONE selected channel (``self.selected_cid``, defaulting to the
invoking channel; the ChannelSelect re-targets it). INACTIVE target ⇒
ChannelPick + ModePick + Refresh; ACTIVE target ⇒ ChannelPick + the
four staff buttons (🔄 Toggle Turns / ♻️ Toggle Reset / 🔁 Reset Count /
🛑 Disable Here — emoji INSIDE the label strings, the shipped
decorator-less ``label=`` form) + Refresh, with the Managing embed
(Mode / Current Count / Taking Turns / Reset on Wrong inline fields,
"Buttons operate on the selected channel." footer). The pick memory is
process-local per (guild, invoker) — the logging ``_route_choice``
precedent (same class as the shipped View attribute).

Deliberate under-port notes (no golden drives any click — D-0064's
select lane): the shipped view EDITED itself in place on every
mutation/pick; the port re-opens a fresh hub send (the projmoon
edit-in-place deviation class, ledgered). ``multiples``/``custom``
modes stay on ``!start_match`` (the shipped NO_ARG_MODES split).
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
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    is_registered,
    panel,
)

__all__ = [
    "NO_ARG_MODES",
    "RULES_CARD_PANEL_ID",
    "counting_hub_spec",
    "ensure_panel_refs",
    "install_counting_panels",
    "rules_card_spec",
]

# shipped hub_panel._ENABLE_MODES verbatim (== _channel_manager.NO_ARG_MODES;
# panel-enable set, selector order) — the golden pins the 9 options in this
# order, labels capitalized.
NO_ARG_MODES = ("normal", "reverse", "skip", "random", "prime",
                "fibonacci", "squares", "cubes", "factorials")

#: the shipped footer literals (hub_panel.build_embed set_footer) — outside
#: FooterMode's vocabulary, hence the renderer_override (channel precedent).
_FOOTER_INACTIVE = "Select a channel above to manage it."
_FOOTER_ACTIVE = "Buttons operate on the selected channel."

#: the shipped view kept the managed channel on the View instance
#: (self.selected_cid); the port keys it per (guild, invoker), in-memory —
#: process-local UI state, the logging ``_route_choice`` precedent. Never
#: golden-rendered (the goldens' single open defaults to the invoking
#: channel), so no runner seeding is needed (playbook trap 20).
_manage_target: dict[tuple[int, int], int] = {}

#: the active-state components the INACTIVE render drops (and vice versa) —
#: the shipped ``_rebuild`` if/else, filtered by CANONICAL id in the
#: renderer_override (overrides run before ``_mint_ephemeral`` on open and
#: before the refresh remap, so canonical-id matching holds on both paths).
_ACTIVE_ONLY = frozenset({
    "counting.hub.counting_toggle_turns",
    "counting.hub.counting_toggle_reset",
    "counting.hub.counting_reset",
    "counting.hub.counting_disable",
})
_INACTIVE_ONLY = frozenset({"counting.hub.counting_enable_mode"})


def counting_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="counting.hub",
        subsystem="counting",
        title="🔢 Counting Manager",
        # the shipped view was author-locked to ctx.author (HubView).
        audience=Audience.INVOKER,
        # discord.Color.blue() — the shipped accent (build_embed).
        frame=EmbedFrameSpec(style_token="blue", footer_mode=FooterMode.NONE),
        body=(TextBlock(""),),
        selectors=(
            # _ChannelPick — Discord-native text-channel picker (wire type
            # 8; the golden pins channel_types [0] + required false).
            SelectorSpec(
                selector_id="counting_pick_channel",
                kind=SelectorKind.CHANNEL,
                placeholder="Select a channel to manage…",
                on_select=HandlerRef("counting.hub_pick_channel"),
                audience_tier="user"),
            # _ModePick — enable counting on the selected INACTIVE channel;
            # provider-fed rich options (label=mode.capitalize(),
            # value=mode — the shipped SelectOption pair; trap 14i lane).
            SelectorSpec(
                selector_id="counting_enable_mode",
                kind=SelectorKind.ENUM,
                placeholder="Enable counting here — pick a mode…",
                options_source=ProviderRef("counting.enable_mode_options"),
                on_select=HandlerRef("counting.hub_enable_mode"),
                audience_tier="staff"),
        ),
        actions=(
            # the shipped active-state staff row pair — emoji INSIDE the
            # label strings (hub_panel used label="🔄 Toggle Turns" etc.,
            # never the separate emoji= field).
            PanelActionSpec(
                action_id="counting_toggle_turns", label="🔄 Toggle Turns",
                style=ActionStyle.PRIMARY, audience_tier="staff",
                handler=HandlerRef("counting.hub_toggle_turns")),
            PanelActionSpec(
                action_id="counting_toggle_reset", label="♻️ Toggle Reset",
                style=ActionStyle.PRIMARY, audience_tier="staff",
                handler=HandlerRef("counting.hub_toggle_reset")),
            PanelActionSpec(
                action_id="counting_reset", label="🔁 Reset Count",
                style=ActionStyle.DANGER, audience_tier="staff",
                handler=HandlerRef("counting.hub_reset")),
            PanelActionSpec(
                action_id="counting_disable", label="🛑 Disable Here",
                style=ActionStyle.DANGER, audience_tier="staff",
                handler=HandlerRef("counting.hub_disable")),
            # _RefreshButton — grey, both states.
            PanelActionSpec(
                action_id="counting_refresh", label="🔄 Refresh",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("counting.hub_refresh")),
        ),
        # the shipped root panel carried NO nav row (Help attaches Back
        # externally — consistency_exceptions.yml names _CountingHubView);
        # the golden pins exactly three component rows.
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("counting.render_hub"),
        justification=(
            "the shipped _CountingHubView is state-keyed on the managed "
            "channel (hub_panel._rebuild + build_embed): the EMBED "
            "description/fields/footer are state-dependent copy the "
            "grammar cannot express ('<#…> is not an active counting "
            "channel…' + 'Select a channel above to manage it.' vs "
            "'Managing <#…>' + Mode/Current Count/Taking Turns/Reset on "
            "Wrong inline fields + 'Buttons operate on the selected "
            "channel.'), and the COMPONENT SET swaps with the same state "
            "(inactive ⇒ ModePick, no staff buttons; active ⇒ the four "
            "staff buttons, no ModePick — the shipped _rebuild if/else). "
            "The override delegates to render_panel and (1) composes the "
            "EMBED, (2) drops exactly the other state's components by "
            "canonical id (_ACTIVE_ONLY / _INACTIVE_ONLY above); every "
            "kept component's bytes come from the spec. goldens/counting/"
            "sweep_countingmenu pins every inactive-state byte."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("counting_pick_channel",),
            ("counting_enable_mode",),
            ("counting_toggle_turns", "counting_toggle_reset"),
            ("counting_reset", "counting_disable"),
            ("counting_refresh",),
        )),)),
    )


# --- state reads ------------------------------------------------------------------


def _target_of(ctx_or_req) -> tuple[int, int]:
    """(guild_id, managed channel) — pick memory, else the invoking
    channel (the shipped selected_cid default)."""
    gid = int(getattr(ctx_or_req, "guild_id", 0) or 0)
    actor = getattr(ctx_or_req, "actor", None)
    uid = int(getattr(actor, "user_id", 0) or 0)
    fallback = int(getattr(ctx_or_req, "channel_id", 0) or 0)
    return gid, _manage_target.get((gid, uid), fallback)


async def _channel_data(gid: int, channel_id: int) -> dict | None:
    """The shipped _channel_data read: the per-channel blob or None."""
    from sb.domain.counting import store

    state = await store.get_state(gid)
    return (state.get("channels") or {}).get(str(channel_id))


# --- renderer override --------------------------------------------------------------


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped state-keyed embed/component assembly
    (see the spec justification)."""
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    base = await render_panel(spec, ctx)
    gid, target = _target_of(ctx)
    data = await _channel_data(gid, target)

    if data:
        drop = _INACTIVE_ONLY
        embed = RenderedEmbed(
            title="🔢 Counting Manager",
            description=f"Managing <#{target}>",
            fields=(
                ("Mode", str(data.get("mode", "normal")).capitalize(), True),
                ("Current Count", str(data.get("current_count", 0)), True),
                ("Taking Turns",
                 "✅" if data.get("taking_turns", False) else "❌", True),
                ("Reset on Wrong",
                 "✅" if data.get("reset_on_wrong_count", False) else "❌",
                 True),
            ),
            footer=_FOOTER_ACTIVE,
            style_token="blue")
    else:
        drop = _ACTIVE_ONLY
        embed = RenderedEmbed(
            title="🔢 Counting Manager",
            description=(
                f"<#{target}> is not an active counting channel.\n\n"
                "Pick a mode below to **enable counting here**, or select "
                "another channel above. `!start_match <mode>` still "
                "creates a fresh channel."),
            footer=_FOOTER_INACTIVE,
            style_token="blue")

    components = tuple(c for c in base.components if c.custom_id not in drop)
    return _dc_replace(base, embed=embed, components=components)


# --- hub handlers -------------------------------------------------------------------


async def _reopen(req):
    """Fresh hub send (the shipped view edited in place — the ledgered
    projmoon deviation class; no golden pins any click)."""
    from sb.kernel.panels.engine import open_panel
    from sb.kernel.interaction.handler_kit import Reply
    from sb.spec.outcomes import SUCCESS

    await open_panel(PanelRef("counting.hub"), req)
    return Reply(SUCCESS, None)


def _register_handlers() -> None:
    from sb.kernel.interaction.handler_kit import (
        Reply,
        ctx_from_request as _ctx_from_req,
    )
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import handler, provider, resolve

    if is_registered(HandlerRef("counting.render_hub")):
        return

    handler("counting.render_hub")(_render_hub)

    @provider("counting.enable_mode_options")
    async def enable_mode_options(ctx) -> tuple[dict, ...]:
        # the shipped SelectOption(label=mode.capitalize(), value=mode)
        # pairs — goldens/counting/sweep_countingmenu pins all nine.
        return tuple({"label": mode.capitalize(), "value": mode}
                     for mode in NO_ARG_MODES)

    @handler("counting.hub_pick_channel")
    async def hub_pick_channel(req) -> Reply:
        # _ChannelPick: re-target the manager onto the picked channel.
        values = tuple(req.args.get("values", ()) or ())
        picked = 0
        if values:
            text = str(values[0]).strip().strip("<#>")
            if text.isdigit():
                picked = int(text)
        gid = int(req.guild_id or 0)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        if picked:
            _manage_target[(gid, uid)] = picked
        return await _reopen(req)

    @handler("counting.hub_refresh")
    async def hub_refresh(req) -> Reply:
        return await _reopen(req)

    @handler("counting.hub_enable_mode")
    async def hub_enable_mode(req) -> Reply:
        # _ModePick: enable counting on the SELECTED (inactive) channel —
        # the shipped whitelist flow (no fresh channel).
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        values = tuple(req.args.get("values", ()) or ())
        mode = str(values[0]).lower() if values else ""
        _, target = _target_of(req)
        result = await engine.run(
            WorkflowRef("counting.enable_channel"),
            _ctx_from_req(req, {"channel_id": target, "mode": mode}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Couldn't start a match.")
        return await _reopen(req)

    def _targeted(route_ref: str):
        # the four staff buttons operate on the SELECTED channel (the
        # shipped footer says so): inject channel_id for _target_channel.
        async def run(req) -> Reply:
            import dataclasses

            _, target = _target_of(req)
            merged = {**dict(req.args or {}), "channel_id": target}
            out = await resolve(HandlerRef(route_ref))(
                dataclasses.replace(req, args=merged))
            if out.outcome != SUCCESS:
                return out
            return await _reopen(req)
        return run

    handler("counting.hub_toggle_turns")(
        _targeted("counting.toggle_turns_route"))
    handler("counting.hub_toggle_reset")(
        _targeted("counting.toggle_reset_route"))
    handler("counting.hub_reset")(_targeted("counting.reset_route"))
    handler("counting.hub_disable")(_targeted("counting.end_match_route"))


@panel("counting.hub")
def _hub_factory() -> PanelSpec:
    return counting_hub_spec()


RULES_CARD_PANEL_ID = "counting.rules_card"

#: the shipped rules embed fields VERBATIM (cogs/counting_cog.py
#: `count_rules` — five non-inline add_field rows;
#: goldens/counting/sweep_count_rules pins every byte).
_RULES_FIELDS: tuple[tuple[str, str], ...] = (
    ("1. Follow the Sequence",
     "Provide the correct next number based on the game mode."),
    ("2. Taking Turns",
     "If enabled, users must take turns before counting again."),
    ("3. Mode-Specific Rules",
     "Each counting mode has unique rules (e.g., Fibonacci sequence, "
     "squares)."),
    ("4. Respect the Channel",
     "Use only the designated counting channel for the game."),
    ("5. Have Fun!",
     "Enjoy the game and encourage others to participate."),
)


def rules_card_spec() -> PanelSpec:
    """The shipped `!count_rules` rules embed (cogs/counting_cog.py — a
    plain ``ctx.send(embed=...)``, never anchored: component-less
    session-lifecycle, the welcome/karma.card recipe;
    goldens/counting/sweep_count_rules pins the bytes)."""
    return PanelSpec(
        panel_id=RULES_CARD_PANEL_ID,
        subsystem="counting",
        title="Counting Game Rules",
        audience=Audience.INVOKER,
        # discord.Color.green() — the shipped accent
        frame=EmbedFrameSpec(style_token="green",
                             footer_mode=FooterMode.NONE),
        body=(),
        actions=(),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("counting.render_rules_card"),
        justification=(
            "the shipped rules embed carries FIVE non-inline add_field "
            "rows and no description (cogs/counting_cog.py count_rules' "
            "literal add_field list — goldens/counting/sweep_count_rules "
            "pins every byte); the card declares no components and the "
            "renderer only composes the embed (the welcome status-card "
            "recipe)."),
        session_lifecycle=True,
    )


async def _render_rules_card(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped static embed verbatim (see
    _RULES_FIELDS)."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    embed = RenderedEmbed(
        title="Counting Game Rules",
        description="",
        fields=_RULES_FIELDS,
        footer="",
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


@panel(RULES_CARD_PANEL_ID)
def _rules_factory() -> PanelSpec:
    return rules_card_spec()


_register_handlers()


def _register_rules_render() -> None:
    from sb.spec.refs import handler as _handler

    if not is_registered(HandlerRef("counting.render_rules_card")):
        _handler("counting.render_rules_card")(_render_rules_card)


_register_rules_render()


def install_counting_panels() -> tuple[PanelSpec, ...]:
    out = []
    for spec in (counting_hub_spec(), rules_card_spec()):
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

    if not is_registered(_P("counting.hub")):
        _panel("counting.hub")(_hub_factory)
    if not is_registered(_P(RULES_CARD_PANEL_ID)):
        _panel(RULES_CARD_PANEL_ID)(_rules_factory)
    _register_rules_render()
    _register_handlers()
