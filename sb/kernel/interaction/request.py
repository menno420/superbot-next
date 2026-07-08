"""The surface-agnostic request (frozen L0 spec 02 §3.1 + the absorption
batch). Kernel decision logic sees NO discord objects — the adapters
normalize everything here.

RC-12 LANDS HERE: `ActorRef.member_tier` (the pre-computed 6-tier ladder
string from `member_tier_from_member`, spec 04 §2 — computable from the
INTERACTION_CREATE payload, no privileged intent; spec 14 consumes it) and
the A-12/R-16 `role_ids: frozenset[int]` ride the same batch, alongside the
already-applied RC-18 `actor_type`. Field order: the four non-default fields
keep their positions; `actor_type`, `member_tier`, `role_ids` are trailing
defaulted fields (Gate-0 Group-2 pin, extended by A-12).

PIN-4: `Surface.MAINTENANCE` is the ONE background/headless member — 09
scheduler fires AND 11 sweep-repairs both classify under it (never a
per-sibling "scheduler"/"maintenance" split). RC-11: this interaction
`Surface` is NOT unified with the namespace `Surface` enum.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from typing import Mapping, Protocol, runtime_checkable

from sb.spec.outcomes import ReplyVisibility

__all__ = [
    "ActorRef",
    "ConfirmPrompt",
    "NLProvenance",
    "ResolveRequest",
    "Surface",
    "SurfaceResponder",
    "TargetRef",
]


class Surface(enum.Enum):
    SLASH = "slash"
    PREFIX = "prefix"
    COMPONENT = "component"
    MODAL = "modal"
    NL_INTENT = "nl_intent"
    NL_ORCHESTRATION = "nl_orchestration"
    MAINTENANCE = "maintenance"     # PIN-4/RC-19 — the ONE background member
    SETUP = "setup"                 # the wizard render surface (02 §3.3 fold-in)


@dataclass(frozen=True)
class ActorRef:
    """Normalized by the adapter (generalizes CommandAccessContext)."""

    user_id: int | None
    is_guild_operator: bool          # owner/administrator/manage_guild (shipped)
    is_bot_owner: bool               # is_platform_owner — the bootstrap-leg fact
    is_dm: bool
    actor_type: str = "user"         # RC-18: user | system | backfill | setup_delegate
    member_tier: str | None = None   # RC-12: pre-computed tier in the target guild
    role_ids: frozenset[int] = field(default_factory=frozenset)  # A-12/R-16


@dataclass(frozen=True)
class TargetRef:
    key: str                         # command name | "<panel_id>.<action_id>" (K1-reserved)
    spec: object                     # CommandSpec | PanelActionSpec | SelectorSpec
    # every spec carries authority_ref / enabled_when / reply_visibility /
    # defer_mode(*) / cooldown (§3.0, duck-read with the pinned defaults);
    # the ROUTABLE ref (route | handler | on_select) is read generically at
    # step 5. (*) frozen on PanelActionSpec, §3.0-added on the other two.


@dataclass(frozen=True)
class NLProvenance:
    """rung-3/4 only — feeds audit + did-you-mean privacy."""

    nl_text: str
    intent_key: str
    confidence: float
    orchestration_id: str | None     # links the steps of one rung-4 plan


@dataclass(frozen=True)
class ConfirmPrompt:
    """The kernel-owned confirm surface payload (02 §3.2 step 5): the
    control's custom_id encodes (target_key, confirm_token, request_id) —
    request_id doubles as the re-entry idempotency key."""

    target_key: str
    request_id: str
    challenge: object                # sb.spec.confirmation.Challenge
    prompt_text: str = "Are you sure?"
    timeout_s: int = 60


@dataclass(frozen=True)
class ResolveRequest:
    surface: Surface
    target: TargetRef
    actor: ActorRef
    guild_id: int | None
    channel_id: int | None
    args: Mapping[str, object]       # parsed/extracted, surface-normalized
    responder: "SurfaceResponder"    # the ack/reply PORT — never a raw discord object
    origin: object                   # opaque surface-native handle; kernel never inspects
    provenance: NLProvenance | None = None
    confirmed: bool = False          # True on the re-entrant confirm dispatch
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@runtime_checkable
class SurfaceResponder(Protocol):
    """The ack/reply port (defined by the kernel, implemented in
    adapters/discord — layer rule: kernel imports ports it defines)."""

    surface: Surface

    def is_acked(self) -> bool: ...
    def committed_visibility(self) -> ReplyVisibility | None: ...
    async def ack(self, *, ephemeral: bool) -> None: ...
    async def deny(self, message: str, *, ephemeral: bool) -> None: ...
    async def open_modal(self, modal_ref: object) -> None: ...
    async def open_confirm(self, prompt: ConfirmPrompt) -> None: ...
    async def render(self, result: object) -> None: ...
