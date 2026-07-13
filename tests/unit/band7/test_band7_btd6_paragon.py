"""BTD6 paragon calculator — the armed session surface (ORDER 017
night-run fix slice A): the pure paragon power model + reverse solver
(oracle ``utils/btd6/paragon_math.py`` test vectors, ported), the armed
panel specs (the `btd6.paragon_pending` terminal retired), the
state-parameterized renderer (the shipped ``rebuild()``), and the
select/modal handlers with the shipped error copy.

Oracle: menno420/superbot disbot/views/btd6/paragon_view.py +
paragon_modals.py + utils/btd6/paragon_math.py (@7f7628e1);
goldens/btd6/sweep_paragon pins the default-state open bytes."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from sb.domain.btd6 import paragon_math as pm
from sb.domain.btd6 import paragon_panel as pp
from sb.domain.btd6.paragon_math import ParagonInputs, SolveStrategy

run = asyncio.run

_DART = "apex_plasma_master"

UID, GID = 42, 1


# --- the pure power model (oracle test vectors, ported verbatim) -------------


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


def _dart_bp() -> int:
    return pm.base_price(pm.resolve_paragon(_DART), "medium")


def test_forward_matches_validated_api_example():
    bd = pm.compute_breakdown(
        ParagonInputs(tower=_DART, pops=8_000_000, cash_spent=150_000,
                      upgrade_count=60, tier5_count=1, geraldo_totems=5),
        _dart_bp())
    assert (bd.pops.power, bd.upgrades.power, bd.cash.power,
            bd.extra_t5s.power, bd.totems.power) == (
        44444, 6000, 20000, 6000, 10000)
    assert bd.total_power == 86444
    assert bd.degree == 68


def test_total_power_is_reported_raw_while_degree_caps_at_100():
    bd = pm.compute_breakdown(
        ParagonInputs(tower=_DART, pops=99_999_999, upgrade_count=250,
                      tier5_count=1, geraldo_totems=100),
        _dart_bp())
    assert bd.total_power == 306000
    assert bd.degree == 100


def test_axis_caps_enforced():
    bd = pm.compute_breakdown(
        ParagonInputs(tower=_DART, pops=10**9, upgrade_count=10_000,
                      cash_spent=10**9, tier5_count=99),
        _dart_bp())
    assert bd.pops.power == pm.POPS_POWER_CAP and bd.pops.capped
    assert bd.upgrades.power == pm.UPGRADES_POWER_CAP and bd.upgrades.capped
    assert bd.cash.power == pm.CASH_POWER_CAP and bd.cash.capped
    assert bd.extra_t5s.power == pm.T5_POWER_CAP and bd.extra_t5s.capped
    assert bd.totems.max_power is None and bd.totems.capped is False
    assert bd.wasted_cash > 0


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


def test_validate_warns_on_solo_non_dart_extra_t5():
    warnings = pm.validate_inputs(
        ParagonInputs(tower="Monkey Sub", tier5_count=1, player_count=1))
    assert any(w.type == "extra_t5_ignored" for w in warnings)


def test_validate_clamps_coop_extra_t5():
    warnings = pm.validate_inputs(
        ParagonInputs(tower="Monkey Sub", tier5_count=20, player_count=4))
    assert any(w.type == "extra_t5_clamped" for w in warnings)


def test_validate_flags_upgrade_overflow_and_unknown_tower():
    assert any(w.type == "upgrades_capped" for w in pm.validate_inputs(
        ParagonInputs(tower=_DART, upgrade_count=200)))
    assert any(w.type == "unknown_tower" for w in pm.validate_inputs(
        ParagonInputs(tower="zzz")))


def test_t5_power_cap_follows_the_mode_limits():
    assert pm.t5_power_cap_for("solo", is_dart=True) == pm.POWER_PER_EXTRA_T5
    assert pm.t5_power_cap_for("solo", is_dart=False) == 0
    assert pm.t5_power_cap_for("coop", is_dart=False) == pm.T5_POWER_CAP


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


def test_least_cash_minimises_cash_versus_balanced():
    dart = pm.resolve_paragon(_DART)
    least = pm.solve_requirements(dart, 60, SolveStrategy.LEAST_CASH,
                                  player_count=1)
    balanced = pm.solve_requirements(dart, 60, SolveStrategy.BALANCED,
                                     player_count=1)
    assert least.inputs.cash_spent <= balanced.inputs.cash_spent
    assert least.inputs.cash_spent == 0


def test_least_tiers_and_least_pops_minimise_their_axis():
    # the remaining least-X axes (#336's oracle pins, ported in the
    # arbitration delta): each strategy never spends more of ITS axis
    # than the balanced split does.
    dart = pm.resolve_paragon(_DART)
    balanced = pm.solve_requirements(dart, 60, SolveStrategy.BALANCED,
                                     player_count=1)
    least_tiers = pm.solve_requirements(dart, 60, SolveStrategy.LEAST_TIERS,
                                        player_count=1)
    least_pops = pm.solve_requirements(dart, 60, SolveStrategy.LEAST_POPS,
                                       player_count=1)
    assert least_tiers.inputs.upgrade_count <= balanced.inputs.upgrade_count
    assert least_pops.inputs.pops <= balanced.inputs.pops


def test_solo_non_dart_degree_100_needs_twenty_totems():
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


# --- the armed panel specs -----------------------------------------------------


def test_paragon_spec_is_armed_and_golden_shaped():
    from sb.domain.btd6.panels import paragon_spec
    from sb.spec.outcomes import DeferMode
    from sb.spec.refs import HandlerRef, PanelRef

    spec = paragon_spec()
    assert spec.session_lifecycle is True
    assert spec.title == "🔮 Paragon Calculator"
    by_sel = {s.selector_id: s for s in spec.selectors}
    assert set(by_sel) == {"paragon", "players", "difficulty", "tier5"}
    for sel in by_sel.values():
        assert sel.on_select == HandlerRef("btd6.paragon_select")
    # golden-pinned default rosters (sweep_paragon).
    assert len(tuple(by_sel["paragon"].options_source)) == 13
    assert tuple(by_sel["tier5"].options_source)[0]["default"] is True
    by_act = {a.action_id: a for a in spec.actions}
    assert by_act["calc"].handler == HandlerRef("btd6.paragon_calc_submit")
    assert by_act["calc"].defer_mode is DeferMode.MODAL
    assert by_act["calc"].modal is not None
    assert [f.field_id for f in by_act["calc"].modal.fields] == [
        "pops", "cash_spent", "slider_cash", "upgrade_count",
        "geraldo_totems"]
    assert by_act["requirements"].handler == HandlerRef(
        "btd6.paragon_requirements_open")
    assert by_act["stats"].handler == HandlerRef("btd6.paragon_stats_view")
    assert by_act["back"].handler == PanelRef("btd6.hub")


def test_requirements_spec_shape():
    from sb.domain.btd6.panels import paragon_requirements_spec
    from sb.spec.outcomes import DeferMode
    from sb.spec.refs import HandlerRef

    spec = paragon_requirements_spec()
    assert spec.panel_id == "btd6.paragon_requirements"
    assert spec.session_lifecycle is True
    (sel,) = spec.selectors
    assert sel.on_select == HandlerRef("btd6.paragon_req_select")
    assert [o["value"] for o in sel.options_source] == [
        "balanced", "least_cash", "least_tiers", "least_pops"]
    by_act = {a.action_id: a for a in spec.actions}
    assert by_act["enter_target"].defer_mode is DeferMode.MODAL
    assert by_act["enter_target"].modal.fields[0].field_id == "target"
    assert by_act["back_calc"].handler == HandlerRef(
        "btd6.paragon_back_to_calc")


def test_stats_spec_shape():
    from sb.domain.btd6.panels import paragon_stats_spec
    from sb.spec.outcomes import DeferMode
    from sb.spec.refs import HandlerRef

    spec = paragon_stats_spec()
    assert spec.panel_id == "btd6.paragon_stats"
    assert spec.session_lifecycle is True
    (sel,) = spec.selectors
    assert sel.on_select == HandlerRef("btd6.paragon_degree_select")
    # the shipped milestone roster, degree 1 selected by default.
    assert [o["value"] for o in sel.options_source] == [
        "1", "5", "10", "20", "30", "40", "50", "60", "70", "80", "90",
        "100"]
    assert [o["value"] for o in sel.options_source if o.get("default")] == [
        "1"]
    by_act = {a.action_id: a for a in spec.actions}
    assert by_act["enter_degree"].defer_mode is DeferMode.MODAL
    assert by_act["enter_degree"].modal.fields[0].field_id == "degree"
    assert by_act["enter_degree"].modal.modal_id == "btd6.paragon_degree_form"
    assert by_act["back_stats"].handler == HandlerRef(
        "btd6.paragon_stats_back")


def test_specs_pass_the_compile_fences():
    from sb.domain.btd6 import panels
    from sb.kernel.panels.compile import check_panel

    for build in (panels.paragon_spec, panels.paragon_requirements_spec,
                  panels.paragon_stats_spec):
        assert check_panel(build()) is None


def test_pending_terminal_retired():
    from sb.domain.btd6 import service
    from sb.spec.refs import HandlerRef, is_registered

    service.ensure_handler_refs()
    pp.ensure_paragon_refs()
    assert not is_registered(HandlerRef("btd6.paragon_pending"))
    for name in ("btd6.paragon_select", "btd6.paragon_calc_submit",
                 "btd6.paragon_requirements_open", "btd6.paragon_req_select",
                 "btd6.paragon_target_submit", "btd6.paragon_stats_view",
                 "btd6.paragon_degree_select", "btd6.paragon_degree_submit",
                 "btd6.paragon_stats_back",
                 "btd6.paragon_back_to_calc", "btd6.render_paragon",
                 "btd6.render_paragon_requirements",
                 "btd6.render_paragon_stats"):
        assert is_registered(HandlerRef(name)), name


def test_manifest_carries_all_three_paragon_panels():
    from sb.manifest.btd6 import MANIFEST

    ids = {p.panel_id for p in MANIFEST.panels}
    assert {"btd6.paragon", "btd6.paragon_requirements",
            "btd6.paragon_stats"} <= ids


# --- the state-parameterized renderer (the shipped rebuild()) --------------------


def _ctx(params: dict | None = None):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=GID, actor=SimpleNamespace(user_id=UID),
        channel_id=2, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(),
        params=dict(params or {}))


def _rendered_selects(rendered) -> dict:
    return {c.custom_id: c for c in rendered.components
            if c.kind == "selector"}


def test_render_default_state_matches_the_golden_bytes():
    from sb.domain.btd6.panels import paragon_spec

    rendered = run(pp.render_paragon(paragon_spec(), _ctx()))
    assert rendered.embed.title == "🔮 Paragon Calculator — Apex Plasma Master"
    assert rendered.embed.description == (
        "**Paragon:** Apex Plasma Master (Dart Monkey)\n"
        "**Players:** 1 (solo)\n**Difficulty:** Medium\n**Extra T5s:** 0")
    assert rendered.embed.footer == (
        "Solo: 1 extra T5 (Dart only) · Co-op: up to 9 · totems are uncapped")
    selects = _rendered_selects(rendered)
    tier5 = selects["btd6.paragon.tier5"]
    assert [o["label"] for o in tier5.options] == ["0 extra T5", "1 extra T5"]
    assert tier5.disabled is False
    link = rendered.components[-1]
    assert link.url == "https://paragon-calc.vercel.app/"
    assert link.label == "🌐 Web calculator"


def test_render_coop_state_rebounds_the_tier5_roster():
    from sb.domain.btd6.panels import paragon_spec

    rendered = run(pp.render_paragon(
        paragon_spec(),
        _ctx({"paragon_id": "nautic_siege_core", "player_count": 4,
              "difficulty": "hard", "tier5_count": 3})))
    assert "**Players:** 4 (coop)" in rendered.embed.description
    assert "**Difficulty:** Hard" in rendered.embed.description
    selects = _rendered_selects(rendered)
    tier5 = selects["btd6.paragon.tier5"]
    assert len(tier5.options) == 10          # co-op: 0..9 (shipped)
    assert tier5.options[3]["default"] is True
    paragon_sel = selects["btd6.paragon.paragon"]
    assert [o["value"] for o in paragon_sel.options if o["default"]] == [
        "nautic_siege_core"]


def test_render_solo_non_dart_disables_the_tier5_select():
    from sb.domain.btd6.panels import paragon_spec

    rendered = run(pp.render_paragon(
        paragon_spec(), _ctx({"paragon_id": "magus_perfectus"})))
    tier5 = _rendered_selects(rendered)["btd6.paragon.tier5"]
    assert tier5.disabled is True
    assert [o["label"] for o in tier5.options] == [
        "0 extra T5 (not allowed here)"]     # the shipped _Tier5Select copy


def test_render_requirements_page():
    from sb.domain.btd6.panels import paragon_requirements_spec

    rendered = run(pp.render_paragon_requirements(
        paragon_requirements_spec(),
        _ctx({"paragon_id": "magus_perfectus", "player_count": 2,
              "strategy": "least_cash"})))
    assert rendered.embed.title == "🎯 Requirements — Magus Perfectus"
    assert "**Strategy:** Least cash" in rendered.embed.description
    assert rendered.embed.footer == (
        "Least-X maxes the other inputs; totems top up only the highest "
        "degrees.")
    strategy = _rendered_selects(rendered)[
        "btd6.paragon_requirements.solve_strategy"]
    assert [o["value"] for o in strategy.options if o["default"]] == [
        "least_cash"]
    assert rendered.components[-1].url == "https://paragon-calc.vercel.app/"


# --- the handlers ------------------------------------------------------------------


@dataclass
class FakeReq:
    """dataclasses.replace-compatible request stand-in."""

    args: dict = field(default_factory=dict)
    actor: object = None
    guild_id: int = GID
    channel_id: int = 2
    origin: object = None
    request_id: str = "r1"
    surface: object = None


def _req(args: dict | None = None, message_id: int = 555) -> FakeReq:
    return FakeReq(
        args=dict(args or {}),
        actor=SimpleNamespace(user_id=UID),
        origin=SimpleNamespace(message=SimpleNamespace(id=message_id)))


@pytest.fixture(autouse=True)
def _clean_state():
    pp._STATE.clear()
    yield
    pp._STATE.clear()


@pytest.fixture()
def captured_cards(monkeypatch):
    """Capture the btd6.card opens (the result-card presentation lane)."""
    from sb.kernel.panels import engine

    opened = []

    async def open_panel(ref, req):
        opened.append((ref.name, dict(req.args)))
        return "777"

    monkeypatch.setattr(engine, "open_panel", open_panel)
    return opened


@pytest.fixture()
def captured_refresh(monkeypatch):
    from sb.kernel.panels import engine

    calls = []

    async def refresh_session_view(req, *, message_key, params,
                                   expire=False):
        calls.append((message_key, dict(params)))
        return True

    monkeypatch.setattr(engine, "refresh_session_view",
                        refresh_session_view)
    return calls


def test_select_updates_state_and_refreshes(captured_refresh):
    reply = run(pp.paragon_select(_req(
        {"session_action": "players", "values": ("4",)})))
    assert reply.user_message is None
    assert pp._STATE["555"]["player_count"] == 4
    # co-op keeps the shipped default extra-T5 (0) until picked.
    assert captured_refresh[-1][0] == "555"
    assert captured_refresh[-1][1]["player_count"] == 4


def test_select_reclamps_tier5_on_mode_change(captured_refresh):
    # co-op Sub with 5 extra T5 …
    run(pp.paragon_select(_req(
        {"session_action": "paragon", "values": ("nautic_siege_core",)})))
    run(pp.paragon_select(_req(
        {"session_action": "players", "values": ("4",)})))
    run(pp.paragon_select(_req(
        {"session_action": "tier5", "values": ("5",)})))
    assert pp._STATE["555"]["tier5_count"] == 5
    # … dropping to solo re-clamps to the solo non-Dart limit (0) — the
    # shipped rebuild() posture.
    run(pp.paragon_select(_req(
        {"session_action": "players", "values": ("1",)})))
    assert pp._STATE["555"]["tier5_count"] == 0


def test_calc_submit_presents_the_validated_result_card(captured_cards):
    pp._store_state("555", {"paragon_id": _DART, "player_count": 1,
                            "difficulty": "medium", "tier5_count": 1})
    reply = run(pp.paragon_calc_submit(_req(
        {"pops": "8,000,000", "cash_spent": "$150000", "slider_cash": "",
         "upgrade_count": "60", "geraldo_totems": "5"})))
    assert reply.user_message is None
    panel_id, args = captured_cards[-1]
    assert panel_id == "btd6.card"
    embed = args["_card"]
    assert embed.title == "🔮 Apex Plasma Master — Degree 68"
    assert "**Total power:** 86,444" in embed.description
    breakdown_field = dict((n, v) for n, v, *_ in embed.fields)[
        "Power breakdown"]
    assert "💥 **Pops:** 44,444 / 90,000 (49%)" in breakdown_field
    assert embed.footer == ("Dart Monkey • Medium • solo • base $150,000 "
                            "• local formula")


def test_calc_submit_error_copy_is_shipped_verbatim(captured_cards):
    from sb.spec.outcomes import BLOCKED

    reply = run(pp.paragon_calc_submit(_req({"pops": "abc"})))
    assert reply.outcome is BLOCKED
    assert reply.user_message == "❌ Pops must be a whole number."
    assert not captured_cards


def test_target_submit_range_error_copy(captured_cards):
    from sb.spec.outcomes import BLOCKED

    for raw, msg in (("", "Target degree is required."),
                     ("0", "Target degree must be at least 1."),
                     ("101", "Target degree must be at most 100.")):
        reply = run(pp.paragon_target_submit(_req({"target": raw})))
        assert reply.outcome is BLOCKED
        assert reply.user_message == f"❌ {msg}"
    assert not captured_cards


def test_target_submit_presents_the_build_card(captured_cards):
    pp._store_state("555", {"paragon_id": "nautic_siege_core",
                            "player_count": 1, "difficulty": "medium",
                            "strategy": "least_cash"})
    reply = run(pp.paragon_target_submit(_req({"target": "100"})))
    assert reply.user_message is None
    _, args = captured_cards[-1]
    embed = args["_card"]
    assert embed.title == "🎯 Nautic Siege Core — reach Degree 100"
    fields = dict((n, v) for n, v, *_ in embed.fields)
    assert "🔱 **Geraldo totems:** 20" in fields["Recommended sacrifices"]
    assert "🔱 Totems required" in fields
    assert "⚠️ *Not live-confirmed — computed locally.*" \
        in embed.description


def test_requirements_open_seeds_the_page_state(captured_cards):
    pp._store_state("555", {"paragon_id": "magus_perfectus",
                            "player_count": 2, "difficulty": "hard",
                            "tier5_count": 4})
    run(pp.paragon_requirements_open(_req({"session_action":
                                           "requirements"})))
    panel_id, args = captured_cards[-1]
    assert panel_id == "btd6.paragon_requirements"
    assert args["paragon_id"] == "magus_perfectus"
    assert args["strategy"] == "balanced"
    # the opened page's state store rides the returned message key.
    assert pp._STATE["777"]["strategy"] == "balanced"
    assert "tier5_count" not in pp._STATE["777"]


def test_back_to_calc_reopens_without_extra_t5(captured_cards):
    pp._store_state("555", {"paragon_id": "magus_perfectus",
                            "player_count": 2, "difficulty": "hard",
                            "strategy": "least_pops"})
    run(pp.paragon_back_to_calc(_req({})))
    panel_id, args = captured_cards[-1]
    assert panel_id == "btd6.paragon"
    assert args["paragon_id"] == "magus_perfectus"
    assert args["tier5_count"] == 0          # the shipped back-button reset
    assert "strategy" not in pp._STATE["777"]


def test_stats_open_routes_to_the_degree_view(captured_cards):
    # the shipped _StatsButton: a combat-stats paragon opens the
    # btd6.paragon_stats degree view at Degree 1 (#336's port, the
    # arbitration delta).
    pp._store_state("555", {"paragon_id": _DART, "player_count": 1,
                            "difficulty": "medium", "tier5_count": 0})
    reply = run(pp.paragon_stats_view(_req({})))
    assert reply.user_message is None
    panel_id, args = captured_cards[-1]
    assert panel_id == "btd6.paragon_stats"
    assert args["paragon_id"] == _DART
    assert args["degree"] == 1
    # the opened page's state store rides the returned message key.
    assert pp._STATE["777"]["degree"] == 1


def test_stats_degree_card_headline_rides_the_ported_formulas():
    e1 = pp.stats_degree_card(_DART, 1)
    assert e1.title == "👑 Apex Plasma Master — Degree 1"
    assert "**Power required:** 0" in e1.description
    assert "**Boss-damage multiplier:** ×1.0" in e1.description
    assert "×2 (paragons deal ×2 vs Elite Bosses)" in e1.description
    assert e1.footer == "BTD6 stats v55.1"
    assert e1.fields  # the ported per-attack breakdown

    e100 = pp.stats_degree_card(_DART, 100)
    assert "**Power required:** 200,000" in e100.description
    assert "**Boss-damage multiplier:** ×2.25" in e100.description
    assert "×4.5 (paragons deal ×2 vs Elite Bosses)" in e100.description


def test_degree_select_and_submit_refresh_the_stats_view(captured_refresh):
    pp._store_state("555", {"paragon_id": _DART, "player_count": 1,
                            "difficulty": "medium", "tier5_count": 0,
                            "degree": 1})
    run(pp.paragon_degree_select(_req({"values": ("50",)})))
    assert pp._STATE["555"]["degree"] == 50
    assert captured_refresh[-1][1]["degree"] == 50
    # 🔢 Enter degree: non-numeric falls to degree 1 (the shipped
    # ValueError posture), the range clamps 1..100 in stats_state.
    run(pp.paragon_degree_submit(_req({"degree": "abc"})))
    assert pp._STATE["555"]["degree"] == 1
    run(pp.paragon_degree_submit(_req({"degree": "500"})))
    assert pp._STATE["555"]["degree"] == 100
    assert captured_refresh[-1][1]["degree"] == 100


def test_stats_back_reopens_the_calculator_with_extra_t5(captured_cards):
    pp._store_state("555", {"paragon_id": _DART, "player_count": 1,
                            "difficulty": "hard", "tier5_count": 1,
                            "degree": 60})
    run(pp.paragon_stats_back(_req({})))
    panel_id, args = captured_cards[-1]
    assert panel_id == "btd6.paragon"
    assert args["paragon_id"] == _DART
    assert args["tier5_count"] == 1          # the stats page never edits it
    assert "degree" not in args


def test_render_stats_page_defaults_the_milestone_select():
    from sb.domain.btd6.panels import paragon_stats_spec

    rendered = run(pp.render_paragon_stats(
        paragon_stats_spec(), _ctx({"paragon_id": _DART, "degree": "50"})))
    assert rendered.embed.title == "👑 Apex Plasma Master — Degree 50"
    degree_sel = _rendered_selects(rendered)[
        "btd6.paragon_stats.degree_pick"]
    assert [o["value"] for o in degree_sel.options if o.get("default")] == [
        "50"]


def test_stats_card_moduleless_copy_is_shipped_verbatim(monkeypatch,
                                                        captured_cards):
    from sb.domain.btd6 import stats as stats_mod

    monkeypatch.setattr(stats_mod, "get_paragon_stats", lambda pid: None)
    run(pp.paragon_stats_view(_req({})))
    _, args = captured_cards[-1]
    embed = args["_card"]
    assert embed.title == "📊 Paragon stats"
    assert embed.description == (
        "No combat-stats module is published for this paragon yet — only "
        "its cost is known. Pick another paragon to see full stats.")
    assert embed.style_token == "orange"
