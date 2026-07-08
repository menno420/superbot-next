"""The narrow reverse importer's core (S14, frozen L0 spec 13 §2.4).

Semantics per derived `rollback_class` (§2.4c):
  REVERSE_IMPORTABLE / LEDGER    -> re-insert each post-`cutover_flip_ts` row
                                    into the OLD DB by `mutation_id`
                                    (`INSERT .. ON CONFLICT (mutation_id) DO
                                    NOTHING`) — never a replay of effects.
  REVERSE_IMPORTABLE / AGGREGATE -> copy the NEW ABSOLUTE aggregate value over
                                    the frozen OLD value, upsert-by-natural-key
                                    — never per-mutation deltas (double-apply).
  DECLARED_LOSS                  -> NOT imported; enters the M1/M2 loss manifest.
  REPLAY_INTENT                  -> a HUMAN-REVIEWED replay list; never auto.

Both write tiers are idempotent (mutation_id PK / absolute-value upsert), so
a re-run re-imports nothing. The per-store importer BODIES register here as
the port bands land their REVERSE_IMPORTABLE stores (economy_audit_log, the
XP/karma aggregates); `check_rollback_disposition` fences the covered set ==
the derived REVERSE_IMPORTABLE set — in BOTH directions (§2.5).

The delta boundary is `cutover_flip_ts` — the UTC instant the Railway
service flips the new worker live (§5.4 step 4 end), written ONCE by the
cutover-runbook flip op through the audited settings seam under
`CUTOVER_FLIP_TS_KEY`, never `os.getenv`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Mapping, Sequence

from sb.spec.versioning import RollbackClass, StoreSpec, derive_rollback_class

# The global kernel marker (settings key, global scope / guild_id=None).
CUTOVER_FLIP_TS_KEY = "platform.cutover_flip_ts"

# Machine-readable stop codes (mirrors run_verify_import's discipline).
STOP_CODES = (
    "reverse_importer_coverage_gap",   # covered set != derived REVERSE_IMPORTABLE set
    "cutover_flip_ts_unset",           # the delta boundary marker is missing
    "store_import_failed",             # a per-store importer raised
)


# --- the covered-set registry ----------------------------------------------------

# table -> async importer(store, old_conn, new_conn, flip_ts) -> rows_imported
_REVERSE_IMPORTERS: dict[str, Callable[..., Awaitable[int]]] = {}


def register_reverse_importer(table: str,
                              fn: Callable[..., Awaitable[int]]) -> None:
    prior = _REVERSE_IMPORTERS.get(table)
    if prior is not None and prior is not fn:
        raise ValueError(f"reverse importer for {table!r} registered twice")
    _REVERSE_IMPORTERS[table] = fn


def reverse_importer_coverage() -> frozenset[str]:
    """The covered table set — `check_rollback_disposition` fences this
    against the derived REVERSE_IMPORTABLE set, both directions."""
    return frozenset(_REVERSE_IMPORTERS)


def clear_reverse_importers_for_tests() -> None:
    _REVERSE_IMPORTERS.clear()


# --- write-tier SQL builders (the two idempotent shapes) --------------------------

def ledger_reinsert_sql(table: str, columns: Sequence[str],
                        key_column: str = "mutation_id") -> str:
    """LEDGER tier: re-insert by natural ledger key, conflict = no-op."""
    cols = ", ".join(columns)
    params = ", ".join(f"${i + 1}" for i in range(len(columns)))
    return (f"INSERT INTO {table} ({cols}) VALUES ({params}) "
            f"ON CONFLICT ({key_column}) DO NOTHING")


def aggregate_upsert_sql(table: str, natural_key: Sequence[str],
                         value_columns: Sequence[str]) -> str:
    """AGGREGATE tier: absolute-value upsert by natural key — writing the
    same absolute value twice is a no-op; robust to any audit_log gap."""
    cols = list(natural_key) + list(value_columns)
    params = ", ".join(f"${i + 1}" for i in range(len(cols)))
    sets = ", ".join(f"{c} = EXCLUDED.{c}" for c in value_columns)
    return (f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({params}) "
            f"ON CONFLICT ({', '.join(natural_key)}) DO UPDATE SET {sets}")


# --- the loss manifest (M1 owner sign-off + M2 per-subject ledger) ----------------

@dataclass(frozen=True)
class M1Row:
    """One DECLARED_LOSS store — the owner reviews and SIGNS this (SF-g
    signed-disposition rail; never a silent auto-drop)."""

    store: str
    rollback_class: str
    forward_map_kind: str
    rows_lost: int
    guilds_affected: int


@dataclass(frozen=True)
class M2Row:
    """One (guild, user, store) lost amount — the granularity the CUT-3
    comms/compensation hook needs (fed, not owned here)."""

    guild_id: int
    user_id: int
    store: str
    value_lost: Any


@dataclass(frozen=True)
class LossManifest:
    m1: tuple[M1Row, ...]
    m2: tuple[M2Row, ...]


def build_loss_manifest(
    declared_loss_stores: Sequence[StoreSpec],
    deltas: Mapping[str, Mapping[str, Any]],
) -> LossManifest:
    """`deltas[table]` = {"rows_lost": int, "guilds_affected": int,
    "per_subject": [(guild_id, user_id, value_lost), ...]} — computed by
    walking EACH STORE's post-flip delta (never the generic audit_log,
    which has no store column — §2.5). A non-value collapsed store
    contributes no M2 rows, only its M1 count."""
    m1: list[M1Row] = []
    m2: list[M2Row] = []
    for store in declared_loss_stores:
        d = deltas.get(store.table, {})
        kind = store.forward_map_kind.value if store.forward_map_kind else "derived"
        m1.append(M1Row(store=store.table, rollback_class="declared_loss",
                        forward_map_kind=kind,
                        rows_lost=int(d.get("rows_lost", 0)),
                        guilds_affected=int(d.get("guilds_affected", 0))))
        if store.bears_value:
            for guild_id, user_id, value in d.get("per_subject", ()):
                m2.append(M2Row(guild_id=guild_id, user_id=user_id,
                                store=store.table, value_lost=value))
    return LossManifest(m1=tuple(m1), m2=tuple(m2))


# --- the driver -------------------------------------------------------------------

@dataclass(frozen=True)
class ReverseImportReport:
    imported: Mapping[str, int]          # table -> rows/keys written to OLD
    replay_intent: tuple[str, ...]       # tables whose slice awaits human review
    loss: LossManifest
    stop_code: str | None = None
    detail: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


async def reverse_import(stores: Sequence[StoreSpec], *, old_conn, new_conn,
                         cutover_flip_ts: datetime | None,
                         deltas: Mapping[str, Mapping[str, Any]] | None = None,
                         retired_tables: frozenset[str] = frozenset(),
                         clock: Callable[[], datetime] | None = None,
                         ) -> ReverseImportReport:
    """The rollback-playbook step: bucket every store by its DERIVED
    rollback_class, run the registered importer for each REVERSE_IMPORTABLE
    store, list REPLAY_INTENT slices for human review, and emit the
    DECLARED_LOSS M1/M2 manifest. Machine-readable stop-codes, never a
    silent partial (the §5.2 importer discipline)."""
    started = clock() if clock else None
    if cutover_flip_ts is None:
        return ReverseImportReport(
            imported={}, replay_intent=(), loss=LossManifest((), ()),
            stop_code="cutover_flip_ts_unset",
            detail=f"write {CUTOVER_FLIP_TS_KEY} via the audited settings seam "
                   f"at the flip (spec 13 §2.4a)", started_at=started)

    buckets: dict[RollbackClass, list[StoreSpec]] = {c: [] for c in RollbackClass}
    for store in stores:
        buckets[derive_rollback_class(store, retired_tables=retired_tables)].append(store)

    reverse_set = {s.table for s in buckets[RollbackClass.REVERSE_IMPORTABLE]}
    covered = reverse_importer_coverage()
    if reverse_set != covered:
        return ReverseImportReport(
            imported={}, replay_intent=(), loss=LossManifest((), ()),
            stop_code="reverse_importer_coverage_gap",
            detail=f"derived={sorted(reverse_set)} covered={sorted(covered)}",
            started_at=started)

    imported: dict[str, int] = {}
    for store in buckets[RollbackClass.REVERSE_IMPORTABLE]:
        try:
            imported[store.table] = await _REVERSE_IMPORTERS[store.table](
                store, old_conn=old_conn, new_conn=new_conn,
                flip_ts=cutover_flip_ts)
        except Exception as exc:  # noqa: BLE001 — surfaced as a stop-code
            return ReverseImportReport(
                imported=imported, replay_intent=(), loss=LossManifest((), ()),
                stop_code="store_import_failed",
                detail=f"{store.table}: {exc}", started_at=started)

    loss = build_loss_manifest(buckets[RollbackClass.DECLARED_LOSS], deltas or {})
    return ReverseImportReport(
        imported=imported,
        replay_intent=tuple(sorted(s.table for s in buckets[RollbackClass.REPLAY_INTENT])),
        loss=loss, started_at=started,
        finished_at=clock() if clock else None)
