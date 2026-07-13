"""BTD6 Paragon calculator surface (band 7) — the D-0046 named successor
port ("the paragon power calculator (sacrifice math/reverse solver)"),
EXECUTED by the 2026-07-13 curation rework: the calc / requirements /
stats flows of the shipped ``!paragon`` panel wired onto the ported math
(oracle disbot ``views/btd6/paragon_view.py`` + ``paragon_modals.py`` +
``views/btd6/paragon_stats_view.py`` + ``services/paragon_service.py``
@7f7628e1 — copy and embed fields carried verbatim where the ported math
exposes them). Retires the ``btd6.paragon_pending`` terminals.

Flow map (shipped view -> this engine):

* the four landing selects (paragon / players / difficulty / extra-T5)
  RE-OPEN ``btd6.paragon`` with the pick folded into the panel args —
  state travels through the session-mint args exactly like the ai policy
  widgets' ``_open_page`` posture (the shipped ``safe_edit`` in-place
  swap becomes open-with-new-state; click routes are golden-unpinned,
  the #151 class);
* 🧮 Calculate opens the shipped ParagonForwardModal twin (G-10); the
  submit computes LOCALLY via :func:`paragon_math.compute_breakdown`
  and presents the shipped result embed;
* 🎯 Requirements opens the ``btd6.paragon_requirements`` page (the
  shipped ParagonRequirementsView twin); its target-degree form submit
  runs :func:`paragon_math.solve_requirements`;
* 📊 Stats opens the ``btd6.paragon_stats`` degree view over the ported
  :func:`sb.domain.btd6.stats.paragon_stats_at_degree` (the shipped
  ParagonStatsView's degree picker; the degree-independent BASE infobox
  view rides the deep-stats successor — ``paragon_degrees.degree_row``
  stays ledgered there, so this page opens at Degree 1, whose scaled
  values equal the base values by the wiki formulas).

Ledgered deviations from the shipped bytes (no golden pins any of them):

* NO LIVE API — the shipped ``paragon_service`` live-API wrapper and its
  live-vs-local reconciliation are not ported (successor lane), so every
  result presents the shipped LOCAL-fallback posture: gold accent,
  "estimate" footer suffix, and an explicit local-estimate line (worded
  for this build: the reconciliation is *not armed*, not "unreachable").
* Select DEFAULTS re-render via option providers on each re-open; the
  extra-T5 select re-bounds its options like the shipped ``_Tier5Select``
  but cannot render *disabled* when the limit is 0 (the grammar has no
  per-selector disabled facet) — the single shipped
  "0 extra T5 (not allowed here)" option is kept and the handler clamps
  server-side regardless.

Registered at MODULE IMPORT (declaring IS reserving — the BUG A rule,
sb/domain/role/handlers.py pattern)."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from sb.kernel.interaction.handler_kit import Reply
from sb.kernel.panels.render import RenderedEmbed
from sb.spec.outcomes import SUCCESS

__all__ = [
    "CalculatorState",
    "calculator_state",
    "ensure_paragon_surface_refs",
    "requirement_card",
    "requirements_config_embed",
    "result_card",
    "stats_degree_embed",
    "stats_missing_card",
    "unknown_tower_card",
]

#: the live web Paragon Calculator + its Discord author credit (shipped
#: services/paragon_service.CALCULATOR_PUBLIC_URL / CALCULATOR_AUTHOR_NAME).
CALCULATOR_PUBLIC_URL = "https://paragon-calc.vercel.app/"
CALCULATOR_AUTHOR_NAME = "notausgang0341"

_DEFAULT_PARAGON = "apex_plasma_master"

# the shipped view vocab (views/btd6/paragon_view.py verbatim).
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
    "balanced": "Balanced (even split)",
    "least_cash": "Least cash",
    "least_tiers": "Least tiers",
    "least_pops": "Least pops",
}

#: the shipped degree-select milestones (views/btd6/paragon_stats_view.py).
DEGREE_MILESTONES: tuple[int, ...] = (1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)


def _fmt(value: int) -> str:
    return f"{value:,}"


# --- state (the shipped ParagonCalculatorView fields, args-carried) ------------


@dataclass(frozen=True)
class CalculatorState:
    """The shipped view's config surface, decoded from panel args."""

    paragon_id: str
    player_count: int
    difficulty: str
    tier5_count: int
    strategy: str = "balanced"
    degree: int = 1


def _int_arg(params: dict, key: str, default: int) -> int:
    try:
        return int(str(params.get(key) or default))
    except (TypeError, ValueError):
        return default


def calculator_state(params: dict | None) -> CalculatorState:
    """Decode + clamp the calculator state (the shipped ``rebuild()``
    clamp: the extra-T5 choice stays within the mode/paragon limit; the
    degree stays 1..100; players 1..4)."""
    from sb.domain.btd6 import paragon_math

    params = params or {}
    paragon_id = str(params.get("paragon") or _DEFAULT_PARAGON)
    player_count = min(4, max(1, _int_arg(params, "players", 1)))
    difficulty = str(params.get("difficulty") or "medium")
    if difficulty not in ("easy", "medium", "hard", "impoppable"):
        difficulty = "medium"
    tier5 = max(0, _int_arg(params, "tier5", 0))
    paragon = paragon_math.resolve_paragon(paragon_id)
    limit = paragon_math.max_extra_t5_count(
        paragon_math.game_mode_for(player_count),
        is_dart=bool(paragon and paragon.is_dart))
    strategy = str(params.get("strategy") or "balanced")
    if strategy not in _STRATEGY_LABEL:
        strategy = "balanced"
    degree = min(100, max(1, _int_arg(params, "degree", 1)))
    return CalculatorState(
        paragon_id=paragon_id, player_count=player_count,
        difficulty=difficulty, tier5_count=min(tier5, limit),
        strategy=strategy, degree=degree)


# --- embed builders (shipped views/btd6/paragon_view.py, field for field) ------


def _credits_field() -> tuple[str, str]:
    """The shipped ``_add_credits_field`` bytes."""
    return ("🔗 Web calculator & credits",
            f"[paragon-calc.vercel.app]({CALCULATOR_PUBLIC_URL}) — built by "
            f"**{CALCULATOR_AUTHOR_NAME}**")


def _axis_line(axis) -> str:
    """The shipped ``_axis_line`` verbatim."""
    if axis.max_power is None:
        return (f"{_AXIS_EMOJI[axis.key]} **{_AXIS_LABEL[axis.key]}:** "
                f"{_fmt(axis.power)} (uncapped)")
    pct = f" ({axis.fill_pct:.0f}%)" if axis.fill_pct is not None else ""
    capped = " • **capped**" if axis.capped else ""
    return (f"{_AXIS_EMOJI[axis.key]} **{_AXIS_LABEL[axis.key]}:** "
            f"{_fmt(axis.power)} / {_fmt(axis.max_power)}{pct}{capped}")


def result_card(paragon, breakdown, warnings, *, difficulty: str,
                base_price_value: int, game_mode: str) -> RenderedEmbed:
    """The shipped ``build_result_embed``, LOCAL-estimate branch (gold
    accent + "estimate" footer suffix — the only branch this build can
    produce; the live branch rides the un-ported service)."""
    lines = [f"**Total power:** {_fmt(breakdown.total_power)}"]
    if breakdown.degree < 100:
        lines.append(f"**To Degree {breakdown.next_degree}:** "
                     f"+{_fmt(breakdown.power_for_next_degree)} power")
    else:
        lines.append("**Maximum degree reached.** 🏆")
    lines.append("\n⚠️ *Local estimate — the live-calculator reconciliation "
                 "is not armed in this build.*")
    fields: list[tuple[str, str]] = [
        ("Power breakdown",
         "\n".join(_axis_line(axis) for axis in breakdown.axes)),
    ]
    if breakdown.wasted_cash > 0:
        fields.append(("💸 Wasted cash",
                       f"${_fmt(breakdown.wasted_cash)} gave no benefit "
                       "(cash power is capped)."))
    notes = [w.message for w in warnings]
    if notes:
        fields.append(("⚠️ Notes", "\n".join(f"• {note}" for note in notes)))
    fields.append(_credits_field())
    return RenderedEmbed(
        title=f"🔮 {paragon.name} — Degree {breakdown.degree}",
        description="\n".join(lines),
        fields=tuple(fields),
        footer=(f"{paragon.tower} • {difficulty.title()} • {game_mode} • "
                f"base ${_fmt(base_price_value)} • estimate"),
        style_token="gold")


def requirement_card(paragon, solution) -> RenderedEmbed:
    """The shipped ``build_requirement_embed`` (local-solve posture: the
    reach line is the local forward confirm — the same value the shipped
    fallback showed — and the not-live-confirmed line rides verbatim)."""
    from sb.domain.btd6 import paragon_math

    inputs = solution.inputs
    desc = [
        f"**Strategy:** {_STRATEGY_LABEL[solution.strategy.value]}",
        f"**This build reaches:** Degree {solution.breakdown.degree}",
        "\n⚠️ *Not live-confirmed — computed locally.*",
    ]
    fields: list[tuple[str, str]] = [
        ("Recommended sacrifices",
         f"💥 **Pops:** {_fmt(inputs.pops)}\n"
         f"⬆️ **Upgrade tiers:** {inputs.upgrade_count}\n"
         f"💰 **Cash:** ${_fmt(inputs.cash_spent)}\n"
         f"🛡️ **Extra T5s:** {inputs.tier5_count}\n"
         f"🔱 **Geraldo totems:** {inputs.geraldo_totems}"),
    ]
    if solution.requires_totems:
        fields.append(("🔱 Totems required",
                       "Capped inputs alone can't reach this degree — "
                       "Geraldo totems make up the rest."))
    fields.append(_credits_field())
    return RenderedEmbed(
        title=f"🎯 {paragon.name} — reach Degree {solution.target_degree}",
        description="\n".join(desc),
        fields=tuple(fields),
        footer=(f"{paragon.tower} • {inputs.difficulty.title()} • "
                f"{paragon_math.game_mode_for(inputs.player_count)}"),
        style_token="green")


def unknown_tower_card() -> RenderedEmbed:
    """The shipped ``build_error_embed`` ParagonUnknownTowerError branch."""
    from sb.domain.btd6 import paragon_math

    towers = ", ".join(paragon_math.local_valid_towers()[:8])
    return RenderedEmbed(
        title="🔮 Paragon Calculator",
        description=f"Couldn't match that paragon. Try one of: {towers}…",
        style_token="red")


def requirements_config_embed(state: CalculatorState) -> RenderedEmbed:
    """The shipped ``build_requirements_config_embed``."""
    from sb.domain.btd6 import paragon_math

    paragon = paragon_math.resolve_paragon(state.paragon_id)
    name = paragon.name if paragon else state.paragon_id
    mode = paragon_math.game_mode_for(state.player_count)
    return RenderedEmbed(
        title=f"🎯 Requirements — {name}",
        description=(
            f"**Strategy:** {_STRATEGY_LABEL[state.strategy]}\n"
            f"**Players:** {state.player_count} ({mode})\n"
            f"**Difficulty:** {state.difficulty.title()}\n\n"
            "Choose a strategy, then **Enter target degree** to get a build."),
        fields=(_credits_field(),),
        footer="Least-X maxes the other inputs; totems top up only the "
               "highest degrees.",
        style_token="blurple")


def stats_missing_card() -> RenderedEmbed:
    """The shipped module-less-paragon branch (Root of all Nature /
    Herald of Everfrost — no wiki stats data page), verbatim."""
    return RenderedEmbed(
        title="📊 Paragon stats",
        description=(
            "No combat-stats module is published for this paragon yet — "
            "only its cost is known. Pick another paragon to see full stats."),
        style_token="orange")


def stats_degree_embed(paragon_id: str, degree: int) -> RenderedEmbed:
    """The paragon degree view over the PORTED per-attack math
    (:func:`stats.paragon_stats_at_degree`): the shipped
    ``build_paragon_degree_embed`` headline lines verbatim (power / boss
    multiplier / elite multiplier), then one field per attack from the
    ported projectile breakdown (the shipped full cell-group table rides
    ``paragon_degrees.degree_row`` — the deep-stats successor)."""
    from sb.domain.btd6 import paragon_degrees, stats

    row = stats.paragon_stats_at_degree(paragon_id, degree)
    pstats = stats.get_paragon_stats(paragon_id)
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


# --- handler plumbing -----------------------------------------------------------


def _ok(text: str) -> Reply:
    return Reply(SUCCESS, text)


def _picked(req) -> str:
    values = tuple(req.args.get("values", ()) or ())
    return str(values[0]) if values else ""


def _state_args(req, **extra) -> dict:
    """The current args minus the click's transport keys, plus *extra* —
    the state that travels to the next panel open (the ai policy widgets'
    ``_open_page`` posture)."""
    args = {k: v for k, v in dict(req.args or {}).items()
            if k not in ("values", "session_action")}
    args.update(extra)
    return args


async def _open(req, panel_id: str, args: dict) -> None:
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef(panel_id), dataclasses.replace(req, args=args))


async def _card(req, embed: RenderedEmbed) -> None:
    """Present one embed reply through the ``btd6.card`` panel (the
    oracle_surface posture)."""
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef("btd6.card"),
                     dataclasses.replace(
                         req, args={**dict(req.args), "_card": embed}))


def _parse_int(raw: str, *, field: str, minimum: int = 0,
               maximum: int | None = None) -> int:
    """The shipped ``paragon_modals._parse_int`` verbatim."""
    cleaned = raw.strip().replace(",", "").replace("$", "").replace(" ", "")
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


# --- handlers ---------------------------------------------------------------------


_SELECT_KEYS = {"paragon": "paragon", "players": "players",
                "difficulty": "difficulty", "tier5": "tier5"}


async def paragon_select(req) -> Reply | None:
    """One of the four landing selects (the shipped _ParagonSelect /
    _PlayerCountSelect / _DifficultySelect / _Tier5Select callbacks):
    fold the pick into the state and re-open the calculator (the state
    clamp happens in :func:`calculator_state` on render — the shipped
    ``rebuild()``)."""
    action = str(req.args.get("session_action") or "")
    key = _SELECT_KEYS.get(action)
    picked = _picked(req)
    if key is None or not picked:
        return _ok("This selector is no longer available — reopen `!paragon`.")
    await _open(req, "btd6.paragon", _state_args(req, **{key: picked}))
    return None


async def paragon_calc_submit(req) -> Reply | None:
    """🧮 Calculate — the shipped ``ParagonForwardModal.on_submit`` over
    the LOCAL formula (``paragon_service.calculate``'s fallback lane:
    resolve → compute_breakdown → validate_inputs → result embed)."""
    from sb.domain.btd6 import paragon_math

    try:
        pops = _parse_int(str(req.args.get("pops") or ""), field="Pops")
        cash = _parse_int(str(req.args.get("cash_spent") or ""),
                          field="Cash spent")
        slider = _parse_int(str(req.args.get("slider_cash") or ""),
                            field="Slider cash")
        upgrades = _parse_int(str(req.args.get("upgrade_count") or ""),
                              field="Upgrade tiers")
        totems = _parse_int(str(req.args.get("geraldo_totems") or ""),
                            field="Geraldo totems")
    except ValueError as exc:
        return _ok(f"❌ {exc}")
    state = calculator_state(req.args)
    paragon = paragon_math.resolve_paragon(state.paragon_id)
    if paragon is None:
        await _card(req, unknown_tower_card())
        return None
    inputs = paragon_math.ParagonInputs(
        tower=paragon.paragon_id, pops=pops, cash_spent=cash,
        slider_cash=slider, upgrade_count=upgrades,
        tier5_count=state.tier5_count, geraldo_totems=totems,
        player_count=state.player_count, difficulty=state.difficulty)
    bp = paragon_math.base_price(paragon, state.difficulty)
    breakdown = paragon_math.compute_breakdown(inputs, bp)
    warnings = paragon_math.validate_inputs(inputs)
    await _card(req, result_card(
        paragon, breakdown, warnings, difficulty=state.difficulty,
        base_price_value=bp,
        game_mode=paragon_math.game_mode_for(state.player_count)))
    return None


async def paragon_requirements_open(req) -> None:
    """🎯 Requirements — the shipped _RequirementsButton: open the
    strategy/target config page carrying the calculator state."""
    await _open(req, "btd6.paragon_requirements", _state_args(req))
    return None


async def paragon_strategy_select(req) -> Reply | None:
    """The shipped _StrategySelect callback."""
    picked = _picked(req)
    if picked not in _STRATEGY_LABEL:
        return _ok("This selector is no longer available — reopen `!paragon`.")
    await _open(req, "btd6.paragon_requirements",
                _state_args(req, strategy=picked))
    return None


async def paragon_target_submit(req) -> Reply | None:
    """🎯 Enter target degree — the shipped ``ParagonTargetModal.on_submit``
    over the local reverse solver (``paragon_service.requirements``'s
    solve leg; the live confirm ride is not armed — the reach line is the
    local forward confirm, the shipped fallback value)."""
    from sb.domain.btd6 import paragon_math

    try:
        target = _parse_int(str(req.args.get("target") or ""),
                            field="Target degree", minimum=1, maximum=100)
    except ValueError as exc:
        return _ok(f"❌ {exc}")
    state = calculator_state(req.args)
    paragon = paragon_math.resolve_paragon(state.paragon_id)
    if paragon is None:
        await _card(req, unknown_tower_card())
        return None
    solution = paragon_math.solve_requirements(
        paragon, target, paragon_math.SolveStrategy(state.strategy),
        player_count=state.player_count, difficulty=state.difficulty)
    await _card(req, requirement_card(paragon, solution))
    return None


async def paragon_stats_open(req) -> None:
    """📊 Stats — the shipped _StatsButton: the module-less branch answers
    the shipped orange card; otherwise open the degree view at Degree 1."""
    from sb.domain.btd6 import stats

    state = calculator_state(req.args)
    pstats = stats.get_paragon_stats(state.paragon_id)
    if pstats is None or not pstats.has_combat_stats:
        await _card(req, stats_missing_card())
        return None
    await _open(req, "btd6.paragon_stats", _state_args(req, degree="1"))
    return None


async def paragon_degree_select(req) -> Reply | None:
    """The shipped _DegreeSelect callback (milestone pick)."""
    picked = _picked(req)
    if not picked.isdigit():
        return _ok("This selector is no longer available — reopen `!paragon`.")
    await _open(req, "btd6.paragon_stats", _state_args(req, degree=picked))
    return None


async def paragon_degree_submit(req) -> Reply | None:
    """🔢 Enter degree — the shipped ``_DegreeModal.on_submit`` (a
    non-numeric entry falls to degree 1, the shipped ``ValueError``
    posture; the range clamps 1..100 in :func:`calculator_state`)."""
    raw = str(req.args.get("degree") or "").strip()
    try:
        degree = int(raw)
    except ValueError:
        degree = 1
    await _open(req, "btd6.paragon_stats",
                _state_args(req, degree=str(degree)))
    return None


async def paragon_reopen(req) -> None:
    """↩ Calculator — the shipped _BackToCalculatorButton (state carried)."""
    await _open(req, "btd6.paragon", _state_args(req))
    return None


# --- registration — MODULE IMPORT (BUG A rule) --------------------------------------


_HANDLERS = (
    ("btd6.paragon_select", paragon_select),
    ("btd6.paragon_calc_submit", paragon_calc_submit),
    ("btd6.paragon_requirements_open", paragon_requirements_open),
    ("btd6.paragon_strategy_select", paragon_strategy_select),
    ("btd6.paragon_target_submit", paragon_target_submit),
    ("btd6.paragon_stats_open", paragon_stats_open),
    ("btd6.paragon_degree_select", paragon_degree_select),
    ("btd6.paragon_degree_submit", paragon_degree_submit),
    ("btd6.paragon_reopen", paragon_reopen),
)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


def ensure_paragon_surface_refs() -> None:
    _register()


_register()
