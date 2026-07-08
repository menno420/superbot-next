"""Version-extended StoreSpec grammar tests (frozen L0 spec 09 §3.2)."""

from __future__ import annotations

from sb.spec.refs import EngineRef
from sb.spec.versioning import (
    CheckpointClass,
    StoreSpec,
    VersionedRow,
    VersionPolicy,
)


def test_enums_verbatim() -> None:
    assert {c.value for c in CheckpointClass} == {"ledger", "aggregate", "session"}
    assert {p.value for p in VersionPolicy} == {
        "upcast", "reject_and_preserve", "drop"}


def test_storespec_defaults_are_non_destructive() -> None:
    spec = StoreSpec(
        table="event_outbox",
        sole_writer=EngineRef("sb.kernel.outbox"),
        retention="delivered:7d;dead:90d",
        checkpoint_class=CheckpointClass.LEDGER,
        invariant_tag="INV-OUTBOX-SOLE-WRITER",
    )
    assert spec.payload_version == 1
    assert spec.bears_value is False
    assert spec.version_policy is VersionPolicy.REJECT_AND_PRESERVE
    assert spec.active_rows_ref is None
    assert spec.compensation_ref is None


def test_versioned_row_shape() -> None:
    row = VersionedRow(row_id="42", version=1, payload={"bet": 100}, guild_id=7)
    assert row.payload["bet"] == 100
    assert row.guild_id == 7


def test_outbox_store_declaration() -> None:
    from sb.kernel.outbox.store import OUTBOX_STORE

    assert OUTBOX_STORE.table == "event_outbox"
    assert OUTBOX_STORE.checkpoint_class is CheckpointClass.LEDGER  # the ENUM, not "ledger"
    assert OUTBOX_STORE.bears_value is False
    assert OUTBOX_STORE.version_policy is VersionPolicy.REJECT_AND_PRESERVE
    assert OUTBOX_STORE.reader_domains == ("operator_dashboard",)
