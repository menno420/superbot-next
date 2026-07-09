"""PROOF_CHANNEL subsystem manifest (band 5) — the shipped prize-claim
family verbatim (cogs/proof_channel_cog.py): +prize / -prize /
prizestatus / prizemenu / timedprize, the _PrizeManagerView hub, the
bug-#8 durable timed-lock rows + the proof:lock_reconcile sweep, and the
Q-0064 proof_channel binding (the schemas.py declaration — the literal
'#proof' name lookup stays the live adapter's compatibility fallback).
"""

from __future__ import annotations

from sb.domain.proof_channel import handlers as _handlers
from sb.domain.proof_channel.handlers import install_proof_panels
from sb.domain.proof_channel.ops import register_ops
from sb.domain.proof_channel.store import PROOF_LOCKS_STORE
from sb.kernel.scheduler.due_queue import declare_task
from sb.spec.commands import CommandKind, CommandSpec, CooldownSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef
from sb.spec.scheduler import Interval, ManagedTaskSpec, TaskDurability
from sb.spec.settings import BindingKind, BindingSpec


def _cmd(name: str, route, *, summary: str, usage: str,
         cooldown: CooldownSpec | None = None) -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX, route=route,
                       audience_tier="staff", capability="proof_channel",
                       cooldown=cooldown, summary=summary, usage=usage)


_COMMANDS = (
    _cmd("+prize", HandlerRef("proof_channel.grant"),
         summary="Grant a winner exclusive access to the proof channel.",
         usage="+prize @winner"),
    _cmd("-prize", HandlerRef("proof_channel.end"),
         summary="End the prize session — proof channel read-only again.",
         usage="-prize"),
    _cmd("prizestatus", HandlerRef("proof_channel.status"),
         summary="Show the proof channel's current lock state.",
         usage="!prizestatus"),
    _cmd("prizemenu", PanelRef("proof_channel.hub"),
         cooldown=CooldownSpec(rate=2, per_s=10),
         summary="Open the interactive prize channel management panel.",
         usage="!prizemenu"),
    _cmd("timedprize", HandlerRef("proof_channel.timed_grant"),
         summary="Grant timed access; auto-unlocks after N minutes "
                 "(survives restarts).",
         usage="timedprize @winner <minutes>"),
)

_SETTINGS = (
    BindingSpec(name="proof_channel", kind=BindingKind.CHANNEL,
                hint="Channel used for prize-claim sessions (`+prize` / "
                     "`timedprize` lock it to the winner). When bound it "
                     "takes precedence over the legacy lookup of a channel "
                     "literally named `proof`."),
)

#: bug #8: the durable auto-unlock — restart-safe minute-granularity sweep.
LOCK_RECONCILE_TASK = declare_task(ManagedTaskSpec(
    name="proof:lock_reconcile",
    trigger=Interval(seconds=60),
    handler=HandlerRef("proof_channel.lock_reconcile_fire"),
    durability=TaskDurability.IN_MEMORY,
))

MANIFEST = SubsystemManifest(
    key="proof_channel",
    version=1,
    commands=_COMMANDS,
    panels=install_proof_panels(),
    settings=_SETTINGS,
    stores=(PROOF_LOCKS_STORE,),
    events=(),
    capabilities=(),
)

register_ops()


def _ensure_refs() -> None:
    from sb.domain.proof_channel import ops as _ops
    from sb.domain.proof_channel import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _handlers.ensure_handler_refs()
    _handlers.ensure_panel_refs()
    register_ops()
    install_proof_panels()


ENSURE_REFS = _ensure_refs
