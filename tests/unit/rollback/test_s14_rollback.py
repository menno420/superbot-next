"""S14 — backup/DR/rollback: the rollback_class derivation, the resolved +
coverage fences, the reverse-import driver, the SB_VERIFY_BOOT rails
(frozen L0 spec 13 §2.2/§2.4/§2.5)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from sb.spec.refs import EngineRef
from sb.spec.versioning import (
    CheckpointClass,
    ForwardMapKind,
    RollbackClass,
    RollbackUnresolved,
    StoreSpec,
    derive_rollback_class,
    registered_stores,
    resolve_forward_map_kind,
)
from tools.check_rollback_disposition import check as fence_check
from tools.importer.reverse import (
    CUTOVER_FLIP_TS_KEY,
    LossManifest,
    build_loss_manifest,
    clear_reverse_importers_for_tests,
    ledger_reinsert_sql,
    register_reverse_importer,
    reverse_import,
    reverse_importer_coverage,
)

FLIP = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def _store(table="t", *, kind=None, bears_value=False,
           checkpoint=CheckpointClass.AGGREGATE, replay_intent=False):
    return StoreSpec(table=table, sole_writer=EngineRef("test"), retention="90d",
                     checkpoint_class=checkpoint, invariant_tag="test",
                     bears_value=bears_value, forward_map_kind=kind,
                     replay_intent=replay_intent)


# --- the derivation table (spec 13 §2.4b — mechanical) ----------------------------

class TestDerivation:
    def test_non_invertible_is_declared_loss(self):
        for kind in (ForwardMapKind.COLLAPSE, ForwardMapKind.NEW_ONLY,
                     ForwardMapKind.DROP):
            s = _store(kind=kind, bears_value=True)
            assert derive_rollback_class(s) is RollbackClass.DECLARED_LOSS

    def test_invertible_value_bearing_is_reverse_importable(self):
        for kind in (ForwardMapKind.NAME_STABLE, ForwardMapKind.RENAME):
            s = _store(kind=kind, bears_value=True,
                       checkpoint=CheckpointClass.LEDGER)
            assert derive_rollback_class(s) is RollbackClass.REVERSE_IMPORTABLE

    def test_invertible_non_value_is_declared_loss_by_posture(self):
        s = _store(kind=ForwardMapKind.NAME_STABLE, bears_value=False)
        assert derive_rollback_class(s) is RollbackClass.DECLARED_LOSS

    def test_replay_intent_narrows(self):
        s = _store(kind=ForwardMapKind.RENAME, bears_value=True, replay_intent=True)
        assert derive_rollback_class(s) is RollbackClass.REPLAY_INTENT

    def test_session_collapse_short_circuit_always_wins(self):
        s = _store(kind=ForwardMapKind.NAME_STABLE, bears_value=True,
                   checkpoint=CheckpointClass.SESSION)
        assert resolve_forward_map_kind(s) is ForwardMapKind.COLLAPSE
        assert derive_rollback_class(s) is RollbackClass.DECLARED_LOSS

    def test_retirement_derives_drop(self):
        s = _store(table="old_thing")
        assert (resolve_forward_map_kind(s, retired_tables=frozenset({"old_thing"}))
                is ForwardMapKind.DROP)

    def test_unresolved_raises(self):
        with pytest.raises(RollbackUnresolved):
            derive_rollback_class(_store(kind=None))


# --- the fences (spec 13 §2.5) ----------------------------------------------------

class TestFences:
    def setup_method(self):
        clear_reverse_importers_for_tests()

    def teardown_method(self):
        clear_reverse_importers_for_tests()

    def test_committed_kernel_stores_resolve(self):
        assert fence_check(stores=registered_stores(), covered=frozenset(),
                           retired_tables=frozenset()) == []

    def test_all_kernel_stores_are_declared_loss(self):
        # fresh-chain tables: no old-schema home => NEW_ONLY => DECLARED_LOSS
        for store in registered_stores():
            assert derive_rollback_class(store) is RollbackClass.DECLARED_LOSS

    def test_unresolved_store_red(self):
        problems = fence_check(stores=(_store(kind=None),), covered=frozenset(),
                               retired_tables=frozenset())
        assert any("rollback_class_unresolved" in p for p in problems)

    def test_coverage_gap_both_directions(self):
        rev = _store(table="economy_audit_log", kind=ForwardMapKind.NAME_STABLE,
                     bears_value=True, checkpoint=CheckpointClass.LEDGER)
        # derived REVERSE_IMPORTABLE but uncovered
        problems = fence_check(stores=(rev,), covered=frozenset(),
                               retired_tables=frozenset())
        assert any("no reverse importer registered" in p for p in problems)
        # covered but not derived
        problems = fence_check(stores=(_store(kind=ForwardMapKind.NEW_ONLY),),
                               covered=frozenset({"ghost_table"}),
                               retired_tables=frozenset())
        assert any("ghost_table" in p for p in problems)

    def test_replay_intent_widening_red(self):
        bad = _store(kind=ForwardMapKind.NEW_ONLY, bears_value=False,
                     replay_intent=True)
        problems = fence_check(stores=(bad,), covered=frozenset(),
                               retired_tables=frozenset())
        assert any("NARROWING override" in p for p in problems)


# --- the reverse-import driver (spec 13 §2.4c) -------------------------------------

class TestReverseImport:
    def setup_method(self):
        clear_reverse_importers_for_tests()

    def teardown_method(self):
        clear_reverse_importers_for_tests()

    def test_flip_ts_unset_stops(self):
        report = run(reverse_import((), old_conn=None, new_conn=None,
                                    cutover_flip_ts=None))
        assert report.stop_code == "cutover_flip_ts_unset"
        assert CUTOVER_FLIP_TS_KEY in (report.detail or "")

    def test_coverage_gap_stops(self):
        rev = _store(table="economy_audit_log", kind=ForwardMapKind.NAME_STABLE,
                     bears_value=True, checkpoint=CheckpointClass.LEDGER)
        report = run(reverse_import((rev,), old_conn=None, new_conn=None,
                                    cutover_flip_ts=FLIP))
        assert report.stop_code == "reverse_importer_coverage_gap"

    def test_full_run_buckets_and_imports(self):
        rev = _store(table="economy_audit_log", kind=ForwardMapKind.NAME_STABLE,
                     bears_value=True, checkpoint=CheckpointClass.LEDGER)
        replay = _store(table="xp_ledger", kind=ForwardMapKind.RENAME,
                        bears_value=True, replay_intent=True)
        lost_value = _store(table="fishing_state", kind=ForwardMapKind.COLLAPSE,
                            bears_value=True)
        lost_cfg = _store(table="bindings", kind=ForwardMapKind.NAME_STABLE,
                          bears_value=False)

        async def importer(store, *, old_conn, new_conn, flip_ts):
            assert flip_ts == FLIP
            return 42

        register_reverse_importer("economy_audit_log", importer)
        deltas = {"fishing_state": {"rows_lost": 7, "guilds_affected": 2,
                                    "per_subject": [(1, 10, 500), (2, 20, 30)]},
                  "bindings": {"rows_lost": 3, "guilds_affected": 1,
                               "per_subject": [(1, 10, 999)]}}
        report = run(reverse_import((rev, replay, lost_value, lost_cfg),
                                    old_conn=object(), new_conn=object(),
                                    cutover_flip_ts=FLIP, deltas=deltas))
        assert report.stop_code is None
        assert report.imported == {"economy_audit_log": 42}
        assert report.replay_intent == ("xp_ledger",)
        m1_tables = {r.store for r in report.loss.m1}
        assert m1_tables == {"fishing_state", "bindings"}
        # M2 only for VALUE-bearing declared-loss stores (bindings has none)
        assert all(r.store == "fishing_state" for r in report.loss.m2)
        assert len(report.loss.m2) == 2

    def test_ledger_reinsert_sql_shape(self):
        sql = ledger_reinsert_sql("economy_audit_log",
                                  ("mutation_id", "amount", "occurred_at"))
        assert "ON CONFLICT (mutation_id) DO NOTHING" in sql
        assert sql.startswith("INSERT INTO economy_audit_log")


# --- SB_VERIFY_BOOT rails (spec 13 §2.2c) ------------------------------------------

class TestVerifyBootRails:
    BASE = {
        "DISCORD_BOT_TOKEN_PRODUCTION": "x",
        "DATABASE_URL": "postgresql://u@localhost/db",
        "SB_DATA_PLANE": "test",
        "SB_TEST_DB_HOSTS": "localhost",
    }

    def test_verify_boot_requires_test_plane(self):
        from sb.kernel.config import StartupError, preflight
        env = dict(self.BASE)
        env.update({"SB_DATA_PLANE": "prod", "SB_VERIFY_BOOT": "true",
                    "SB_PROD_ATTEST": "tok", "RAILWAY_SERVICE_NAME": "worker",
                    "SB_INTENT_MSGCONTENT_OK": "true", "SB_INTENT_MEMBERS_OK": "true"})
        with pytest.raises(StartupError) as ei:
            preflight(env)
        assert any(e.env_var == "SB_VERIFY_BOOT" for e in ei.value.errors)

    def test_verify_boot_on_test_plane_ok(self):
        from sb.kernel.config import preflight
        env = dict(self.BASE, SB_VERIFY_BOOT="true")
        cfg = preflight(env)
        assert cfg.SB_VERIFY_BOOT is True

    def test_config_field_count_is_47(self):
        from sb.spec.config import CONFIG_FIELDS
        assert len(CONFIG_FIELDS) == 47  # 38 harvested + 9 operational (S14 +1)
