"""BTD6 panels (band 7) — the SHIPPED hub (`!btd6` / `!btd6menu` →
views/btd6/panel.py BTD6PanelView, Menu Layout B) plus the oracle-card
presentation panels.

* ``btd6.hub`` — the shipped 🐵 BTD6 Assistant panel byte-for-byte
  (goldens/btd6/sweep_btd6 + sweep_btd6menu): the Layout-B category hub —
  row 0 Ask (🧠, green) / Live Events / Units / Rounds; row 1 Maps & Modes
  / Strategy / Status / 🛠️ Admin — on the shipped PERSISTENT custom_ids
  (``btd6:ask`` … ``btd6:admin``, carried verbatim via
  ``custom_id_override``). The shipped view was never anchored in
  panel_anchors (``session_lifecycle=True`` — the goldens pin the
  no-anchor-row delta) and never edited on click.
* ``btd6.card`` — the generic one-embed reply card every `!btd6 <sub>`
  command presents through (the shipped ``ctx.send(embed=…)``).
* ``btd6.ctteam`` — the CT-team view + the shipped "Set CT team…" button
  (session-minted id — the golden's ``<cid:1>``), staff-visible only.

Click routes are golden-UNPINNED (no btd6 golden drives a click): Ask /
Units / Rounds open the G-10 lookup modals over the reference views;
Maps & Modes / Status open their catalog cards; Strategy lists published
strategies; Live Events shows the events usage view; Admin (staff) the
ops usage view.
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.outcomes import DeferMode, ReplyVisibility
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    ModalFieldSpec,
    ModalFieldStyle,
    ModalSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
    SelectorKind,
    SelectorSpec,
    TextBlock,
)
from sb.spec.refs import HandlerRef, PanelRef, is_registered, panel

__all__ = [
    "btd6_hub_spec",
    "ensure_panel_refs",
    "install_btd6_panels",
    "paragon_spec",
]

# --- paragon calculator landing panel (shipped views/btd6/paragon_view.py
# ParagonCalculatorView + build_calculator_embed @7f7628e1) -------------------
#: the live web Paragon Calculator + its Discord author credit (shipped
#: services/paragon_service.CALCULATOR_PUBLIC_URL / CALCULATOR_AUTHOR_NAME).
_PARAGON_CALC_URL = "https://paragon-calc.vercel.app/"
_PARAGON_CALC_AUTHOR = "notausgang0341"
_DEFAULT_PARAGON = "apex_plasma_master"
#: (value, label) difficulty rows in the shipped select order.
_PARAGON_DIFFICULTIES = (
    ("easy", "Easy (0.85x)"),
    ("medium", "Medium (1.0x)"),
    ("hard", "Hard (1.08x)"),
    ("impoppable", "Impoppable (1.2x)"),
)

ASK_MODAL = ModalSpec(
    modal_id="btd6.ask_form",
    title="Ask BTD6 Assistant",
    fields=(
        ModalFieldSpec(field_id="name", label="Your question",
                       required=True, max_length=300),
    ),
    on_submit=HandlerRef("btd6.cmd_ask"),
)

TOWER_MODAL = ModalSpec(
    modal_id="btd6.tower_form",
    title="Tower Lookup",
    fields=(
        ModalFieldSpec(field_id="name", label="Tower name",
                       required=True, max_length=60),
    ),
    on_submit=HandlerRef("btd6.ref_tower_view"),
)

ROUND_MODAL = ModalSpec(
    modal_id="btd6.round_form",
    title="Round Lookup",
    fields=(
        ModalFieldSpec(field_id="name",
                       label="Round number (add 'abr' for ABR)",
                       required=True, max_length=12),
    ),
    on_submit=HandlerRef("btd6.ref_round_view"),
)

#: The shipped StrategySubmitModal, field for field (ORACLE disbot
#: views/btd6/strategy_submit.py @8214200a, reconstructed via search_code
#: fragments — full-file oracle reads stay denied; the default branch can
#: be AHEAD of the corpus sha 7f7628e1, trap-24 caveat ledgered in
#: D-0073). field_ids are the submit handler's args keys (the same
#: title/summary/map/mode/hero vocabulary `_submit_params` already reads
#: for the `!btd6strat submit` text lane).
STRATEGY_MODAL = ModalSpec(
    modal_id="btd6.strategy_form",
    title="Submit BTD6 strategy",
    fields=(
        ModalFieldSpec(field_id="title", label="Title",
                       placeholder="e.g. CHIMPS Bloody Puddles 4-2-0 "
                                   "Super Monkey",
                       required=True, max_length=100),
        ModalFieldSpec(field_id="summary", label="Summary",
                       style=ModalFieldStyle.PARAGRAPH,
                       placeholder="Short pitch — when and why this "
                                   "strategy works.",
                       required=True, max_length=500),
        ModalFieldSpec(field_id="map", label="Map (optional)",
                       placeholder="e.g. Bloody Puddles",
                       required=False, max_length=80),
        ModalFieldSpec(field_id="mode", label="Mode (optional)",
                       placeholder="e.g. CHIMPS",
                       required=False, max_length=40),
        ModalFieldSpec(field_id="hero", label="Hero (optional)",
                       placeholder="e.g. Geraldo",
                       required=False, max_length=40),
    ),
    on_submit=HandlerRef("btd6.strategy_form_submit"),
)


def btd6_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="btd6.hub",
        subsystem="btd6",
        title="🐵 BTD6 Assistant",
        audience=Audience.PUBLIC,
        frame=EmbedFrameSpec(style_token="green", footer_mode=FooterMode.NONE),
        actions=(
            # row 0 — Ask (modal) + the highest-traffic browse categories.
            PanelActionSpec(
                action_id="ask", label="Ask", emoji="🧠",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("btd6.cmd_ask"),
                defer_mode=DeferMode.MODAL, modal=ASK_MODAL,
                result_render=ResultRender.RESULT_CARD,
                custom_id_override="btd6:ask"),
            PanelActionSpec(
                action_id="events", label="Live Events", emoji="🎯",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("btd6.events_usage_view"),
                result_render=ResultRender.RESULT_CARD,
                custom_id_override="btd6:events"),
            PanelActionSpec(
                action_id="units", label="Units", emoji="🗼",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("btd6.ref_tower_view"),
                defer_mode=DeferMode.MODAL, modal=TOWER_MODAL,
                result_render=ResultRender.RESULT_CARD,
                custom_id_override="btd6:units"),
            PanelActionSpec(
                action_id="rounds", label="Rounds", emoji="🎲",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("btd6.ref_round_view"),
                defer_mode=DeferMode.MODAL, modal=ROUND_MODAL,
                result_render=ResultRender.RESULT_CARD,
                custom_id_override="btd6:rounds"),
            # row 1 — reference categories + staff.
            PanelActionSpec(
                action_id="maps", label="Maps & Modes", emoji="🗺️",
                audience_tier="user",
                handler=HandlerRef("btd6.cmd_diagnostics"),
                result_render=ResultRender.RESULT_CARD,
                custom_id_override="btd6:maps"),
            PanelActionSpec(
                action_id="strategy", label="Strategy", emoji="📋",
                audience_tier="user",
                handler=HandlerRef("btd6.strat_published_view"),
                result_render=ResultRender.RESULT_CARD,
                custom_id_override="btd6:strategy"),
            PanelActionSpec(
                action_id="status", label="Status", emoji="📊",
                audience_tier="user",
                handler=HandlerRef("btd6.cmd_status"),
                result_render=ResultRender.RESULT_CARD,
                custom_id_override="btd6:status"),
            # emoji IN the label (the shipped wire shape — no emoji field).
            PanelActionSpec(
                action_id="admin", label="🛠️ Admin",
                audience_tier="staff",
                handler=HandlerRef("btd6.ops_usage_view"),
                result_render=ResultRender.RESULT_CARD,
                custom_id_override="btd6:admin"),
        ),
        # the shipped BTD6PanelView carried its two button rows PLUS the
        # standard-nav 📚 Help slot (goldens pin the three rows: ask/events/
        # units/rounds · maps/strategy/status/admin · nav:help) and was
        # never anchored.
        navigation=NavigationSpec(show_help=True, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("btd6.render_hub"),
        justification=(
            "the shipped hub embed is live-data-parameterized (dataset "
            "version/counts + per-kind freshness lines) with the command "
            "legend + ` • ctx=btd6_hub:main` footer — outside FooterMode's "
            "vocabulary and the static TextBlock grammar. The override "
            "delegates the component rows to the grammar renderer and "
            "replaces ONLY the embed (goldens/btd6/sweep_btd6menu pins "
            "every byte)."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("ask", "events", "units", "rounds"),
            ("maps", "strategy", "status", "admin"),)),)),
    )


def card_spec() -> PanelSpec:
    """The generic oracle-card reply (one embed, zero components)."""
    return PanelSpec(
        panel_id="btd6.card",
        subsystem="btd6",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("btd6.render_card"),
        justification=(
            "the shipped `!btd6 <sub>` replies are fully live-data-"
            "parameterized embeds built by sb/domain/btd6/oracle_cards.py "
            "(colors/footers/fields outside the grammar vocabulary — "
            "goldens/btd6 pins the bytes). Zero components; the renderer "
            "presents the handler-built RenderedEmbed verbatim."),
    )


def strategy_submit_spec() -> PanelSpec:
    """The strategy-submission page — the G-10 declaring surface for the
    shipped StrategySubmitModal twin (``btd6.strategy_form``).

    ENGINE-SHAPE deviation, ledgered (D-0073; standing terms re-ruled
    D-0076): the shipped ingress was the `/btd6 strat submit` app command
    calling ``send_modal`` directly (disbot cogs/btd6/_unified.py
    strat_submit_slash). The CommandSpec modal facet now EXISTS
    (sb/spec/commands.py `modal`, D-0076 — the D-0073 named successor),
    but DECLARING the `/btd6 strat submit` row stays GOLDEN-BLOCKED:
    goldens/btd6/sweep_slash_btd6_strat_submit pins the unregistered-slash
    SILENCE (zero calls, the #151 drop rule; the #218 trap-17 class of 30
    `sweep_slash_btd6_*` pins) and a registered slash open records a
    type-9 call — so the form's declaring PanelActionSpec stays on this
    session page (the D-0054/D-0066 intermediating-button posture). The
    page itself is engine copy no golden pins; the FORM and its submit
    bytes are the oracle's. `reply_visibility=EPHEMERAL` commits the
    shipped ``safe_defer(interaction, ephemeral=True)`` flag on the submit
    re-entry (goldens/btd6/btd6_strategy_form_* pin flags 64 on both
    hops)."""
    return PanelSpec(
        panel_id="btd6.strategy_submit",
        subsystem="btd6",
        title="Submit BTD6 strategy",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="green", footer_mode=FooterMode.NONE),
        body=(TextBlock(text="Share a strategy with this server — the "
                             "button opens the submission form; staff "
                             "review with `!btd6 pending`."),),
        actions=(
            PanelActionSpec(
                action_id="open_strategy_form", label="Submit strategy…",
                emoji="📝", style=ActionStyle.PRIMARY, audience_tier="user",
                defer_mode=DeferMode.MODAL, modal=STRATEGY_MODAL,
                reply_visibility=ReplyVisibility.EPHEMERAL,
                handler=HandlerRef("btd6.strategy_form_submit"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(("open_strategy_form",),)),)),
    )


def ctteam_spec() -> PanelSpec:
    """The CT-team view + the shipped staff-only 'Set CT team…' button."""
    return PanelSpec(
        panel_id="btd6.ctteam",
        subsystem="btd6",
        title="🛡️ BTD6 — Your CT Team",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="gold", footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="set_team", label="Set CT team…", emoji="🛡️",
                style=ActionStyle.PRIMARY, audience_tier="staff",
                handler=HandlerRef("btd6.ctteam_set_pending"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("btd6.render_ctteam"),
        justification=(
            "the shipped CT-team embed carries the ` • ctx=btd6_ct:team` "
            "footer and a Manage-Server-only button on a discord.py "
            "auto-minted id (goldens/btd6/sweep_btd6_ctteam pins the "
            "<cid:1> mix) — the renderer gates the button on the opener's "
            "operator fact and delegates minting to the session engine."),
        layout=LayoutSpec(pages=(PageSpec(rows=(("set_team",),)),)),
    )


def _paragon_options() -> tuple[dict, ...]:
    from sb.domain.btd6 import paragon_math

    return tuple(
        {"label": p.name[:100], "value": p.paragon_id,
         "description": p.tower[:100],
         "default": p.paragon_id == _DEFAULT_PARAGON}
        for p in paragon_math.PARAGONS
    )


def _tier5_options() -> tuple[dict, ...]:
    from sb.domain.btd6 import paragon_math

    # the default landing state (solo Dart) — the shipped _Tier5Select bounds
    # its options by ``max_extra_t5_count`` for the current mode/paragon.
    limit = paragon_math.max_extra_t5_count(
        paragon_math.game_mode_for(1), is_dart=True)
    return tuple(
        {"label": f"{n} extra T5", "value": str(n), "default": n == 0}
        for n in range(0, max(limit, 0) + 1)
    )


def paragon_spec() -> PanelSpec:
    """The BTD6 Paragon calculator landing panel (`!paragon`) — the shipped
    ParagonCalculatorView + build_calculator_embed, byte-for-byte
    (goldens/btd6/sweep_paragon).

    Roster / players / difficulty / extra-T5 selectors on the shipped default
    state (Apex Plasma Master · solo · Medium · 0 extra T5) plus the button
    row (🧮 Calculate · 🎯 Requirements · 📊 Stats · ↩ BTD6 · 🌐 Web
    calculator LINK). The degree solver + reverse requirements solver + live
    web-calc reconciliation are a NAMED SUCCESSOR PORT (D-0046): the compute
    buttons + selectors land on the ``btd6.paragon_pending`` terminal, the
    ↩ BTD6 button opens the hub, and the golden exercises the initial open
    only. A session view (never anchored; minted 32-hex ids the Normalizer
    symbolizes as <cid:N>)."""
    players = tuple(
        {"label": "Solo (1 player)" if n == 1 else f"Co-op ({n} players)",
         "value": str(n), "default": n == 1}
        for n in (1, 2, 3, 4)
    )
    difficulties = tuple(
        {"label": label, "value": value, "default": value == "medium"}
        for value, label in _PARAGON_DIFFICULTIES
    )
    return PanelSpec(
        panel_id="btd6.paragon",
        subsystem="btd6",
        title="🔮 Paragon Calculator",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="green", footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="paragon", kind=SelectorKind.ENUM,
                on_select=HandlerRef("btd6.paragon_pending"),
                options_source=_paragon_options(),
                placeholder="Choose a paragon…", audience_tier="user"),
            SelectorSpec(
                selector_id="players", kind=SelectorKind.ENUM,
                on_select=HandlerRef("btd6.paragon_pending"),
                options_source=players,
                placeholder="Players…", audience_tier="user"),
            SelectorSpec(
                selector_id="difficulty", kind=SelectorKind.ENUM,
                on_select=HandlerRef("btd6.paragon_pending"),
                options_source=difficulties,
                placeholder="Difficulty…", audience_tier="user"),
            SelectorSpec(
                selector_id="tier5", kind=SelectorKind.ENUM,
                on_select=HandlerRef("btd6.paragon_pending"),
                options_source=_tier5_options(),
                placeholder="Extra T5s…", audience_tier="user"),
        ),
        actions=(
            PanelActionSpec(
                action_id="calc", label="🧮 Calculate degree",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("btd6.paragon_pending"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="requirements", label="🎯 Requirements",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("btd6.paragon_pending"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="stats", label="📊 Stats",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("btd6.paragon_pending"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="back", label="↩ BTD6",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef("btd6.hub"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("btd6.render_paragon"),
        justification=(
            "the shipped paragon landing embed carries an arbitrary footer "
            "('Solo: 1 extra T5 (Dart only) · Co-op: up to 9 · totems are "
            "uncapped') and three STATIC fields — both outside FooterMode "
            "and the block grammar's provider-fed field vocabulary — and the "
            "component row mixes a LINK button (🌐 Web calculator, no "
            "custom_id) with the session's minted dispatch ids. The override "
            "delegates the roster/players/difficulty/extra-T5 selectors + the "
            "four dispatch buttons to the grammar renderer, replaces ONLY the "
            "embed, and injects the link button (goldens/btd6/sweep_paragon "
            "pins every byte)."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("paragon",),
            ("players",),
            ("difficulty",),
            ("tier5",),
            ("calc", "requirements", "stats", "back"),)),)),
    )


# --- renderer overrides ------------------------------------------------------


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar-rendered components + the shipped hub embed bytes."""
    from sb.domain.btd6 import oracle_cards
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered, embed=oracle_cards.hub_card())


async def _render_paragon(spec: PanelSpec, ctx) -> object:
    """Grammar-rendered selectors/buttons + the shipped landing embed +
    the injected 🌐 Web calculator LINK button (the shipped
    build_calculator_embed default state: Apex Plasma Master · solo ·
    Medium · 0 extra T5)."""
    from sb.domain.btd6 import paragon_math
    from sb.kernel.panels.render import (
        RenderedComponent,
        RenderedEmbed,
        render_panel,
    )

    rendered = await render_panel(spec, ctx)
    paragon = paragon_math.resolve_paragon(_DEFAULT_PARAGON)
    name = paragon.name if paragon else _DEFAULT_PARAGON
    tower = paragon.tower if paragon else ""
    player_count = 1
    difficulty = "medium"
    tier5_count = 0
    mode = paragon_math.game_mode_for(player_count)
    embed = RenderedEmbed(
        title=f"🔮 Paragon Calculator — {name}",
        description=(
            f"**Paragon:** {name} ({tower})\n"
            f"**Players:** {player_count} ({mode})\n"
            f"**Difficulty:** {difficulty.title()}\n"
            f"**Extra T5s:** {tier5_count}"),
        fields=(
            ("🧮 Calculate degree",
             "Enter your pops / cash / tiers / totems to see the degree "
             "you'd get."),
            ("🎯 Requirements for a degree",
             "Pick a strategy and a target degree to get a recommended "
             "build."),
            ("🔗 Web calculator & credits",
             f"[paragon-calc.vercel.app]({_PARAGON_CALC_URL}) — built by "
             f"**{_PARAGON_CALC_AUTHOR}**"),
        ),
        footer="Solo: 1 extra T5 (Dart only) · Co-op: up to 9 · totems "
               "are uncapped",
        style_token="green",
    )
    link = RenderedComponent(
        kind="button", custom_id="", label="🌐 Web calculator", row=4,
        style=ActionStyle.LINK.value, url=_PARAGON_CALC_URL)
    return _dc_replace(rendered, embed=embed,
                       components=rendered.components + (link,))


async def _render_card(spec: PanelSpec, ctx) -> object:
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    embed = (ctx.params or {}).get("_card")
    if not isinstance(embed, RenderedEmbed):  # defensive: never a crash
        embed = RenderedEmbed(title="", description="")
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_ctteam(spec: PanelSpec, ctx) -> object:
    from sb.domain.btd6 import oracle_cards
    from sb.kernel.panels.render import RenderedComponent, RenderedPanel

    components = ()
    if bool((ctx.params or {}).get("can_manage")):
        components = (RenderedComponent(
            kind="button", custom_id=f"{spec.panel_id}.set_team",
            label="Set CT team…", row=0, style=ActionStyle.PRIMARY.value,
            emoji="🛡️"),)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=oracle_cards.ctteam_card(),
        components=components,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


# --- registration --------------------------------------------------------------


_SPECS = {
    "btd6.hub": btd6_hub_spec,
    "btd6.card": card_spec,
    "btd6.ctteam": ctteam_spec,
    "btd6.strategy_submit": strategy_submit_spec,
    "btd6.paragon": paragon_spec,
}

_RENDERERS = {
    "btd6.render_hub": _render_hub,
    "btd6.render_card": _render_card,
    "btd6.render_ctteam": _render_ctteam,
    "btd6.render_paragon": _render_paragon,
}


def _register_refs() -> None:
    from sb.spec.refs import handler

    for pid, factory in _SPECS.items():
        if not is_registered(PanelRef(pid)):
            panel(pid)(factory)
    for name, fn in _RENDERERS.items():
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


_register_refs()


def install_btd6_panels() -> tuple[PanelSpec, ...]:
    out = []
    for factory in _SPECS.values():
        spec = factory()
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def ensure_panel_refs() -> None:
    _register_refs()
