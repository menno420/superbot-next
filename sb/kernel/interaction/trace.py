"""The dispatch-trace seam (frozen L0 spec 02 §3.5): `command.dispatched`,
`EventSpec(observability_only=True, owner_subsystem="kernel")` — the named
carve-out to the §2.8 owner rule. Distinct from and ADDITIVE to the
per-mutation `emit_audit_action` fired inside K7 — one command ⇒ one
dispatch-trace + zero-or-more mutation-audit rows.

Payload carries the RC-2/RC-5 transparency signal: `override_applied` /
`base_allowed`, DERIVED from the 10-field `AuthorityDecision`. Emitted
best-effort over the composition-root bus (observability_only — no outbox
row); always logged.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from sb.spec.events import EventSpec, FieldSpec, register_event_specs

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sb.kernel.authority.decision import AuthorityDecision
    from sb.kernel.interaction.request import ResolveRequest
    from sb.spec.outcomes import DenialReason

logger = logging.getLogger("sb.kernel.interaction.trace")

__all__ = ["EVT_COMMAND_DISPATCHED", "emit_dispatch_trace", "install_trace_bus"]

EVT_COMMAND_DISPATCHED = "command.dispatched"

COMMAND_DISPATCHED_SPEC = EventSpec(
    name=EVT_COMMAND_DISPATCHED,
    payload_schema=(
        FieldSpec("request_id", "str"),
        FieldSpec("surface", "str"),
        FieldSpec("command_key", "str"),
        FieldSpec("actor_id", "int | None"),
        FieldSpec("guild_id", "int | None"),
        FieldSpec("authority_ref", "str"),
        FieldSpec("lane", "str"),
        FieldSpec("override_applied", "bool"),
        FieldSpec("base_allowed", "bool"),
        FieldSpec("orchestration_id", "str | None", required=False),
        FieldSpec("outcome", "str"),
        FieldSpec("reason", "str"),
    ),
    owner_subsystem="kernel",          # the reserved observability owner
    observability_only=True,
)

register_event_specs([COMMAND_DISPATCHED_SPEC])

_bus: object | None = None


def install_trace_bus(bus: object) -> None:
    global _bus
    _bus = bus


def emit_dispatch_trace(req: "ResolveRequest", decision: "AuthorityDecision", *,
                        override_applied: bool, base_allowed: bool,
                        outcome: str, reason: "DenialReason",
                        note: str = "") -> None:
    """Fire-and-forget (observability only — never blocks or fails dispatch).
    The outcome/reason arrive back-filled (the render step calls this)."""
    payload = {
        "request_id": req.request_id,
        "surface": req.surface.value,
        "command_key": req.target.key,
        "actor_id": req.actor.user_id,
        "guild_id": req.guild_id,
        "authority_ref": decision.authority_ref,
        "lane": decision.lane.value,
        "override_applied": override_applied,
        "base_allowed": base_allowed,
        "orchestration_id": (req.provenance.orchestration_id
                             if req.provenance else None),
        "outcome": outcome,
        "reason": reason.value,
    }
    logger.info("command.dispatched %s", payload)
    if _bus is not None:
        try:
            coro = _bus.emit(EVT_COMMAND_DISPATCHED, **payload)
            if asyncio.iscoroutine(coro):
                asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            pass  # no running loop (sync test context) — the log line stands
        except Exception:  # noqa: BLE001
            logger.warning("trace bus emit failed", exc_info=True)
