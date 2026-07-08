"""The member-erasure executor (S11 — frozen L0 spec 10 §2.A class 12) +
the A-15 read-only export twin.

Completeness is STRUCTURAL, not audited by inspection:
(1) ENUMERATE — the registered StoreSpec inventory (sb.spec.versioning
    register_store — kernel constants now, manifest `stores` facets at the
    port bands), filtered `data_class != NONE`. check_data_lifecycle CI-reds
    any member-data store lacking data_class + erasure_ref, so no member-data
    store exists OUTSIDE this walk.
(2) DELETE vs TOMBSTONE — decided PER STORE, encoded in its `erasure_ref`
    (the executor stays store-agnostic): value/audit stores TOMBSTONE (scrub
    PII, keep the skeleton — R-3 "money/audit families retain"); non-value
    stores hard-DELETE (R-3 "message-dedup families prune").
(3) AUDITED + IDEMPOTENT per store — `run_ref(store.erasure_ref, ctx,
    conn=conn)` in 07 §3.2 external-conn mode (one central audit row on the
    executor's conn), each leg guarded by
    once(IdempotencyKey("privacy.erasure", guild_id,
         f"{store}:{subject_id}:{trigger_epoch}")) — a crash mid-walk RESUMES.
(4) PROVE COMPLETENESS — one terminal ErasureLegResult per enumerated store
    or `complete=False` + `unreached` (a durable, resumable, AUDITED partial,
    never a silent gap).

The container-snapshot copy leg (FJ §4 #11) is OUTSIDE this in-DB inventory —
it interlocks with the credential/backup concerns (specs 12/13); this
executor supplies the machine-walkable inventory those cuts erase against.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping

from sb.kernel.db.idempotency import IdempotencyKey, once, read_outcome, record_outcome
from sb.kernel.db.pool import transaction
from sb.kernel.observability.findings import record_operator_finding
from sb.kernel.workflow import engine as workflow_engine
from sb.kernel.workflow.context import WorkflowContext
from sb.spec.versioning import DataClass, StoreSpec, registered_stores

logger = logging.getLogger("sb.kernel.privacy.erasure")

__all__ = [
    "ErasureDisposition",
    "ErasureLegResult",
    "ErasureResult",
    "ErasureTrigger",
    "ExportResult",
    "install_export_reader",
    "reset_export_readers_for_tests",
    "run_erasure",
    "run_export",
]


class ErasureTrigger(str, enum.Enum):
    GUILD_LEAVE = "guild_leave"          # on_guild_remove ⇒ erase THAT guild's member rows (R-1)
    SUBJECT_REQUEST = "subject_request"  # a member/operator erasure request (R-2)


class ErasureDisposition(str, enum.Enum):
    ERASED = "erased"          # rows hard-DELETEd
    TOMBSTONED = "tombstoned"  # PII scrubbed in place, value/audit skeleton KEPT
    ABSENT = "absent"          # the store held no row for this subject (valid terminal)


@dataclass(frozen=True)
class ErasureLegResult:
    store: str
    disposition: ErasureDisposition
    rows_affected: int
    mutation_id: str


@dataclass(frozen=True)
class ErasureResult:
    complete: bool                       # True IFF every data_class!=NONE store terminal
    legs: tuple[ErasureLegResult, ...]
    unreached: tuple[str, ...] = ()      # failed legs ⇒ complete=False, RETRYABLE


def _member_data_stores() -> tuple[StoreSpec, ...]:
    return tuple(s for s in registered_stores() if s.data_class is not DataClass.NONE)


def _leg_from_result(store: StoreSpec, result: object) -> ErasureLegResult:
    """The erasure workflow reports its disposition through the result's
    `after` mapping ({"disposition": ..., "rows_affected": n}); fallback:
    derived from the store's value class (ledger/aggregate value stores
    tombstone; the rest erase), rows 0 ⇒ ABSENT."""
    after = getattr(result, "after", None)
    disposition = None
    rows = 0
    if isinstance(after, Mapping):
        raw = after.get("disposition")
        if raw:
            disposition = ErasureDisposition(str(raw))
        rows = int(after.get("rows_affected", 0) or 0)
    if disposition is None:
        if rows == 0:
            disposition = ErasureDisposition.ABSENT
        elif store.bears_value or store.checkpoint_class.value in ("ledger", "aggregate"):
            disposition = ErasureDisposition.TOMBSTONED
        else:
            disposition = ErasureDisposition.ERASED
    return ErasureLegResult(store=store.table, disposition=disposition,
                            rows_affected=rows,
                            mutation_id=str(getattr(result, "mutation_id", "")))


async def run_erasure(trigger: ErasureTrigger, *, guild_id: int,
                      subject_id: int | None, actor: object,
                      trigger_epoch: int = 0) -> ErasureResult:
    """The audited, idempotent, provably-complete walk (spec 10 §2.A)."""
    legs: list[ErasureLegResult] = []
    unreached: list[str] = []
    for store in _member_data_stores():
        if store.erasure_ref is None:   # unreachable under the fence; belt-and-braces
            unreached.append(store.table)
            continue
        key = IdempotencyKey(
            namespace="privacy.erasure", guild_id=guild_id,
            dedup_token=f"{store.table}:{subject_id or 0}:{trigger.value}:{trigger_epoch}")
        ctx = WorkflowContext(
            actor=actor, guild_id=guild_id, request_id=key.render(),
            params={"subject_id": subject_id, "guild_id": guild_id,
                    "trigger": trigger.value})
        try:
            async with transaction() as conn:
                if await once(key, conn=conn):
                    result = await workflow_engine.run_ref(
                        store.erasure_ref, ctx, conn=conn)
                    await record_outcome(key, result.outcome,
                                         result_ref=result.mutation_id, conn=conn)
                    legs.append(_leg_from_result(store, result))
                else:
                    prior = await read_outcome(key, conn=conn)
                    legs.append(ErasureLegResult(
                        store=store.table, disposition=ErasureDisposition.ABSENT,
                        rows_affected=0,
                        mutation_id=str(prior.result_ref) if prior and prior.result_ref
                        else "replay"))
        except Exception:  # noqa: BLE001 — a failed leg is a RESUMABLE partial
            logger.warning("erasure leg failed for %s", store.table, exc_info=True)
            unreached.append(store.table)
    complete = not unreached
    if not complete:
        record_operator_finding(
            source="privacy.erasure", severity="error",
            summary=f"erasure incomplete ({trigger.value}, guild {guild_id})",
            detail=f"unreached stores: {unreached} — re-fire to resume "
                   f"(per-store once() makes the walk idempotent)")
    return ErasureResult(complete=complete, legs=tuple(legs),
                         unreached=tuple(unreached))


# --- the A-15 read-only export twin ---------------------------------------------

# Per-store export reader port: (store, guild_id, subject_id) -> rows.
# Read-only — installed by each store's owning band; a store with no reader
# is reported, never silently skipped.
ExportReader = Callable[[StoreSpec, int, int | None], Awaitable[tuple[Mapping[str, Any], ...]]]

_export_readers: dict[str, ExportReader] = {}


def install_export_reader(table: str, reader: ExportReader) -> None:
    _export_readers[table] = reader


def reset_export_readers_for_tests() -> None:
    _export_readers.clear()


@dataclass(frozen=True)
class ExportResult:
    complete: bool
    rows: Mapping[str, tuple[Mapping[str, Any], ...]]   # table -> subject rows
    unreached: tuple[str, ...] = ()


async def run_export(*, subject_id: int, guild_ids: tuple[int, ...],
                     ) -> ExportResult:
    """The read-only twin of run_erasure (A-15): the subject's data across
    every member-data store, iterated ACCOUNT-LEVEL across guilds. Zero
    writes — no audit rows, no once() (idempotent by nature)."""
    rows: dict[str, list[Mapping[str, Any]]] = {}
    unreached: list[str] = []
    for store in _member_data_stores():
        reader = _export_readers.get(store.table)
        if reader is None:
            unreached.append(store.table)
            continue
        collected: list[Mapping[str, Any]] = []
        try:
            for guild_id in guild_ids:
                collected.extend(await reader(store, guild_id, subject_id))
        except Exception:  # noqa: BLE001
            logger.warning("export leg failed for %s", store.table, exc_info=True)
            unreached.append(store.table)
            continue
        rows[store.table] = collected
    return ExportResult(complete=not unreached,
                        rows={k: tuple(v) for k, v in rows.items()},
                        unreached=tuple(unreached))
