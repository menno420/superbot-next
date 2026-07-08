"""Platform-governance runtime mechanics (S15, frozen L0 spec 14 §2.B-§2.C).

Two latched operator signals riding ONE notice carrier (the operator-finding
seam) + two installable durable-latch ports (settings rows; the settings
band installs real readers/writers — defaults are in-memory so the
mechanics are live and honest before the port bands land):

1. `emit_degrade_notices` — the §2.B once-per-STATE-CHANGE dedup: persist
   the last-emitted degrade set under `platform.degrade_state`; a redeploy
   under the SAME denial does not re-fire (merge=deploy = minutes apart,
   Q-0193); only a change (new denial, or a denial cleared) fires.
   `/lifecycle` diag reads the LIVE markers, never the latch.

2. `evaluate_guild_cap` — the §2.C active lead-time alert: on
   GUILD_CREATE (+ a heartbeat belt-and-braces re-check) compare the guild
   count against the ordered thresholds (75, 90); each fires EXACTLY ONCE
   across restarts via a per-threshold durable latch
   (`platform.guildcap.<t>`) — a one-way lead-time signal, never an
   oscillating alarm. Sets the `guild_count` gauge.

The verification-application itself is an owner/ops milestone (PG-1) — the
signal exists so it fires with WEEKS of lead time, not reactively at the
~100-guild wall.
"""

from __future__ import annotations

from typing import Callable, Iterable

from sb.kernel.config import DegradedCapability
from sb.kernel.observability import metrics as _metrics
from sb.kernel.observability.findings import record_operator_finding

__all__ = [
    "GUILD_CAP_THRESHOLDS",
    "DEGRADE_STATE_KEY",
    "GUILD_CAP_LATCH_PREFIX",
    "emit_degrade_notices",
    "evaluate_guild_cap",
    "install_state_store",
    "reset_platform_governance_for_tests",
]

GUILD_CAP_THRESHOLDS: tuple[int, ...] = (75, 90)
DEGRADE_STATE_KEY = "platform.degrade_state"
GUILD_CAP_LATCH_PREFIX = "platform.guildcap."


# --- the durable latch port (settings rows; in-memory default) --------------------

_MEM: dict[str, str] = {}


def _mem_read(key: str) -> str | None:
    return _MEM.get(key)


def _mem_write(key: str, value: str) -> None:
    _MEM[key] = value


_READ: Callable[[str], str | None] = _mem_read
_WRITE: Callable[[str, str], None] = _mem_write


def install_state_store(read: Callable[[str], str | None],
                        write: Callable[[str, str], None]) -> None:
    """The settings band installs the durable (settings-row) latch store;
    until then the in-memory default holds (latches survive within a
    process, not across restarts — honest v1, noted in the ledger)."""
    global _READ, _WRITE
    _READ, _WRITE = read, write


def reset_platform_governance_for_tests() -> None:
    global _READ, _WRITE
    _MEM.clear()
    _READ, _WRITE = _mem_read, _mem_write


# --- §2.B: the degrade notice, once per state change -------------------------------

def _render_state(markers: Iterable[DegradedCapability]) -> str:
    return ",".join(sorted(m.intent for m in markers)) or "none"


def emit_degrade_notices(markers: tuple[DegradedCapability, ...]) -> bool:
    """Compare the CURRENT degrade set against the persisted one; emit ONE
    operator notice on change (including a restore — a cleared denial fires
    a 'capability restored' notice), then update the latch. Returns True
    iff a notice fired."""
    current = _render_state(markers)
    persisted = _READ(DEGRADE_STATE_KEY)
    if persisted == current:
        return False
    if markers:
        detail = "; ".join(
            f"{m.intent}: {', '.join(m.degrades)} disabled" for m in markers)
        record_operator_finding(
            source="platform", severity="warning",
            summary=f"privileged-intent degrade active: {current}",
            detail=f"{detail}. Slash/component surface fully serves "
                   f"(spec 14 §2.A); re-approval is picked up on the next "
                   f"deploy's boot.")
    elif persisted is not None:
        record_operator_finding(
            source="platform", severity="info",
            summary="privileged-intent capabilities restored",
            detail=f"previous degrade set: {persisted}")
    _WRITE(DEGRADE_STATE_KEY, current)
    return True


# --- §2.C: the guild-cap lead-time alert -------------------------------------------

def evaluate_guild_cap(guild_count: int) -> tuple[int, ...]:
    """The latched threshold check — call on GUILD_CREATE (primary) and the
    lifecycle heartbeat (belt-and-braces). Sets the `guild_count` gauge,
    fires each crossed threshold exactly once (durable latch), returns the
    thresholds fired THIS call."""
    registry = _metrics.active_registry()
    if registry is not None:
        try:
            registry.gauge("guild_count").set(guild_count)
        except Exception:  # noqa: BLE001 — observability only
            pass
    fired: list[int] = []
    for threshold in GUILD_CAP_THRESHOLDS:
        if guild_count < threshold:
            continue
        latch_key = f"{GUILD_CAP_LATCH_PREFIX}{threshold}"
        if _READ(latch_key) is not None:
            continue  # one-way signal: stays latched even if the count drops
        _WRITE(latch_key, "fired")
        record_operator_finding(
            source="platform", severity="warning",
            summary=f"approaching the unverified-bot guild cap "
                    f"({guild_count}/100)",
            detail=f"threshold {threshold} crossed — apply for Discord "
                   f"verification NOW (lead time to the ~100 wall; the "
                   f"application declares the message_content justification, "
                   f"spec 14 §2.C / PG-1).")
        fired.append(threshold)
    return tuple(fired)
