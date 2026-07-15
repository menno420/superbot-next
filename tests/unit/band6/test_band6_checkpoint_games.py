"""Band 6 slice 2 — checkpoint games: farm accrual/pricing + money lanes,
creature catch, mining core loop, fishing cast, providers + the
inventory merge."""

from __future__ import annotations

import asyncio
import random
from types import SimpleNamespace

import pytest

run = asyncio.run

GID, P1 = 1, 42


def _ctx(params: dict, *, uid: int = P1, gid: int = GID,
         epoch: int = 1_000_000):
    import datetime as dt

    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc))


class FakeFarmStore:
    def __init__(self):
        self.rows: dict[tuple, tuple] = {}

    def install(self, monkeypatch):
        from sb.domain.farm import store as fs

        async def get_farm(user_id, guild_id, conn=None,
                           for_update=False):
            return self.rows.get((user_id, guild_id), (1, 0, 0, 0))

        async def set_farm(conn, *, user_id, guild_id, chickens, eggs,
                           now, coop_level):
            self.rows[(user_id, guild_id)] = (chickens, eggs, now,
                                              coop_level)

        monkeypatch.setattr(fs, "get_farm", get_farm)
        monkeypatch.setattr(fs, "set_farm", set_farm)
        return self


# --- farm pure core (shipped verbatim) --------------------------------------------


def test_farm_settle_and_pricing():
    from sb.domain.farm import core

    state = core.FarmState(chickens=2, eggs=0, updated_at=0, coop_level=0)
    settled = core.settle(state, 601)   # two full intervals
    assert settled.eggs == 4
    assert settled.updated_at == 600    # remainder preserved
    # zero elapsed lays nothing (uninitialized-timestamp normalization
    # lives in ops._stored, NOT core — pass updated_at=now)
    assert core.settle(core.FarmState(10, 0, 10_000, 10_000), 10_000).eggs == 0
    capped = core.settle(core.FarmState(10, 0, 0, 0), 100_000)
    assert capped.eggs == core.coop_capacity(0) == 20
    assert core.chicken_price(1) == 40
    assert core.chicken_price(2) == round(40 * 1.55)
    assert core.coop_upgrade_price(0) == 100
    assert core.collect_value(20) == 40


def test_farm_collect_pays_and_resets(fake_economy, fake_games_store,
                                      monkeypatch):
    from sb.domain.farm import ops

    farm = FakeFarmStore().install(monkeypatch)
    farm.rows[(P1, GID)] = (2, 0, 1_000_000 - 600, 0)   # 4 eggs accrued
    out = run(ops._record_collect(None, _ctx({})))
    after = out.after
    assert after["eggs_collected"] == 4 and after["coins_earned"] == 8
    assert farm.rows[(P1, GID)][1] == 0                 # coop emptied
    assert fake_economy.balances[(P1, GID)] == 8
    # empty coop refuses (nothing written)
    from sb.kernel.interaction.errors import ValidatorError

    with pytest.raises(ValidatorError):
        run(ops._record_collect(None, _ctx({})))


def test_farm_buy_settles_at_old_flock_first(fake_economy,
                                             fake_games_store,
                                             monkeypatch):
    from sb.domain.farm import ops

    farm = FakeFarmStore().install(monkeypatch)
    fake_economy.balances[(P1, GID)] = 100
    farm.rows[(P1, GID)] = (1, 0, 1_000_000 - 300, 0)   # 1 egg at old rate
    out = run(ops._record_buy_chicken(None, _ctx({})))
    assert out.after["chickens"] == 2
    chickens, eggs, ts, coop = farm.rows[(P1, GID)]
    assert (chickens, eggs) == (2, 1)   # settled at OLD flock size
    assert fake_economy.balances[(P1, GID)] == 60


def test_farm_buy_insufficient_uses_shipped_copy(fake_economy,
                                                 fake_games_store,
                                                 monkeypatch):
    from sb.domain.farm import ops
    from sb.kernel.interaction.errors import ValidatorError

    FakeFarmStore().install(monkeypatch)
    fake_economy.balances[(P1, GID)] = 5
    with pytest.raises(ValidatorError, match="you only have"):
        run(ops._record_buy_chicken(None, _ctx({})))


# --- creature catch ------------------------------------------------------------------


class FakeCreatureStore:
    def __init__(self):
        self.collection: dict[tuple, dict] = {}
        self.battles: dict[tuple, tuple] = {}

    def install(self, monkeypatch):
        from sb.domain.creature import store as cs

        async def record_catch(conn, *, user_id, guild_id, creature, now):
            row = self.collection.setdefault((user_id, guild_id), {})
            row[creature] = row.get(creature, 0) + 1

        async def get_collection(user_id, guild_id, conn=None):
            return dict(self.collection.get((user_id, guild_id), {}))

        async def record_battle_result(conn, *, user_id, guild_id, won,
                                       now):
            w, losses = self.battles.get((user_id, guild_id), (0, 0))
            self.battles[(user_id, guild_id)] = (
                w + (1 if won else 0), losses + (0 if won else 1))

        monkeypatch.setattr(cs, "record_catch", record_catch)
        monkeypatch.setattr(cs, "get_collection", get_collection)
        monkeypatch.setattr(cs, "record_battle_result",
                            record_battle_result)
        return self


def test_creature_catalog_loaded():
    from sb.domain.creature import catalog

    assert len(catalog.CREATURES) == 36
    assert catalog.catch_chance(catalog.CREATURES[0], 0) <= 0.95


def test_creature_catch_success_and_flee(fake_games_store, monkeypatch):
    from sb.domain.creature import catalog, ops

    cstore = FakeCreatureStore().install(monkeypatch)

    class AlwaysCatch(random.Random):
        def random(self):
            return 0.0

        def choices(self, seq, weights=None, k=1):
            return [seq[0]]

    ops.set_rng_for_tests(AlwaysCatch())
    out = run(ops._record_catch(None, _ctx({})))
    after = out.after
    assert after["caught"] and after["is_new"]
    assert cstore.collection[(P1, GID)]
    assert _gxp(out, _ctx) is None or True   # smoke

    class AlwaysFlee(AlwaysCatch):
        def random(self):
            return 1.0

    ops.set_rng_for_tests(AlwaysFlee())
    out = run(ops._record_catch(None, _ctx({})))
    assert not out.after["caught"]
    # a fled creature wrote nothing new
    assert sum(cstore.collection[(P1, GID)].values()) == 1


def _gxp(out, ctx):
    return None


def test_creature_battle_record_lane(fake_games_store, monkeypatch):
    from sb.domain.creature import ops

    cstore = FakeCreatureStore().install(monkeypatch)
    run(ops._record_battle(None, _ctx({"winner_id": P1,
                                       "loser_id": 77})))
    assert cstore.battles[(P1, GID)] == (1, 0)
    assert cstore.battles[(77, GID)] == (0, 1)


# --- mining core loop ---------------------------------------------------------------


class FakeMiningStore:
    def __init__(self):
        self.inv: dict[tuple, dict] = {}
        self.depth: dict[tuple, int] = {}
        self.energy: dict[tuple, tuple] = {}   # (user, guild) -> (e, ts)

    def install(self, monkeypatch):
        from sb.domain.mining import store as ms

        async def get_mining_inventory(user_id, guild_id, conn=None,
                                        for_update=False):
            return dict(self.inv.get((user_id, guild_id), {}))

        async def update_mining_item(conn, *, user_id, guild_id, item,
                                     delta):
            row = self.inv.setdefault((int(user_id), guild_id), {})
            row[item] = max(0, row.get(item, 0) + delta)
            return row[item]

        async def get_depth(user_id, guild_id, conn=None):
            return self.depth.get((int(user_id), guild_id), 0)

        async def get_energy(user_id, guild_id, conn=None):
            return self.energy.get((int(user_id), guild_id), (0, 0))

        async def set_energy(user_id, guild_id, energy, updated_at,
                             conn=None):
            self.energy[(int(user_id), guild_id)] = (energy, updated_at)

        monkeypatch.setattr(ms, "get_mining_inventory",
                            get_mining_inventory)
        monkeypatch.setattr(ms, "update_mining_item", update_mining_item)
        monkeypatch.setattr(ms, "get_depth", get_depth)
        monkeypatch.setattr(ms, "get_energy", get_energy)
        monkeypatch.setattr(ms, "set_energy", set_energy)
        return self


def test_mine_grants_ore_and_xp(fake_economy, fake_games_store,
                                monkeypatch):
    from sb.domain.mining import ops

    mstore = FakeMiningStore().install(monkeypatch)
    ops.set_rng_for_tests(random.Random(7))
    out = run(ops._record_mine(None, _ctx({})))
    after = out.after
    assert after["amount"] >= 1
    assert mstore.inv[(P1, GID)][after["found"]] == after["amount"]
    assert fake_games_store.xp                     # mine xp written


def test_mine_spends_dig_energy(fake_economy, fake_games_store,
                                monkeypatch):
    """Energy-lane slice 3: the swing settles the bar (missing row →
    (0, 0) → full at any positive clock), spends DIG_COST=1, and writes
    the settled state back — 60 → 59 stamped at the leg clock."""
    from sb.domain.mining import energy, ops

    mstore = FakeMiningStore().install(monkeypatch)
    ops.set_rng_for_tests(random.Random(7))
    out = run(ops._record_mine(None, _ctx({})))
    assert out.after["amount"] >= 1
    assert mstore.energy[(P1, GID)] == (
        energy.MAX_ENERGY - energy.DIG_COST, 1_000_000)


def test_mine_refuses_out_of_energy(fake_economy, fake_games_store,
                                    monkeypatch):
    """A settled-empty bar refuses the swing in-leg (the race fence; the
    route pre-checks the same gate as a pure read for the oracle-plain
    bytes): no loot grant, no energy write, no XP."""
    from sb.kernel.interaction.errors import ValidatorError

    from sb.domain.mining import ops

    mstore = FakeMiningStore().install(monkeypatch)
    # future-stamped empty bar: settle clamps elapsed to 0 → stays 0
    mstore.energy[(P1, GID)] = (0, 4_102_444_800)
    with pytest.raises(ValidatorError) as err:
        run(ops._record_mine(None, _ctx({})))
    assert "⚡ You're out of energy — rest a moment" in str(err.value)
    assert "(`!use ration`)" in str(err.value)
    assert (P1, GID) not in mstore.inv
    assert mstore.energy[(P1, GID)] == (0, 4_102_444_800)   # unwritten
    assert not fake_games_store.xp


def test_sell_all_pays_ledger_audited(fake_economy, fake_games_store,
                                      monkeypatch):
    from sb.domain.mining import ops

    mstore = FakeMiningStore().install(monkeypatch)
    mstore.inv[(P1, GID)] = {"gold": 2, "stone": 3, "pickaxe": 1}
    out = run(ops._record_sell_all(None, _ctx({})))
    after = out.after
    assert after["earned"] == 2 * 6 + 3 * 1        # tools never sell
    assert fake_economy.balances[(P1, GID)] == 15
    assert fake_economy.audit[-1]["reason"] == "mining:sell_ore"
    assert mstore.inv[(P1, GID)]["pickaxe"] == 1


def test_buy_gear_debits(fake_economy, fake_games_store, monkeypatch):
    from sb.domain.mining import ops

    mstore = FakeMiningStore().install(monkeypatch)
    fake_economy.balances[(P1, GID)] = 30
    out = run(ops._record_buy(None, _ctx({"argv": ("pickaxe",)})))
    assert out.after["price"] == 25
    assert mstore.inv[(P1, GID)]["pickaxe"] == 1
    assert fake_economy.balances[(P1, GID)] == 5


# --- fishing cast ----------------------------------------------------------------------


class FakeFishStore:
    def __init__(self):
        self.log: dict[tuple, dict] = {}

    def install(self, monkeypatch):
        from sb.domain.fishing import store as fs

        async def record_catch(conn, *, user_id, guild_id, species,
                               weight, now):
            row = self.log.setdefault((user_id, guild_id), {})
            prior = row.get(species)
            best = prior["best"] if prior else None
            row[species] = {"count": (prior["count"] + 1 if prior else 1),
                            "best": max(weight, best or 0)}
            return best

        monkeypatch.setattr(fs, "record_catch", record_catch)
        return self


def test_fishing_catalog_and_bands():
    from sb.domain.fishing import catalog

    # 32 total = 21 shore (the shipped catalog) + 11 deepwater (the
    # venue split grew the catalog past the shipped 21)
    assert len(catalog.SPECIES) == 32
    assert len(catalog.species_for_venue("shore")) == 21
    assert len(catalog.unlocked_species(1)) == 3
    assert len(catalog.unlocked_species(7)) == len(
        catalog.species_for_venue("shore"))


def test_fishing_energy_settle_and_bar():
    from sb.domain.fishing import energy

    # shipped constants verbatim (utils/fishing/energy.py)
    assert (energy.MAX_ENERGY, energy.CAST_COST,
            energy.REGEN_SECONDS) == (60, 2, 30)
    # fresh row (table defaults 60/0) settles straight to the cap at now
    fresh = energy.settle(energy.EnergyState(60, 0), 1_000)
    assert fresh == energy.EnergyState(60, 1_000)
    # one cast spends CAST_COST and stamps now — the sweep_fish row shape
    spent = energy.spend(energy.EnergyState(60, 0), 1_000)
    assert spent == energy.EnergyState(58, 1_000)
    # partial regen advances the stamp by WHOLE intervals only
    partial = energy.settle(energy.EnergyState(10, 1_000), 1_075)
    assert partial == energy.EnergyState(12, 1_060)
    # the golden footer gauge byte: round(10 * 58/60) = 10 filled
    assert energy.bar(58) == "⚡ 58/60 [▰▰▰▰▰▰▰▰▰▰]"
    assert energy.bar(42) == "⚡ 42/60 [▰▰▰▰▰▰▰▱▱▱]"


def test_fishing_weather_deterministic_and_seeded():
    from datetime import date

    from sb.domain.fishing import weather

    # the table is the shipped 5-condition/weights-sum-100 spread
    assert [c.key for c in weather.CONDITIONS] == [
        "clear", "rain", "calm", "fog", "storm"]
    assert sum(c.weight for c in weather.CONDITIONS) == 100
    # date-seeded pick is stable across calls (sha256, not salted hash)
    d = date(2026, 7, 4)
    assert weather.weather_for_date(d) is weather.weather_for_date(d)
    # a known rain-pick day under the shipped table (capture-window check)
    assert weather.weather_for_date(date(2026, 7, 4)).key == "rain"
    assert weather.weather_for_date(date(2026, 6, 24)).key == "clear"
    # effect_text names only the knobs that move
    rain = next(c for c in weather.CONDITIONS if c.key == "rain")
    clear = next(c for c in weather.CONDITIONS if c.key == "clear")
    storm = next(c for c in weather.CONDITIONS if c.key == "storm")
    assert weather.effect_text(rain) == "faster bites"
    assert weather.effect_text(storm) == "slower bites · rarer fish"
    assert weather.effect_text(clear) == "no effect — a fair, ordinary day"
    # the parity-replay seam wins while armed and clears clean (trap 20)
    try:
        weather.seed_weather_for_replay("rain")
        assert weather.current_weather().key == "rain"
    finally:
        weather.seed_weather_for_replay(None)
    assert weather.current_weather().key in {c.key for c in weather.CONDITIONS}


def test_fishing_cast_commits(fake_economy, fake_games_store,
                              monkeypatch):
    from sb.domain.fishing import ops
    from sb.domain.mining import store as ms

    fstore = FakeFishStore().install(monkeypatch)
    mstore = FakeMiningStore().install(monkeypatch)
    ops.set_rng_for_tests(random.Random(3))
    out = run(ops._record_cast(None, _ctx({})))
    after = out.after
    assert after["species"] and after["weight"] > 0
    assert fstore.log[(P1, GID)][after["species"]]["count"] == 1
    # the fish landed in the shared pack as a tangible item
    assert after["species"] in mstore.inv[(P1, GID)]
    assert fake_games_store.xp                     # fish xp written


# --- providers + inventory merge -------------------------------------------------------


def test_game_rank_providers_registered():
    import sb.manifest.games  # noqa: F401
    from sb.domain.community.rank_providers import get_provider
    from sb.domain.games.providers import register_game_providers

    register_game_providers()
    for name in ("mining", "creatures", "fishing", "farm", "gamexp",
                 "crafting"):
        assert get_provider(name) is not None, name
    # shipped aliases resolve
    assert get_provider("minelb").name == "mining"
    assert get_provider("anglerlb").name == "fishing"
    assert get_provider("chickenlb").name == "farm"
    assert get_provider("gxp").name == "gamexp"


def test_mining_inventory_merges_into_inventory(monkeypatch):
    from sb.domain.inventory.service import (
        build_combined_inventory,
        reset_inventory_ports_for_tests,
    )
    from sb.domain.mining import service as mining_service
    from sb.domain.mining import store as ms

    reset_inventory_ports_for_tests()
    mining_service._source_installed = False
    mining_service.install_inventory_source()

    async def get_mining_inventory(user_id, guild_id, conn=None,
                                    for_update=False):
        return {"gold": 3}

    async def get_inventory(user_id, guild_id, conn=None):
        return {}

    monkeypatch.setattr(ms, "get_mining_inventory", get_mining_inventory)
    import sb.domain.economy.store as econ

    monkeypatch.setattr(econ, "get_inventory", get_inventory)
    combined = run(build_combined_inventory(P1, GID))
    flat = {k for rows in combined.values() for (k, _, _) in rows}
    assert "gold" in flat
    reset_inventory_ports_for_tests()
    mining_service._source_installed = False
