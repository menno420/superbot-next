"""Creature panels (band 6 / parity flip) — the SHIPPED surfaces byte-for-byte:

* ``creature.hub`` — disbot/views/creature/{menu,embeds}.py
  ``CreatureMenuView`` + ``build_menu_embed``: the 🐾 Creatures embed
  (CREATURE_COLOR green, the five-affordance description, the live
  "Your progress" field, the "Only you can use this panel." footer
  literal) over the five shipped buttons (Catch 🐾 success · Dex 📖
  secondary · Challenge ⚔️ primary · Ladder 🏆 secondary · How to play
  📖 secondary) and the shipped standard nav row (📚 Help + ↩ Games —
  ``home_hub="games"`` explicit, the casino precedent).
  ``parity/goldens/creature/sweep_creatures.json`` pins every byte:
  run-minted ``<cid:N>`` button ids (timeout session view ⇒
  ``session_lifecycle=True``, no ``panel_anchors`` row), emoji as
  SEPARATE wire fields next to the labels (trap 15a), the literal
  ``nav:help`` / ``nav:hub:games`` slots riding through the mint.

* ``creature.dex_card`` / ``creature.collectors_card`` /
  ``creature.record_card`` / ``creature.battletop_card`` — the four
  component-less result cards (disbot/views/creature/embeds.py
  ``build_dex_embed`` / ``build_collectors_embed`` /
  ``build_record_embed`` / ``build_battletop_embed``, the karma-card
  recipe): read-parameterized embeds outside the static grammar
  vocabulary, composed whole by their renderer overrides. The four
  sweep goldens (sweep_dex, the re-homed sweep_dextop, sweep_cbrecord,
  sweep_cbattletop) pin the empty-state bytes verbatim.

* ``creature.rules_card`` — ``build_rules_embed`` verbatim (INFO_COLOR
  blue): a STATIC quick-reference, grammar-rendered (TextBlock), no
  override. No golden clicks it (the shipped 📖 affordance replied
  ephemeral).

* ``creature.challenge`` — disbot/views/creature_battle/challenge.py
  ``CreatureBattleChallengeView``: the shipped CONTENT-only send (no
  embed) carrying the Accept ⚔️ (green) / Decline ❌ (red) pair, locked
  to the challenged player (``BaseView`` ``author=opponent`` — the
  override sets ``invoker_lock`` to the opponent).
  ``parity/goldens/creature/sweep_cbattle.json`` pins the open bytes.

Trap-24 drift check (creature row): the oracle current-head fragments
(embeds.py menu/dex/collectors/record/battletop/rules builders +
CREATURE_COLOR/BATTLE_COLOR; menu.py button decorators; challenge.py
button decorators + decline copy; cogs/creature_cog.py +
creature_battle_cog.py command bodies) match the corpus goldens
byte-for-byte — NO drift (corpus sha 7f7628e1).

Under-port ledger (no golden pins these corners):
* the shipped hub buttons EDITED the menu message in place
  (``interaction.response.edit_message``); the port opens the result
  cards as fresh sends (the karma/casino open lane).
* the shipped Challenge button opened the ``_ChallengePickView`` user
  select; a native USER picker seam does not exist yet (only
  role/channel — the ticket/logging natives), so the button is a
  declared pending terminal (the D-0030 xp-config posture).

Accept now resolves the battle immediately (the shipped
utils/creatures/battle.py combat math ported to
sb/domain/creature/battle.py + views/creature_battle/render.py ported to
battle_service.build_result_view) and records the result through the
audited creature.record_battle_result lane — the challenge card's
``resolved`` stage renders the outcome embed in place (D-0079).
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.outcomes import ReplyVisibility
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
    TextBlock,
)
from sb.spec.refs import HandlerRef, handler, is_registered, panel

__all__ = [
    "BATTLETOP_PANEL_ID",
    "CHALLENGE_PANEL_ID",
    "COLLECTORS_PANEL_ID",
    "DEX_CARD_PANEL_ID",
    "HUB_PANEL_ID",
    "RECORD_PANEL_ID",
    "RULES_PANEL_ID",
    "battletop_card_spec",
    "challenge_spec",
    "collectors_card_spec",
    "creature_hub_spec",
    "dex_card_spec",
    "ensure_panel_refs",
    "install_creature_panels",
    "record_card_spec",
    "rules_card_spec",
]

HUB_PANEL_ID = "creature.hub"
DEX_CARD_PANEL_ID = "creature.dex_card"
COLLECTORS_PANEL_ID = "creature.collectors_card"
RECORD_PANEL_ID = "creature.record_card"
BATTLETOP_PANEL_ID = "creature.battletop_card"
CHALLENGE_PANEL_ID = "creature.challenge"
RULES_PANEL_ID = "creature.rules_card"

#: the shipped footer literal (views/creature/embeds.py build_menu_embed)
#: — outside FooterMode's vocabulary, hence the renderer_override (the
#: casino/community precedent).
_HUB_FOOTER = "Only you can use this panel."

#: views/creature/embeds.py build_dex_embed footer, verbatim.
_DEX_FOOTER = "🐾 Catch to hunt · 🏆 Ladder for the leaderboard"

#: views/creature/embeds.py build_record_embed footer, verbatim.
_RECORD_FOOTER = "⚔️ Challenge a trainer to fight · 🏆 Ladder for the rankings"

#: views/creature/embeds.py medal prefixes (collectors + battletop).
_MEDALS = ("🥇", "🥈", "🥉")


def _winrate(wins: int, losses: int) -> str:
    """views/creature/embeds.py ``winrate`` verbatim — ``NN%``, or ``—``
    with no battles (goldens/creature/sweep_cbrecord pins the em-dash)."""
    total = wins + losses
    if total == 0:
        return "—"
    return f"{round(100 * wins / total)}%"


def _hub_description() -> str:
    """views/creature/embeds.py build_menu_embed description, verbatim —
    the counts interpolate the catalog exactly like the shipped f-string
    (len(CREATURES)=36, len(ELEMENTS)=6; the golden pins the rendered
    bytes)."""
    from sb.domain.creature import catalog

    elements = tuple(dict.fromkeys(c.element for c in catalog.CREATURES))
    return (
        f"Catch from **{len(catalog.CREATURES)}** original creatures "
        f"across {len(elements)} elements. Rarer creatures show up less "
        "often and are harder to catch — fill out your dex, then battle "
        "other trainers in a level-normalized PvP where type matchups "
        "decide it.\n\n"
        "**🐾 Catch** — head into the wild\n"
        "**📖 Dex** — browse your collection by element\n"
        "**⚔️ Challenge** — battle another trainer\n"
        "**🏆 Ladder** — the server's top trainers\n"
        "**📖 How to play** — the rules"
    )


#: views/creature/embeds.py build_rules_embed description, verbatim (the
#: shipped 📖 quick-reference — a STATIC card, grammar-rendered).
_RULES_DESCRIPTION = (
    "**The loop**\n"
    "1. **🐾 Catch** — head into the wild. A creature appears (rarer ones "
    "show up less often); the catch can succeed or it can flee.\n"
    "2. **📖 Dex** — every creature you've caught, browsable by element. "
    "Fill it out by catching the rarer elements and rarities.\n"
    "3. **⚔️ Challenge** — battle another trainer. Both teams are "
    "**normalized to level 50**, so it's about your collection and **type "
    "matchups**, never who ground more XP (anti-pay-to-win).\n\n"
    "**Good to know**\n"
    "• Catching and winning battles both award **creature XP** — no coins, "
    "nothing to lose.\n"
    "• You need **at least one creature** to battle, so catch first.\n"
    "• **🏆 Ladder** ranks the server's top trainers by wins."
)


# The shipped hub Challenge button opened _ChallengePickView (a user
# select); a native USER picker seam does not exist yet, so it stays a
# declared pending terminal (the D-0030 xp-config posture: declared +
# honest refusal, never silent; challenge directly with `!cbattle
# @member` meanwhile). The Accept battle-resolution terminal is NO LONGER
# pending — it ports here as the real auto-resolve handler
# (creature.challenge_accept in service.py; D-0079). Registered at module
# import AND from ensure_panel_refs (the #141 doctrine).
def _register_pending() -> tuple[HandlerRef, ...]:
    from sb.domain.operator_spine import pending_handler as _pending

    return (
        _pending(
            "creature.challenge_pick_pending",
            "⚔️ The trainer picker ports with the native user-select "
            "seam — challenge directly with `!cbattle @member` until "
            "then."),
    )


(_PENDING_CHALLENGE_PICK,) = _register_pending()


def creature_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id=HUB_PANEL_ID,
        subsystem="creature",
        title="🐾 Creatures",
        audience=Audience.INVOKER,
        # CREATURE_COLOR green (3066993); the footer literal + the live
        # progress field ride the override (see justification).
        frame=EmbedFrameSpec(style_token="green",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_hub_description()),),
        actions=(
            PanelActionSpec(
                action_id="creature_catch", label="Catch", emoji="🐾",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("creature.catch_route")),
            PanelActionSpec(
                action_id="creature_dex", label="Dex", emoji="📖",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("creature.dex_view")),
            PanelActionSpec(
                action_id="creature_challenge", label="Challenge",
                emoji="⚔️", style=ActionStyle.PRIMARY,
                audience_tier="user",
                handler=HandlerRef("creature.challenge_pick_pending"),
                reply_visibility=ReplyVisibility.EPHEMERAL),
            PanelActionSpec(
                action_id="creature_ladder", label="Ladder", emoji="🏆",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("creature.battletop_view")),
            PanelActionSpec(
                action_id="creature_howto", label="How to play",
                emoji="📖", style=ActionStyle.SECONDARY,
                audience_tier="user",
                handler=HandlerRef("creature.rules_view"),
                reply_visibility=ReplyVisibility.EPHEMERAL),
        ),
        # the shipped standard nav row: 📚 Help + the hub-named home
        # button "↩ Games" (nav:help / nav:hub:games — both pinned by
        # the golden); home_hub explicit, the casino/cleanup precedent.
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("creature.render_hub"),
        justification=(
            "two shipped surfaces sit outside the grammar's vocabulary "
            "(goldens/creature/sweep_creatures pins both): (1) the "
            "FOOTER is the shipped literal 'Only you can use this "
            "panel.' (views/creature/embeds.py build_menu_embed) — "
            "outside FooterMode's none/subsystem/provenance set (the "
            "casino/community precedent); (2) the 'Your progress' FIELD "
            "interpolates the invoker's LIVE collection count and "
            "creature level ('**0/36** creatures · level **1**') — "
            "read-parameterized state outside the static TextBlock/"
            "FieldsBlock vocabulary. Title, description, colors and "
            "every component stay grammar-rendered."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("creature_catch", "creature_dex", "creature_challenge",
             "creature_ladder", "creature_howto"),)),)),
    )


async def _member_display(user_id: int, guild_id: int) -> str:
    """Display name through the guild-directory read port (renderer
    paths carry no origin member object — the economy/casino precedent);
    degrades to the shipped resolver fallback ``User {id}``
    (cogs/creature_cog.py ``_name``), never invented data."""
    try:
        from sb.domain.utility.service import guild_directory

        member = await guild_directory().member_info(guild_id, user_id)
        name = member.tag.rsplit("#", 1)[0]
        return name or f"User {user_id}"
    except Exception:  # noqa: BLE001 — no directory ⇒ the shipped fallback
        return f"User {user_id}"


async def _progress(user_id: int, guild_id: int) -> tuple[int, int, dict]:
    """(caught_unique, level, collection_log) — the shipped
    views/creature/menu.py ``load_progress`` read set."""
    from sb.domain.creature import catalog, store
    from sb.domain.creature.ops import creature_level_from_xp
    from sb.domain.games import xp as game_xp
    from sb.domain.games.store import game_xp_rows

    log = await store.get_collection(user_id, guild_id)
    rows = await game_xp_rows(user_id, guild_id)
    xp_map = {str(r["game"]): int(r["xp"]) for r in rows}
    level = creature_level_from_xp(xp_map.get(game_xp.GAME_CREATURE, 0))
    known = {c.name for c in catalog.CREATURES}
    caught_unique = sum(1 for name in log if name in known)
    return caught_unique, level, log


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped footer literal +
    the live 'Your progress' field (see justification)."""
    from sb.domain.creature import catalog
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    caught_unique, level, _log = await _progress(uid, gid)
    embed = _dc_replace(
        rendered.embed,
        fields=(("Your progress",
                 f"**{caught_unique}/{len(catalog.CREATURES)}** creatures "
                 f"· level **{level}**"),),
        footer=_HUB_FOOTER)
    return _dc_replace(rendered, embed=embed)


def _card_spec(panel_id: str, style_token: str, render_ref: str,
               justification: str) -> PanelSpec:
    """A component-less transient result card (the karma-card recipe:
    ``session_lifecycle=True``, zero components, override-composed
    embed)."""
    return PanelSpec(
        panel_id=panel_id,
        subsystem="creature",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token=style_token,
                             footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef(render_ref),
        justification=justification,
        session_lifecycle=True,
    )


def dex_card_spec() -> PanelSpec:
    return _card_spec(
        DEX_CARD_PANEL_ID, "green", "creature.render_dex",
        "the shipped dex is read-parameterized end to end "
        "(views/creature/embeds.py build_dex_embed: the display-name "
        "title, the counts/level description, the six per-element INLINE "
        "fields with per-creature caught/not-yet lines, the footer "
        "literal) — outside the static grammar vocabulary; zero "
        "components, the renderer only composes the embed "
        "(goldens/creature/sweep_dex pins the empty-state bytes).")


def collectors_card_spec() -> PanelSpec:
    return _card_spec(
        COLLECTORS_PANEL_ID, "green", "creature.render_collectors",
        "the shipped Top Collectors board is read-parameterized "
        "(views/creature/embeds.py build_collectors_embed: medal-ranked "
        "member lines or the empty-state invitation) — outside the "
        "static grammar vocabulary; zero components "
        "(goldens/creature/sweep_dextop pins the empty-state bytes).")


def record_card_spec() -> PanelSpec:
    return _card_spec(
        RECORD_PANEL_ID, "red", "creature.render_record",
        "the shipped battle record is read-parameterized "
        "(views/creature/embeds.py build_record_embed: the display-name "
        "title, the W/L/winrate description, the footer literal) — "
        "outside the static grammar vocabulary; zero components "
        "(goldens/creature/sweep_cbrecord pins the empty-state bytes).")


def battletop_card_spec() -> PanelSpec:
    return _card_spec(
        BATTLETOP_PANEL_ID, "red", "creature.render_battletop",
        "the shipped Top Trainers ladder is read-parameterized "
        "(views/creature/embeds.py build_battletop_embed: medal-ranked "
        "member lines or the empty-state invitation) — outside the "
        "static grammar vocabulary; zero components "
        "(goldens/creature/sweep_cbattletop pins the empty-state "
        "bytes).")


def rules_card_spec() -> PanelSpec:
    """The shipped 'how to play' quick-reference — a fully STATIC card
    (build_rules_embed has no parameters), grammar-rendered: no
    override. The shipped send was an ephemeral component reply; no
    golden clicks it."""
    return PanelSpec(
        panel_id=RULES_PANEL_ID,
        subsystem="creature",
        title="📖 How to play Creatures",
        audience=Audience.INVOKER,
        # INFO_COLOR blue (utils/ui_constants.py).
        frame=EmbedFrameSpec(style_token="blue",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_RULES_DESCRIPTION),),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        session_lifecycle=True,
    )


def challenge_spec() -> PanelSpec:
    return PanelSpec(
        panel_id=CHALLENGE_PANEL_ID,
        subsystem="creature",
        title="",
        # the shipped challenge message is a PUBLIC channel send; the
        # VIEW is locked to the challenged player (BaseView
        # author=opponent) — the override sets invoker_lock.
        audience=Audience.PUBLIC,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        body=(TextBlock(""),),
        actions=(
            PanelActionSpec(
                action_id="cbattle_accept", label="Accept", emoji="⚔️",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("creature.challenge_accept"),
                reply_visibility=ReplyVisibility.EPHEMERAL),
            PanelActionSpec(
                action_id="cbattle_decline", label="Decline", emoji="❌",
                style=ActionStyle.DANGER, audience_tier="user",
                handler=HandlerRef("creature.challenge_decline"),
                reply_visibility=ReplyVisibility.EPHEMERAL),
        ),
        # the shipped CreatureBattleChallengeView carried ONLY its two
        # buttons (no nav slots; timeout session view) — the golden pins
        # exactly one component row.
        navigation=NavigationSpec(show_help=False, show_home=False),
        renderer_override=HandlerRef("creature.render_challenge"),
        justification=(
            "the shipped challenge message is a CONTENT-only send (no "
            "embed) whose copy interpolates both trainers' mentions "
            "('{opponent} — {challenger} challenges you to a creature "
            "battle! …' — cogs/creature_battle_cog.py), and the view is "
            "locked to the CHALLENGED player, not the invoker "
            "(challenge.py BaseView author=opponent) — the override "
            "returns embed=None + the content line and sets "
            "invoker_lock to the opponent (both outside the grammar's "
            "vocabulary; the logging bind-picker content-only "
            "precedent). The declined terminal re-renders the shipped "
            "'❌ {name} declined the challenge.' edit with both buttons "
            "disabled. goldens/creature/sweep_cbattle pins the open "
            "bytes; the two buttons delegate to render_panel."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("cbattle_accept", "cbattle_decline"),)),)),
    )


async def _render_dex(spec: PanelSpec, ctx) -> object:
    """renderer_override — views/creature/embeds.py ``build_dex_embed``
    verbatim (the ``!dex`` cog path passes no element filter)."""
    from sb.domain.creature import catalog
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    caught_unique, level, log = await _progress(uid, gid)
    known = {c.name for c in catalog.CREATURES}
    total = sum(c for name, c in log.items() if name in known)
    by_element: dict[str, list[str]] = {}
    for creature in catalog.CREATURES:
        count = log.get(creature.name)
        if count:
            line = f"{creature.emoji} **{creature.name}** ×{count}"
        else:
            line = f"{creature.emoji} {creature.name} — *not yet caught*"
        by_element.setdefault(creature.element, []).append(line)
    name = await _member_display(uid, gid)
    embed = RenderedEmbed(
        title=f"🐾 {name}'s Creature Dex",
        description=(
            f"**{caught_unique}/{len(catalog.CREATURES)}** creatures "
            f"discovered · **{total}** total catches · Creature level "
            f"**{level}**"),
        fields=tuple((element, "\n".join(lines), True)
                     for element, lines in by_element.items()),
        footer=_DEX_FOOTER,
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_collectors(spec: PanelSpec, ctx) -> object:
    """renderer_override — ``build_collectors_embed`` verbatim; ranked
    by total creatures caught (the shipped cog docstring's order)."""
    from sb.domain.creature import catalog, store
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    gid = int(ctx.guild_id or 0)
    rows = await store.top_catchers(gid)
    rows = sorted(rows, key=lambda r: (-int(r["total"]),
                                       -int(r["species"])))
    if not rows:
        description = ("No one has been catching yet — be the first "
                       "with `!catch`!")
    else:
        lines = []
        for rank, row in enumerate(rows):
            prefix = (_MEDALS[rank] if rank < len(_MEDALS)
                      else f"**{rank + 1}.**")
            name = await _member_display(int(row["user_id"]), gid)
            lines.append(
                f"{prefix} {name} — **{int(row['total'])}** caught "
                f"({int(row['species'])}/{len(catalog.CREATURES)} "
                "creatures)")
        description = "\n".join(lines)
    embed = RenderedEmbed(title="🐾 Top Collectors",
                          description=description,
                          style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_record(spec: PanelSpec, ctx) -> object:
    """renderer_override — ``build_record_embed`` verbatim; the target
    defaults to the invoker (the shipped ``!cbrecord [member]``)."""
    from sb.domain.creature import store
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    gid = int(ctx.guild_id or 0)
    params = getattr(ctx, "params", {}) or {}
    target = int(params.get("record_target")
                 or getattr(ctx.actor, "user_id", 0) or 0)
    wins, losses = await store.get_battle_record(target, gid)
    name = await _member_display(target, gid)
    embed = RenderedEmbed(
        title=f"⚔️ {name}'s Battle Record",
        description=(f"**{wins}** wins · **{losses}** losses · "
                     f"win rate **{_winrate(wins, losses)}**"),
        footer=_RECORD_FOOTER,
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_battletop(spec: PanelSpec, ctx) -> object:
    """renderer_override — ``build_battletop_embed`` verbatim."""
    from sb.domain.creature import store
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    gid = int(ctx.guild_id or 0)
    rows = await store.top_battlers(gid)
    if not rows:
        description = ("No battles won yet — challenge someone with "
                       "`!cbattle @member`!")
    else:
        lines = []
        for rank, row in enumerate(rows):
            prefix = (_MEDALS[rank] if rank < len(_MEDALS)
                      else f"**{rank + 1}.**")
            name = await _member_display(int(row["user_id"]), gid)
            wins, losses = int(row["wins"]), int(row["losses"])
            lines.append(f"{prefix} {name} — **{wins}**W · {losses}L "
                         f"({_winrate(wins, losses)})")
        description = "\n".join(lines)
    embed = RenderedEmbed(title="⚔️ Top Trainers",
                          description=description,
                          style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_challenge(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped CONTENT-only challenge send +
    the opponent lock; ``params['stage']`` swaps stages: ``declined``
    renders the shipped decline edit (both buttons disabled — the shipped
    ``item.disabled = True`` walk), ``resolved`` renders the auto-resolve
    outcome (the battle embed, or the go-catch nudge when a fighter has no
    team) with the buttons disabled (D-0079)."""
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    rendered = await render_panel(spec, ctx)
    params = getattr(ctx, "params", {}) or {}
    opponent = int(params.get("cb_opponent_id") or 0)
    challenger = int(params.get("cb_challenger_id")
                     or getattr(ctx.actor, "user_id", 0) or 0)
    stage = str(params.get("stage", "") or "")
    if stage == "declined":
        name = await _member_display(opponent, int(ctx.guild_id or 0))
        components = tuple(_dc_replace(c, disabled=True)
                           for c in rendered.components)
        return _dc_replace(
            rendered, embed=None,
            content=f"❌ {name} declined the challenge.",
            components=components,
            invoker_lock=opponent or None)
    if stage == "resolved":
        from sb.domain.creature.battle_service import NO_TEAM_MSG

        components = tuple(_dc_replace(c, disabled=True)
                           for c in rendered.components)
        if params.get("cb_no_team"):
            # neither/one fighter has a team — the shipped go-catch nudge.
            return _dc_replace(
                rendered, embed=None, content=NO_TEAM_MSG,
                components=components, invoker_lock=opponent or None)
        embed = RenderedEmbed(
            title="⚔️ Creature Battle",
            description=str(params.get("cb_desc") or ""),
            fields=tuple((str(n), str(v), bool(i))
                         for n, v, i in params.get("cb_fields", ())),
            style_token="green")
        return _dc_replace(
            rendered, embed=embed, content=None, components=components,
            invoker_lock=opponent or None)
    content = (
        f"<@{opponent}> — <@{challenger}> challenges you to a creature "
        "battle! Teams are level-normalized; your collection and type "
        "matchups decide it.")
    return _dc_replace(rendered, embed=None, content=content,
                       invoker_lock=opponent or None)


@panel(HUB_PANEL_ID)
def _hub_factory() -> PanelSpec:
    return creature_hub_spec()


@panel(DEX_CARD_PANEL_ID)
def _dex_factory() -> PanelSpec:
    return dex_card_spec()


@panel(COLLECTORS_PANEL_ID)
def _collectors_factory() -> PanelSpec:
    return collectors_card_spec()


@panel(RECORD_PANEL_ID)
def _record_factory() -> PanelSpec:
    return record_card_spec()


@panel(BATTLETOP_PANEL_ID)
def _battletop_factory() -> PanelSpec:
    return battletop_card_spec()


@panel(CHALLENGE_PANEL_ID)
def _challenge_factory() -> PanelSpec:
    return challenge_spec()


@panel(RULES_PANEL_ID)
def _rules_factory() -> PanelSpec:
    return rules_card_spec()


_ALL_SPECS = (
    creature_hub_spec, dex_card_spec, collectors_card_spec,
    record_card_spec, battletop_card_spec, challenge_spec,
    rules_card_spec,
)

_FACTORIES = (
    (HUB_PANEL_ID, _hub_factory),
    (DEX_CARD_PANEL_ID, _dex_factory),
    (COLLECTORS_PANEL_ID, _collectors_factory),
    (RECORD_PANEL_ID, _record_factory),
    (BATTLETOP_PANEL_ID, _battletop_factory),
    (CHALLENGE_PANEL_ID, _challenge_factory),
    (RULES_PANEL_ID, _rules_factory),
)

_RENDERS = (
    ("creature.render_hub", _render_hub),
    ("creature.render_dex", _render_dex),
    ("creature.render_collectors", _render_collectors),
    ("creature.render_record", _render_record),
    ("creature.render_battletop", _render_battletop),
    ("creature.render_challenge", _render_challenge),
)


def install_creature_panels() -> tuple[PanelSpec, ...]:
    out = []
    for build in _ALL_SPECS:
        spec = build()
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def _register_renders() -> None:
    for name, fn in _RENDERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef, panel as _panel

    _register_renders()
    _register_pending()
    for panel_id, factory in _FACTORIES:
        if not is_registered(PanelRef(panel_id)):
            _panel(panel_id)(factory)


_register_renders()
