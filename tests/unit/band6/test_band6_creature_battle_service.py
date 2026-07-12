"""Unit coverage for the creature PvP battle SERVICE seam
(sb/domain/creature/battle_service.py) — the resolve read-path + the pure
outcome-card presentation helpers (D-0079). No DB: the collection reader is
monkeypatched over the store, like the band-6 fakes pattern.
"""

from __future__ import annotations

import asyncio
import random

from sb.domain.creature import battle as engine
from sb.domain.creature import battle_service as bs
from sb.domain.creature.catalog import Creature

run = asyncio.run


def _c(name: str, element: str, archetype: str = "balanced",
       emoji: str = "🔥") -> Creature:
    return Creature(name=name, element=element, rarity="Common",
                    archetype=archetype, emoji=emoji)


def _install_pools(monkeypatch, pools: dict[int, dict[str, int]],
                   catalog: dict[str, Creature]) -> None:
    from sb.domain.creature import catalog as cat
    from sb.domain.creature import store

    async def get_collection(user_id, guild_id, conn=None):
        return dict(pools.get(user_id, {}))

    monkeypatch.setattr(store, "get_collection", get_collection)
    monkeypatch.setattr(cat, "creature_by_name",
                        lambda name: catalog.get(name.strip().lower()))


_CATALOG = {
    "cindling": _c("Cindling", "Ember"),
    "rippling": _c("Rippling", "Tide", emoji="🌊"),
    "sproutle": _c("Sproutle", "Bramble", emoji="🌿"),
    "emberpaw": _c("Emberpaw", "Ember", "attacker"),
    "splashfin": _c("Splashfin", "Tide", "attacker", "🌊"),
    "thornkit": _c("Thornkit", "Bramble", "attacker", "🌿"),
}


def test_resolve_pvp_returns_result_and_is_seed_deterministic(monkeypatch):
    _install_pools(
        monkeypatch,
        {1: {"Cindling": 1, "Rippling": 1, "Sproutle": 1},
         2: {"Emberpaw": 1, "Splashfin": 1, "Thornkit": 1}},
        _CATALOG)

    def _resolve():
        return run(bs.resolve_pvp(1, 2, 99, rng=random.Random("svc-seed")))

    a = _resolve()
    b = _resolve()
    assert a is not None and b is not None
    # same seed -> same winner + same roster shape.
    assert a.outcome.winner == b.outcome.winner
    assert len(a.team_a) == 3 and len(a.team_b) == 3
    assert isinstance(a.a_won, bool)


def test_resolve_pvp_none_when_a_pool_is_empty(monkeypatch):
    _install_pools(
        monkeypatch,
        {1: {"Cindling": 1}, 2: {}},
        _CATALOG)
    assert run(bs.resolve_pvp(1, 2, 99, rng=random.Random(0))) is None


def test_resolve_pvp_skips_unknown_catalog_names(monkeypatch):
    # a collection with only unknown (superseded) names yields no team -> None.
    _install_pools(
        monkeypatch,
        {1: {"Cindling": 1}, 2: {"GhostMon": 3}},
        _CATALOG)
    assert run(bs.resolve_pvp(1, 2, 99, rng=random.Random(0))) is None


def test_build_result_view_fields_and_winner():
    team_a = engine.build_team([_c("Cindling", "Ember")], 50)
    team_b = engine.build_team([_c("Splashfin", "Tide", "attacker", "🌊")], 50)
    outcome = engine.resolve_battle(team_a, team_b, rng=random.Random(5))
    result = bs.PvpResult(outcome=outcome, team_a=tuple(team_a),
                          team_b=tuple(team_b))
    winner_id = 1 if result.a_won else 2

    description, fields = bs.build_result_view(
        "Alice", "Bob", 1, 2, result, winner_id=winner_id,
        records={1: (3, 1), 2: (0, 2)}, xp_note="🎉 Reached game level **1**!")

    assert "<@1> vs <@2>" in description
    names = [f[0] for f in fields]
    assert names == ["Alice's team", "Bob's team", "Highlights", "Winner",
                     "Records"]
    winner_field = dict((f[0], f[1]) for f in fields)["Winner"]
    assert winner_field.startswith(f"🏆 <@{winner_id}>")
    assert "🎉 Reached game level **1**!" in winner_field
    records_field = dict((f[0], f[1]) for f in fields)["Records"]
    assert "Alice — **3**W · **1**L" in records_field
    assert "Bob — **0**W · **2**L" in records_field


def test_build_result_view_marks_fainted_and_highlights():
    # a lopsided 1v1: the loser faints, so its roster line carries 💀 and a
    # KO highlight appears.
    team_a = engine.build_team([_c("Emberpaw", "Ember", "attacker")], 50)
    team_b = engine.build_team([_c("Sproutle", "Bramble")], 50)  # Ember>Bramble
    outcome = engine.resolve_battle(team_a, team_b, rng=random.Random(2))
    result = bs.PvpResult(outcome=outcome, team_a=tuple(team_a),
                          team_b=tuple(team_b))
    winner_id = 1 if result.a_won else 2
    _desc, fields = bs.build_result_view(
        "Alice", "Bob", 1, 2, result, winner_id=winner_id)
    by_name = dict((f[0], f[1]) for f in fields)
    # exactly one team wiped; its line carries the 💀 marker.
    assert ("💀" in by_name["Alice's team"]) ^ ("💀" in by_name["Bob's team"])
    assert "took down" in by_name["Highlights"]
    # no records field when records is None.
    assert "Records" not in by_name


def test_build_result_view_no_records_field_when_none():
    team_a = engine.build_team([_c("Cindling", "Ember")], 50)
    team_b = engine.build_team([_c("Rippling", "Tide", emoji="🌊")], 50)
    outcome = engine.resolve_battle(team_a, team_b, rng=random.Random(1))
    result = bs.PvpResult(outcome=outcome, team_a=tuple(team_a),
                          team_b=tuple(team_b))
    _desc, fields = bs.build_result_view("A", "B", 1, 2, result, winner_id=1)
    assert [f[0] for f in fields] == ["A's team", "B's team", "Highlights",
                                      "Winner"]
