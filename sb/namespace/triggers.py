"""Custom-trigger set-time validation (frozen L0 spec 03 §3.3; Q-0225, T2-12).

The sole runtime consumer of `is_reserved`. Custom triggers stay ADDITIVE at
runtime (the union rule — never K1's concern); this gates set-time only, so a
guild can never register a word that shadows a reserved command, a tombstone,
or a common word. A word equal to a SUBCOMMAND name is available (subcommand
names are not bare-word invokable).
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.namespace.index import ReservationIndex
from sb.namespace.kinds import NamespaceKind, Origin
from sb.namespace.records import ReservationHit


@dataclass(frozen=True)
class TriggerAvailability:
    available: bool
    reason: str | None                 # "reserved_command"|"tombstoned"|"banned_common_word"|"too_short"|None
    conflict: ReservationHit | None    # the blocking record when available=False


def check_trigger(word: str, *, index: ReservationIndex, min_len: int) -> TriggerAvailability:
    """ONE lookup against the real is_reserved API, then branch on hit.origin.

    Common-word bans are stored kind="command", origin="ban" (spec 03 §3.7),
    so a single COMMAND lookup covers reserved commands, tombstones AND bans;
    the origin disambiguates the reason.
    """
    w = word.casefold()
    if len(w) < min_len:
        return TriggerAvailability(False, "too_short", None)

    hit = index.is_reserved(w, NamespaceKind.COMMAND, surface=None)  # both surfaces, top-level
    if hit is None:
        return TriggerAvailability(True, None, None)

    reason = {
        Origin.BAN: "banned_common_word",
        Origin.TOMBSTONE: "tombstoned",
        Origin.MANIFEST: "reserved_command",
        Origin.LEGACY: "reserved_command",
    }[hit.origin]
    return TriggerAvailability(False, reason, hit)
