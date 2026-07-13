"""The grid Mine port (curation rework rows 45/59) — the pure grid module
(oracle ``disbot/utils/mining/grid.py`` @ 9c16365, verbatim), the
position/fog-of-war store accessors on ``mining_player_state`` (migration
0054 — pos_x/pos_y oracle columns + the FLAGGED ``discovered`` JSONB
deviation), and the ``mining.record_dig`` leg's write set.

DB-free: the ``_RecordingConn`` SQL-shape pin (the 0052 energy-store test
pattern) plus monkeypatched store reads for the leg test.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

run = asyncio.run

GID, P1 = 1, 42

MIGRATION = (Path(__file__).resolve().parents[3] / "migrations"
             / "0054_mining_grid.sql")


class _RecordingConn:
    def __init__(self, row: dict | None = None):
        self.row = row
        self.queries: list[str] = []
        self.params: list[tuple] = []

    async def fetchrow(self, query: str, *params: object):
        self.queries.append(query)
        self.params.append(params)
        return self.row

    async def execute(self, query: str, *params: object):
        self.queries.append(query)
        self.params.append(params)
        return "OK"


# --- the pure grid module -------------------------------------------------------


def test_cell_at_is_deterministic_and_process_stable():
    """Q-0173: a cell is a pure function of (seed, x, y, z) — same inputs,
    same cell, negative coordinates included (the splitmix64-style mix
    never touches Python's per-process string-hash randomization)."""
    from sb.domain.mining import grid

    a = grid.cell_at(12345, -3, 7, 2)
    b = grid.cell_at(12345, -3, 7, 2)
    assert a == b
    assert a.richness == {"normal": 1.0, "rich": 2.0, "barren": 0.5,
                          "treasure": 2.0}[a.feature.value]
    # a different seed gives an independent world (spot check: SOME cell
    # in a small window differs)
    window_a = [grid.cell_at(1, x, y, 0).feature
                for x in range(-4, 5) for y in range(-4, 5)]
    window_b = [grid.cell_at(2, x, y, 0).feature
                for x in range(-4, 5) for y in range(-4, 5)]
    assert window_a != window_b


def test_step_and_move_phrase_are_the_oracle_dpad():
    from sb.domain.mining import grid

    assert grid.step(0, 0, grid.NORTH) == (0, 1)
    assert grid.step(0, 0, grid.SOUTH) == (0, -1)
    assert grid.step(0, 0, grid.EAST) == (1, 0)
    assert grid.step(0, 0, grid.WEST) == (-1, 0)
    assert grid.step(3, 4, grid.DOWN) == (3, 4)  # vertical: no lateral move
    assert grid.move_phrase(grid.DOWN) == "deeper"
    assert grid.move_phrase(grid.UP) == "upward"
    assert grid.LATERAL == {"north", "south", "east", "west"}


def test_reveal_radius_is_non_regressive_and_capped():
    """light 0/1 → the base 2 (a torch changes nothing — BUG-0026's
    non-regressive rule); lantern (2) → 3; diamond lantern (3) → 4;
    capped at 4."""
    from sb.domain.mining.grid import reveal_radius

    assert reveal_radius(0) == 2
    assert reveal_radius(1) == 2
    assert reveal_radius(2) == 3
    assert reveal_radius(3) == 4
    assert reveal_radius(9) == 4


def test_render_local_map_fog_player_and_legend():
    from sb.domain.mining import grid

    body = grid.render_local_map(1, 0, 0, 0, set(), radius=2)
    lines = body.split("\n")
    assert len(lines) == 5
    assert all(len(line.split(" ")) == 5 for line in lines)
    # undiscovered cells are fog; the player's own cell is always @
    assert lines[2].split(" ")[2] == grid.PLAYER_GLYPH
    flat = body.replace("\n", " ").split(" ")
    assert flat.count(grid.FOG_GLYPH) == 24
    # a discovered cell shows its feature glyph, not fog
    body2 = grid.render_local_map(1, 0, 0, 0, {(1, 0)}, radius=2)
    assert body2.replace("\n", " ").split(" ").count(grid.FOG_GLYPH) == 23
    assert grid.MAP_LEGEND == ("@ you · . rock · * rich · - barren · "
                               "$ treasure · ? unexplored")


def test_apply_cell_to_loot_folds_richness_and_flavour():
    from sb.domain.mining.grid import Cell, CellFeature, apply_cell_to_loot

    rich = Cell(0, 0, 0, CellFeature.RICH, "gold", 2.0)
    found, amount, note = apply_cell_to_loot(rich, "stone", 2)
    assert (found, amount) == ("gold", 4)          # lucky strike swaps ore
    assert note == "💎 You struck a rich gold vein!"
    barren = Cell(0, 0, 0, CellFeature.BARREN, "iron", 0.5)
    found, amount, note = apply_cell_to_loot(barren, "stone", 1)
    assert (found, amount) == ("stone", 1)         # floor: never nothing
    assert note == "The rock here is barren — slim pickings."
    normal = Cell(0, 0, 0, CellFeature.NORMAL, "iron", 1.0)
    assert apply_cell_to_loot(normal, "stone", 2) == ("stone", 2, None)


def test_describe_cell_copy():
    from sb.domain.mining.grid import Cell, CellFeature, describe_cell

    assert describe_cell(Cell(0, 0, 0, CellFeature.NORMAL, "iron", 1.0)) == \
        "You're standing on ordinary rock."
    assert describe_cell(
        Cell(0, 0, 0, CellFeature.TREASURE, "diamond", 2.0)) == \
        "You're standing on a treasure pocket (diamond)."


def test_mine_multiplier_equipped_tool_wins_legacy_matched():
    """Oracle mine_multiplier verbatim: equipped tool scales with
    mining_power (pickaxe ×1.125, diamond ×1.5); no tool + inventory
    pickaxe keeps the matched legacy bonus; bare hands ×1.0."""
    from sb.domain.mining import equipment, rewards

    assert rewards.mine_multiplier({}, {}) == 1.0
    assert rewards.mine_multiplier({}, {"pickaxe": 1}) == \
        rewards.LEGACY_PICKAXE_MULT
    assert rewards.mine_multiplier({equipment.TOOL: "pickaxe"}, {}) == \
        1.0 + 2 * rewards.TOOL_POWER_GAIN
    assert rewards.mine_multiplier({equipment.TOOL: "diamond pickaxe"},
                                   {}) == 1.5


# --- the store accessors (migration 0054 shapes) --------------------------------


def test_get_position_missing_row_reads_origin():
    from sb.domain.mining import store

    conn = _RecordingConn(row=None)
    assert run(store.get_position(P1, GID, conn=conn)) == (0, 0)
    assert "pos_x, pos_y FROM mining_player_state" in conn.queries[0]
    assert conn.params[0] == (str(P1), GID)      # TEXT user ids


def test_set_position_upserts_without_now_touch():
    from sb.domain.mining import store

    conn = _RecordingConn()
    run(store.set_position(conn, user_id=P1, guild_id=GID, x=3, y=-2))
    q = conn.queries[0]
    assert "INSERT INTO mining_player_state" in q
    assert "ON CONFLICT (user_id, guild_id)" in q
    assert "pos_x=$3, pos_y=$4" in q
    assert "now()" not in q                       # BIGINT-epoch band rule
    assert conn.params[0] == (str(P1), GID, 3, -2)


def test_mark_discovered_is_a_single_jsonb_merge():
    """The flagged 0054 deviation: one idempotent `discovered || $patch`
    statement (the oracle's ON CONFLICT DO NOTHING posture) — no
    read-modify-write."""
    from sb.domain.mining import store

    conn = _RecordingConn()
    run(store.mark_discovered(conn, user_id=P1, guild_id=GID,
                              depth=2, x=-1, y=4))
    q = conn.queries[0]
    assert len(conn.queries) == 1
    assert "discovered = mining_player_state.discovered || $3::jsonb" in q
    assert json.loads(conn.params[0][2]) == {"2:-1:4": 1}


def test_get_discovered_window_filters_depth_and_box():
    from sb.domain.mining import store

    blob = json.dumps({"0:0:1": 1, "0:9:9": 1, "1:0:2": 1, "junk": 1})
    conn = _RecordingConn(row={"discovered": blob})
    got = run(store.get_discovered_window(P1, GID, 0, -2, 2, -2, 2,
                                          conn=conn))
    assert got == {(0, 1)}   # other-depth, out-of-box and junk keys drop
    # missing row → empty set
    assert run(store.get_discovered_window(
        P1, GID, 0, -2, 2, -2, 2, conn=_RecordingConn(row=None))) == set()


def test_migration_0054_shape_and_checksum_row():
    ddl = MIGRATION.read_text()
    for frag in (
        "ALTER TABLE mining_player_state ADD COLUMN IF NOT EXISTS pos_x "
        "INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE mining_player_state ADD COLUMN IF NOT EXISTS pos_y "
        "INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE mining_player_state ADD COLUMN IF NOT EXISTS "
        "discovered JSONB NOT NULL DEFAULT '{}'::jsonb",
    ):
        assert frag in ddl
    # NO new table: fog of war deliberately rides mining_player_state (the
    # parity R2 / wp-stack-lane rationale lives in the migration header).
    assert "CREATE TABLE" not in ddl
    checksums = json.loads(
        (MIGRATION.parent / "checksums.json").read_text())
    assert "0054_mining_grid.sql" in checksums


def test_no_new_store_spec_for_the_grid():
    """The deviation's guard: the grid added NO store row — position + fog
    ride MINING_PLAYER_STATE_STORE (erasure via mining.erase_subject_state
    covers the columns with the row)."""
    from sb.spec.versioning import registered_stores

    tables = {s.table for s in registered_stores()}
    assert "mining_player_state" in tables
    assert "mining_discovered" not in tables


# --- the record_dig leg ----------------------------------------------------------


class _Store:
    """Monkeypatch double for sb.domain.mining.store inside the leg."""

    def __init__(self):
        self.position = (0, 0)
        self.depth = 0
        self.energy = (35, 10_000)
        self.equipment: dict[str, str] = {}
        self.skills: dict[str, int] = {}
        self.inventory = {"pickaxe": 1}
        self.seed = GID
        self.writes: list[tuple] = []

    def install(self, monkeypatch):
        from sb.domain.mining import store as real

        async def get_position(uid, gid, conn=None):
            return self.position

        async def get_depth(uid, gid, conn=None):
            return self.depth

        async def get_energy(uid, gid, conn=None):
            return self.energy

        async def get_equipment(uid, gid, conn=None):
            return dict(self.equipment)

        async def get_skills(uid, gid, conn=None):
            return dict(self.skills)

        async def get_mining_inventory(uid, gid, conn=None):
            return dict(self.inventory)

        async def get_world_seed(gid, conn=None):
            return self.seed

        async def get_gear_wear(uid, gid, conn=None):
            return {}

        async def set_energy(uid, gid, energy, updated_at, conn=None):
            self.writes.append(("energy", energy))

        async def set_position(conn, *, user_id, guild_id, x, y):
            self.writes.append(("position", x, y))

        async def set_depth(conn, *, user_id, guild_id, depth):
            self.writes.append(("depth", depth))

        async def update_mining_item(conn, *, user_id, guild_id, item,
                                     delta):
            self.writes.append(("grant", item, delta))

        async def mark_discovered(conn, *, user_id, guild_id, depth, x, y):
            self.writes.append(("discovered", depth, x, y))

        async def record_depth(conn, *, user_id, guild_id, depth):
            self.writes.append(("record_depth", depth))
            return False

        for name, fn in (("get_position", get_position),
                         ("get_depth", get_depth),
                         ("get_energy", get_energy),
                         ("get_equipment", get_equipment),
                         ("get_skills", get_skills),
                         ("get_mining_inventory", get_mining_inventory),
                         ("get_world_seed", get_world_seed),
                         ("get_gear_wear", get_gear_wear),
                         ("set_energy", set_energy),
                         ("set_position", set_position),
                         ("set_depth", set_depth),
                         ("update_mining_item", update_mining_item),
                         ("mark_discovered", mark_discovered),
                         ("record_depth", record_depth)):
            monkeypatch.setattr(real, name, fn)


def _ctx(direction: str):
    from sb.kernel.workflow.context import WorkflowContext

    class _Actor:
        user_id = P1

    return WorkflowContext(actor=_Actor(), guild_id=GID,
                           request_id="t-dig",
                           params={"direction": direction})


def test_record_dig_lateral_moves_mines_marks_and_spends(monkeypatch):
    """One lateral dig = ONE txn's write set: energy spend + position move
    + loot grant + fog mark (+ mine XP — patched to a no-award here)."""
    from sb.domain.mining import ops
    from sb.domain.games import xp as game_xp

    doubles = _Store()
    doubles.install(monkeypatch)

    async def no_award(conn, *, user_id, guild_id, game, action, now,
                       depth=0):
        return game_xp.GameXpAward(game, action, 0, 0, 0, 0, False)

    monkeypatch.setattr(game_xp, "award_in_txn", no_award)

    ctx = _ctx("north")
    out = run(ops._record_dig(None, ctx))
    after = out.after
    assert after["moved"] is True
    assert (after["x"], after["y"], after["depth"]) == (0, 1, 0)
    assert after["amount"] >= 1 and after["found"]
    assert after["message"] == (f"You dig **north** and mine "
                                f"**{after['amount']}× "
                                f"{after['found']}**!")
    kinds = [w[0] for w in doubles.writes]
    assert kinds[0] == "energy"                 # spend settles first
    assert ("position", 0, 1) in doubles.writes
    assert ("discovered", 0, 0, 1) in doubles.writes
    assert any(k == "grant" for k in kinds)
    assert "depth" not in kinds                  # lateral: no depth write
    assert ctx.params["_gxp"].action == "mine"


def test_record_dig_gearless_down_refuses_with_no_write(monkeypatch):
    """The light gate (record_descend posture): a gearless Deeper dig
    raises ValidatorError — no move, no loot, no energy spend."""
    import pytest

    from sb.domain.mining import ops
    from sb.kernel.interaction.errors import ValidatorError

    doubles = _Store()
    doubles.install(monkeypatch)
    with pytest.raises(ValidatorError):
        run(ops._record_dig(None, _ctx("down")))
    assert doubles.writes == []


def test_record_dig_out_of_energy_refuses_with_no_write(monkeypatch):
    import pytest

    from sb.domain.mining import ops
    from sb.kernel.interaction.errors import ValidatorError

    import time as _time

    doubles = _Store()
    # fresh stamp at (real) now → zero regen since, zero energy stored
    doubles.energy = (0, int(_time.time()))
    doubles.install(monkeypatch)
    with pytest.raises(ValidatorError):
        run(ops._record_dig(None, _ctx("north")))
    assert doubles.writes == []


def test_dig_op_is_registered_with_xp_emits():
    from sb.domain.mining import ops

    assert ops.DIG.op_key == "mining.dig"
    assert ops.DIG.audit_verb == "mining_grid_dug"
    assert ops.DIG.legs[0].handler.name == "mining.record_dig"
    assert ops.DIG in ops._OPS
    assert {e.event for e in ops.DIG.emits} == {"game_xp.awarded",
                                                "game_xp.level_up"}
