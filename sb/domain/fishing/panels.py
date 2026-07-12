"""Fishing panels (band 6 / parity flip) — the SHIPPED surfaces byte-for-byte:

* ``fishing.cast`` — disbot/views/fishing/cast_view.py ``prepare_cast``'s
  waiting-for-a-bite panel: the GAME_COLOR purple embed ("You cast a line
  from the shoreline… 🏖️" + the Reel coaching italic), the
  weather-of-the-day field (shown only when the condition moves a knob —
  clear renders silent, shipped conditional), the venue+energy footer
  (``🏖️ Shore · ⚡ 58/60 [▰▰▰▰▰▰▰▰▰▰]``) and the single grey
  ``🎣 Waiting for a bite…`` button. ``goldens/fishing/sweep_fish.json``
  pins every byte: the run-minted ``<cid:1>`` button id (timeout session
  view ⇒ ``session_lifecycle=True``, no ``panel_anchors`` row), the
  emoji-in-label form (trap 15a's other flavor), style 2, and the spent
  fresh-bar ``fishing_energy`` row (60→58, CAST_COST=2) the cast-open
  handler writes BEFORE the panel renders.

* ``fishing.log`` — disbot/views/fishing/menu.py's fishdex embed
  (``build_fishdex_embed`` lane): the ``🎣 {display_name}'s Fishing Log``
  blue embed — the discovered/total/level description line, one field per
  venue (``🏖️ Shore — up to size #N`` / ``⛵ Deepwater (boat-only) — up
  to size #N``) listing every species as caught (**bold** ×count · 🏅
  trophy) / not-yet-caught / ``🔒 ??? — *locked*``, and the literal
  cast/sail/rod footer. ``goldens/fishing/sweep_fishlog.json`` pins the
  fresh-angler read (0/32 · 0 catches · level 1/7) with ZERO components
  (``components: []`` — the karma error-card zero-component session-panel
  wire shape) and no db_delta row (a pure read).

Trap-24 drift check (fishing row): the oracle current-head fragments
(views/fishing/cast_view.py description/field/footer + the reel button
decorator; views/fishing/menu.py log title/description/venue
fields/footer + _venue_log_lines; utils/fishing/weather.py CONDITIONS +
effect_text; utils/fishing/energy.py bar/settle constants) match the
corpus goldens byte-for-byte — NO drift (corpus sha 7f7628e1).

Under-port ledger (no golden pins these corners):
* the shipped cast view ran the live minigame in-place — bite-delay
  timers flipping the button to the reel window, fake-out shakes, early
  reel escapes, a reeled catch EDITING the panel into the result embed
  (``interaction.response.edit_message``). The port's Reel button routes
  the audited instant-catch lane (``fishing.cast`` K7 op — dex upsert +
  materials + game-XP in one leg txn) and opens the result as a fresh
  result card (the farm in-place-edit under-port precedent); the timing
  layer (utils/fishing/minigame.py) rides the D-0043 successor port with
  the rod/bait/venue systems.
* the shipped ``active_casts`` one-line-in-the-water guard is process
  state of that timer layer — same successor.
* the deepwater venue profile ("from the boat, out over the deep water",
  ⛵) needs the sail lane (pending terminal) — every port cast is a
  shore cast, exactly the shipped fresh-player posture the golden pins.

MONEY-RACE NOTE (#217 / coordinator ruling 2026-07-12): this module and
the cast-open handler touch NO money primitive — fishing_energy is game
pacing, never coins; reads/writes here are the shipped unlocked
get→settle→set pair on a non-money table. The FOR UPDATE + advisory-lock
shapes (sb/domain/games/wager.py, sb/domain/games/store.py, farm/mining
#217 legs) are not in this diff; fishing's own K7 leg
(ops.py record_cast) is untouched.
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
    ResultRender,
    TextBlock,
)
from sb.spec.refs import HandlerRef, handler, is_registered, panel

__all__ = [
    "CAST_PANEL_ID",
    "LOG_PANEL_ID",
    "cast_spec",
    "ensure_panel_refs",
    "install_fishing_panels",
    "log_spec",
]

CAST_PANEL_ID = "fishing.cast_panel"
LOG_PANEL_ID = "fishing.log"

#: The shore venue's display identity (utils/fishing/venue.py
#: SHORE_PROFILE — name="Shore", emoji="🏖️"); the deepwater profile
#: rides the sail successor (module docstring).
SHORE_NAME = "Shore"
SHORE_EMOJI = "🏖️"

#: views/fishing/cast_view.py, verbatim (the golden pins the rendered
#: bytes; ``where`` = "from the shoreline" — every port cast is shore).
_CAST_DESCRIPTION = (
    "You cast a line from the shoreline… 🏖️\n"
    "*Watch the water — hit **Reel** the moment it bites, but not before!*"
)

#: views/fishing/menu.py set_footer literal, verbatim.
_LOG_FOOTER = "🎣 Cast to fish · ⛵ Set sail for the deep · 🎒 Rod to upgrade"


def cast_spec() -> PanelSpec:
    return PanelSpec(
        panel_id=CAST_PANEL_ID,
        subsystem="fishing",
        title="",
        audience=Audience.INVOKER,
        # GAME_COLOR purple (10181046, utils/ui_constants.py) — the farm
        # hub token; description/weather-field/footer ride the override.
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_CAST_DESCRIPTION),),
        actions=(
            PanelActionSpec(
                action_id="fishing_reel", label="🎣 Waiting for a bite…",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("fishing.fish_route"),
                result_render=ResultRender.RESULT_CARD),
        ),
        # the shipped CastView is a bare timer view — no help/home nav row
        # (the golden pins the single-button component row).
        navigation=NavigationSpec(show_help=False, show_home=False),
        renderer_override=HandlerRef("fishing.render_cast"),
        justification=(
            "two shipped surfaces sit outside the grammar's vocabulary "
            "(goldens/fishing/sweep_fish pins both): (1) the FOOTER "
            "interpolates the venue profile and the invoker's LIVE "
            "settled energy gauge ('🏖️ Shore · ⚡ 58/60 [▰▰▰▰▰▰▰▰▰▰]', "
            "views/fishing/cast_view.py footer = profile + energy.bar) — "
            "outside FooterMode's vocabulary (the farm balance-footer "
            "precedent); (2) the WEATHER FIELD is the day's shared "
            "condition rendered only when it moves a cast knob "
            "(cast_view's clear-is-silent conditional; name '{emoji} "
            "{name}', value '*{blurb}* ({effect_text})') — day-keyed "
            "state outside the static TextBlock/FieldsBlock vocabulary. "
            "Description, color and the component stay grammar-rendered."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(("fishing_reel",),)),)),
    )


def log_spec() -> PanelSpec:
    """The shipped fishdex — a component-less per-read result card (the
    shipped send was a plain ``ctx.send(embed=...)``, never an anchored
    panel; the karma card/casino precedent)."""
    return PanelSpec(
        panel_id=LOG_PANEL_ID,
        subsystem="fishing",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blue", footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("fishing.render_log"),
        justification=(
            "the shipped fishdex embed is read-parameterized end to end "
            "(views/fishing/menu.py; goldens/fishing/sweep_fishlog pins "
            "the bytes): the TITLE carries the invoker's display name "
            "('🎣 AdminActor's Fishing Log'), the description "
            "interpolates discovered/total/level, and the per-venue "
            "fields render the live dex (caught ×count · trophy / not "
            "yet caught / locked) against the level-banded species "
            "catalog — all outside the static grammar vocabulary. Zero "
            "components; the renderer only composes the embed."),
        session_lifecycle=True,
    )


async def _member_display_name(user_id: int, guild_id: int) -> str:
    """The invoker's display name through the guild-directory read port
    (the karma/economy author-line precedent) — degrades to the bare
    mention, never invented data."""
    try:
        from sb.domain.utility.service import guild_directory

        member = await guild_directory().member_info(guild_id, user_id)
    except Exception:  # noqa: BLE001 — no directory ⇒ mention fallback
        return f"<@{user_id}>"
    return member.tag.rsplit("#", 1)[0]


async def _render_cast(spec: PanelSpec, ctx) -> object:
    """renderer_override — cast_view.py's embed dressing (see
    justification): grammar render + the weather field + the
    venue/energy footer. The energy was already settled+spent by the
    cast-open handler (the write precedes the render — the golden's
    58/60 gauge is the POST-spend read)."""
    from sb.domain.fishing import energy as energy_mod
    from sb.domain.fishing import weather as weather_mod
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    params = getattr(ctx, "params", {}) or {}
    current = params.get("cast_energy")
    if current is None:
        # direct panel open (no cast-open hop) — honest settled read,
        # no spend.
        from sb.domain.fishing import store
        from sb.kernel.workflow.context import SYSTEM_CLOCK

        uid = int(getattr(ctx.actor, "user_id", 0) or 0)
        gid = int(ctx.guild_id or 0)
        now = int(SYSTEM_CLOCK().timestamp())
        cur, ts = await store.get_fishing_energy(uid, gid)
        current = energy_mod.settle(energy_mod.EnergyState(cur, ts),
                                    now).current
    w = weather_mod.current_weather()
    fields: tuple = ()
    if w.bite_speed_mult != 1.0 or w.rarity_mult != 1.0:
        # Only show the forecast when it actually changes the cast
        # (clear = silent) — cast_view.py verbatim.
        fields = ((f"{w.emoji} {w.name}",
                   f"*{w.blurb}* ({weather_mod.effect_text(w)})"),)
    footer = (f"{SHORE_EMOJI} {SHORE_NAME} · "
              + energy_mod.bar(int(current)))
    embed = _dc_replace(rendered.embed, fields=fields, footer=footer)
    return _dc_replace(rendered, embed=embed)


async def _render_log(spec: PanelSpec, ctx) -> object:
    """renderer_override — menu.py's fishdex embed verbatim (see
    justification)."""
    from sb.domain.fishing import catalog, store
    from sb.domain.games import xp as game_xp
    from sb.domain.games.store import game_xp_rows
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    rows = await store.get_catch_log(uid, gid)
    log = {str(r["species"]): int(r["count"]) for r in rows}
    records = {str(r["species"]): float(r["best_weight"]) for r in rows}
    known = set(catalog.fish_names())
    xp_rows = {str(r["game"]): int(r["xp"])
               for r in await game_xp_rows(uid, gid)}
    level = catalog.fishing_level_from_xp(
        xp_rows.get(game_xp.GAME_FISHING, 0))
    caught = sum(1 for name in log if name in known)
    total = sum(c for name, c in log.items() if name in known)
    name = await _member_display_name(uid, gid)
    fields: list[tuple] = []
    for venue, label in (
        (catalog.SHORE_VENUE, "🏖️ Shore"),
        (catalog.DEEPWATER, "⛵ Deepwater (boat-only)"),
    ):
        cap = catalog.max_size_rank_for_level(level, venue)
        lines = _venue_log_lines(log, venue, cap, records)
        if lines:
            fields.append((f"{label} — up to size #{cap}",
                           "\n".join(lines)))
    embed = RenderedEmbed(
        title=f"🎣 {name}'s Fishing Log",
        description=(
            f"**{caught}/{len(known)}** species discovered · "
            f"**{total}** total catches · "
            f"Fishing level **{level}/{catalog.MAX_LEVEL}**"),
        fields=tuple(fields),
        footer=_LOG_FOOTER,
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


def _venue_log_lines(log: dict[str, int], venue: str, cap: int,
                     records: dict[str, float]) -> list[str]:
    """views/fishing/menu.py ``_venue_log_lines`` verbatim — one line per
    species in the venue: caught (bold, ×count, 🏅 trophy) /
    unlocked-but-uncaught / locked."""
    from sb.domain.fishing import catalog

    lines: list[str] = []
    for species in catalog.species_for_venue(venue):
        count = log.get(species.name, 0)
        unlocked = species.size_rank <= cap
        if count:
            best = records.get(species.name, 0.0)
            trophy = f" · 🏅 {best:g}kg" if best > 0 else ""
            lines.append(
                f"{species.emoji} **{species.name.title()}** "
                f"(#{species.size_rank}) ×{count}{trophy}")
        elif unlocked:
            lines.append(
                f"{species.emoji} {species.name.title()} "
                f"(#{species.size_rank}) — *not yet caught*")
        else:
            lines.append(f"🔒 ??? (#{species.size_rank}) — *locked*")
    return lines


@panel(CAST_PANEL_ID)
def _cast_factory() -> PanelSpec:
    return cast_spec()


@panel(LOG_PANEL_ID)
def _log_factory() -> PanelSpec:
    return log_spec()


_FACTORIES = (
    (CAST_PANEL_ID, _cast_factory),
    (LOG_PANEL_ID, _log_factory),
)

_RENDERS = (
    ("fishing.render_cast", _render_cast),
    ("fishing.render_log", _render_log),
)


def install_fishing_panels() -> tuple[PanelSpec, ...]:
    out = []
    for build in (cast_spec, log_spec):
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
    from sb.spec.refs import PanelRef as _P, panel as _panel

    _register_renders()
    for panel_id, factory in _FACTORIES:
        if not is_registered(_P(panel_id)):
            _panel(panel_id)(factory)


_register_renders()
