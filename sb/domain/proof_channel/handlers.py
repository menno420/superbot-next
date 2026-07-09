"""Proof-channel handlers + panel (band 5) — the shipped prize command
family and the _PrizeManagerView as declared grammar (G-10 modal for the
timed grant)."""

from __future__ import annotations

from dataclasses import dataclass

from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["Reply", "ensure_handler_refs", "ensure_panel_refs",
           "install_proof_panels", "prize_hub_spec"]


@dataclass(frozen=True)
class Reply:
    outcome: str
    user_message: str


def _ctx_from_req(req, params: dict):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=req.actor, guild_id=int(req.guild_id or 0),
        request_id=req.request_id, confirmed=req.confirmed, params=params)


def _member_token(argv) -> int | None:
    for t in argv:
        s = str(t).strip("<@!>")
        if s.isdigit() and len(s) >= 15:
            return int(s)
    return None


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("proof_channel.grant")):
        return

    @handler("proof_channel.grant")
    async def grant(req) -> Reply:
        """+prize @winner — exclusive access to the proof channel."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        winner = req.args.get("winner_id") or _member_token(argv)
        if not winner:
            return Reply(BLOCKED, "Usage: `+prize @winner`")
        result = await engine.run(
            WorkflowRef("proof_channel.grant_access"),
            _ctx_from_req(req, {"winner_id": int(winner)}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or
                         "Could not grant proof-channel access.")
        after = (result.after or {}).get("record", {})
        return Reply(SUCCESS, f"<@{winner}> has been granted access to "
                              f"<#{after.get('channel_id', 0)}>!")

    @handler("proof_channel.timed_grant")
    async def timed_grant(req) -> Reply:
        """timedprize @winner <minutes> — auto-unlocks (durable, bug #8)."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        winner = req.args.get("winner_id") or _member_token(argv)
        minutes = req.args.get("duration")
        if minutes is None:
            digits = [str(t) for t in argv if str(t).isdigit()
                      and len(str(t)) < 15]
            minutes = int(digits[0]) if digits else None
        if not winner or not minutes or int(minutes) <= 0:
            return Reply(BLOCKED, "Usage: `timedprize @winner <minutes>`")
        result = await engine.run(
            WorkflowRef("proof_channel.grant_access"),
            _ctx_from_req(req, {"winner_id": int(winner),
                                "duration_minutes": int(minutes)}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or
                         "Could not grant timed access.")
        after = (result.after or {}).get("record", {})
        return Reply(SUCCESS,
                     f"<@{winner}> has access to "
                     f"<#{after.get('channel_id', 0)}> for {minutes} "
                     f"minute(s) — auto-unlocks at "
                     f"{after.get('unlock_at', '?')}.")

    @handler("proof_channel.end")
    async def end(req) -> Reply:
        """-prize — end the session, channel read-only again."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        result = await engine.run(
            WorkflowRef("proof_channel.end_access"),
            _ctx_from_req(req, {"reason": "manual end"}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or
                         "Could not end the prize session.")
        after = (result.after or {}).get("record", {})
        return Reply(SUCCESS, f"<#{after.get('channel_id', 0)}> is now "
                              "read-only for everyone.")

    @handler("proof_channel.status")
    async def status(req) -> Reply:
        """prizestatus — DB-truth lock state (live overwrites render is
        the adapter's presentation)."""
        from sb.domain.proof_channel import service, store

        gid = int(req.guild_id or 0)
        cid = await service.bound_proof_channel(gid)
        if not cid:
            return Reply(BLOCKED,
                         "Channel '#proof' not bound. Bind `proof_channel` "
                         "in settings (or create #proof).")
        lock = await store.get_lock(gid, cid)
        if lock is None:
            return Reply(SUCCESS, f"<#{cid}>: no active timed prize lock.")
        return Reply(SUCCESS,
                     f"<#{cid}>: locked for <@{lock['winner_id']}> until "
                     f"{lock['unlock_at']}.")


def _register_task_fire() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("proof_channel.lock_reconcile_fire")):
        return

    @handler("proof_channel.lock_reconcile_fire")
    async def lock_reconcile_fire(ctx) -> str:
        """The proof:lock_reconcile sweep body (bug #8 durable timers)."""
        from sb.domain.proof_channel.service import reconcile_due_locks

        resolved = await reconcile_due_locks()
        return f"resolved={resolved}"


# --- panel ------------------------------------------------------------------------

def prize_hub_spec():
    from sb.spec.panels import (
        ActionStyle,
        Audience,
        EmbedFrameSpec,
        FieldsBlock,
        FooterMode,
        LayoutSpec,
        ModalFieldSpec,
        ModalSpec,
        NavigationSpec,
        PageSpec,
        PanelActionSpec,
        PanelSpec,
        ResultRender,
        TextBlock,
    )
    from sb.spec.refs import ProviderRef, WorkflowRef, is_registered, provider

    ref = ProviderRef("proof_channel.status_overview")
    if not is_registered(ref):
        @provider("proof_channel.status_overview")
        async def status_overview(ctx: object):
            from sb.domain.proof_channel import service, store

            gid = int(getattr(ctx, "guild_id", 0) or 0)
            cid = await service.bound_proof_channel(gid)
            if not cid:
                return (("Channel", "*(unbound — bind `proof_channel`)*"),)
            lock = await store.get_lock(gid, cid)
            state = (f"locked for <@{lock['winner_id']}> until "
                     f"{lock['unlock_at']}" if lock else "no timed lock")
            return (("Channel", f"<#{cid}>"), ("State", state))

    return PanelSpec(
        panel_id="proof_channel.hub",
        subsystem="proof_channel",
        title="🏆 Prize Channel Manager",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(TextBlock("Grant winners exclusive proof-channel access — "
                        "manual or timed (auto-unlock survives restarts)."),
              FieldsBlock(provider=ref)),
        actions=(
            PanelActionSpec(
                action_id="prize_grant", label="Grant", emoji="🎁",
                style=ActionStyle.SUCCESS, audience_tier="staff",
                handler=WorkflowRef("proof_channel.grant_access"),
                modal=ModalSpec(
                    modal_id="proof_channel.grant_form",
                    title="Grant prize access",
                    fields=(ModalFieldSpec(field_id="winner_id",
                                           label="Winner user id",
                                           required=True),)),
            ),
            PanelActionSpec(
                action_id="prize_timed", label="Timed", emoji="⏱️",
                style=ActionStyle.PRIMARY, audience_tier="staff",
                handler=WorkflowRef("proof_channel.grant_access"),
                modal=ModalSpec(
                    modal_id="proof_channel.timed_form",
                    title="Timed prize access",
                    fields=(
                        ModalFieldSpec(field_id="winner_id",
                                       label="Winner user id", required=True),
                        ModalFieldSpec(field_id="duration_minutes",
                                       label="Duration (minutes)",
                                       required=True),
                    )),
            ),
            PanelActionSpec(
                action_id="prize_end", label="End", emoji="🔒",
                style=ActionStyle.DANGER, audience_tier="staff",
                handler=WorkflowRef("proof_channel.end_access")),
            PanelActionSpec(
                action_id="prize_refresh", label="Refresh", emoji="🔄",
                audience_tier="staff",
                handler=PanelRefLocal(),
                result_render=ResultRender.REFRESH_PANEL),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("prize_grant", "prize_timed", "prize_end", "prize_refresh"),
        )),)),
    )


def PanelRefLocal():
    from sb.spec.refs import PanelRef

    return PanelRef("proof_channel.hub")


def install_proof_panels():
    from sb.kernel.panels.registry import register_panel

    spec = prize_hub_spec()
    try:
        return (register_panel(spec),)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return (spec,)
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef, is_registered, panel

    if not is_registered(PanelRef("proof_channel.hub")):
        @panel("proof_channel.hub")
        def _factory():
            return prize_hub_spec()


def ensure_handler_refs() -> None:
    _register()
    _register_task_fire()


_register()
_register_task_fire()
