"""Band 7 — the BTD6 paragon calculator wired onto the ported math (the
D-0046 named successor port, executed by the 2026-07-13 curation rework):

* the pure power model + reverse solver carry the ORACLE's own unit pins
  (disbot tests/unit/btd6/test_paragon_math.py @7f7628e1 — the forward
  example validated field-by-field against the live Paragon Calculator
  API; no invented numbers);
* the surface handlers (selects → state re-open, forward form → local
  result card, target form → reverse-solve card, stats → degree view)
  drive the REAL handlers with the panel engine's open seam captured;
* the ``btd6.paragon_pending`` terminal is RETIRED — nothing registers
  it, and every paragon panel route resolves to a live handler.

goldens/btd6/sweep_paragon pins the initial open only (verified via the
golden-parity gate, not here); every click route below is
golden-unpinned (#151 class), so these are the pinning tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.domain.btd6 import paragon_math as pm
from sb.domain.btd6 import paragon_surface as ps
from sb.domain.btd6.paragon_math import ParagonInputs, SolveStrategy

run = asyncio.run

_DART = "apex_plasma_master"


# --- thresholds (oracle pins) --------------------------------------------------


def test_threshold_anchors_and_monotonic():
    assert pm.threshold(1) == 1693
    assert pm.threshold(100) == 200_000
    assert all(pm.threshold(d) < pm.threshold(d + 1) for d in range(1, 100))


def test_degree_from_power_round_trips_every_degree():
    for degree in range(1, 101):
        assert pm.degree_from_power(pm.threshold(degree)) == degree
        if degree > 1:
            assert pm.degree_from_power(pm.threshold(degree) - 1) == degree - 1


def test_degree_floor_is_one_even_at_zero_power():
    assert pm.degree_from_power(0) == 1
    assert pm.power_for_next_degree(0) == pm.threshold(2)


def test_power_for_next_degree_is_zero_at_max():
    assert pm.power_for_next_degree(pm.TOTAL_POWER_FOR_MAX_DEGREE) == 0
    assert pm.next_degree(pm.TOTAL_POWER_FOR_MAX_DEGREE) == 100


# --- forward replica (the oracle's live-API-validated example) ------------------


def _dart_bp() -> int:
    return pm.base_price(pm.resolve_paragon(_DART), "medium")


def test_forward_matches_validated_api_example():
    bd = pm.compute_breakdown(
        ParagonInputs(
            tower=_DART,
            pops=8_000_000,
            cash_spent=150_000,
            upgrade_count=60,
            tier5_count=1,
            geraldo_totems=5,
        ),
        _dart_bp(),
    )
    assert (
        bd.pops.power,
        bd.upgrades.power,
        bd.cash.power,
        bd.extra_t5s.power,
        bd.totems.power,
    ) == (44444, 6000, 20000, 6000, 10000)
    assert bd.total_power == 86444
    assert bd.degree == 68


def test_total_power_is_reported_raw_while_degree_caps_at_100():
    bd = pm.compute_breakdown(
        ParagonInputs(
            tower=_DART,
            pops=99_999_999,
            upgrade_count=250,
            tier5_count=1,
            geraldo_totems=100,
        ),
        _dart_bp(),
    )
    assert bd.total_power == 306000
    assert bd.degree == 100


def test_axis_caps_enforced():
    bd = pm.compute_breakdown(
        ParagonInputs(
            tower=_DART,
            pops=10**9,
            upgrade_count=10_000,
            cash_spent=10**9,
            tier5_count=99,
        ),
        _dart_bp(),
    )
    assert bd.pops.power == pm.POPS_POWER_CAP and bd.pops.capped
    assert bd.upgrades.power == pm.UPGRADES_POWER_CAP and bd.upgrades.capped
    assert bd.cash.power == pm.CASH_POWER_CAP and bd.cash.capped
    assert bd.extra_t5s.power == pm.T5_POWER_CAP and bd.extra_t5s.capped
    assert bd.totems.max_power is None and bd.totems.capped is False


def test_income_counts_as_four_pops():
    bd = pm.compute_breakdown(ParagonInputs(tower=_DART, income=45), _dart_bp())
    assert bd.pops.power == 1  # 45 income * 4 = 180 pops -> exactly 1 power


def test_slider_cash_has_five_percent_premium():
    bp = _dart_bp()
    spent = pm.compute_breakdown(
        ParagonInputs(tower=_DART, cash_spent=15000), bp).cash.power
    slider = pm.compute_breakdown(
        ParagonInputs(tower=_DART, slider_cash=15000), bp).cash.power
    assert slider < spent  # the slider is 95% efficient


# --- validation warnings (oracle pins) ------------------------------------------


def test_validate_warns_on_solo_non_dart_extra_t5():
    warnings = pm.validate_inputs(
        ParagonInputs(tower="Monkey Sub", tier5_count=1, player_count=1))
    assert any(w.type == "extra_t5_ignored" for w in warnings)


def test_validate_clamps_coop_extra_t5():
    warnings = pm.validate_inputs(
        ParagonInputs(tower="Monkey Sub", tier5_count=20, player_count=4))
    assert any(w.type == "extra_t5_clamped" for w in warnings)


def test_validate_flags_upgrade_overflow_and_unknown_tower():
    assert any(
        w.type == "upgrades_capped"
        for w in pm.validate_inputs(ParagonInputs(tower=_DART, upgrade_count=200)))
    assert any(
        w.type == "unknown_tower"
        for w in pm.validate_inputs(ParagonInputs(tower="zzz")))


# --- reverse solver (oracle pins) ------------------------------------------------


def test_every_strategy_reaches_the_target_degree():
    for paragon in pm.PARAGONS:
        for player_count in (1, 4):
            for strategy in SolveStrategy:
                for target in (1, 25, 50, 75, 90, 95, 100):
                    sol = pm.solve_requirements(
                        paragon, target, strategy,
                        player_count=player_count, difficulty="medium")
                    assert sol.breakdown.degree >= target, (
                        paragon.paragon_id, player_count, strategy.value,
                        target, sol.breakdown.degree)


def test_least_axes_minimise_their_axis():
    dart = pm.resolve_paragon(_DART)
    balanced = pm.solve_requirements(dart, 60, SolveStrategy.BALANCED,
                                     player_count=1)
    least_cash = pm.solve_requirements(dart, 60, SolveStrategy.LEAST_CASH,
                                       player_count=1)
    least_tiers = pm.solve_requirements(dart, 60, SolveStrategy.LEAST_TIERS,
                                        player_count=1)
    least_pops = pm.solve_requirements(dart, 60, SolveStrategy.LEAST_POPS,
                                       player_count=1)
    assert least_cash.inputs.cash_spent == 0  # mid degree reachable via pops
    assert least_cash.inputs.cash_spent <= balanced.inputs.cash_spent
    assert least_tiers.inputs.upgrade_count <= balanced.inputs.upgrade_count
    assert least_pops.inputs.pops <= balanced.inputs.pops


def test_solo_non_dart_degree_100_needs_twenty_totems():
    # The API reference's own tip: maxing the capped sources leaves a 40k gap.
    sub = pm.resolve_paragon("Monkey Sub")
    sol = pm.solve_requirements(sub, 100, SolveStrategy.LEAST_CASH,
                                player_count=1)
    assert sol.inputs.geraldo_totems == 20
    assert sol.requires_totems is True


def test_coop_reaches_degree_100_without_totems():
    sub = pm.resolve_paragon("Monkey Sub")
    sol = pm.solve_requirements(sub, 100, SolveStrategy.BALANCED,
                                player_count=4)
    assert sol.breakdown.degree == 100
    assert sol.inputs.geraldo_totems == 0


# --- state decode / clamp (the shipped rebuild()) ---------------------------------


def test_calculator_state_defaults_are_the_shipped_landing_state():
    state = ps.calculator_state({})
    assert (state.paragon_id, state.player_count, state.difficulty,
            state.tier5_count, state.strategy, state.degree) == (
        _DART, 1, "medium", 0, "balanced", 1)


def test_calculator_state_clamps_tier5_to_the_mode_limit():
    # solo non-Dart: limit 0 (the shipped rebuild() min()).
    state = ps.calculator_state({"paragon": "root_of_all_nature",
                                 "players": "1", "tier5": "5"})
    assert state.tier5_count == 0
    # co-op: limit 9.
    state = ps.calculator_state({"paragon": "root_of_all_nature",
                                 "players": "4", "tier5": "50"})
    assert state.tier5_count == 9
    # garbage decodes to defaults, degree/players clamp.
    state = ps.calculator_state({"players": "9", "difficulty": "zzz",
                                 "degree": "500", "strategy": "zzz"})
    assert state.player_count == 4
    assert state.difficulty == "medium"
    assert state.degree == 100
    assert state.strategy == "balanced"


# --- the surface handlers (engine open seam captured) -----------------------------


def _req(args=None, gid=1, uid=42):
    from sb.kernel.interaction.request import ResolveRequest, Surface, TargetRef

    return ResolveRequest(
        surface=Surface.COMPONENT,
        target=TargetRef(key="btd6.paragon.test", spec=None),
        actor=SimpleNamespace(user_id=uid),
        guild_id=gid, channel_id=5,
        args=dict(args or {}), responder=None, origin=None)


@pytest.fixture()
def opened(monkeypatch):
    """Capture the panel-engine open seam the handlers present through."""
    from sb.kernel.panels import engine

    calls: list[tuple[str, dict]] = []

    async def _open_panel(ref, req):
        calls.append((ref.name, dict(req.args)))
        return "msg"

    monkeypatch.setattr(engine, "open_panel", _open_panel)
    return calls


def test_paragon_select_folds_the_pick_into_a_reopen(opened):
    out = run(ps.paragon_select(_req({
        "session_action": "players", "values": ("4",),
        "paragon": "navarch_of_the_seas"})))
    assert out is None
    (panel_id, args), = opened
    assert panel_id == "btd6.paragon"
    assert args["players"] == "4"
    assert args["paragon"] == "navarch_of_the_seas"   # prior state carried
    assert "values" not in args and "session_action" not in args


def test_paragon_select_unknown_action_answers_politely(opened):
    out = run(ps.paragon_select(_req({"session_action": "zzz",
                                      "values": ("1",)})))
    assert "no longer available" in out.user_message
    assert opened == []


def test_calc_submit_presents_the_validated_result_card(opened):
    out = run(ps.paragon_calc_submit(_req({
        "pops": "8,000,000", "cash_spent": "$150000", "slider_cash": "",
        "upgrade_count": "60", "geraldo_totems": "5", "tier5": "1"})))
    assert out is None
    (panel_id, args), = opened
    assert panel_id == "btd6.card"
    card = args["_card"]
    # the oracle build_result_embed bytes over the API-validated example.
    assert card.title == "🔮 Apex Plasma Master — Degree 68"
    assert "**Total power:** 86,444" in card.description
    assert "**To Degree 69:** +1,567 power" in card.description
    assert "Local estimate" in card.description
    breakdown = dict(f[:2] for f in card.fields)["Power breakdown"]
    assert "💥 **Pops:** 44,444 / 90,000 (49%)" in breakdown
    assert "🔱 **Geraldo totems:** 10,000 (uncapped)" in breakdown
    assert card.footer == ("Dart Monkey • Medium • solo • "
                           "base $150,000 • estimate")
    assert card.style_token == "gold"


def test_calc_submit_rejects_non_numeric_fields(opened):
    out = run(ps.paragon_calc_submit(_req({"pops": "lots"})))
    assert out.user_message == "❌ Pops must be a whole number."
    assert opened == []


def test_target_submit_presents_the_reverse_solve_card(opened):
    out = run(ps.paragon_target_submit(_req({
        "target": "100", "paragon": "nautic_siege_core",
        "players": "1", "strategy": "least_cash"})))
    assert out is None
    (panel_id, args), = opened
    assert panel_id == "btd6.card"
    card = args["_card"]
    assert card.title == "🎯 Nautic Siege Core — reach Degree 100"
    assert "**Strategy:** Least cash" in card.description
    assert "**This build reaches:** Degree 100" in card.description
    assert "Not live-confirmed" in card.description
    fields = dict(f[:2] for f in card.fields)
    assert "🔱 **Geraldo totems:** 20" in fields["Recommended sacrifices"]
    assert "🔱 Totems required" in fields
    assert card.footer == "Monkey Sub • Medium • solo"


def test_target_submit_requires_a_degree_in_range(opened):
    out = run(ps.paragon_target_submit(_req({"target": ""})))
    assert out.user_message == "❌ Target degree is required."
    out = run(ps.paragon_target_submit(_req({"target": "500"})))
    assert out.user_message == "❌ Target degree must be at most 100."
    assert opened == []


def test_requirements_open_and_back_carry_the_state(opened):
    run(ps.paragon_requirements_open(_req({"paragon": "glaive_dominus",
                                           "difficulty": "hard"})))
    run(ps.paragon_reopen(_req({"paragon": "glaive_dominus"})))
    assert [c[0] for c in opened] == ["btd6.paragon_requirements",
                                      "btd6.paragon"]
    assert opened[0][1]["paragon"] == "glaive_dominus"
    assert opened[0][1]["difficulty"] == "hard"


def test_strategy_select_reopens_with_the_pick(opened):
    run(ps.paragon_strategy_select(_req({"values": ("least_tiers",)})))
    (panel_id, args), = opened
    assert panel_id == "btd6.paragon_requirements"
    assert args["strategy"] == "least_tiers"


def test_stats_open_routes_to_the_degree_view(opened):
    run(ps.paragon_stats_open(_req({"paragon": _DART})))
    (panel_id, args), = opened
    assert panel_id == "btd6.paragon_stats"
    assert args["degree"] == "1"


def test_stats_open_module_less_paragon_answers_the_shipped_card(
        opened, monkeypatch):
    from sb.domain.btd6 import stats

    monkeypatch.setattr(stats, "get_paragon_stats", lambda pid: None)
    run(ps.paragon_stats_open(_req({"paragon": _DART})))
    (panel_id, args), = opened
    assert panel_id == "btd6.card"
    card = args["_card"]
    assert card.title == "📊 Paragon stats"
    assert card.description.startswith(
        "No combat-stats module is published for this paragon yet")
    assert card.style_token == "orange"


def test_degree_select_and_submit_reopen_the_stats_view(opened):
    run(ps.paragon_degree_select(_req({"values": ("50",)})))
    run(ps.paragon_degree_submit(_req({"degree": "abc"})))  # shipped: -> 1
    assert [c[0] for c in opened] == ["btd6.paragon_stats"] * 2
    assert opened[0][1]["degree"] == "50"
    assert opened[1][1]["degree"] == "1"


# --- the embeds over the ported math ----------------------------------------------


def test_stats_degree_embed_headline_rides_the_ported_formulas():
    e1 = ps.stats_degree_embed(_DART, 1)
    assert e1.title == "👑 Apex Plasma Master — Degree 1"
    assert "**Power required:** 0" in e1.description
    assert "**Boss-damage multiplier:** ×1.0" in e1.description
    assert "×2 (paragons deal ×2 vs Elite Bosses)" in e1.description
    assert e1.footer == "BTD6 stats v55.1"
    assert e1.fields  # the ported per-attack breakdown

    e100 = ps.stats_degree_embed(_DART, 100)
    assert "**Power required:** 200,000" in e100.description
    assert "**Boss-damage multiplier:** ×2.25" in e100.description
    assert "×4.5 (paragons deal ×2 vs Elite Bosses)" in e100.description


def test_requirements_config_embed_is_the_shipped_copy():
    embed = ps.requirements_config_embed(ps.calculator_state(
        {"paragon": "magus_perfectus", "players": "2",
         "difficulty": "impoppable", "strategy": "least_pops"}))
    assert embed.title == "🎯 Requirements — Magus Perfectus"
    assert "**Strategy:** Least pops" in embed.description
    assert "**Players:** 2 (coop)" in embed.description
    assert "**Difficulty:** Impoppable" in embed.description
    assert "Enter target degree" in embed.description
    assert embed.footer == ("Least-X maxes the other inputs; totems top up "
                            "only the highest degrees.")
    assert embed.style_token == "blurple"


# --- registration: the pending terminal is retired ---------------------------------


def test_paragon_pending_is_retired_and_the_routes_are_live():
    import sb.manifest.btd6 as manifest
    from sb.domain.btd6 import panels
    from sb.spec.refs import HandlerRef, is_registered, resolve

    manifest.ENSURE_REFS()
    assert not is_registered(HandlerRef("btd6.paragon_pending"))
    for name in ("btd6.paragon_select", "btd6.paragon_calc_submit",
                 "btd6.paragon_requirements_open",
                 "btd6.paragon_strategy_select", "btd6.paragon_target_submit",
                 "btd6.paragon_stats_open", "btd6.paragon_degree_select",
                 "btd6.paragon_degree_submit", "btd6.paragon_reopen"):
        assert resolve(HandlerRef(name)) is not None

    spec = panels.paragon_spec()
    routed = {a.action_id: a for a in spec.actions}
    assert routed["calc"].handler == HandlerRef("btd6.paragon_calc_submit")
    assert routed["calc"].modal is panels.PARAGON_FORWARD_MODAL
    assert [f.field_id for f in routed["calc"].modal.fields] == [
        "pops", "cash_spent", "slider_cash", "upgrade_count",
        "geraldo_totems"]  # the shipped ParagonForwardModal, field for field
    assert routed["requirements"].handler == HandlerRef(
        "btd6.paragon_requirements_open")
    assert routed["stats"].handler == HandlerRef("btd6.paragon_stats_open")
    for selector in spec.selectors:
        assert selector.on_select == HandlerRef("btd6.paragon_select")
    # no route anywhere in the paragon specs names the retired terminal.
    for factory in (panels.paragon_spec, panels.paragon_requirements_spec,
                    panels.paragon_stats_spec):
        page_spec = factory()
        refs = [a.handler for a in page_spec.actions] + [
            s.on_select for s in page_spec.selectors]
        assert HandlerRef("btd6.paragon_pending") not in refs
