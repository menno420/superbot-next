"""Fishing cast-leg depth wiring (PR-A) — the shipped ``begin_cast``
knob compound driving the cast roll (services/fishing_workflow.py:384-518
@cdb26804), the ``commit_catch``-verbatim Reel leg (draw order
bonus → pearl → coral; fishing_workflow.py:174-278), the new pure
minigame/gear/energy halves, and the pending-cast registry. NO golden
pins a cast write yet (PR-B mints those); byte-safety here means every
knob reads exactly neutral for a fresh player."""

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


def _req(uid: int = P1):
    return _FakeReq(actor=SimpleNamespace(user_id=uid, actor_type="user"))


class ScriptRng:
    """A recording RNG — pins the draw ORDER and scripts the values."""

    def __init__(self, randoms=(), choice_index=0, uniform_value=None):
        self.calls: list[str] = []
        self._randoms = list(randoms)
        self._choice_index = choice_index
        self._uniform_value = uniform_value

    def random(self):
        self.calls.append("random")
        return self._randoms.pop(0) if self._randoms else 0.99

    def choices(self, pool, weights=None, k=1):
        self.calls.append("choices")
        return [pool[self._choice_index]]

    def uniform(self, lo, hi):
        self.calls.append("uniform")
        return lo if self._uniform_value is None else self._uniform_value


def _freeze_clock(monkeypatch, now: int = NOW):
    from sb.kernel.workflow import context as ctx_mod

    monkeypatch.setattr(
        ctx_mod, "SYSTEM_CLOCK",
        lambda: SimpleNamespace(timestamp=lambda: now))


def _install_world(monkeypatch, *, energy=(60, 0), venue="shore",
                   rod_tier=0, bait=("", 0), structures=None,
                   equipment=None, skills=None, xp=0):
    """Monkeypatch every state read the wired cast_open touches; return
    the recording sinks."""
    from sb.domain.fishing import store as fs
    from sb.domain.games import store as gs
    from sb.domain.mining import store as ms

    sinks = SimpleNamespace(energy_writes=[], bait_writes=[],
                            bait_clears=[], bait_consumes=[],
                            bait_state={"row": tuple(bait)})

    async def get_fishing_energy(user_id, guild_id, conn=None):
        return energy

    async def set_fishing_energy(user_id, guild_id, e, ts, conn=None):
        sinks.energy_writes.append((e, ts))

    async def get_fishing_venue(user_id, guild_id, conn=None):
        return venue

    async def get_rod_tier(user_id, guild_id, conn=None):
        return rod_tier

    async def get_active_bait(user_id, guild_id, conn=None):
        return sinks.bait_state["row"]

    async def set_active_bait(user_id, guild_id, key, charges, conn=None):
        sinks.bait_writes.append((key, charges))
        sinks.bait_state["row"] = (key, charges)

    async def clear_active_bait(user_id, guild_id, conn=None):
        sinks.bait_clears.append((user_id, guild_id))
        sinks.bait_state["row"] = ("", 0)

    async def consume_bait_charge(user_id, guild_id, bait_key, conn=None):
        # the real store's conditional-decrement contract: relative,
        # keyed on the loadout, clearing the pack in-statement at 0,
        # None when nothing matched (swapped/emptied concurrently).
        key, charges = sinks.bait_state["row"]
        if key != bait_key or charges < 1:
            return None
        left = charges - 1
        sinks.bait_state["row"] = ("", 0) if left <= 0 else (key, left)
        sinks.bait_consumes.append((bait_key, left))
        return left

    async def get_structures(user_id, guild_id, conn=None):
        return dict(structures or {})

    async def get_equipment(user_id, guild_id, conn=None):
        return dict(equipment or {})

    async def get_skills(user_id, guild_id, conn=None):
        return dict(skills or {})

    async def game_xp_rows(user_id, guild_id, conn=None):
        return ([{"game": "fishing", "xp": xp}] if xp else [])

    monkeypatch.setattr(fs, "get_fishing_energy", get_fishing_energy)
    monkeypatch.setattr(fs, "set_fishing_energy", set_fishing_energy)
    monkeypatch.setattr(fs, "get_fishing_venue", get_fishing_venue)
    monkeypatch.setattr(fs, "get_rod_tier", get_rod_tier)
    monkeypatch.setattr(fs, "get_active_bait", get_active_bait)
    monkeypatch.setattr(fs, "set_active_bait", set_active_bait)
    monkeypatch.setattr(fs, "clear_active_bait", clear_active_bait)
    monkeypatch.setattr(fs, "consume_bait_charge", consume_bait_charge)
    monkeypatch.setattr(ms, "get_structures", get_structures)
    monkeypatch.setattr(ms, "get_equipment", get_equipment)
    monkeypatch.setattr(ms, "get_skills", get_skills)
    monkeypatch.setattr(gs, "game_xp_rows", game_xp_rows)
    return sinks


def _capture_open_panel(monkeypatch):
    from sb.kernel.panels import engine as panels_engine

    opened: list = []

    async def _open_panel(ref, req):
        opened.append((ref, req))

    monkeypatch.setattr(panels_engine, "open_panel", _open_panel)
    return opened


def _cast_route():
    from sb.domain.fishing import service
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    service.reset_pending_casts_for_tests()
    return resolve(HandlerRef("fishing.cast_open"))


# --- the pure halves: gear converters, minigame table, energy hooks ---------------


def test_gear_multiplier_half_verbatim():
    """oracle utils/fishing/gear.py:33-65 — 0.04/0.03 converters, caps
    1.40/0.75, exactly neutral at zero stats."""
    from sb.domain.fishing import gear

    assert gear.PULL_PER_FISHING_POWER == 0.04
    assert gear.BITE_SPEED_PER_BITE_LUCK == 0.03
    assert gear.MAX_GEAR_PULL == 1.40
    assert gear.MIN_GEAR_BITE_SPEED == 0.75
    zero = SimpleNamespace(fishing_power=0, bite_luck=0)
    assert gear.fishing_pull_mult(zero) == 1.0
    assert gear.fishing_bite_speed_mult(zero) == 1.0
    assert gear.has_fishing_bonus(zero) is False
    # the full charm ladder: fp6 → ×1.24, bl3 → ×0.91
    full = SimpleNamespace(fishing_power=6, bite_luck=3)
    assert gear.fishing_pull_mult(full) == 1.0 + 0.04 * 6
    assert gear.fishing_bite_speed_mult(full) == 1.0 - 0.03 * 3
    assert gear.has_fishing_bonus(full) is True
    # caps hold against any over-stacked future stats
    big = SimpleNamespace(fishing_power=99, bite_luck=99)
    assert gear.fishing_pull_mult(big) == 1.40
    assert gear.fishing_bite_speed_mult(big) == 0.75
    # negatives clamp to neutral (oracle max(0, …))
    neg = SimpleNamespace(fishing_power=-3, bite_luck=-3)
    assert gear.fishing_pull_mult(neg) == 1.0
    assert gear.fishing_bite_speed_mult(neg) == 1.0


def test_minigame_table_and_resolves_verbatim():
    """oracle utils/fishing/minigame.py:29-61 constants + the pure
    resolve functions (only is_trophy is consumed this slice)."""
    from sb.domain.fishing import catalog, minigame

    assert minigame.REACTION_WINDOW == 2.5
    assert (minigame.BITE_DELAY_MIN, minigame.BITE_DELAY_MAX) == (3.0, 6.0)
    assert minigame.BITE_DELAY_FLOOR == 1.5
    assert (minigame.FAKEOUT_CHANCE, minigame.FAKEOUT_LEAD) == (0.45, 0.6)
    assert minigame.TROPHY_BAND_FRACTION == 1.0 / 3.0
    assert minigame.FIGHT_WINDOW == 2.5
    assert minigame.FIGHT_INTER_ROUND_DELAY == 0.8
    assert (minigame.FIGHT_MIN_TAPS, minigame.FIGHT_MAX_TAPS) == (2, 4)
    assert minigame.SHORE_ESCAPE_CHANCE == 0.06
    # bite delay: floored, speed-scaled before the floor
    rng = ScriptRng(uniform_value=4.0)
    assert minigame.roll_bite_delay(rng, speed=1.0) == 4.0
    rng = ScriptRng(uniform_value=4.0)
    assert minigame.roll_bite_delay(rng, speed=0.1) == 1.5   # the floor
    # premature grace: 0 never forgives, 1 always (no draw either way)
    assert minigame.roll_premature_grace(0.0, ScriptRng()) is False
    assert minigame.roll_premature_grace(1.0, ScriptRng()) is True
    # is_trophy: top third of the species' OWN venue band at the level
    sole = catalog.species_by_name("sardine")       # shore #3
    assert sole is not None and sole.size_rank == 3
    # level 1 shore cap = 3, threshold = 2 → #3 is a trophy
    assert minigame.is_trophy(sole, 1) is True
    # level 7 shore cap = 21, threshold = 14 → #3 is ordinary
    assert minigame.is_trophy(sole, 7) is False
    assert minigame.escape_clue(sole, 1) == (
        "💭 *...it looked like a real **Sardine**, too.*")
    assert minigame.escape_clue(sole, 7) is None
    # reel-fight taps scale 2…4 with size rank /21
    assert minigame.reel_fight_taps(sole) == 2 + round(2 * (3 / 21.0))
    # fight escape: base·(0.6 + rank/21)·(1 − resist)
    assert minigame.fight_escape_chance(sole, 0.0) == (
        0.06 * (0.6 + 3 / 21.0))
    assert minigame.fight_escape_chance(sole, 1.0) == 0.0
    # reel window bounds
    assert minigame.reel_is_in_time(0.0) is True
    assert minigame.reel_is_in_time(2.5) is True
    assert minigame.reel_is_in_time(2.51) is False
    assert minigame.reel_is_in_time(-0.1) is False


def test_energy_boathouse_hook_seconds_until_and_spend_drift_fix():
    """oracle utils/fishing/energy.py:82-121 — regen_seconds_for
    ``max(1, round(base·mult))``, seconds_until clamps, spend keeps the
    settled updated_at (remainder-preserving)."""
    from sb.domain.fishing import energy

    # the boathouse interval hook (NEW — the oracle regen_seconds_for)
    assert energy.regen_seconds_for(1.0) == 30       # unbuilt ⇒ base
    assert energy.regen_seconds_for(0.88) == 26      # Boathouse lvl 1
    assert energy.regen_seconds_for(0.76) == 23      # Boathouse lvl 2
    assert energy.regen_seconds_for(0.0) == 1        # never 0 (div-by-0)
    # spend keeps the settled stamp — partial regen survives the spend
    state = energy.EnergyState(10, 100)
    spent = energy.spend(state, 145)                 # 45 s: gains 1, rem 15
    assert spent == energy.EnergyState(9, 130)       # NOT stamped 145
    # a fresh full bar still stamps now (the golden-pinned 58/60 row)
    spent = energy.spend(energy.EnergyState(60, 0), NOW)
    assert spent == energy.EnergyState(58, NOW)
    # seconds_until (the oracle name for the port's old mis-named fn):
    # remainder credited, target clamped to the cap, floor at 0
    assert energy.seconds_until(energy.EnergyState(0, 100), 122, 2) == 38
    assert energy.seconds_until(energy.EnergyState(60, 0), NOW, 2) == 0
    assert energy.seconds_until(
        energy.EnergyState(59, NOW), NOW, 999) == 30  # min(max, target)


def test_reward_rolls_clamp_and_coral_gating():
    """oracle utils/fishing/rewards.py — bonus clamp [0,1], coral 0.06
    deepwater-only, and the load-bearing no-draw-on-shore property."""
    from sb.domain.fishing import ops

    assert ops.CORAL_DROP_CHANCE == 0.06
    assert ops.coral_drop_chance("deepwater") == 0.06
    assert ops.coral_drop_chance("shore") == 0.0
    assert ops.coral_drop_chance("junk") == 0.0      # normalize → shore
    # shore coral roll consumes NO draw (the pinned trajectory depends
    # on it — rewards.py roll_coral_drop returns before drawing)
    rng = ScriptRng(randoms=[0.0])
    assert ops.roll_coral_drop("shore", rng) is False
    assert rng.calls == []
    rng = ScriptRng(randoms=[0.0])
    assert ops.roll_coral_drop("deepwater", rng) is True
    assert rng.calls == ["random"]
    # bonus clamp: an over-large fishery chance can never exceed 1
    assert ops.roll_bonus_catch(ScriptRng(randoms=[0.9999]),
                                chance=5.0) is True
    assert ops.roll_bonus_catch(ScriptRng(randoms=[0.0]),
                                chance=-1.0) is False
    # default = the base 0.10
    assert ops.roll_bonus_catch(ScriptRng(randoms=[0.0999])) is True
    assert ops.roll_bonus_catch(ScriptRng(randoms=[0.10])) is False


# --- cast_open = the shipped begin_cast --------------------------------------------


def test_cast_open_compounds_every_knob_into_the_roll(monkeypatch):
    """begin_cast L458-471: effective_pull = rod × bait × weather × gear
    × tide_pool; the roll gets the deepwater pool; fishery fixes the
    double-catch chance; the boathouse interval reaches the settle."""
    from sb.domain.fishing import bait as bait_mod
    from sb.domain.fishing import catalog, gear, ops, rods, service, weather
    from sb.domain.mining import character, structures
    from sb.spec.outcomes import SUCCESS

    route = _cast_route()
    _freeze_clock(monkeypatch)
    sinks = _install_world(
        monkeypatch,
        energy=(0, NOW - 52),                 # needs the 26 s interval
        venue="deepwater", rod_tier=2, bait=("grub", 2),
        structures={"tide_pool": 2, "dock": 1, "boathouse": 1,
                    "fishery": 2})
    stats = SimpleNamespace(fishing_power=4, bite_luck=2)
    monkeypatch.setattr(character, "character_stats",
                        lambda equipped, alloc=None: stats)
    opened = _capture_open_panel(monkeypatch)

    rolled: list = []
    real_roll = ops.roll_catch

    def spy_roll(level, rng=None, *, rarity_pull=1.0, venue="shore"):
        rolled.append((level, rarity_pull, venue))
        return real_roll(level, ScriptRng(choice_index=0),
                         rarity_pull=rarity_pull, venue=venue)

    monkeypatch.setattr(ops, "roll_catch", spy_roll)
    try:
        weather.seed_weather_for_replay("storm")
        reply = run(route(_req()))
    finally:
        weather.seed_weather_for_replay(None)
    assert reply.outcome is SUCCESS

    (level, pull, venue), = rolled
    assert level == 1 and venue == "deepwater"
    # the compound, in the shipped factor order (L458-464)
    rod = rods.rod_for_tier(2)
    grub = bait_mod.bait_by_key("grub")
    storm = weather.CONDITIONS[4]
    assert (rod.rarity_pull, grub.rarity_pull, storm.rarity_mult) == (
        1.25, 1.50, 1.30)
    expected_pull = (rod.rarity_pull * grub.rarity_pull
                     * storm.rarity_mult
                     * gear.fishing_pull_mult(stats)
                     * structures.tide_pool_pull_mult(2))
    assert pull == expected_pull
    # boathouse lvl 1 → 26 s interval → 52 s regenerated the 2-cost cast
    # (at the bare 30 s interval this cast would have been BLOCKED);
    # spend kept the settled stamp.
    assert sinks.energy_writes == [(0, NOW)]
    # one grub charge spent: 2 → 1 (a relative consume — never an
    # absolute set, never a clear)
    assert sinks.bait_consumes == [("grub", 1)]
    assert sinks.bait_state["row"] == ("grub", 1)
    assert sinks.bait_writes == [] and sinks.bait_clears == []
    # the pending cast parked with the fishery-adjusted chance
    entry = service._PENDING_CASTS[(P1, GID)]
    assert entry["venue"] == "deepwater"
    assert entry["level_before"] == 1
    assert entry["double_catch_chance"] == (
        ops.BONUS_CATCH_CHANCE + structures.fishery_bonus_chance(2))
    assert catalog.species_by_name(entry["species"]).venue == "deepwater"
    # the panel args carry the shipped cast-note flags
    (_, req), = opened
    assert req.args["cast_venue"] == "deepwater"
    assert req.args["cast_bait_key"] == "grub"
    assert req.args["cast_bait_charges_left"] == 1
    assert req.args["cast_gear_bonus"] is True
    assert req.args["cast_tide_pool"] is True
    assert req.args["cast_dock"] is True
    assert req.args["cast_energy"] == 0
    service.reset_pending_casts_for_tests()


def test_cast_open_boathouse_unbuilt_keeps_the_bare_interval(monkeypatch):
    """The additive-safety half: the SAME drained bar that cast fine at
    Boathouse lvl 1 is BLOCKED at the bare 30 s interval, with the
    shipped seconds_until wait."""
    from sb.spec.outcomes import BLOCKED

    route = _cast_route()
    _freeze_clock(monkeypatch)
    _install_world(monkeypatch, energy=(0, NOW - 52))
    reply = run(route(_req()))
    assert reply.outcome is BLOCKED
    # settle: +1 at 30 s (remainder 22) → 1 short; 30 − 22 = 8 s wait
    assert reply.user_message == (
        "🎣 You're out of energy — let the line rest. "
        "Ready to cast again in **8s**.")


def test_cast_open_fresh_player_rolls_the_exact_neutral_profile(
        monkeypatch):
    """BYTE-SAFETY: a fresh player (no rows anywhere, the golden replay
    world) compounds to exactly pull 1.0 / shore / base double-catch —
    the pre-wiring starter roll — and spends no bait."""
    from sb.domain.fishing import ops, service, weather
    from sb.spec.outcomes import SUCCESS

    route = _cast_route()
    _freeze_clock(monkeypatch)
    sinks = _install_world(monkeypatch)      # all defaults = fresh
    opened = _capture_open_panel(monkeypatch)
    rolled: list = []
    real_roll = ops.roll_catch

    def spy_roll(level, rng=None, *, rarity_pull=1.0, venue="shore"):
        rolled.append((level, rarity_pull, venue))
        return real_roll(level, ScriptRng(), rarity_pull=rarity_pull,
                         venue=venue)

    monkeypatch.setattr(ops, "roll_catch", spy_roll)
    try:
        # sweep_fish's capture-day condition: Rain — rarity_mult 1.0,
        # so even under the seeded golden weather the pull byte is 1.0.
        weather.seed_weather_for_replay("rain")
        reply = run(route(_req()))
    finally:
        weather.seed_weather_for_replay(None)
    assert reply.outcome is SUCCESS
    assert rolled == [(1, 1.0, "shore")]
    # the golden-pinned fresh-bar spend: 60 → 58 stamped now
    assert sinks.energy_writes == [(58, NOW)]
    assert sinks.bait_writes == [] and sinks.bait_clears == []
    assert sinks.bait_consumes == []
    entry = service._PENDING_CASTS[(P1, GID)]
    assert entry["double_catch_chance"] == ops.BONUS_CATCH_CHANCE
    (_, req), = opened
    assert req.args["cast_energy"] == 58
    assert req.args["cast_venue"] == "shore"
    assert req.args["cast_bait_key"] == ""
    assert req.args["cast_gear_bonus"] is False
    assert req.args["cast_tide_pool"] is False
    assert req.args["cast_dock"] is False
    service.reset_pending_casts_for_tests()


def test_cast_open_last_bait_charge_clears_the_pack(monkeypatch):
    """begin_cast L493-502: the last charge spends → the pack clears
    (never a 0-charge row — the consume clears in-statement), and the
    panel note says 0 left."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import SUCCESS

    route = _cast_route()
    _freeze_clock(monkeypatch)
    sinks = _install_world(monkeypatch, bait=("worm", 1))
    opened = _capture_open_panel(monkeypatch)
    reply = run(route(_req()))
    assert reply.outcome is SUCCESS
    assert sinks.bait_consumes == [("worm", 0)]
    assert sinks.bait_state["row"] == ("", 0)
    assert sinks.bait_writes == [] and sinks.bait_clears == []
    (_, req), = opened
    assert req.args["cast_bait_key"] == "worm"
    assert req.args["cast_bait_charges_left"] == 0
    service.reset_pending_casts_for_tests()


def test_cast_open_consume_never_clobbers_a_concurrent_bait_buy(
        monkeypatch):
    """REGRESSION (cast-vs-buy lost update): the cast's bait consume is
    a relative, key-conditional decrement — a bait BUY committing
    between the cast's unlocked read and its consume keeps its
    coin-bought charges. The handler reads ("worm", 3); the buy's txn
    (held behind lock_bait_slot) stacks the loadout to 13 and commits
    inside the window; the consume must land 12 — the old absolute
    write-back (bait_charges - 1 = 2) ate 10 paid charges."""
    from sb.domain.fishing import service
    from sb.domain.fishing import store as fs
    from sb.spec.outcomes import SUCCESS

    route = _cast_route()
    _freeze_clock(monkeypatch)
    sinks = _install_world(monkeypatch, bait=("worm", 3))
    opened = _capture_open_panel(monkeypatch)

    real_read = fs.get_active_bait

    async def stale_read_then_buy_commits(user_id, guild_id, conn=None):
        row = await real_read(user_id, guild_id, conn=conn)
        # the deterministic interleave: the moment the cast holds its
        # stale snapshot, the concurrent buy's committed stack lands.
        sinks.bait_state["row"] = ("worm", 13)
        return row

    monkeypatch.setattr(fs, "get_active_bait", stale_read_then_buy_commits)
    reply = run(route(_req()))
    assert reply.outcome is SUCCESS
    # the consume decremented the COMMITTED count: 13 → 12
    assert sinks.bait_state["row"] == ("worm", 12)
    assert sinks.bait_consumes == [("worm", 12)]
    assert sinks.bait_writes == [] and sinks.bait_clears == []
    (_, req), = opened
    assert req.args["cast_bait_charges_left"] == 12
    service.reset_pending_casts_for_tests()


def test_cast_open_consume_never_eats_a_concurrently_replaced_pack(
        monkeypatch):
    """REGRESSION (cast-vs-buy replace/clear): the cast rolled with the
    last worm charge, but a buy of a DIFFERENT bait replaced the loadout
    inside the window — the consume's key condition misses (None), the
    fresh pack survives untouched, and the cast keeps the effects it
    rolled with (0 left on the panel). The old path called
    clear_active_bait and ate the whole purchase."""
    from sb.domain.fishing import service
    from sb.domain.fishing import store as fs
    from sb.spec.outcomes import SUCCESS

    route = _cast_route()
    _freeze_clock(monkeypatch)
    sinks = _install_world(monkeypatch, bait=("worm", 1))
    opened = _capture_open_panel(monkeypatch)

    real_read = fs.get_active_bait

    async def stale_read_then_replace(user_id, guild_id, conn=None):
        row = await real_read(user_id, guild_id, conn=conn)
        sinks.bait_state["row"] = ("grub", 5)   # the replacing buy commits
        return row

    monkeypatch.setattr(fs, "get_active_bait", stale_read_then_replace)
    reply = run(route(_req()))
    assert reply.outcome is SUCCESS
    # the purchase survives; nothing matched → no decrement, no clear
    assert sinks.bait_state["row"] == ("grub", 5)
    assert sinks.bait_consumes == []
    assert sinks.bait_writes == [] and sinks.bait_clears == []
    (_, req), = opened
    assert req.args["cast_bait_key"] == "worm"   # what the cast rolled with
    assert req.args["cast_bait_charges_left"] == 0
    service.reset_pending_casts_for_tests()


def test_cast_open_duplicate_guard_is_the_shipped_copy(monkeypatch):
    """cast_view.py prepare_cast L86-87: a second cast while a line is
    in the water answers the shipped guard; a stale pending cast (past
    the 45 s oracle view timeout) is overwritten instead."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED, SUCCESS

    route = _cast_route()
    _freeze_clock(monkeypatch)
    _install_world(monkeypatch)
    _capture_open_panel(monkeypatch)
    assert run(route(_req())).outcome is SUCCESS
    reply = run(route(_req()))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "🎣 You've already got a line in the water — reel that one in "
        "first!")
    # age the pending cast past the oracle _VIEW_TIMEOUT → overwrite
    service._PENDING_CASTS[(P1, GID)]["rolled_at"] = NOW - 46
    assert run(route(_req())).outcome is SUCCESS
    service.reset_pending_casts_for_tests()


def test_cast_open_quiet_venue_never_charges(monkeypatch):
    """begin_cast L480-491: energy is spent only once a catch actually
    rolled — a catalog failure answers the quiet-venue copy, no write."""
    from sb.domain.fishing import ops
    from sb.spec.outcomes import BLOCKED

    route = _cast_route()
    _freeze_clock(monkeypatch)
    sinks = _install_world(monkeypatch, venue="deepwater")
    monkeypatch.setattr(
        ops, "roll_catch",
        lambda level, rng=None, *, rarity_pull=1.0, venue="shore": None)
    reply = run(route(_req()))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "⛵ The deepwater is quiet right now — try later.")
    assert sinks.energy_writes == []
    assert sinks.bait_writes == [] and sinks.bait_clears == []
    assert sinks.bait_consumes == []


# --- the Reel leg = the shipped commit_catch ---------------------------------------


def _leg_ctx(params: dict):
    return SimpleNamespace(
        actor=SimpleNamespace(user_id=P1), guild_id=GID,
        clock=lambda: SimpleNamespace(timestamp=lambda: NOW),
        params=params)


def _install_leg_sinks(monkeypatch, *, prior_best=None, award=None):
    from sb.domain.fishing import store as fs
    from sb.domain.games import store as gs
    from sb.domain.games import xp as game_xp
    from sb.domain.mining import store as ms

    writes: list = []

    async def game_xp_rows(user_id, guild_id, conn=None):
        return []  # a fresh player — the fallback seam reads level 1

    monkeypatch.setattr(gs, "game_xp_rows", game_xp_rows)

    async def record_catch(conn, *, user_id, guild_id, species, weight,
                           now):
        writes.append(("record_catch", species, weight))
        return prior_best

    async def update_mining_item(conn, *, user_id, guild_id, item, delta):
        writes.append(("item", item, delta))
        return delta

    default = game_xp.GameXpAward("fishing", "fish", 25, 25, 25, 0, False)

    async def award_in_txn(conn, *, user_id, guild_id, game, action, now,
                           depth=0):
        writes.append(("award", game, action))
        return award or default

    monkeypatch.setattr(fs, "record_catch", record_catch)
    monkeypatch.setattr(ms, "update_mining_item", update_mining_item)
    monkeypatch.setattr(game_xp, "award_in_txn", award_in_txn)
    return writes


def test_record_cast_commits_the_pending_deepwater_cast(monkeypatch):
    """commit_catch verbatim: draws bonus → pearl → coral (the pinned
    order, L207-224), writes record_catch → pearl → coral → fish(×2) →
    xp (L211-261), and answers the _finish_caught copy (cast_view.py
    L398-456) byte-for-byte."""
    from sb.domain.fishing import ops

    rng = ScriptRng(randoms=[0.0, 0.0, 0.0])   # bonus, pearl, coral all hit
    ops.set_rng_for_tests(rng)
    try:
        writes = _install_leg_sinks(monkeypatch)
        outcome = run(ops._record_cast(object(), _leg_ctx({
            "species": "lanternfish", "weight": 3.5,
            "venue": "deepwater", "double_catch_chance": 0.20,
            "level_before": 1})))
    finally:
        ops.set_rng_for_tests(__import__("random").Random())
    # the three draws, in order, on the module rng
    assert rng.calls == ["random", "random", "random"]
    # the txn write order (pearl and coral BEFORE the fish; fish last)
    assert writes == [
        ("record_catch", "lanternfish", 3.5),
        ("item", "pearl", 1),
        ("item", "coral", 1),
        ("item", "lanternfish", 2),            # ×2 — the lucky double
        ("award", "fishing", "fish"),
    ]
    after = outcome.after
    assert after["species"] == "lanternfish"
    assert after["venue"] == "deepwater"
    assert after["bonus_catch"] and after["pearl_found"]
    assert after["coral_found"] and after["new_personal_best"]
    assert after["fishing_level"] == 1
    # the oracle result copy, byte-for-byte (title line + description)
    assert after["message"] == (
        "🎣 Caught it!\n"
        "You reeled in 🐟 a **Lanternfish**!  (size #2 of 11 deepwater)\n"
        "⚖️ It weighs **3.5 kg**. 🏅 **New personal best!**\n"
        "🍀 **Lucky double catch!** A second 🐟 **Lanternfish** for the "
        "craft bin.\n"
        "🦪 **A pearl!** A rare crafting material — save them up to "
        "craft the premium **Royal Feast** bait (`!craftpearl`).\n"
        "🪸 **A piece of coral!** A rare deepwater find — carve it into "
        "cosmetic curios for your collection (`!curios`).")


def test_record_cast_shore_commit_draws_no_coral(monkeypatch):
    """The shore trajectory: bonus → pearl only (roll_coral_drop returns
    without a draw), single fish grant, no material rows."""
    from sb.domain.fishing import ops

    rng = ScriptRng(randoms=[0.99, 0.99])      # both miss
    ops.set_rng_for_tests(rng)
    try:
        writes = _install_leg_sinks(monkeypatch, prior_best=9.9)
        outcome = run(ops._record_cast(object(), _leg_ctx({
            "species": "minnow", "weight": 0.2, "venue": "shore",
            "double_catch_chance": 0.10, "level_before": 1})))
    finally:
        ops.set_rng_for_tests(__import__("random").Random())
    assert rng.calls == ["random", "random"]   # NO third (coral) draw
    assert writes == [
        ("record_catch", "minnow", 0.2),
        ("item", "minnow", 1),
        ("award", "fishing", "fish"),
    ]
    after = outcome.after
    assert not after["bonus_catch"] and not after["pearl_found"]
    assert not after["coral_found"] and not after["new_personal_best"]
    assert after["message"] == (
        "🎣 Caught it!\n"
        "You reeled in 🐟 a **Minnow**!  (size #1 of 21 shore)\n"
        "⚖️ It weighs **0.2 kg**.")


def test_record_cast_fallback_rolls_the_starter_profile(monkeypatch):
    """A Reel with no pending cast (direct op invocation) keeps the
    roll-at-commit STARTER seam — the shipped legacy fish(): shore pool,
    pull 1.0, base double-catch — so the op still works standalone."""
    from sb.domain.fishing import catalog, ops

    # choices → first pool entry (minnow #1), uniform → lo (0.65)
    rng = ScriptRng(randoms=[0.99, 0.99])
    ops.set_rng_for_tests(rng)
    try:
        writes = _install_leg_sinks(monkeypatch)
        outcome = run(ops._record_cast(object(), _leg_ctx({})))
    finally:
        ops.set_rng_for_tests(__import__("random").Random())
    # species + weight drawn at commit, then bonus → pearl (no coral —
    # the fallback is a shore cast)
    assert rng.calls == ["choices", "uniform", "random", "random"]
    after = outcome.after
    assert after["venue"] == "shore"
    species = catalog.species_by_name(after["species"])
    assert species is not None and species.venue == "shore"
    assert writes[0][0] == "record_catch"
    assert writes[-1] == ("award", "fishing", "fish")


def test_record_cast_level_up_appends_the_shipped_notes(monkeypatch):
    """The 🌟 fishing-level line (cast_view L439-444) + the shipped
    GameXpAward.note (game_xp_service.py) on a shared-level boundary."""
    from sb.domain.fishing import ops
    from sb.domain.games import xp as game_xp

    # 125 fishing xp → level 2 (the shared curve's first boundary), and
    # the shared level crossed → leveled_up carries the 🎉 note.
    award = game_xp.GameXpAward("fishing", "fish", 25, 125, 125, 1, True)
    rng = ScriptRng(randoms=[0.99, 0.99])
    ops.set_rng_for_tests(rng)
    try:
        _install_leg_sinks(monkeypatch, award=award)
        outcome = run(ops._record_cast(object(), _leg_ctx({
            "species": "minnow", "weight": 0.2, "venue": "shore",
            "double_catch_chance": 0.10, "level_before": 1})))
    finally:
        ops.set_rng_for_tests(__import__("random").Random())
    after = outcome.after
    assert after["fishing_level"] == 2
    assert after["message"].endswith(
        "\n\n🌟 **Fishing level 2!** You can now catch fish up to "
        "size #6.\n"
        "🎉 Game level up — you reached **Level 1**!")


# --- fish_route pops the registry --------------------------------------------------


def test_fish_route_pops_the_pending_cast_into_the_op(monkeypatch):
    from sb.domain.fishing import service
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    service.reset_pending_casts_for_tests()
    _freeze_clock(monkeypatch)
    route = resolve(HandlerRef("fishing.fish_route"))
    service._PENDING_CASTS[(P1, GID)] = {
        "rolled_at": NOW, "token": 7, "species": "lanternfish",
        "weight": 3.5, "venue": "deepwater", "double_catch_chance": 0.20,
        "level_before": 1}
    seen: list = []

    async def fake_run(ref, ctx):
        seen.append(dict(ctx.params))
        return SimpleNamespace(
            outcome=SUCCESS,
            after={"cast": {"message": "ok"}}, user_message=None)

    monkeypatch.setattr(engine, "run", fake_run)
    reply = run(route(_req()))
    assert reply.outcome is SUCCESS and reply.user_message == "ok"
    assert seen == [{"species": "lanternfish", "weight": 3.5,
                     "venue": "deepwater", "double_catch_chance": 0.20,
                     "level_before": 1}]
    # popped — a second token-less Reel finds no pending cast (the
    # direct-invocation fallback seam)
    assert (P1, GID) not in service._PENDING_CASTS
    reply = run(route(_req()))
    assert reply.outcome is SUCCESS
    assert seen[1] == {}
    service.reset_pending_casts_for_tests()


def _reel_req(token=None):
    args = {} if token is None else {"cast_token": token}
    return _FakeReq(actor=SimpleNamespace(user_id=P1, actor_type="user"),
                    guild_id=GID, args=args)


def test_fish_route_stale_token_never_pops_the_newer_cast(monkeypatch):
    """codex #373 P1: a late Reel from a replaced cast answers the
    shipped got-away terminal (cast_view.py window-expiry copy) and the
    NEWER pending cast stays parked, untouched."""
    from sb.domain.fishing import service
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    service.reset_pending_casts_for_tests()
    _freeze_clock(monkeypatch)
    route = resolve(HandlerRef("fishing.fish_route"))
    newer = {"rolled_at": NOW, "token": 2, "species": "minnow",
             "weight": 0.2, "venue": "shore",
             "double_catch_chance": 0.10, "level_before": 1}
    service._PENDING_CASTS[(P1, GID)] = newer

    async def fake_run(ref, ctx):  # must never be reached
        raise AssertionError("stale Reel must not commit")

    monkeypatch.setattr(engine, "run", fake_run)
    reply = run(route(_reel_req(token=1)))     # the OLD cast's click
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "🌊 *...the line goes slack. The fish got away.*")
    assert service._PENDING_CASTS[(P1, GID)] is newer   # untouched
    service.reset_pending_casts_for_tests()


def test_fish_route_expired_cast_answers_the_got_away_clue(monkeypatch):
    """codex #373 P1/P2: a Reel past the 45 s oracle window surfaces the
    paid timed-out cast with the shipped _got_away soft-fail (trophy
    clue at the cast's own level_before) and never lands the fish."""
    from sb.domain.fishing import service
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    service.reset_pending_casts_for_tests()
    _freeze_clock(monkeypatch)
    route = resolve(HandlerRef("fishing.fish_route"))
    # sardine #3 IS a trophy at level 1 (cap 3) → the clue line appends
    service._PENDING_CASTS[(P1, GID)] = {
        "rolled_at": NOW - 46, "token": 5, "species": "sardine",
        "weight": 1.0, "venue": "shore", "double_catch_chance": 0.10,
        "level_before": 1}

    async def fake_run(ref, ctx):  # must never be reached
        raise AssertionError("expired Reel must not commit")

    monkeypatch.setattr(engine, "run", fake_run)
    reply = run(route(_reel_req(token=5)))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "🌊 *...the line goes slack. The fish got away.*\n"
        "💭 *...it looked like a real **Sardine**, too.*")
    assert (P1, GID) not in service._PENDING_CASTS
    service.reset_pending_casts_for_tests()


def test_fish_route_restores_the_paid_cast_on_a_failed_commit(
        monkeypatch):
    """codex #373 P2: the entry is popped exclusively for the commit and
    RESTORED when the workflow returns non-success — the paid cast stays
    landable."""
    from sb.domain.fishing import service
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import BLOCKED, SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    service.reset_pending_casts_for_tests()
    _freeze_clock(monkeypatch)
    route = resolve(HandlerRef("fishing.fish_route"))
    entry = {"rolled_at": NOW, "token": 3, "species": "minnow",
             "weight": 0.2, "venue": "shore",
             "double_catch_chance": 0.10, "level_before": 1}
    service._PENDING_CASTS[(P1, GID)] = entry
    outcomes = [BLOCKED, SUCCESS]

    async def fake_run(ref, ctx):
        outcome = outcomes.pop(0)
        return SimpleNamespace(
            outcome=outcome, after={"cast": {"message": "ok"}},
            user_message="db hiccup" if outcome is BLOCKED else None)

    monkeypatch.setattr(engine, "run", fake_run)
    reply = run(route(_reel_req(token=3)))
    assert reply.outcome is BLOCKED
    assert service._PENDING_CASTS[(P1, GID)] is entry   # restored
    # the retry lands it and clears the slot
    reply = run(route(_reel_req(token=3)))
    assert reply.outcome is SUCCESS
    assert (P1, GID) not in service._PENDING_CASTS
    service.reset_pending_casts_for_tests()


def test_cast_open_reserves_before_the_first_await(monkeypatch):
    """codex #373 P1: two concurrent Casts for one player can never both
    pass the guard — the slot is reserved synchronously before the first
    await (the oracle's own TOCTOU: guard at prepare_cast L86 but
    active_casts.add only in view.start() L184)."""
    import asyncio

    from sb.spec.outcomes import BLOCKED, SUCCESS

    route = _cast_route()
    _freeze_clock(monkeypatch)
    _install_world(monkeypatch)
    _capture_open_panel(monkeypatch)

    async def both():
        return await asyncio.gather(route(_req()), route(_req()))

    first, second = run(both())
    assert sorted([first.outcome, second.outcome],
                  key=str) == sorted([SUCCESS, BLOCKED], key=str)
    blocked = first if first.outcome is BLOCKED else second
    assert blocked.user_message == (
        "🎣 You've already got a line in the water — reel that one in "
        "first!")
    from sb.domain.fishing import service

    # exactly ONE energy/bait-bearing cast parked
    entry = service._PENDING_CASTS[(P1, GID)]
    assert "species" in entry
    service.reset_pending_casts_for_tests()


def test_cast_open_releases_the_reservation_on_blocked_exits(monkeypatch):
    """The reservation never outlives a refused cast — an out-of-energy
    gate leaves the registry empty (a raise path is covered by the same
    finally)."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED

    route = _cast_route()
    _freeze_clock(monkeypatch)
    _install_world(monkeypatch, energy=(0, NOW))     # drained, no regen
    reply = run(route(_req()))
    assert reply.outcome is BLOCKED
    assert service._PENDING_CASTS == {}


def test_cast_open_sweeps_expired_lines(monkeypatch):
    """codex #373 P2: abandoned pending casts past the 45 s window are
    swept opportunistically on any cast open (the oracle view's
    on-timeout active_casts.discard, cast_view.py:188)."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import SUCCESS

    route = _cast_route()
    _freeze_clock(monkeypatch)
    _install_world(monkeypatch)
    _capture_open_panel(monkeypatch)
    # another player's abandoned line, long past the window
    service._PENDING_CASTS[(999, GID)] = {
        "rolled_at": NOW - 300, "token": 1, "species": "minnow",
        "weight": 0.2, "venue": "shore", "double_catch_chance": 0.10,
        "level_before": 1}
    assert run(route(_req())).outcome is SUCCESS
    assert (999, GID) not in service._PENDING_CASTS
    assert (P1, GID) in service._PENDING_CASTS
    service.reset_pending_casts_for_tests()
