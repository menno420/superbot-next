"""Fishing minigame timing rung (D-0043, slices 1+2): cast_open rolls
bite-delay + fake-out at cast time (strictly AFTER the catch roll, on
the same private cast RNG), parks the timing state, and ARMS the live
cues (nibble / BITE! / got-away one-shot timers — D-0090); fish_route
resolves the Reel click — premature spook / one premature-grace
forgive, the ENFORCED late window (slice 2: past bite_at + window =
too-slow), and the trophy reel-fight whose rounds open on the 0.8 s
beat with their own enforced windows. Enforcement is reel_is_in_time
timestamp math on SYSTEM_CLOCK; the timers only carry panel edits and
no-op headless (EDIT_UNAVAILABLE). Copy is oracle cast_view.py
@bbc524e verbatim."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace

run = asyncio.run

GID, P1 = 1, 42
NOW = 1_000_000


@dataclass(frozen=True)
class _FakeReq:
    """The ResolveRequest subset these handlers touch."""

    actor: object = field(
        default_factory=lambda: SimpleNamespace(user_id=P1,
                                                actor_type="user"))
    guild_id: int = GID
    channel_id: int = 2
    args: dict = field(default_factory=dict)
    origin: object = None
    request_id: str = "r1"
    surface: object = None
    confirmed: bool = False


class ScriptRng:
    """A recording RNG — pins the draw ORDER and scripts the values."""

    def __init__(self, randoms=(), choice_index=0, uniforms=()):
        self.calls: list[str] = []
        self._randoms = list(randoms)
        self._choice_index = choice_index
        self._uniforms = list(uniforms)

    def random(self):
        self.calls.append("random")
        return self._randoms.pop(0) if self._randoms else 0.99

    def choices(self, pool, weights=None, k=1):
        self.calls.append("choices")
        return [pool[self._choice_index]]

    def uniform(self, lo, hi):
        self.calls.append("uniform")
        return self._uniforms.pop(0) if self._uniforms else lo


def _freeze_clock(monkeypatch, now: float = NOW):
    from sb.kernel.workflow import context as ctx_mod

    monkeypatch.setattr(
        ctx_mod, "SYSTEM_CLOCK",
        lambda: SimpleNamespace(timestamp=lambda: now))


def _route():
    from sb.domain.fishing import service
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    service.reset_pending_casts_for_tests()
    return resolve(HandlerRef("fishing.fish_route"))


def _reel_req(token=1):
    return _FakeReq(actor=SimpleNamespace(user_id=P1, actor_type="user"),
                    guild_id=GID, args={"cast_token": token})


def _entry(**over):
    """A parked slice-1 cast entry (the cast_open shape)."""
    base = {
        "rolled_at": NOW, "token": 1, "species": "minnow", "weight": 0.2,
        "venue": "shore", "double_catch_chance": 0.10, "level_before": 1,
        "cast_at_f": float(NOW), "bite_at_f": float(NOW) + 4.0,
        "reaction_window": 2.5, "grace": 0.0, "grace_used": False,
        "fakeout": False, "trophy": False, "taps_required": 0,
        "taps_done": 0, "fight": False, "rod_name": "Bare Rod",
        "escape_resist": 0.0, "base_escape": 0.06,
    }
    base.update(over)
    return base


def _no_commit(monkeypatch):
    from sb.kernel.workflow import engine

    async def fake_run(ref, ctx):  # must never be reached
        raise AssertionError("this Reel must not commit")

    monkeypatch.setattr(engine, "run", fake_run)


def _commit_spy(monkeypatch):
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS

    seen: list = []

    async def fake_run(ref, ctx):
        seen.append(dict(ctx.params))
        return SimpleNamespace(outcome=SUCCESS,
                               after={"cast": {"message": "landed"}},
                               user_message=None)

    monkeypatch.setattr(engine, "run", fake_run)
    return seen


def _arm_rng(rng):
    from sb.domain.fishing import ops

    ops.set_rng_for_tests(rng)


def _disarm_rng():
    import random

    from sb.domain.fishing import ops

    ops.set_rng_for_tests(random.Random())


# --- cast_open rolls the timing at cast time ---------------------------------------


def test_cast_open_rolls_timing_after_the_catch_on_the_cast_rng(
        monkeypatch):
    """The pinned draw order — catch (choices → weight uniform) FIRST,
    then bite uniform → fake-out random on the SAME cast RNG — and the
    parked timing state: bite_at_f = cast_at_f + max(floor,
    uniform × effective_bite_speed), window = venue + rod bonus."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, resolve
    from tests.unit.band6.test_band6_fishing_cast_wiring import (
        _capture_open_panel,
        _install_world,
    )

    service.ensure_handler_refs()
    service.reset_pending_casts_for_tests()
    route = resolve(HandlerRef("fishing.cast_open"))
    _freeze_clock(monkeypatch)
    _install_world(monkeypatch)          # fresh shore player, bare rod
    _capture_open_panel(monkeypatch)
    # weight uniform → 1.0, bite uniform → 5.0, fake-out random → 0.30
    rng = ScriptRng(randoms=[0.30], uniforms=[1.0, 5.0])
    _arm_rng(rng)
    try:
        from sb.domain.fishing import weather

        weather.seed_weather_for_replay("rain")
        try:
            reply = run(route(_FakeReq()))
        finally:
            weather.seed_weather_for_replay(None)
    finally:
        _disarm_rng()
    assert reply.outcome is SUCCESS
    assert rng.calls == ["choices", "uniform", "uniform", "random"]
    entry = service._PENDING_CASTS[(P1, GID)]
    # rain bite_speed_mult 0.85 × bare rod 1.0 ⇒ 5.0 × 0.85 = 4.25
    assert entry["cast_at_f"] == float(NOW)
    assert entry["bite_at_f"] == float(NOW) + 4.25
    assert entry["reaction_window"] == 2.5      # shore 2.5 + bare rod 0.0
    assert entry["grace"] == 0.0
    assert entry["fakeout"] is True             # 0.30 < FAKEOUT_CHANCE 0.45
    assert entry["fight"] is False and entry["taps_done"] == 0
    assert entry["escape_resist"] == 0.0
    assert entry["base_escape"] == 0.06
    assert entry["rod_name"] == "Bare Rod"
    service.reset_pending_casts_for_tests()


# --- premature: spook / grace -------------------------------------------------------


def test_premature_reel_on_a_bare_rod_spooks_with_no_draw(monkeypatch):
    """A pre-bite click with grace 0 answers the oracle 🌀 spook terminal
    (verbatim; NO trophy clue — the oracle never wraps the premature
    spook in _got_away), pops the paid cast, writes nothing, and
    consumes NO rng draw (roll_premature_grace short-circuits ≤ 0)."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED

    route = _route()
    _freeze_clock(monkeypatch, NOW + 0.5)      # bite at NOW+4.0 — early
    _no_commit(monkeypatch)
    service._PENDING_CASTS[(P1, GID)] = _entry(
        species="sardine", trophy=True, taps_required=2)  # even a trophy
    rng = ScriptRng()
    _arm_rng(rng)
    try:
        reply = run(route(_reel_req()))
    finally:
        _disarm_rng()
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "🌀 You reeled too early — the fish darted off. "
        "*Hold your nerve!*")
    assert rng.calls == []                      # grace 0 ⇒ no draw
    assert (P1, GID) not in service._PENDING_CASTS
    service.reset_pending_casts_for_tests()


def test_premature_grace_forgives_once_then_spooks(monkeypatch):
    """The rod's premature_grace forgives ONE pre-bite slip (the oracle
    😅 edit, rod-name-interpolated; the cast stays parked, grace spent),
    and the SECOND slip spooks even when the roll would forgive again."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED, SUCCESS

    route = _route()
    _freeze_clock(monkeypatch, NOW + 0.5)
    _no_commit(monkeypatch)
    entry = _entry(grace=0.6, rod_name="Diamond Rod")
    service._PENDING_CASTS[(P1, GID)] = entry
    rng = ScriptRng(randoms=[0.59, 0.0])       # both under 0.6
    _arm_rng(rng)
    try:
        first = run(route(_reel_req()))
        second = run(route(_reel_req()))
    finally:
        _disarm_rng()
    assert first.outcome is SUCCESS
    # no live panel session in this harness → the degrade text reply
    # carries the oracle grace copy verbatim
    assert first.user_message == (
        "😅 *You twitch the rod too soon — but the Diamond Rod steadies "
        "it. The line's still in the water… hold your nerve.*")
    assert entry["grace_used"] is True
    assert rng.calls == ["random"]             # the second slip never rolls
    assert second.outcome is BLOCKED
    assert second.user_message == (
        "🌀 You reeled too early — the fish darted off. "
        "*Hold your nerve!*")
    assert (P1, GID) not in service._PENDING_CASTS
    service.reset_pending_casts_for_tests()


# --- in-window / late ---------------------------------------------------------------


def test_in_window_ordinary_fish_commits_unchanged(monkeypatch):
    """bite_at ≤ now ≤ bite_at + window, non-trophy → the existing
    audited commit path with the parked params, entry popped."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import SUCCESS

    route = _route()
    _freeze_clock(monkeypatch, NOW + 5.0)      # bite 4.0, window 2.5
    seen = _commit_spy(monkeypatch)
    service._PENDING_CASTS[(P1, GID)] = _entry()
    reply = run(route(_reel_req()))
    assert reply.outcome is SUCCESS and reply.user_message == "landed"
    assert seen == [{"species": "minnow", "weight": 0.2, "venue": "shore",
                     "double_catch_chance": 0.10, "level_before": 1}]
    assert (P1, GID) not in service._PENDING_CASTS
    service.reset_pending_casts_for_tests()


def test_late_reel_past_the_window_is_too_slow(monkeypatch):
    """D-0043 slice 2 — the enforcement flip: now past bite_at + window
    answers the oracle too-slow got-away terminal (an ordinary fish
    carries no clue), pops the paid cast, writes nothing."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED

    route = _route()
    _freeze_clock(monkeypatch, NOW + 30.0)     # the parity 30 s click
    _no_commit(monkeypatch)
    service._PENDING_CASTS[(P1, GID)] = _entry()
    reply = run(route(_reel_req()))
    assert reply.outcome is BLOCKED
    assert reply.user_message == "🌊 *...too slow. The fish got away.*"
    assert (P1, GID) not in service._PENDING_CASTS
    service.reset_pending_casts_for_tests()


def test_late_reel_on_a_trophy_appends_the_clue(monkeypatch):
    """A too-slow trophy rides the oracle _got_away wrapper — the 💭
    tease appends (unlike the premature spook, which never gets one)."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED

    route = _route()
    # bite 4.0 + window 2.5 = 6.5; 6.51 is JUST past it (the boundary
    # 6.5 itself is in-time — reel_is_in_time is inclusive).
    _freeze_clock(monkeypatch, NOW + 6.51)
    _no_commit(monkeypatch)
    service._PENDING_CASTS[(P1, GID)] = _entry(
        species="sardine", trophy=True, taps_required=2)
    reply = run(route(_reel_req()))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "🌊 *...too slow. The fish got away.*\n"
        "💭 *...it looked like a real **Sardine**, too.*")
    assert (P1, GID) not in service._PENDING_CASTS
    service.reset_pending_casts_for_tests()


def test_window_boundary_click_is_still_in_time(monkeypatch):
    """elapsed == window commits (reel_is_in_time is inclusive — the
    oracle 0.0 ≤ elapsed ≤ window)."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import SUCCESS

    route = _route()
    _freeze_clock(monkeypatch, NOW + 6.5)      # bite 4.0 + window 2.5
    seen = _commit_spy(monkeypatch)
    service._PENDING_CASTS[(P1, GID)] = _entry()
    reply = run(route(_reel_req()))
    assert reply.outcome is SUCCESS
    assert len(seen) == 1
    service.reset_pending_casts_for_tests()


# --- the trophy reel-fight ----------------------------------------------------------


def test_trophy_hook_starts_the_fight_and_taps_land_it(monkeypatch):
    """In-window trophy: click 1 hooks (the oracle 🎣 Hooked-a-big-one
    edit; no commit) and opens round 1 on the 0.8 s beat, each further
    IN-WINDOW click is one tap — escape roll on the cast RNG,
    tension-bar advance, next round re-armed — and the LAST tap
    commits."""
    from sb.domain.fishing import minigame, service
    from sb.spec.outcomes import SUCCESS

    route = _route()
    _freeze_clock(monkeypatch, NOW + 5.0)
    seen = _commit_spy(monkeypatch)
    # sardine (#3) IS a trophy at level 1 (shore cap 3, threshold 2)
    entry = _entry(species="sardine", weight=1.0, trophy=True,
                   taps_required=2)
    service._PENDING_CASTS[(P1, GID)] = entry
    rng = ScriptRng(randoms=[0.99, 0.99])      # both taps hold
    _arm_rng(rng)
    try:
        hook = run(route(_reel_req()))
        assert hook.outcome is SUCCESS
        assert hook.user_message == (
            "🎣 **Hooked a big one!** It dives deep — hang on…")
        assert entry["fight"] is True and seen == []
        # round 1 opens one suspense beat after the hook (the oracle
        # _run_fight_round sleep), with its live cues armed.
        assert entry["fight_round_open_f"] == NOW + 5.0 + (
            minigame.FIGHT_INTER_ROUND_DELAY)
        assert len(entry["timers"]) == 2       # arm + expiry
        _freeze_clock(monkeypatch, NOW + 6.0)  # inside round 1's window
        tap1 = run(route(_reel_req()))
        assert tap1.outcome is SUCCESS
        assert tap1.user_message == "💪 Reeling it in… `▰▱`"
        assert entry["taps_done"] == 1 and seen == []
        # the next round re-armed off the tap's resolve time.
        assert entry["fight_round_open_f"] == NOW + 6.0 + (
            minigame.FIGHT_INTER_ROUND_DELAY)
        _freeze_clock(monkeypatch, NOW + 7.0)  # inside round 2's window
        tap2 = run(route(_reel_req()))
    finally:
        _disarm_rng()
    assert rng.calls == ["random", "random"]   # one escape roll per tap
    assert tap2.outcome is SUCCESS and tap2.user_message == "landed"
    assert seen == [{"species": "sardine", "weight": 1.0, "venue": "shore",
                     "double_catch_chance": 0.10, "level_before": 1}]
    assert (P1, GID) not in service._PENDING_CASTS
    service.reset_pending_casts_for_tests()


def test_click_between_fight_rounds_is_the_mash_ignore(monkeypatch):
    """A click BEFORE the round opens (inside the 0.8 s beat) is the
    oracle safe_defer mash-ignore: no state moves, no rng draw, the
    fight stays live."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import SUCCESS

    route = _route()
    _freeze_clock(monkeypatch, NOW + 5.5)      # round opens at 5.8
    _no_commit(monkeypatch)
    entry = _entry(species="sardine", trophy=True, taps_required=2,
                   fight=True, fight_round_open_f=NOW + 5.8)
    service._PENDING_CASTS[(P1, GID)] = entry
    rng = ScriptRng()
    _arm_rng(rng)
    try:
        reply = run(route(_reel_req()))
    finally:
        _disarm_rng()
    assert reply.outcome is SUCCESS and reply.user_message is None
    assert rng.calls == []                     # no escape roll on a mash
    assert entry["taps_done"] == 0
    assert service._PENDING_CASTS[(P1, GID)] is entry
    service.reset_pending_casts_for_tests()


def test_late_fight_tap_past_the_round_window_is_too_slow(monkeypatch):
    """A tap past the round's window answers the oracle too-slow
    terminal + the trophy clue (a fight IS a trophy) — no draw, no
    write, the paid cast is gone."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED

    route = _route()
    # round opened at 5.8, window 2.5 ⇒ closes 8.3; click at 8.4.
    _freeze_clock(monkeypatch, NOW + 8.4)
    _no_commit(monkeypatch)
    entry = _entry(species="sardine", trophy=True, taps_required=2,
                   fight=True, fight_round_open_f=NOW + 5.8)
    service._PENDING_CASTS[(P1, GID)] = entry
    rng = ScriptRng()
    _arm_rng(rng)
    try:
        reply = run(route(_reel_req()))
    finally:
        _disarm_rng()
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "🌊 *...too slow. The fish got away.*\n"
        "💭 *...it looked like a real **Sardine**, too.*")
    assert rng.calls == []                     # a late tap never rolls
    assert (P1, GID) not in service._PENDING_CASTS
    service.reset_pending_casts_for_tests()


def test_trophy_tap_escape_snaps_the_line_with_the_clue(monkeypatch):
    """A tap whose escape roll fires answers the oracle 💥 snap terminal
    + the trophy clue (a fight IS a trophy), pops the paid cast, and
    never commits. Deepwater base_escape × rod escape_resist reach the
    roll: sardine rank 3 ⇒ chance = 0.22·(0.6+3/21)·(1−0.5) ≈ 0.0817."""
    from sb.domain.fishing import minigame, service
    from sb.domain.fishing import catalog
    from sb.spec.outcomes import BLOCKED

    route = _route()
    _freeze_clock(monkeypatch, NOW + 5.0)
    _no_commit(monkeypatch)
    entry = _entry(species="sardine", trophy=True, taps_required=3,
                   fight=True, base_escape=0.22, escape_resist=0.5)
    service._PENDING_CASTS[(P1, GID)] = entry
    sardine = catalog.species_by_name("sardine")
    chance = minigame.fight_escape_chance(sardine, 0.5, base_escape=0.22)
    rng = ScriptRng(randoms=[chance - 0.0001])  # just under ⇒ escapes
    _arm_rng(rng)
    try:
        reply = run(route(_reel_req()))
    finally:
        _disarm_rng()
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "💥 It gave one last thrash, **snapped the line**, and bolted!\n"
        "💭 *...it looked like a real **Sardine**, too.*")
    assert (P1, GID) not in service._PENDING_CASTS
    service.reset_pending_casts_for_tests()


def test_fight_outlives_nothing_past_the_45s_sweep(monkeypatch):
    """The 45 s pending sweep stays the OUTER bound around the whole
    ladder — a fight click past the oracle view timeout answers the
    got-away terminal, never a tap."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED

    route = _route()
    _freeze_clock(monkeypatch, NOW + 46.0)
    _no_commit(monkeypatch)
    service._PENDING_CASTS[(P1, GID)] = _entry(
        species="sardine", trophy=True, taps_required=2, fight=True)
    reply = run(route(_reel_req()))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "🌊 *...the line goes slack. The fish got away.*\n"
        "💭 *...it looked like a real **Sardine**, too.*")
    assert (P1, GID) not in service._PENDING_CASTS
    service.reset_pending_casts_for_tests()


def test_pre_slice_entry_shape_resolves_as_in_time(monkeypatch):
    """An entry WITHOUT the slice-1 timing fields (the pre-slice shape)
    commits exactly as before — the resolution ladder is additive."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import SUCCESS

    route = _route()
    _freeze_clock(monkeypatch, NOW)
    seen = _commit_spy(monkeypatch)
    service._PENDING_CASTS[(P1, GID)] = {
        "rolled_at": NOW, "token": 1, "species": "minnow", "weight": 0.2,
        "venue": "shore", "double_catch_chance": 0.10, "level_before": 1}
    reply = run(route(_reel_req()))
    assert reply.outcome is SUCCESS
    assert len(seen) == 1
    service.reset_pending_casts_for_tests()


# --- the live-cue timers (D-0043 slice 2 / D-0090) ----------------------------------


class _FakeHandle:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


def test_cast_open_arms_the_live_cue_timers(monkeypatch):
    """The cast park arms the oracle _run_bite cues: nibble (the rolled
    fake-out fits its lead — delay 4.25, 4.25−0.6 > 1.5) + BITE! arm +
    got-away expiry = 3 one-shot timers; the push-edit context rides
    the entry."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, resolve
    from tests.unit.band6.test_band6_fishing_cast_wiring import (
        _capture_open_panel,
        _install_world,
    )

    service.ensure_handler_refs()
    service.reset_pending_casts_for_tests()
    route = resolve(HandlerRef("fishing.cast_open"))
    _freeze_clock(monkeypatch)
    _install_world(monkeypatch)
    _capture_open_panel(monkeypatch)
    # weight 1.0, bite uniform 5.0 (×0.85 rain = 4.25), fake-out 0.30<0.45
    rng = ScriptRng(randoms=[0.30], uniforms=[1.0, 5.0])
    _arm_rng(rng)
    try:
        from sb.domain.fishing import weather

        weather.seed_weather_for_replay("rain")
        try:
            reply = run(route(_FakeReq()))
        finally:
            weather.seed_weather_for_replay(None)
    finally:
        _disarm_rng()
    assert reply.outcome is SUCCESS
    entry = service._PENDING_CASTS[(P1, GID)]
    assert len(entry["timers"]) == 3
    assert entry["guild_id"] == GID
    assert entry["actor"] is not None
    service.reset_pending_casts_for_tests()


def test_short_lead_or_no_fakeout_skips_the_nibble_timer(monkeypatch):
    """The oracle lead-fit guard: a fake-out whose nibble would land
    under the bite floor (delay − FAKEOUT_LEAD ≤ BITE_DELAY_FLOOR) is
    silent — and a cast that never rolled one arms only BITE! +
    got-away (2 timers each)."""
    from sb.domain.fishing import service
    from sb.spec.refs import HandlerRef, resolve
    from tests.unit.band6.test_band6_fishing_cast_wiring import (
        _capture_open_panel,
        _install_world,
    )

    service.ensure_handler_refs()
    route = resolve(HandlerRef("fishing.cast_open"))
    _freeze_clock(monkeypatch)
    _install_world(monkeypatch)
    _capture_open_panel(monkeypatch)
    from sb.domain.fishing import weather

    for randoms, uniforms in (
        ([0.30], [1.0, 2.0]),   # fake-out rolled, but 1.7−0.6 ≤ 1.5
        ([0.60], [1.0, 5.0]),   # no fake-out (0.60 ≥ 0.45)
    ):
        service.reset_pending_casts_for_tests()
        rng = ScriptRng(randoms=list(randoms), uniforms=list(uniforms))
        _arm_rng(rng)
        try:
            weather.seed_weather_for_replay("rain")
            try:
                run(route(_FakeReq()))
            finally:
                weather.seed_weather_for_replay(None)
        finally:
            _disarm_rng()
        entry = service._PENDING_CASTS[(P1, GID)]
        assert len(entry["timers"]) == 2
    service.reset_pending_casts_for_tests()


def test_got_away_timer_pops_the_entry_and_noops_headless():
    """The unprompted window expiry (real short delays): the got-away
    timer pops the paid cast with NO DB write, and its panel edit
    no-ops headless (no editor installed — EDIT_UNAVAILABLE), never a
    crash."""
    from sb.domain.fishing import service

    async def main():
        entry = _entry(cast_at_f=0.0, bite_at_f=0.02, reaction_window=0.02)
        entry["panel_key"] = "424242"      # no live session either
        entry["guild_id"] = GID
        service._PENDING_CASTS[(P1, GID)] = entry
        service._arm_bite_timers((P1, GID), entry)
        await asyncio.sleep(0.3)
        assert (P1, GID) not in service._PENDING_CASTS

    run(main())
    service.reset_pending_casts_for_tests()


def test_stale_timer_never_touches_a_newer_cast():
    """The identity guard (the oracle _round_id staleness token): a
    timer armed for a replaced entry wakes, sees the newer cast, and
    exits without popping it."""
    from sb.domain.fishing import service

    async def main():
        entry = _entry(cast_at_f=0.0, bite_at_f=0.01, reaction_window=0.01)
        service._PENDING_CASTS[(P1, GID)] = entry
        service._arm_bite_timers((P1, GID), entry)
        newer = _entry(token=2)
        service._PENDING_CASTS[(P1, GID)] = newer     # replaced
        await asyncio.sleep(0.2)
        assert service._PENDING_CASTS[(P1, GID)] is newer

    run(main())
    service.reset_pending_casts_for_tests()


def test_terminal_paths_cancel_the_armed_timers(monkeypatch):
    """A premature spook disarms the cast's live cues (and the test
    reset does too) — no orphaned timer outlives its entry."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED

    route = _route()
    _freeze_clock(monkeypatch, NOW + 0.5)
    _no_commit(monkeypatch)
    entry = _entry()
    spook_handle = _FakeHandle()
    entry["timers"] = [spook_handle]
    service._PENDING_CASTS[(P1, GID)] = entry
    reply = run(route(_reel_req()))
    assert reply.outcome is BLOCKED
    assert spook_handle.cancelled

    reset_handle = _FakeHandle()
    parked = _entry(token=3)
    parked["timers"] = [reset_handle]
    service._PENDING_CASTS[(P1, GID)] = parked
    service.reset_pending_casts_for_tests()
    assert reset_handle.cancelled
    assert service._PENDING_CASTS == {}


# --- the cast panel prompt override -------------------------------------------------


def test_render_cast_prompt_override_is_a_bare_description_embed():
    """cast_prompt renders the oracle _edit_message shape — description
    only, no weather field, no footer, components kept — and its absence
    leaves the golden-pinned waiting-panel composition path untouched."""
    from sb.domain.fishing import panels
    from sb.domain.fishing.panels import cast_spec
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    ctx = PanelContext(
        bot=None, guild_id=GID, actor=SimpleNamespace(user_id=P1),
        channel_id=9, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(),
        params={"cast_prompt": "💪 Reeling it in… `▰▱`",
                "cast_energy": 58, "cast_venue": "shore"})
    rendered = run(panels._render_cast(cast_spec(), ctx))
    assert rendered.embed.description == "💪 Reeling it in… `▰▱`"
    assert rendered.embed.fields == ()
    assert rendered.embed.footer == ""
    assert len(rendered.components) == 1       # the Reel button survives


def _prompt_ctx(params: dict):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=GID, actor=SimpleNamespace(user_id=P1),
        channel_id=9, origin=PanelOrigin.ANCHOR,
        audience=Audience.INVOKER, locale=LocaleContext(),
        params={"cast_energy": 58, "cast_venue": "shore", **params})


def test_render_cast_bite_arm_knobs_flip_color_and_button():
    """The push-edit BITE! arm (oracle _arm): SUCCESS_COLOR embed + the
    Reel button flipped to the armed label/style — the slice-2 params
    the timers pass (absent ⇒ golden-pinned bytes untouched, covered by
    the bare-prompt test above)."""
    from sb.domain.fishing import panels
    from sb.domain.fishing.panels import cast_spec

    rendered = run(panels._render_cast(cast_spec(), _prompt_ctx({
        "cast_prompt": "🐟 **BITE!** Reel it in — quick!",
        "cast_prompt_style": "green",
        "cast_button_label": "Reel it in!",
        "cast_button_style": "success"})))
    assert rendered.embed.description == "🐟 **BITE!** Reel it in — quick!"
    assert rendered.embed.style_token == "green"
    (button,) = rendered.components
    assert button.label == "Reel it in!"
    assert button.style == "success"
    assert button.disabled is False


def test_render_cast_terminal_knobs_disable_the_button():
    """The unprompted got-away terminal (oracle _fail): ERROR_COLOR +
    the button kept but disabled."""
    from sb.domain.fishing import panels
    from sb.domain.fishing.panels import cast_spec

    rendered = run(panels._render_cast(cast_spec(), _prompt_ctx({
        "cast_prompt": "🌊 *...the line goes slack. The fish got away.*",
        "cast_prompt_style": "red",
        "cast_button_label": "Reel it in!",
        "cast_button_style": "success",
        "cast_disable": True})))
    assert rendered.embed.style_token == "red"
    (button,) = rendered.components
    assert button.disabled is True
    assert button.label == "Reel it in!"
