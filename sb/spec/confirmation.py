"""ConfirmationSpec — the manifest confirmation leaf (design-spec §2.7,
frozen; spec 07 §2 homes it here as a K1/K2-readable spec leaf, NOT a K7
kernel type — `sb.kernel.workflow.result` re-exports it).

Read at compile time by 01 P6 (destructive/typed-challenge rules) and by the
K7 `audit_completeness` fence (`op.reversibility == IRREVERSIBLE ⇒
confirmation is not None`); at runtime by the K8 resolver's step-5 confirm
gate and K7's headless confirm backstop (spec 07 §3.3 step 2 — presence, not
reversibility). Stdlib-only leaf.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Literal

from sb.spec.roles import register_field_roles

__all__ = ["Challenge", "ConfirmationSpec"]


class Challenge(enum.Enum):
    """The confirm round-trip mechanism (design-spec §2.7: typed for
    irreversible)."""

    BUTTON = "button"
    TYPED_PHRASE = "typed_phrase"
    TYPED_HASH = "typed_hash"


@dataclass(frozen=True)
class ConfirmationSpec:
    """Design-spec §2.7, verbatim field set. `re_check_actor` is frozen
    `Literal[True]` — confirmation ALWAYS re-resolves authority (satisfied
    structurally by the resolver's confirm-as-second-dispatch, 02 §3.2)."""

    reversibility: str                       # [S] shipped constant (REVERSIBLE|COMPENSATABLE|IRREVERSIBLE)
    challenge: Challenge = Challenge.BUTTON  # [S] typed_* for irreversible (P6 rule)
    timeout_s: int = 60                      # [S]
    re_check_actor: Literal[True] = True     # [S] FROZEN True
    snapshot_before: bool = True             # [S] before-state into the audit payload


register_field_roles(
    "ConfirmationSpec",
    reversibility="S", challenge="S", timeout_s="S",
    re_check_actor="S", snapshot_before="S",
)
