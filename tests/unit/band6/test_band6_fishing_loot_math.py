"""Fishing catch/loot MATH + populated-leaderboard rendering depth.

The bite/reel TIMING state machine and the refusal/BLOCKED paths are
already thoroughly covered (test_band6_fishing_minigame_timing.py,
test_band6_fishing_cast_wiring.py). The thin spots this file pins are
the pure number curves the cast rides — ``catalog.nominal_weight`` /
``roll_weight`` (the trophy-record spread + the 0.01 floor),
``ops.pearl_drop_chance`` / ``roll_pearl_drop`` (the linear curve + the
0.15 saturation cap), ``ops.roll_catch`` (the inverse-size weighting,
the ``max(1.0, rarity_pull)`` clamp, the empty-pool ``None`` branch),
and ``catalog.max_size_rank_for_level`` (the ``max(1, level) * 3`` band
under the ``min(band, venue_size_cap)`` cap) — plus the POPULATED
``fishing.top_view`` / ``fishing.trophies_view`` bodies (medals →
``**N.**``, the ``caught (S/T species)`` line, the 🐟 emoji fallback for
a species missing from the catalog, and ``_angler_name`` degrading to
``User {id}``). All DB-free: injected RNGs + monkeypatched store reads.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace

run = asyncio.run

GID, P1 = 1, 42


class ScriptRng:
    """A recording RNG — pins the draw ORDER and scripts the values
    (the house idiom, mirrored from test_band6_fishing_cast_wiring.py)."""

    def __init__(self, *, uniform=None, randoms=(), choice_index=0):
        self.calls: list[str] = []
        self._uniform = uniform
        self._randoms = list(randoms)
        self._choice_index = choice_index
        self.weights_seen: list | None = None
        self.pool_seen: list | None = None

    def uniform(self, lo, hi):
        self.calls.append("uniform")
        return lo if self._uniform is None else self._uniform

    def random(self):
        self.calls.append("random")
        return self._randoms.pop(0) if self._randoms else 0.99

    def choices(self, pool, weights=None, k=1):
        self.calls.append("choices")
        self.pool_seen = list(pool)
        self.weights_seen = list(weights) if weights is not None else None
        return [pool[self._choice_index]]


# --- weight math: the trophy-record spread + the 0.01 floor -----------------------


def test_nominal_weight_is_the_0_18_x_rank_1_65_curve():
    """catalog.nominal_weight — the shipped ``round(0.18 · rank^1.65, 2)``
    at a low and a high rank (the trophy record's per-catch expectation)."""
    from sb.domain.fishing import catalog

    minnow = catalog.species_by_name("minnow")       # size_rank 1
    shark = catalog.species_by_name("shark")         # size_rank 20
    assert minnow is not None and minnow.size_rank == 1
    assert shark is not None and shark.size_rank == 20
    # rank 1: 0.18 · 1^1.65 = 0.18
    assert catalog.nominal_weight(minnow) == round(0.18 * 1 ** 1.65, 2)
    assert catalog.nominal_weight(minnow) == 0.18
    # rank 20: the high end of the curve
    assert catalog.nominal_weight(shark) == round(0.18 * 20 ** 1.65, 2)
    assert catalog.nominal_weight(shark) == 25.23


def test_roll_weight_pins_the_spread_band_ends_and_the_floor():
    """catalog.roll_weight — ``uniform(0.65, 1.55)`` scales the nominal;
    the two spread ends bound a catch, and a tiny nominal × a tiny factor
    hits the ``max(0.01, …)`` floor (never a 0 kg trophy)."""
    from sb.domain.fishing import catalog

    shark = catalog.species_by_name("shark")         # nominal 25.23
    # the spread band ends: 0.65 (lightest) and 1.55 (heaviest) — a single
    # uniform draw, then the rounded product.
    lo = ScriptRng(uniform=0.65)
    assert catalog.roll_weight(shark, lo) == round(25.23 * 0.65, 2)
    assert catalog.roll_weight(shark, lo) == 16.4     # (2nd call, same value)
    hi = ScriptRng(uniform=1.55)
    assert catalog.roll_weight(shark, hi) == round(25.23 * 1.55, 2)
    assert catalog.roll_weight(shark, hi) == 39.11
    # each roll_weight is a single uniform draw (two calls above ⇒ two draws)
    assert lo.calls == ["uniform", "uniform"]
    # the floor: minnow's 0.18 nominal × a below-band factor rounds to 0.0,
    # and ``max(0.01, …)`` lifts it to the 0.01 floor.
    minnow = catalog.species_by_name("minnow")
    assert round(catalog.nominal_weight(minnow) * 0.02, 2) == 0.0
    assert catalog.roll_weight(minnow, ScriptRng(uniform=0.02)) == 0.01


# --- pearl math: the linear curve + the 0.15 saturation cap -----------------------


def test_pearl_drop_chance_curve_and_saturation_cap():
    """ops.pearl_drop_chance — 0.02 base at rank 1, +0.004/rank linear,
    saturating at PEARL_DROP_MAX_CHANCE == 0.15 for a big enough rank."""
    from sb.domain.fishing import ops

    assert ops.PEARL_DROP_BASE_CHANCE == 0.02
    assert ops.PEARL_DROP_PER_SIZE_RANK == 0.004
    assert ops.PEARL_DROP_MAX_CHANCE == 0.15
    assert ops.pearl_drop_chance(1) == 0.02
    # linear +0.004 per rank above 1
    assert ops.pearl_drop_chance(2) == round(0.02 + 0.004, 4)
    assert ops.pearl_drop_chance(21) == round(0.02 + 0.004 * 20, 4)
    # the sub-1 floor: rank clamps to 1, so rank 0 == rank 1
    assert ops.pearl_drop_chance(0) == 0.02
    # the cap boundary: rank 33 is still under the cap, rank 34 saturates.
    assert ops.pearl_drop_chance(33) == round(0.02 + 0.004 * 32, 4)
    assert ops.pearl_drop_chance(33) < 0.15
    assert ops.pearl_drop_chance(34) == 0.15
    assert ops.pearl_drop_chance(999) == 0.15


def test_roll_pearl_drop_on_both_sides_of_the_threshold():
    """ops.roll_pearl_drop — a single ``random()`` draw compared to the
    rank's chance: a draw just under hits, a draw at/over misses."""
    from sb.domain.fishing import ops

    chance = ops.pearl_drop_chance(21)               # 0.10
    hit = ScriptRng(randoms=[chance - 0.0001])
    miss = ScriptRng(randoms=[chance])               # strict ``<`` ⇒ miss
    assert ops.roll_pearl_drop(21, hit) is True
    assert ops.roll_pearl_drop(21, miss) is False
    assert hit.calls == ["random"] and miss.calls == ["random"]


# --- roll_catch: inverse-size weighting + the pull clamp --------------------------


def test_roll_catch_inverse_size_weighting_clamp_and_empty_pool():
    """ops.roll_catch — the weight per species is ``1 / rank^(1/pull)``;
    a ``rarity_pull < 1`` is clamped by ``max(1.0, …)`` (can't sharpen
    toward the small end), a huge pull flattens selection toward the big
    fish, and an empty pool returns ``None`` outright."""
    from sb.domain.fishing import catalog, ops

    # pull 1.0 ⇒ pure inverse-size weights (1/rank): the unlocked shore
    # band at level 7 is ranks 1..21, so the first three are 1, 1/2, 1/3.
    neutral = ScriptRng(choice_index=0)
    ops.roll_catch(7, neutral, rarity_pull=1.0, venue="shore")
    assert neutral.weights_seen[:3] == [1.0, 1.0 / 2, 1.0 / 3]

    # a sub-1 pull is CLAMPED to 1.0 — the weights are identical to pull 1,
    # so a player can never sharpen the roll toward tiny fish.
    clamped = ScriptRng(choice_index=0)
    ops.roll_catch(7, clamped, rarity_pull=0.3, venue="shore")
    assert clamped.weights_seen == neutral.weights_seen

    # a huge pull FLATTENS the distribution toward the big end — the
    # max/min weight ratio collapses toward 1 (vs. 21× at pull 1).
    flat = ScriptRng(choice_index=0)
    ops.roll_catch(7, flat, rarity_pull=100.0, venue="shore")
    neutral_spread = max(neutral.weights_seen) / min(neutral.weights_seen)
    flat_spread = max(flat.weights_seen) / min(flat.weights_seen)
    assert neutral_spread == 21.0
    assert flat_spread < 1.1 < neutral_spread

    # the roll returns a real Catch (species + rolled weight) — one
    # choices draw then one uniform for the weight.
    picked = ScriptRng(choice_index=0)
    catch = ops.roll_catch(7, picked, rarity_pull=1.0, venue="shore")
    assert isinstance(catch, catalog.Catch)
    assert catch.species.size_rank == 1
    assert picked.calls == ["choices", "uniform"]

    # the empty-pool branch: a venue with no species yields None BEFORE
    # any draw (never an IndexError on an empty ``choices``).
    empty = ScriptRng()
    assert ops.roll_catch(1, empty, venue="no-such-venue") is None
    assert empty.calls == []


# --- level band cap: max(1, level)*3 under min(band, venue_size_cap) --------------


def test_max_size_rank_for_level_band_and_venue_cap():
    """catalog.max_size_rank_for_level — the ``max(1, level) * 3`` band,
    the ``min(band, venue_size_cap)`` ceiling, and the level floor."""
    from sb.domain.fishing import catalog

    assert catalog.FISH_PER_LEVEL == 3
    assert catalog.venue_size_cap("shore") == 21
    # the raw band, uncapped where band < cap
    assert catalog.max_size_rank_for_level(1, "shore") == 3
    assert catalog.max_size_rank_for_level(2, "shore") == 6
    # band == cap exactly at level 7 (7 * 3 == 21 == the shore cap)
    assert catalog.max_size_rank_for_level(7, "shore") == 21
    # the cap BITES past level 7: band 24 clamps to the 21-species cap.
    assert 8 * catalog.FISH_PER_LEVEL == 24
    assert catalog.max_size_rank_for_level(8, "shore") == 21
    # the level floor: 0 and negatives floor to band 3 (max(1, level)).
    assert catalog.max_size_rank_for_level(0, "shore") == 3
    assert catalog.max_size_rank_for_level(-5, "shore") == 3


# --- the populated leaderboard bodies (service.py) --------------------------------


@dataclass(frozen=True)
class _Req:
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


def _capture_card(monkeypatch):
    """Patch the ``_card`` open_panel lane and return the captured embeds
    (the leaderboard body rides ``req.args['_card'].description``)."""
    from sb.kernel.panels import engine as panels_engine

    opened: list = []

    async def _open_panel(ref, req):
        opened.append(req.args["_card"])

    monkeypatch.setattr(panels_engine, "open_panel", _open_panel)
    return opened


def _route(name: str):
    from sb.domain.fishing import service
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    return resolve(HandlerRef(name))


def test_top_view_renders_medals_then_numbers_and_degrades_names(monkeypatch):
    """fishing.top_view populated body: 🥇🥈🥉 for the top three then
    ``**4.**``, the ``— **N** caught (S/T species)`` line at the full
    catalog total, and ``_angler_name`` degrading to ``User {id}`` when
    the guild directory can't resolve the member."""
    from sb.domain.fishing import catalog, store
    from sb.domain.utility import service as util_service
    from sb.spec.outcomes import SUCCESS

    total = len(catalog.SPECIES)

    async def fake_top(guild_id, known_species, limit=10, conn=None):
        return [{"user_id": 7, "total": 30, "species": 5},
                {"user_id": 8, "total": 20, "species": 3},
                {"user_id": 9, "total": 10, "species": 2},
                {"user_id": 10, "total": 5, "species": 1}]

    async def unresolved(guild_id, user_id):
        raise RuntimeError("member gone")   # ⇒ the ``User {id}`` fallback

    monkeypatch.setattr(store, "top_fishers", fake_top)
    monkeypatch.setattr(
        util_service, "guild_directory",
        lambda: SimpleNamespace(member_info=unresolved))
    cards = _capture_card(monkeypatch)

    reply = run(_route("fishing.top_view")(_Req()))
    assert reply.outcome is SUCCESS
    assert cards[-1].title == "🎣 Top Anglers"
    assert cards[-1].description == (
        f"🥇 User 7 — **30** caught (5/{total} species)\n"
        f"🥈 User 8 — **20** caught (3/{total} species)\n"
        f"🥉 User 9 — **10** caught (2/{total} species)\n"
        f"**4.** User 10 — **5** caught (1/{total} species)")


def test_top_view_empty_world_keeps_the_golden_prompt(monkeypatch):
    """The no-rows body is the shipped empty-world copy (the
    goldens/fishing/sweep_fishtop byte) — the populated path never fires."""
    from sb.domain.fishing import store
    from sb.spec.outcomes import SUCCESS

    async def no_rows(guild_id, known_species, limit=10, conn=None):
        return []

    monkeypatch.setattr(store, "top_fishers", no_rows)
    cards = _capture_card(monkeypatch)
    reply = run(_route("fishing.top_view")(_Req()))
    assert reply.outcome is SUCCESS
    assert cards[-1].description == (
        "No one has cast a line yet — be the first with `!fish`!")


def test_trophies_view_renders_emoji_fallback_and_resolved_names(monkeypatch):
    """fishing.trophies_view populated hall-of-fame: medals then
    ``**4.**``, the catalog species emoji (🦈 for shark) with the 🐟
    fallback for a species the catalog no longer knows, the ``{:g}``
    weight formatting, and the resolved display name (tag minus its
    ``#discriminator``)."""
    from sb.domain.fishing import store
    from sb.domain.utility import service as util_service
    from sb.spec.outcomes import SUCCESS

    async def fake_trophies(guild_id, known_species, limit=10, conn=None):
        return [{"user_id": 7, "species": "shark", "best_weight": 40.5},
                {"user_id": 8, "species": "ghostfish", "best_weight": 12.0},
                {"user_id": 9, "species": "minnow", "best_weight": 0.3},
                {"user_id": 10, "species": "tuna", "best_weight": 0.2}]

    async def resolve_member(guild_id, user_id):
        return SimpleNamespace(tag=f"Angler{user_id}#0001")

    monkeypatch.setattr(store, "top_trophies", fake_trophies)
    monkeypatch.setattr(
        util_service, "guild_directory",
        lambda: SimpleNamespace(member_info=resolve_member))
    cards = _capture_card(monkeypatch)

    reply = run(_route("fishing.trophies_view")(_Req()))
    assert reply.outcome is SUCCESS
    assert cards[-1].title == "🏅 Biggest Catches"
    assert cards[-1].description == (
        "🥇 🦈 **40.5 kg** Shark — Angler7\n"
        # ghostfish is not in the catalog ⇒ the 🐟 emoji fallback
        "🥈 🐟 **12 kg** Ghostfish — Angler8\n"
        "🥉 🐟 **0.3 kg** Minnow — Angler9\n"
        "**4.** 🐟 **0.2 kg** Tuna — Angler10")
