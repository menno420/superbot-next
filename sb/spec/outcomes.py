"""The result-grammar leaf (K6, frozen L0 spec 02 §2/§3.6 + shared-vocab §7.1 — RC-6).

Dependency-free (stdlib only). Home of:

  - the frozen §2.7 outcome constants, re-exported VERBATIM from the shipped
    grounding (`disbot/services/lifecycle/contracts.py:48-52` — source wins,
    Q-0120): ``SUCCESS/PARTIAL/BLOCKED/DECLINED/DISCORD_FAILED`` with the
    shipped lowercase VALUES, so the golden harness reads new-as-old;
  - ``OUTCOMES`` — the closed vocabulary tuple (`record_outcome` validates
    against it; the K3 idempotency layer imports it from HERE — re-homed at
    S7, the DB-layer tuple was the pre-S7 mirror);
  - ``ErrorClass`` / ``DenialReason`` / ``ReplyVisibility`` / ``DeferMode``.

Placement: spec 04 §11's K6 recommendation won over spec 02 §11's K7 (the one
§11 disagreement — build-order §7), so ``kernel/authority`` (K6) can import
``DenialReason`` without forward-referencing K7. The ``Lane`` enum does NOT
live here — it is ``sb.spec.authority.Lane`` (RC-3: 04's ``Lane`` wins; 02's
``AuthorityLane`` is dropped). ``from_exception`` / ``Result`` /
``resolve_reply_visibility`` are K8 runtime (spec 02 §3.3/§3.4/§3.6), landed
at S9 in ``sb/kernel/interaction/`` — this leaf owns only the grammar.
"""

from __future__ import annotations

import enum

__all__ = [
    "BLOCKED",
    "DECLINED",
    "DISCORD_FAILED",
    "OUTCOMES",
    "PARTIAL",
    "SUCCESS",
    "DeferMode",
    "DenialReason",
    "ErrorClass",
    "ReplyVisibility",
]

# ---------------------------------------------------------------------------
# The frozen §2.7 outcome vocabulary — shipped constants VERBATIM
# (`services/lifecycle/contracts.py:48-52`). A partial Discord batch is never
# a transaction. NO sixth constant may ever be added (spec 02 §8 fork 1: the
# {user_error, denied, transient, bug} nuance lives in ErrorClass + reason).
# ---------------------------------------------------------------------------

SUCCESS = "success"                # every step applied
PARTIAL = "partial"                # some steps applied, some failed
BLOCKED = "blocked"                # authority/feasibility — nothing attempted
DECLINED = "declined"              # confirmation required, not given
DISCORD_FAILED = "discord_failed"  # every attempted step failed at the API

OUTCOMES: tuple[str, ...] = (SUCCESS, PARTIAL, BLOCKED, DECLINED, DISCORD_FAILED)


class ErrorClass(enum.Enum):
    """Whose fault a dispatch failure was (spec 02 §3.3)."""

    NONE = "none"
    USER_ERROR = "user_error"
    DENIED = "denied"
    TRANSIENT = "transient"
    BUG = "bug"


class DenialReason(enum.Enum):
    """The fine-grained machine reason (spec 02 §3.6; exactly 12 members —
    frozen-l0-grammar Group 3). ``CHANNEL`` covers both shipped denials
    ``CHANNEL_NOT_ALLOWED`` and ``COMMANDS_DISABLED``, distinguished by
    ``ChannelAccessDecision.detail`` (RC-13); a distinct ``COMMANDS_DISABLED``
    member stays optional-additive (spec 04 §9).
    """

    ALLOWED = "allowed"
    DRAINING = "draining"
    AUTHORITY = "authority"
    DISABLED = "disabled"
    VISIBILITY = "visibility"
    CHANNEL = "channel"
    USER_ERROR = "user_error"
    COOLDOWN = "cooldown"
    AI_THROTTLE = "ai_throttle"
    NOT_FOUND = "not_found"
    CONFIRM_DECLINED = "confirm_declined"
    DISPATCH_ERROR = "dispatch_error"


class ReplyVisibility(enum.Enum):
    """How a dispatch reply renders (spec 02 §3.4, T2-17)."""

    EPHEMERAL = "ephemeral"
    PUBLIC = "public"
    SILENT = "silent"


class DeferMode(enum.Enum):
    """ACK-boundary defer behavior (spec 02 §3.1; frozen [S] on
    PanelActionSpec, optional [S] on CommandSpec/SelectorSpec per §3.0)."""

    AUTO = "auto"
    MODAL = "modal"
    NONE = "none"
