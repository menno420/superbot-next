"""K8 — the interaction runtime (frozen L0 spec 02, post-absorption).

THE single `resolve(ResolveRequest) -> Result` chokepoint every surface
funnels through (slash · prefix · fuzzy · component · modal · nl), the
`from_exception` error envelope inside it, the ephemerality resolver, and
the `SurfaceResponder` port. The SPEC-02 ABSORPTION EDIT is applied
throughout (RC-2/3/4/5/12/13/14/15): 04's 10-field `AuthorityDecision` +
`Lane` are imported (no `AuthorityLane`), `owner_override` is threaded into
channel-access, `build_transparency_audit` + `TransparencySink` are named at
step 4, and `ActorRef` carries `member_tier` (RC-12) + `role_ids` (A-12) +
`actor_type` (RC-18).

The panel/presentation runtime (PanelRuntimeView, EmbedFrame, navigation,
generated settings panels, help-as-projection — canonical plan F-3.4) is the
explicit S9b follow-up: `OPEN_PANEL` dispatches through the installable
panel-engine port defined in `resolve.py`.
"""

from sb.kernel.interaction.errors import ErrorEnvelope, ValidatorError, from_exception
from sb.kernel.interaction.request import (
    ActorRef,
    NLProvenance,
    ResolveRequest,
    Surface,
    SurfaceResponder,
    TargetRef,
)
from sb.kernel.interaction.resolve import resolve
from sb.kernel.interaction.result import Result, lane_default, resolve_reply_visibility

__all__ = [
    "ActorRef",
    "ErrorEnvelope",
    "NLProvenance",
    "ResolveRequest",
    "Result",
    "Surface",
    "SurfaceResponder",
    "TargetRef",
    "ValidatorError",
    "from_exception",
    "lane_default",
    "resolve",
    "resolve_reply_visibility",
]
