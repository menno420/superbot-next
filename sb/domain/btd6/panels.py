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
  (session-minted id — the golden's ``<cid:1>``), staff-visible only;
  ARMED: the button opens the guided-flow modal over the
  ``btd6.ctteam_confirm`` preview+confirm page (sb/domain/btd6/ct_team.py).

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
    "paragon_requirements_spec",
    "paragon_spec",
    "paragon_stats_spec",
]

# --- paragon calculator landing panel (shipped views/btd6/paragon_view.py
# ParagonCalculatorView + build_calculator_embed @7f7628e1; the armed
# select/compute flows live in sb/domain/btd6/paragon_panel.py) ---------------

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
#: The shipped ParagonForwardModal, field for field (ORACLE disbot
#: views/btd6/paragon_modals.py @7f7628e1) — the five numeric inputs; the
#: paragon/players/difficulty/extra-T5 axes ride the parent view's selects
#: (Discord's 5-text-input limit, shipped comment).
PARAGON_CALC_MODAL = ModalSpec(
    modal_id="btd6.paragon_calc_form",
    title="Paragon — enter your numbers",
    fields=(
        ModalFieldSpec(field_id="pops", label="Pops (total damage)",
                       placeholder="e.g. 8000000",
                       required=False, max_length=15),
        ModalFieldSpec(field_id="cash_spent",
                       label="Cash spent (non-T5 towers)",
                       placeholder="e.g. 150000",
                       required=False, max_length=12),
        ModalFieldSpec(field_id="slider_cash", label="Slider cash",
                       placeholder="e.g. 0",
                       required=False, max_length=12),
        ModalFieldSpec(field_id="upgrade_count",
                       label="Upgrade tiers (a 0-2-4 tower = 6)",
                       placeholder="e.g. 60",
                       required=False, max_length=4),
        ModalFieldSpec(field_id="geraldo_totems", label="Geraldo totems",
                       placeholder="e.g. 0",
                       required=False, max_length=4),
    ),
    on_submit=HandlerRef("btd6.paragon_calc_submit"),
)

#: The shipped ParagonTargetModal (same oracle module) — the reverse
#: solver's one required field.
PARAGON_TARGET_MODAL = ModalSpec(
    modal_id="btd6.paragon_target_form",
    title="Paragon — target degree",
    fields=(
        ModalFieldSpec(field_id="target", label="Target degree (1-100)",
                       placeholder="e.g. 90",
                       required=True, max_length=3),
    ),
    on_submit=HandlerRef("btd6.paragon_target_submit"),
)

#: The shipped stats-view _DegreeModal (same oracle module family —
#: views/btd6/paragon_stats_view.py) — one required field.
PARAGON_DEGREE_MODAL = ModalSpec(
    modal_id="btd6.paragon_degree_form",
    title="Paragon degree (1–100)",
    fields=(
        ModalFieldSpec(field_id="degree", label="Degree",
                       placeholder="1–100",
                       required=True, max_length=3),
    ),
    on_submit=HandlerRef("btd6.paragon_degree_submit"),
)

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


#: The shipped CTGroupFlowModal, field for field (ORACLE disbot
#: views/btd6/ct_group_flow.py @9c16365) — step 1 of the guided CT-team
#: flow (Q-0064: URL/id → parse → preview → confirm).
CTTEAM_SET_MODAL = ModalSpec(
    modal_id="btd6.ctteam_set_form",
    title="Set CT team",
    fields=(
        ModalFieldSpec(
            field_id="raw", label="CT bracket URL or id",
            placeholder="https://…/leaderboard/group/<id> or the bare id",
            required=True, max_length=200),
    ),
    on_submit=HandlerRef("btd6.ctteam_set_submit"),
)


def ctteam_spec() -> PanelSpec:
    """The CT-team view + the shipped staff-only 'Set CT team…' button —
    ARMED (the `btd6.ctteam_set_pending` terminal retired, curation
    report 2026-07-13 row 2): the button opens the shipped
    ``CTGroupFlowModal`` over the preview+confirm page
    (sb/domain/btd6/ct_team.py; deviations ledgered there)."""
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
                defer_mode=DeferMode.MODAL, modal=CTTEAM_SET_MODAL,
                reply_visibility=ReplyVisibility.EPHEMERAL,
                handler=HandlerRef("btd6.ctteam_set_submit"),
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


def ctteam_confirm_spec() -> PanelSpec:
    """The guided flow's preview+confirm step (the shipped
    ``CTGroupConfirmView``, author-locked 180s): Confirm commits the ONE
    audited ``btd6.set_ct_team`` write, Cancel discards. A session view
    (never anchored; run-minted ids) — the parsed id rides the session
    args (``ct_group_id``), the cleanup policy-flow state carrier."""
    return PanelSpec(
        panel_id="btd6.ctteam_confirm",
        subsystem="btd6",
        title="🛡️ BTD6 — Confirm CT team",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="gold", footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="confirm", label="Confirm",
                style=ActionStyle.SUCCESS, audience_tier="staff",
                handler=HandlerRef("btd6.ctteam_confirm_submit"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="cancel", label="Cancel",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("btd6.ctteam_cancel"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("btd6.render_ctteam_confirm"),
        justification=(
            "the shipped CTGroupConfirmView (views/btd6/ct_group_flow.py): "
            "author-locked Confirm/Cancel on discord.py auto-minted ids "
            "over the preview embed's ` • ctx=btd6_ct:confirm` footer — "
            "the Confirm callback re-checks Manage Server at execution "
            "time (views rule → the action's staff tier + the op's staff "
            "floor); golden-UNPINNED (no golden drives the guided flow)."),
        layout=LayoutSpec(pages=(PageSpec(rows=(("confirm", "cancel"),)),)),
    )


def paragon_spec() -> PanelSpec:
    """The BTD6 Paragon calculator landing panel (`!paragon`) — the shipped
    ParagonCalculatorView + build_calculator_embed, byte-for-byte
    (goldens/btd6/sweep_paragon pins the initial open).

    Roster / players / difficulty / extra-T5 selectors on the shipped default
    state (Apex Plasma Master · solo · Medium · 0 extra T5) plus the button
    row (🧮 Calculate · 🎯 Requirements · 📊 Stats · ↩ BTD6 · 🌐 Web
    calculator LINK). ARMED (the `btd6.paragon_pending` terminal retired):
    the selectors update per-message state and re-render in place, Calculate
    opens the shipped forward modal over the pure-compute power model,
    Requirements opens the strategy/target page, Stats opens the
    `btd6.paragon_stats` degree view (or the module-less card)
    — sb/domain/btd6/paragon_panel.py (deviations
    ledgered there; the live-API reconciliation stays D-0046). A session
    view (never anchored; minted 32-hex ids the Normalizer symbolizes as
    <cid:N>)."""
    from sb.domain.btd6 import paragon_panel as _pp

    state = _pp.calc_state(None)          # the shipped landing state
    tier5, _t5_disabled = _pp.tier5_options(state)
    return PanelSpec(
        panel_id="btd6.paragon",
        subsystem="btd6",
        title="🔮 Paragon Calculator",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="green", footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="paragon", kind=SelectorKind.ENUM,
                on_select=HandlerRef("btd6.paragon_select"),
                options_source=_pp.paragon_options(state),
                placeholder="Choose a paragon…", audience_tier="user"),
            SelectorSpec(
                selector_id="players", kind=SelectorKind.ENUM,
                on_select=HandlerRef("btd6.paragon_select"),
                options_source=_pp.player_options(state),
                placeholder="Players…", audience_tier="user"),
            SelectorSpec(
                selector_id="difficulty", kind=SelectorKind.ENUM,
                on_select=HandlerRef("btd6.paragon_select"),
                options_source=_pp.difficulty_options(state),
                placeholder="Difficulty…", audience_tier="user"),
            SelectorSpec(
                selector_id="tier5", kind=SelectorKind.ENUM,
                on_select=HandlerRef("btd6.paragon_select"),
                options_source=tier5,
                placeholder="Extra T5s…", audience_tier="user"),
        ),
        actions=(
            PanelActionSpec(
                action_id="calc", label="🧮 Calculate degree",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("btd6.paragon_calc_submit"),
                defer_mode=DeferMode.MODAL, modal=PARAGON_CALC_MODAL,
                reply_visibility=ReplyVisibility.EPHEMERAL,
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="requirements", label="🎯 Requirements",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("btd6.paragon_requirements_open"),
                reply_visibility=ReplyVisibility.EPHEMERAL,
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="stats", label="📊 Stats",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("btd6.paragon_stats_view"),
                reply_visibility=ReplyVisibility.EPHEMERAL,
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
            "embed (re-bounding the select rosters from the live per-message "
            "state — the shipped rebuild()), and injects the link button "
            "(goldens/btd6/sweep_paragon pins every default-state byte)."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("paragon",),
            ("players",),
            ("difficulty",),
            ("tier5",),
            ("calc", "requirements", "stats", "back"),)),)),
    )


def paragon_requirements_spec() -> PanelSpec:
    """The reverse-solver page (shipped ParagonRequirementsView): Strategy…
    select · 🎯 Enter target degree (the shipped ParagonTargetModal) ·
    ↩ Calculator · the 🌐 Web calculator LINK, over the shipped blurple
    config embed. Opened by the calculator's 🎯 Requirements button as its
    own ephemeral panel message (engine-shape deviation ledgered in
    sb/domain/btd6/paragon_panel.py — the shipped click EDITED the
    calculator message in place). Golden-unpinned (#151's class)."""
    from sb.domain.btd6 import paragon_panel as _pp

    state = _pp.req_state(None)
    return PanelSpec(
        panel_id="btd6.paragon_requirements",
        subsystem="btd6",
        title="🎯 Requirements",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        selectors=(
            # selector_id "solve_strategy" (not the shipped bare "strategy")
            # — the manifest-wide never_strand predicate pools component ids
            # per subsystem and the hub already declares a "strategy" ACTION;
            # session ids are minted 32-hex on the wire, so no byte changes.
            SelectorSpec(
                selector_id="solve_strategy", kind=SelectorKind.ENUM,
                on_select=HandlerRef("btd6.paragon_req_select"),
                options_source=_pp.strategy_options(state),
                placeholder="Strategy…", audience_tier="user"),
        ),
        actions=(
            PanelActionSpec(
                action_id="enter_target", label="🎯 Enter target degree",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("btd6.paragon_target_submit"),
                defer_mode=DeferMode.MODAL, modal=PARAGON_TARGET_MODAL,
                reply_visibility=ReplyVisibility.EPHEMERAL,
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="back_calc", label="↩ Calculator",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("btd6.paragon_back_to_calc"),
                reply_visibility=ReplyVisibility.EPHEMERAL,
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("btd6.render_paragon_requirements"),
        justification=(
            "the shipped requirements config embed is state-parameterized "
            "on every description line (strategy/players/difficulty) with "
            "an arbitrary footer ('Least-X maxes the other inputs…') — "
            "outside FooterMode and the static TextBlock grammar — and the "
            "button row mixes the 🌐 Web calculator LINK button (no "
            "custom_id) with the session's minted dispatch ids. The "
            "override delegates the strategy select + two buttons to the "
            "grammar renderer, replaces ONLY the embed, and injects the "
            "link button (the shipped ParagonRequirementsView shape; no "
            "golden pins this click route)."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("solve_strategy",),
            ("enter_target", "back_calc"),)),)),
    )


def paragon_stats_spec() -> PanelSpec:
    """The paragon stats degree view — the shipped ParagonStatsView's
    degree picker (milestone select · 🔢 Enter degree · ↩ Calculator)
    over the PORTED :func:`stats.paragon_stats_at_degree`. Opened by the
    calculator's 📊 Stats button as its own ephemeral panel message
    (engine-shape deviation ledgered in sb/domain/btd6/paragon_panel.py).
    Golden-unpinned (click-reached, #151's class). The degree-independent
    BASE infobox view (``_stat_node_embed`` over ``stats.base``) rides the
    deep-stats successor — this page opens at Degree 1 instead (scaled ==
    base at degree 1 by the wiki formulas), ledgered in paragon_panel."""
    from sb.domain.btd6 import paragon_panel as _pp

    state = _pp.stats_state(None)
    return PanelSpec(
        panel_id="btd6.paragon_stats",
        subsystem="btd6",
        title="👑 Paragon stats",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="gold", footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="degree_pick", kind=SelectorKind.ENUM,
                on_select=HandlerRef("btd6.paragon_degree_select"),
                options_source=_pp.degree_options(state),
                placeholder="Pick a degree…", audience_tier="user"),
        ),
        actions=(
            PanelActionSpec(
                action_id="enter_degree", label="🔢 Enter degree",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("btd6.paragon_degree_submit"),
                defer_mode=DeferMode.MODAL, modal=PARAGON_DEGREE_MODAL,
                reply_visibility=ReplyVisibility.EPHEMERAL,
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="back_stats", label="↩ Calculator",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("btd6.paragon_stats_back"),
                reply_visibility=ReplyVisibility.EPHEMERAL,
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("btd6.render_paragon_stats"),
        justification=(
            "the shipped per-degree stats embed is fully data-parameterized "
            "(power/boss-multiplier headline + per-attack scaled cells with "
            "the 'BTD6 stats v<version>' footer) — outside FooterMode and "
            "the block grammar's provider-fed field vocabulary. The override "
            "delegates the degree select + two buttons to the grammar "
            "renderer and replaces ONLY the embed (no golden pins this "
            "click route)."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("degree_pick",),
            ("enter_degree", "back_stats"),)),)),
    )


# --- renderer overrides ------------------------------------------------------


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar-rendered components + the shipped hub embed bytes."""
    from sb.domain.btd6 import oracle_cards
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered, embed=oracle_cards.hub_card())


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
    from sb.domain.btd6 import ct_team, oracle_cards
    from sb.kernel.panels.render import RenderedComponent, RenderedPanel

    components = ()
    if bool((ctx.params or {}).get("can_manage")):
        components = (RenderedComponent(
            kind="button", custom_id=f"{spec.panel_id}.set_team",
            label="Set CT team…", row=0, style=ActionStyle.PRIMARY.value,
            emoji="🛡️"),)
    # the configured pointer (build_ct_team_embed's read); "" (the
    # golden-pinned unset copy, sweep_btd6_ctteam) on unset OR on a
    # presentation-lane read failure — the view never requires the DB.
    group_id = await ct_team.team_group_id_or_empty(ctx.guild_id)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=oracle_cards.ctteam_card(group_id),
        components=components,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_ctteam_confirm(spec: PanelSpec, ctx) -> object:
    """The preview+confirm step (build_ct_preview_embed over the grammar-
    rendered Confirm/Cancel row): the current → new pointer change plus
    the D-0046 no-active-event preview byte."""
    from sb.domain.btd6 import ct_team, oracle_cards
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    group_id = str((ctx.params or {}).get("ct_group_id") or "")
    current = await ct_team.team_group_id_or_empty(ctx.guild_id)
    return _dc_replace(
        rendered, embed=oracle_cards.ctteam_confirm_card(current, group_id))


# --- registration --------------------------------------------------------------


_SPECS = {
    "btd6.hub": btd6_hub_spec,
    "btd6.card": card_spec,
    "btd6.ctteam": ctteam_spec,
    "btd6.ctteam_confirm": ctteam_confirm_spec,
    "btd6.strategy_submit": strategy_submit_spec,
    "btd6.paragon": paragon_spec,
    "btd6.paragon_requirements": paragon_requirements_spec,
    "btd6.paragon_stats": paragon_stats_spec,
}

_RENDERERS = {
    "btd6.render_hub": _render_hub,
    "btd6.render_card": _render_card,
    "btd6.render_ctteam": _render_ctteam,
    "btd6.render_ctteam_confirm": _render_ctteam_confirm,
    # btd6.render_paragon + btd6.render_paragon_requirements register at
    # sb/domain/btd6/paragon_panel.py import (with the armed handlers).
}


def _register_refs() -> None:
    from sb.spec.refs import handler

    from sb.domain.btd6 import ct_team as _ct
    from sb.domain.btd6 import paragon_panel as _pp

    _ct.ensure_ct_team_refs()
    _pp.ensure_paragon_refs()
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
