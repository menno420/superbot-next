"""BTD6 Paragon calculator — the armed session surface (band 7).

The pure-compute port of the shipped calculator flows (ORACLE
``views/btd6/paragon_view.py`` + ``views/btd6/paragon_modals.py``
@7f7628e1) over :mod:`sb.domain.btd6.paragon_math` (the API-replica power
model the oracle validated field-by-field against the live endpoint):

* the four landing selectors (paragon / players / difficulty / extra-T5)
  update per-message session state and re-render the landing embed IN
  PLACE (the shipped ``rebuild()`` + ``safe_edit`` loop →
  ``refresh_session_view``), re-bounding the extra-T5 roster by
  mode/paragon exactly like the shipped ``_Tier5Select``;
* 🧮 **Calculate degree** opens the shipped ``ParagonForwardModal`` twin
  (5 numeric fields) and answers with the ``build_result_embed`` card;
* 🎯 **Requirements** opens the shipped ``ParagonRequirementsView`` twin
  (strategy select + 🎯 Enter target degree modal + ↩ Calculator) and
  answers with the ``build_requirement_embed`` card;
* 📊 **Stats** opens the shipped ``ParagonStatsView`` twin — the
  ``btd6.paragon_stats`` degree view (milestone select + 🔢 Enter-degree
  modal + ↩ Calculator) over the PORTED
  :func:`sb.domain.btd6.stats.paragon_stats_at_degree` +
  :mod:`sb.domain.btd6.paragon_degrees` formulas — or answers with the
  shipped module-less copy verbatim.

Ledgered deviations (engine-shape, the D-0054 intermediating posture —
no golden pins any of these click routes, #151's drop rule):

* the shipped Requirements/Stats clicks EDITED the calculator message
  into the sub-view; this engine opens the requirements page / stats
  card as its own ephemeral panel message and ↩ Calculator opens a
  fresh landing panel (the ai settings-widget open→work→Back recipe);
* compute is ALWAYS the local formula — the live-API call, its 60s
  cache, and the 429 taxonomy stay the D-0046 named successor. Result
  cards therefore footer ``local formula`` instead of the shipped
  ``API v<n>`` / ``estimate`` pair, and carry NO "live calculator was
  unreachable" warning (nothing was attempted — that copy would lie);
  the requirement card keeps the shipped "Not live-confirmed — computed
  locally." line (true here by construction);
* the stats page opens at Degree 1 — the shipped degree-independent BASE
  infobox view (``_stat_node_embed`` over ``stats.base``) rides the
  deep-stats successor (D-0046); scaled == base at degree 1 by the wiki
  formulas, so no number changes.

Handlers register at MODULE IMPORT (the BUG A rule)."""

from __future__ import annotations

import dataclasses

from sb.domain.btd6 import paragon_math as pm
from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = [
    "DEFAULT_PARAGON",
    "DEGREE_MILESTONES",
    "PARAGON_CALC_AUTHOR",
    "PARAGON_CALC_URL",
    "PARAGON_DIFFICULTIES",
    "calc_state",
    "calculator_card",
    "degree_options",
    "difficulty_options",
    "ensure_paragon_refs",
    "paragon_options",
    "player_options",
    "req_state",
    "requirements_card",
    "stats_degree_card",
    "stats_state",
    "strategy_options",
    "tier5_options",
]

#: the live web Paragon Calculator + its Discord author credit (shipped
#: services/paragon_service.CALCULATOR_PUBLIC_URL / CALCULATOR_AUTHOR_NAME).
PARAGON_CALC_URL = "https://paragon-calc.vercel.app/"
PARAGON_CALC_AUTHOR = "notausgang0341"
DEFAULT_PARAGON = "apex_plasma_master"

#: (value, label) difficulty rows in the shipped select order.
PARAGON_DIFFICULTIES = (
    ("easy", "Easy (0.85x)"),
    ("medium", "Medium (1.0x)"),
    ("hard", "Hard (1.08x)"),
    ("impoppable", "Impoppable (1.2x)"),
)

#: shipped axis presentation maps (views/btd6/paragon_view.py verbatim).
_AXIS_EMOJI = {
    "pops": "💥",
    "upgrades": "⬆️",
    "cash": "💰",
    "extra_t5s": "🛡️",
    "totems": "🔱",
}
_AXIS_LABEL = {
    "pops": "Pops",
    "upgrades": "Upgrade tiers",
    "cash": "Cash",
    "extra_t5s": "Extra T5s",
    "totems": "Geraldo totems",
}
_STRATEGY_LABEL = {
    pm.SolveStrategy.BALANCED: "Balanced (even split)",
    pm.SolveStrategy.LEAST_CASH: "Least cash",
    pm.SolveStrategy.LEAST_TIERS: "Least tiers",
    pm.SolveStrategy.LEAST_POPS: "Least pops",
}

CALC_PANEL_ID = "btd6.paragon"
REQ_PANEL_ID = "btd6.paragon_requirements"
STATS_PANEL_ID = "btd6.paragon_stats"

#: the shipped stats-view degree-select milestones
#: (views/btd6/paragon_stats_view.py @7f7628e1).
DEGREE_MILESTONES = (1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)

#: polite copy for the (rare) evicted-session refresh miss.
_EXPIRED = "This session has expired — open a fresh calculator with `!paragon`."


# --- per-message session state (the shipped view attributes) -----------------

_STATE: dict[str, dict] = {}
_STATE_MAX = 512


def _store_state(key: str, state: dict) -> None:
    if key:
        _STATE[key] = state
        while len(_STATE) > _STATE_MAX:
            _STATE.pop(next(iter(_STATE)))


def _message_key(req) -> str:
    message = getattr(req.origin, "message", None)
    return str(getattr(message, "id", "") or "")


def calc_state(params: dict | None) -> dict:
    """Coerce calculator state out of *params* (defaults = the shipped
    landing state: Apex Plasma Master · solo · Medium · 0 extra T5),
    clamping extra-T5 to the mode/paragon limit (the shipped ``rebuild``)."""
    p = dict(params or {})
    paragon = pm.resolve_paragon(str(p.get("paragon_id") or DEFAULT_PARAGON))
    if paragon is None:  # defensive — the select vocabulary is closed
        paragon = pm.resolve_paragon(DEFAULT_PARAGON)
    try:
        players = int(p.get("player_count") or 1)
    except (TypeError, ValueError):
        players = 1
    players = min(4, max(1, players))
    difficulty = str(p.get("difficulty") or "medium")
    if difficulty not in {v for v, _ in PARAGON_DIFFICULTIES}:
        difficulty = "medium"
    try:
        tier5 = int(p.get("tier5_count") or 0)
    except (TypeError, ValueError):
        tier5 = 0
    limit = pm.max_extra_t5_count(
        pm.game_mode_for(players), is_dart=paragon.is_dart)
    return {
        "paragon_id": paragon.paragon_id,
        "player_count": players,
        "difficulty": difficulty,
        "tier5_count": max(0, min(tier5, limit)),
    }


def req_state(params: dict | None) -> dict:
    """Requirements-page state (the shipped ParagonRequirementsView
    attributes: paragon/players/difficulty + strategy, no extra-T5)."""
    state = calc_state(params)
    state.pop("tier5_count", None)
    raw = str((params or {}).get("strategy") or "balanced")
    try:
        strategy = pm.SolveStrategy(raw)
    except ValueError:
        strategy = pm.SolveStrategy.BALANCED
    state["strategy"] = strategy.value
    return state


def stats_state(params: dict | None) -> dict:
    """Stats-page state (the shipped ParagonStatsView attributes: the
    calculator state + the viewed degree, clamped 1..100)."""
    state = calc_state(params)
    try:
        degree = int((params or {}).get("degree") or 1)
    except (TypeError, ValueError):
        degree = 1
    state["degree"] = min(100, max(1, degree))
    return state


# --- select option rosters (shipped, state-parameterized) ---------------------


def paragon_options(state: dict) -> tuple[dict, ...]:
    return tuple(
        {"label": p.name[:100], "value": p.paragon_id,
         "description": p.tower[:100],
         "default": p.paragon_id == state["paragon_id"]}
        for p in pm.PARAGONS
    )


def player_options(state: dict) -> tuple[dict, ...]:
    return tuple(
        {"label": "Solo (1 player)" if n == 1 else f"Co-op ({n} players)",
         "value": str(n), "default": n == state["player_count"]}
        for n in (1, 2, 3, 4)
    )


def difficulty_options(state: dict) -> tuple[dict, ...]:
    return tuple(
        {"label": label, "value": value,
         "default": value == state["difficulty"]}
        for value, label in PARAGON_DIFFICULTIES
    )


def tier5_options(state: dict) -> tuple[tuple[dict, ...], bool]:
    """``(options, disabled)`` — the shipped ``_Tier5Select`` bounds its
    roster by ``max_extra_t5_count`` and ships DISABLED (with the
    'not allowed here' option) when the limit is 0."""
    paragon = pm.resolve_paragon(state["paragon_id"])
    limit = pm.max_extra_t5_count(
        pm.game_mode_for(state["player_count"]),
        is_dart=bool(paragon and paragon.is_dart))
    if limit <= 0:
        return (({"label": "0 extra T5 (not allowed here)", "value": "0",
                  "default": True},), True)
    return (tuple(
        {"label": f"{n} extra T5", "value": str(n),
         "default": n == state["tier5_count"]}
        for n in range(0, limit + 1)
    ), False)


def strategy_options(state: dict) -> tuple[dict, ...]:
    return tuple(
        {"label": _STRATEGY_LABEL[s], "value": s.value,
         "default": s.value == state["strategy"]}
        for s in pm.SolveStrategy
    )


def degree_options(state: dict) -> tuple[dict, ...]:
    """The shipped ``_DegreeSelect`` milestone roster (a non-milestone
    degree — reached via the modal — simply carries no default)."""
    return tuple(
        {"label": f"Degree {d}", "value": str(d),
         "default": d == state["degree"]}
        for d in DEGREE_MILESTONES
    )


# --- embeds (the shipped builders, RenderedEmbed-shaped) ----------------------


def _fmt(value: int) -> str:
    return f"{value:,}"


def _credits_field() -> tuple[str, str]:
    """The shipped ``_add_credits_field`` — travels with every result."""
    return ("🔗 Web calculator & credits",
            f"[paragon-calc.vercel.app]({PARAGON_CALC_URL}) — built by "
            f"**{PARAGON_CALC_AUTHOR}**")


def calculator_card(state: dict):
    """The shipped ``build_calculator_embed`` (goldens/btd6/sweep_paragon
    pins the default-state bytes)."""
    from sb.kernel.panels.render import RenderedEmbed

    paragon = pm.resolve_paragon(state["paragon_id"])
    name = paragon.name if paragon else state["paragon_id"]
    tower = paragon.tower if paragon else ""
    mode = pm.game_mode_for(state["player_count"])
    return RenderedEmbed(
        title=f"🔮 Paragon Calculator — {name}",
        description=(
            f"**Paragon:** {name} ({tower})\n"
            f"**Players:** {state['player_count']} ({mode})\n"
            f"**Difficulty:** {state['difficulty'].title()}\n"
            f"**Extra T5s:** {state['tier5_count']}"),
        fields=(
            ("🧮 Calculate degree",
             "Enter your pops / cash / tiers / totems to see the degree "
             "you'd get."),
            ("🎯 Requirements for a degree",
             "Pick a strategy and a target degree to get a recommended "
             "build."),
            _credits_field(),
        ),
        footer="Solo: 1 extra T5 (Dart only) · Co-op: up to 9 · totems "
               "are uncapped",
        style_token="green",
    )


def requirements_card(state: dict):
    """The shipped ``build_requirements_config_embed`` (blurple)."""
    from sb.kernel.panels.render import RenderedEmbed

    paragon = pm.resolve_paragon(state["paragon_id"])
    name = paragon.name if paragon else state["paragon_id"]
    mode = pm.game_mode_for(state["player_count"])
    strategy = pm.SolveStrategy(state["strategy"])
    return RenderedEmbed(
        title=f"🎯 Requirements — {name}",
        description=(
            f"**Strategy:** {_STRATEGY_LABEL[strategy]}\n"
            f"**Players:** {state['player_count']} ({mode})\n"
            f"**Difficulty:** {state['difficulty'].title()}\n\n"
            "Choose a strategy, then **Enter target degree** to get a "
            "build."),
        fields=(_credits_field(),),
        footer="Least-X maxes the other inputs; totems top up only the "
               "highest degrees.",
        style_token="blurple",
    )


def _axis_line(axis: pm.AxisBreakdown) -> str:
    if axis.max_power is None:
        return (f"{_AXIS_EMOJI[axis.key]} **{_AXIS_LABEL[axis.key]}:** "
                f"{_fmt(axis.power)} (uncapped)")
    pct = f" ({axis.fill_pct:.0f}%)" if axis.fill_pct is not None else ""
    capped = " • **capped**" if axis.capped else ""
    return (f"{_AXIS_EMOJI[axis.key]} **{_AXIS_LABEL[axis.key]}:** "
            f"{_fmt(axis.power)} / {_fmt(axis.max_power)}{pct}{capped}")


def result_card(paragon: pm.Paragon, breakdown: pm.ParagonBreakdown,
                warnings: tuple[pm.ParagonWarning, ...], state: dict):
    """The shipped ``build_result_embed`` over the local formula (the
    pure-compute posture: footer suffix ``local formula``, no degraded
    gold tint, no invented 'unreachable' warning — module doc)."""
    from sb.kernel.panels.render import RenderedEmbed

    lines = [f"**Total power:** {_fmt(breakdown.total_power)}"]
    if breakdown.degree < pm.MAX_DEGREE:
        lines.append(
            f"**To Degree {breakdown.next_degree}:** "
            f"+{_fmt(breakdown.power_for_next_degree)} power")
    else:
        lines.append("**Maximum degree reached.** 🏆")
    fields = [("Power breakdown",
               "\n".join(_axis_line(axis) for axis in breakdown.axes))]
    if breakdown.wasted_cash > 0:
        fields.append((
            "💸 Wasted cash",
            f"${_fmt(breakdown.wasted_cash)} gave no benefit "
            "(cash power is capped)."))
    notes = [w.message for w in warnings]
    if notes:
        fields.append(("⚠️ Notes",
                       "\n".join(f"• {note}" for note in notes)))
    fields.append(_credits_field())
    bp = pm.base_price(paragon, state["difficulty"])
    return RenderedEmbed(
        title=f"🔮 {paragon.name} — Degree {breakdown.degree}",
        description="\n".join(lines),
        fields=tuple(fields),
        footer=(f"{paragon.tower} • {state['difficulty'].title()} • "
                f"{pm.game_mode_for(state['player_count'])} • "
                f"base ${_fmt(bp)} • local formula"),
        style_token="green",
    )


def requirement_card(paragon: pm.Paragon, solution: pm.RequirementSolution):
    """The shipped ``build_requirement_embed`` — the reverse-solve build
    card (keeps the shipped 'Not live-confirmed' line: true here by
    construction, module doc)."""
    from sb.kernel.panels.render import RenderedEmbed

    inputs = solution.inputs
    fields = [(
        "Recommended sacrifices",
        f"💥 **Pops:** {_fmt(inputs.pops)}\n"
        f"⬆️ **Upgrade tiers:** {inputs.upgrade_count}\n"
        f"💰 **Cash:** ${_fmt(inputs.cash_spent)}\n"
        f"🛡️ **Extra T5s:** {inputs.tier5_count}\n"
        f"🔱 **Geraldo totems:** {inputs.geraldo_totems}")]
    if solution.requires_totems:
        fields.append((
            "🔱 Totems required",
            "Capped inputs alone can't reach this degree — Geraldo totems "
            "make up the rest."))
    fields.append(_credits_field())
    return RenderedEmbed(
        title=f"🎯 {paragon.name} — reach Degree {solution.target_degree}",
        description=(
            f"**Strategy:** {_STRATEGY_LABEL[solution.strategy]}\n"
            f"**This build reaches:** Degree {solution.breakdown.degree}\n\n"
            "⚠️ *Not live-confirmed — computed locally.*"),
        fields=tuple(fields),
        footer=(f"{paragon.tower} • {inputs.difficulty.title()} • "
                f"{pm.game_mode_for(inputs.player_count)}"),
        style_token="green",
    )


def stats_card(paragon_id: str):
    """The base combat-stats card from the ported stats layer, or the
    shipped module-less copy (views/btd6/paragon_view.py
    ``_StatsButton.callback``, verbatim). The 📊 Stats click serves only
    the module-less branch here — combat-stats paragons route to the
    ``btd6.paragon_stats`` degree view (:func:`stats_degree_card`)."""
    from sb.domain.btd6 import stats as stats_mod
    from sb.kernel.panels.render import RenderedEmbed

    stats = stats_mod.get_paragon_stats(paragon_id)
    if stats is None or not stats.has_combat_stats:
        # Module-less paragon (Root of all Nature, Herald of Everfrost):
        # the wiki has no stats data page yet, so only its cost is known.
        return RenderedEmbed(
            title="📊 Paragon stats",
            description=(
                "No combat-stats module is published for this paragon yet "
                "— only its cost is known. Pick another paragon to see "
                "full stats."),
            style_token="orange",
        )
    header = f"{stats.tower_canonical}'s Paragon (tier 6)"
    if stats.cost:
        header += f" · ${stats.cost:,} on Medium"
    header += "\n*Damage, pierce and cooldown scale with degree (1–100).*"
    if stats.is_prose_sourced:
        header += ("\n*ℹ️ Transcribed from the wiki article (no data "
                   "module yet) — primary attacks only.*")
    fields = []
    for attack in stats_mod.attack_breakdown(stats.base.get("attacks") or []):
        parts = [
            f"{name} — **{damage:g}** dmg · **{pierce:g}** pierce"
            for name, damage, pierce in attack.projectiles]
        parts.append(f"cooldown **{attack.cooldown:g}s**")
        fields.append((attack.name, "\n".join(parts)[:1024]))
    if not fields:
        fields.append(("—", "No combat stats."))
    return RenderedEmbed(
        title=f"👑 {stats.canonical} — Base stats",
        description=header,
        fields=tuple(fields),
        footer=f"BTD6 stats v{stats.game_version}",
        style_token="gold",
    )


def stats_degree_card(paragon_id: str, degree: int):
    """The paragon degree view over the PORTED per-attack math
    (:func:`stats.paragon_stats_at_degree`): the shipped
    ``build_paragon_degree_embed`` headline lines verbatim (power / boss
    multiplier / elite multiplier), then one field per attack from the
    ported projectile breakdown (the shipped full cell-group table rides
    ``paragon_degrees.degree_row`` — the deep-stats successor)."""
    from sb.domain.btd6 import paragon_degrees
    from sb.domain.btd6 import stats as stats_mod
    from sb.kernel.panels.render import RenderedEmbed

    row = stats_mod.paragon_stats_at_degree(paragon_id, degree)
    pstats = stats_mod.get_paragon_stats(paragon_id)
    version = pstats.game_version if pstats else ""
    if row is None:
        deg = min(100, max(1, int(degree)))
        canonical = pstats.canonical if pstats else paragon_id
        return RenderedEmbed(
            title=f"👑 {canonical} — Degree {deg}",
            description=(
                f"**Power required:** "
                f"{paragon_degrees.power_for_degree(deg):,}\n"
                f"**Boss-damage multiplier:** "
                f"×{paragon_degrees.boss_multiplier(deg)}\n"
                f"**Elite-boss multiplier:** "
                f"×{paragon_degrees.elite_boss_multiplier(deg):g} "
                "(paragons deal ×2 vs Elite Bosses)"),
            fields=(("—", "No degree-dependent stats."),),
            footer=f"BTD6 stats v{version}",
            style_token="gold")
    fmt = paragon_degrees.format_value
    fields = []
    for attack in row.attacks:
        bits = [
            f"{name} **{fmt(damage)} dmg** · {fmt(pierce)} pierce"
            for name, damage, pierce in attack.projectiles
        ]
        bits.append(f"cooldown **{fmt(attack.cooldown)}s**")
        fields.append((attack.name, " · ".join(bits)[:1024]))
    return RenderedEmbed(
        title=f"👑 {row.canonical} — Degree {row.degree}",
        description=(
            f"**Power required:** {row.power:,}\n"
            f"**Boss-damage multiplier:** ×{row.boss_multiplier}\n"
            f"**Elite-boss multiplier:** "
            f"×{paragon_degrees.elite_boss_multiplier(row.degree):g} "
            "(paragons deal ×2 vs Elite Bosses)"),
        fields=tuple(fields),
        footer=f"BTD6 stats v{version}",
        style_token="gold")


# --- modal input parsing (paragon_modals._parse_int, verbatim) ----------------


def _parse_int(raw: object, *, field: str, minimum: int = 0,
               maximum: int | None = None) -> int:
    cleaned = str(raw or "").strip().replace(",", "").replace("$", "") \
        .replace(" ", "")
    if cleaned == "":
        if minimum > 0:
            raise ValueError(f"{field} is required.")
        return 0
    try:
        value = int(cleaned)
    except ValueError:
        raise ValueError(f"{field} must be a whole number.") from None
    if value < minimum:
        raise ValueError(f"{field} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field} must be at most {maximum}.")
    return value


# --- presentation plumbing ----------------------------------------------------


async def _card(req, embed) -> None:
    """Present one card through the ``btd6.card`` panel (the shared
    oracle-card reply lane)."""
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef("btd6.card"),
                     dataclasses.replace(
                         req, args={**dict(req.args), "_card": embed}))


async def _open_with_state(req, panel_id: str, state: dict) -> None:
    """Open *panel_id* seeded with *state* (rides both the open args —
    the binding/modal-stash lane — and the per-message store)."""
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    key = await open_panel(
        PanelRef(panel_id),
        dataclasses.replace(req, args={**dict(req.args), **state}))
    _store_state(str(key), dict(state))


async def _refresh(req, key: str, state: dict) -> bool:
    from sb.kernel.panels.engine import refresh_session_view

    return await refresh_session_view(req, message_key=key,
                                      params=dict(state))


# --- handlers ------------------------------------------------------------------


async def paragon_select(req) -> Reply:
    """One of the four landing selectors (the shipped ``_ParagonSelect`` /
    ``_PlayerCountSelect`` / ``_DifficultySelect`` / ``_Tier5Select``
    callbacks): update the panel state, clamp extra-T5 to the new
    mode/paragon limit (the shipped ``rebuild()``), and re-render the
    landing embed + selects in place."""
    values = tuple(req.args.get("values", ()) or ())
    if not values:
        return Reply(SUCCESS, None)
    key = _message_key(req)
    state = calc_state(_STATE.get(key) or req.args)
    picked = str(values[0])
    selector = str(req.args.get("session_action") or "")
    if selector == "paragon" and pm.resolve_paragon(picked) is not None:
        state["paragon_id"] = picked
    elif selector == "players" and picked.isdigit():
        state["player_count"] = min(4, max(1, int(picked)))
    elif selector == "difficulty" \
            and picked in {v for v, _ in PARAGON_DIFFICULTIES}:
        state["difficulty"] = picked
    elif selector == "tier5" and picked.isdigit():
        state["tier5_count"] = int(picked)
    state = calc_state(state)            # re-clamp extra-T5 (shipped rebuild)
    _store_state(key, state)
    if not await _refresh(req, key, state):
        return Reply(BLOCKED, _EXPIRED)
    return Reply(SUCCESS, None)


async def paragon_calc_submit(req) -> Reply:
    """🧮 Calculate degree — the shipped ``ParagonForwardModal.on_submit``:
    parse the five numeric fields (error copy verbatim), compute the
    breakdown through the local formula, present the result card."""
    try:
        pops = _parse_int(req.args.get("pops"), field="Pops")
        cash = _parse_int(req.args.get("cash_spent"), field="Cash spent")
        slider = _parse_int(req.args.get("slider_cash"), field="Slider cash")
        upgrades = _parse_int(req.args.get("upgrade_count"),
                              field="Upgrade tiers")
        totems = _parse_int(req.args.get("geraldo_totems"),
                            field="Geraldo totems")
    except ValueError as exc:
        return Reply(BLOCKED, f"❌ {exc}")
    state = calc_state(_STATE.get(_message_key(req)) or req.args)
    paragon = pm.resolve_paragon(state["paragon_id"])
    if paragon is None:  # defensive — the select vocabulary is closed
        return Reply(BLOCKED, "❌ Couldn't match that paragon — pick one "
                              "from the calculator's select.")
    inputs = pm.ParagonInputs(
        tower=paragon.paragon_id, pops=pops, cash_spent=cash,
        slider_cash=slider, upgrade_count=upgrades,
        tier5_count=state["tier5_count"], geraldo_totems=totems,
        player_count=state["player_count"], difficulty=state["difficulty"])
    warnings = tuple(pm.validate_inputs(inputs))
    breakdown = pm.compute_breakdown(
        inputs, pm.base_price(paragon, state["difficulty"]))
    await _card(req, result_card(paragon, breakdown, warnings, state))
    return Reply(SUCCESS, None)


async def paragon_requirements_open(req) -> Reply:
    """🎯 Requirements — open the strategy/target picker seeded with the
    calculator's paragon/players/difficulty (the shipped
    ``_RequirementsButton``; extra-T5 never carries over, shipped)."""
    state = calc_state(_STATE.get(_message_key(req)) or req.args)
    await _open_with_state(req, REQ_PANEL_ID, req_state(state))
    return Reply(SUCCESS, None)


async def paragon_req_select(req) -> Reply:
    """The requirements page's Strategy… select (shipped
    ``_StrategySelect.callback``) — update and re-render in place."""
    values = tuple(req.args.get("values", ()) or ())
    if not values:
        return Reply(SUCCESS, None)
    key = _message_key(req)
    state = req_state(_STATE.get(key) or req.args)
    try:
        state["strategy"] = pm.SolveStrategy(str(values[0])).value
    except ValueError:
        return Reply(SUCCESS, None)
    _store_state(key, state)
    if not await _refresh(req, key, state):
        return Reply(BLOCKED, _EXPIRED)
    return Reply(SUCCESS, None)


async def paragon_target_submit(req) -> Reply:
    """🎯 Enter target degree — the shipped ``ParagonTargetModal.on_submit``
    (error copy verbatim) → the reverse solver → the build card."""
    try:
        target = _parse_int(req.args.get("target"), field="Target degree",
                            minimum=1, maximum=100)
    except ValueError as exc:
        return Reply(BLOCKED, f"❌ {exc}")
    state = req_state(_STATE.get(_message_key(req)) or req.args)
    paragon = pm.resolve_paragon(state["paragon_id"])
    if paragon is None:  # defensive — the select vocabulary is closed
        return Reply(BLOCKED, "❌ Couldn't match that paragon — pick one "
                              "from the calculator's select.")
    solution = pm.solve_requirements(
        paragon, target, pm.SolveStrategy(state["strategy"]),
        player_count=state["player_count"], difficulty=state["difficulty"])
    await _card(req, requirement_card(paragon, solution))
    return Reply(SUCCESS, None)


async def paragon_stats_view(req) -> Reply:
    """📊 Stats — the shipped ``_StatsButton``: the module-less branch
    answers the shipped orange card; otherwise open the
    ``btd6.paragon_stats`` degree view at Degree 1 (scaled == base at
    degree 1, module doc)."""
    from sb.domain.btd6 import stats as stats_mod

    state = calc_state(_STATE.get(_message_key(req)) or req.args)
    pstats = stats_mod.get_paragon_stats(state["paragon_id"])
    if pstats is None or not pstats.has_combat_stats:
        await _card(req, stats_card(state["paragon_id"]))
        return Reply(SUCCESS, None)
    await _open_with_state(req, STATS_PANEL_ID,
                           stats_state({**state, "degree": "1"}))
    return Reply(SUCCESS, None)


async def paragon_degree_select(req) -> Reply:
    """The stats page's milestone pick (the shipped ``_DegreeSelect``
    callback) — update and re-render in place."""
    values = tuple(req.args.get("values", ()) or ())
    if not values:
        return Reply(SUCCESS, None)
    key = _message_key(req)
    state = stats_state(_STATE.get(key) or req.args)
    picked = str(values[0])
    if picked.isdigit():
        state["degree"] = min(100, max(1, int(picked)))
    _store_state(key, state)
    if not await _refresh(req, key, state):
        return Reply(BLOCKED, _EXPIRED)
    return Reply(SUCCESS, None)


async def paragon_degree_submit(req) -> Reply:
    """🔢 Enter degree — the shipped ``_DegreeModal.on_submit`` (a
    non-numeric entry falls to degree 1, the shipped ``ValueError``
    posture; :func:`stats_state` clamps 1..100) — re-render in place."""
    raw = str(req.args.get("degree") or "").strip()
    try:
        degree = int(raw)
    except ValueError:
        degree = 1
    key = _message_key(req)
    state = stats_state(_STATE.get(key) or req.args)
    state["degree"] = min(100, max(1, degree))
    _store_state(key, state)
    if not await _refresh(req, key, state):
        return Reply(BLOCKED, _EXPIRED)
    return Reply(SUCCESS, None)


async def paragon_stats_back(req) -> Reply:
    """↩ Calculator on the stats page — a fresh landing panel carrying the
    full calculator state (the shipped ``_BackToCalculatorButton``;
    extra-T5 kept — the stats page never edits it)."""
    state = stats_state(_STATE.get(_message_key(req)) or req.args)
    state.pop("degree", None)
    await _open_with_state(req, CALC_PANEL_ID, calc_state(state))
    return Reply(SUCCESS, None)


async def paragon_back_to_calc(req) -> Reply:
    """↩ Calculator on the requirements page — a fresh landing panel
    carrying paragon/players/difficulty (the shipped
    ``_BackToCalculatorButton`` rebuilt without extra-T5)."""
    state = req_state(_STATE.get(_message_key(req)) or req.args)
    state.pop("strategy", None)
    await _open_with_state(req, CALC_PANEL_ID, calc_state(state))
    return Reply(SUCCESS, None)


# --- renderer overrides ---------------------------------------------------------


def _with_selector_options(rendered, spec, updates: dict):
    """Rewrite the rendered selects' option rosters/disabled flags from the
    live state (the shipped ``rebuild()`` — the grammar renderer bakes the
    spec's DEFAULT-state options)."""
    out = []
    for comp in rendered.components:
        update = updates.get(comp.custom_id)
        if update is not None:
            options, disabled = update
            comp = dataclasses.replace(comp, options=tuple(options),
                                       disabled=disabled)
        out.append(comp)
    return dataclasses.replace(rendered, components=tuple(out))


async def render_paragon(spec, ctx) -> object:
    """Grammar-rendered selectors/buttons + the shipped landing embed +
    the injected 🌐 Web calculator LINK button, state-parameterized
    (default state = the shipped build_calculator_embed landing —
    goldens/btd6/sweep_paragon pins those bytes)."""
    from sb.kernel.panels.render import RenderedComponent, render_panel
    from sb.spec.panels import ActionStyle

    rendered = await render_panel(spec, ctx)
    state = calc_state(ctx.params)
    t5_options, t5_disabled = tier5_options(state)
    rendered = _with_selector_options(rendered, spec, {
        f"{spec.panel_id}.paragon": (paragon_options(state), False),
        f"{spec.panel_id}.players": (player_options(state), False),
        f"{spec.panel_id}.difficulty": (difficulty_options(state), False),
        f"{spec.panel_id}.tier5": (t5_options, t5_disabled),
    })
    link = RenderedComponent(
        kind="button", custom_id="", label="🌐 Web calculator", row=4,
        style=ActionStyle.LINK.value, url=PARAGON_CALC_URL)
    return dataclasses.replace(
        rendered, embed=calculator_card(state),
        components=rendered.components + (link,))


async def render_paragon_requirements(spec, ctx) -> object:
    """The requirements page (shipped ParagonRequirementsView shape:
    Strategy… select · 🎯 Enter target degree · ↩ Calculator · the 🌐
    link) over the shipped blurple config embed."""
    from sb.kernel.panels.render import RenderedComponent, render_panel
    from sb.spec.panels import ActionStyle

    rendered = await render_panel(spec, ctx)
    state = req_state(ctx.params)
    rendered = _with_selector_options(rendered, spec, {
        f"{spec.panel_id}.solve_strategy": (strategy_options(state), False),
    })
    link = RenderedComponent(
        kind="button", custom_id="", label="🌐 Web calculator", row=1,
        style=ActionStyle.LINK.value, url=PARAGON_CALC_URL)
    return dataclasses.replace(
        rendered, embed=requirements_card(state),
        components=rendered.components + (link,))


async def render_paragon_stats(spec, ctx) -> object:
    """The stats degree view (shipped ParagonStatsView shape: milestone
    select · 🔢 Enter degree · ↩ Calculator) over the ported per-degree
    stats embed (:func:`stats_degree_card`), state-parameterized."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    state = stats_state(ctx.params)
    rendered = _with_selector_options(rendered, spec, {
        f"{spec.panel_id}.degree_pick": (degree_options(state), False),
    })
    return dataclasses.replace(
        rendered,
        embed=stats_degree_card(state["paragon_id"], state["degree"]))


# --- registration — MODULE IMPORT (BUG A rule) -----------------------------------

_HANDLERS = (
    ("btd6.paragon_select", paragon_select),
    ("btd6.paragon_calc_submit", paragon_calc_submit),
    ("btd6.paragon_requirements_open", paragon_requirements_open),
    ("btd6.paragon_req_select", paragon_req_select),
    ("btd6.paragon_target_submit", paragon_target_submit),
    ("btd6.paragon_stats_view", paragon_stats_view),
    ("btd6.paragon_degree_select", paragon_degree_select),
    ("btd6.paragon_degree_submit", paragon_degree_submit),
    ("btd6.paragon_stats_back", paragon_stats_back),
    ("btd6.paragon_back_to_calc", paragon_back_to_calc),
    ("btd6.render_paragon", render_paragon),
    ("btd6.render_paragon_requirements", render_paragon_requirements),
    ("btd6.render_paragon_stats", render_paragon_stats),
)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


_register()


def ensure_paragon_refs() -> None:
    _register()
