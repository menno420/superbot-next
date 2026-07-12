"""Setup-lane channel-provisioning recovery (D-0077) — the create-channel
EFFECT leg's compensator class, defined AHEAD of the setup ops that will
reference it.

The D-0030 named successor slice armed the ChannelStateActions
create/delete surface (sb/domain/channel/service.py + the capture twin);
the setup/quicksetup flip lane declares the ops. The ruling
(docs/decisions.md D-0077): a setup-lane channel CREATE that runs as an
EFFECT leg AFTER a committed DB leg is compensated by DELETING the
created channel — id-guarded (only the exact channel id the create leg
stashed in ``ctx.params["_created_channel_id"]``), best-effort (a failed
delete degrades to an operator finding, never a raise), NotFound treated
as success (the port contract: already-gone IS the goal state — the
oracle's delete_setup_channel ``except discord.NotFound: return True``).
Oracle precedent for the class: disbot/services/ticket_mutation.py
compensates create-with-DB-follow-up by delete
(``await channel.delete(reason="Ticket row insert failed")``).

The oracle's own SETUP lane sequences the create BEFORE any DB write and
never rollback-deletes (its deletes are separate deliberate cleanup ops,
name-guarded) — an op that mirrors that sequencing (the Discord call
INSIDE the DB leg, the moderation.timeout posture) needs NO compensator.
This handler exists for the DB-first leg shape only; whenever the create
leg sits after a DB leg it MUST declare
``compensator=WorkflowRef("setup.compensate_create_channel")``.

No spec is declared here yet: declaring the setup compound op is the
flip lane's move (the setup/quicksetup goldens stay parked on D-0030/
trap-17 until then), so the compensator-invariant sweep
(tests/unit/workflow/test_compensator_invariant.py) picks this module up
the moment the first spec lands."""

from __future__ import annotations

import logging

from sb.kernel.workflow.context import LegOutcome, WorkflowContext
from sb.kernel.workflow.result import StepResult
from sb.spec.refs import WorkflowRef, workflow

__all__ = ["ensure_ops_refs"]

logger = logging.getLogger("sb.domain.setup")


@workflow("setup.compensate_create_channel")
async def _compensate_create_channel(conn, ctx: WorkflowContext) -> LegOutcome:
    """The create-channel compensator (fork E; conn=None): delete the
    channel the create leg minted, so Discord stops carrying a workspace
    the durable record refused. ID-GUARDED — only the exact id the leg
    stashed is touched (never a name lookup, never a session pointer:
    a stale pointer must not delete an operator's channel). BEST-EFFORT
    — a Discord-refused delete records an operator finding and the
    compensation still completes (the orphan channel is visible +
    harmless; the oracle's setup deletes are best-effort the same way).
    NotFound-as-success rides the ChannelStateActions.delete_channel
    port contract, not this handler."""
    del conn  # fork E runs compensators outside the txn
    cid = int(ctx.params.get("_created_channel_id", 0) or 0)
    if not cid:
        # the create leg never ran (or stashed nothing) — nothing to
        # withdraw; never guess at a channel to delete.
        return LegOutcome(
            step=StepResult(0, "compensate_create_channel", True),
            before={}, after={"compensated": "nothing"})
    from sb.domain.channel.service import active_actions

    deleted = True
    try:
        await active_actions().delete_channel(
            cid, reason="setup channel create compensated — a later leg failed")
    except Exception as exc:  # noqa: BLE001 — best-effort withdrawal
        deleted = False
        logger.warning("setup: compensating delete of channel %s failed: %s",
                       cid, exc)
        try:
            from sb.kernel.observability.findings import record_operator_finding

            record_operator_finding(
                source="workflow:setup.compensate_create_channel",
                severity="warning",
                summary=(f"compensating delete of created setup channel "
                         f"{cid} blocked — the channel is orphaned but "
                         f"harmless; delete it by hand or re-run setup"),
                detail="", correlation_id=None)
        except Exception:  # noqa: BLE001 — findings are observability only
            pass
    return LegOutcome(
        step=StepResult(0, "compensate_create_channel", True),
        before={}, after={"compensated": "create_channel",
                          "channel_id": cid, "deleted": deleted})


_REF_TABLE = (
    ("setup.compensate_create_channel", _compensate_create_channel),
)


def ensure_ops_refs() -> None:
    from sb.spec.refs import is_registered
    from sb.spec.refs import workflow as _workflow

    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
