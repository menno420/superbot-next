"""Proof-channel handlers + panel (band 5) — the shipped prize command
family and the _PrizeManagerView as declared grammar (G-10 modal for the
timed grant)."""

from __future__ import annotations


from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs", "ensure_panel_refs",
           "install_proof_panels", "prize_hub_spec"]


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
            # shipped copy verbatim (cogs/proof_channel_cog.py; goldens/
            # proof_channel/sweep_prizestatus pins the byte — the same
            # guard literal ops._resolve_channel carries).
            return Reply(BLOCKED, "Channel '#proof' not found.")
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

#: the shipped footer literal (proof_channel_cog.py build_embed
#: ``set_footer``) — outside FooterMode's none/subsystem/provenance
#: vocabulary, hence the renderer_override below (the cleanup/
#: server_management/ux_lab footer precedent);
#: goldens/proof_channel/sweep_prizemenu.json pins the byte.
_HUB_FOOTER = "Use buttons below to manage prize access."

#: the shipped no-channel branch copy (build_embed's ``else`` arm),
#: verbatim — the golden pins the byte.
_HUB_NO_CHANNEL = "⚠️ No `#proof` channel found. Create one first."


def prize_hub_spec():
    from sb.spec.panels import (
        ActionStyle,
        Audience,
        EmbedFrameSpec,
        FooterMode,
        LayoutSpec,
        ModalFieldSpec,
        ModalSpec,
        NavigationSpec,
        PageSpec,
        PanelActionSpec,
        PanelSpec,
        ResultRender,
    )
    from sb.spec.outcomes import DeferMode
    from sb.spec.refs import HandlerRef, WorkflowRef

    return PanelSpec(
        panel_id="proof_channel.hub",
        subsystem="proof_channel",
        title="🏆 Prize Channel Manager",
        audience=Audience.INVOKER,
        # the shipped accent — ECONOMY_COLOR == discord.Color.gold()
        # (goldens/proof_channel/sweep_prizemenu pins 15844367).
        frame=EmbedFrameSpec(style_token="gold",
                             footer_mode=FooterMode.NONE),
        # no declared body: the shipped build_embed description is
        # STATE-dependent (Managing <#ch> / the no-channel warning) —
        # the renderer_override below supplies it (see justification).
        actions=(
            # the shipped _PrizeManagerView buttons — emoji IN the labels
            # (discord.ui.button(label="🏆 Grant Access", ...)), verbatim.
            PanelActionSpec(
                action_id="prize_grant", label="🏆 Grant Access",
                style=ActionStyle.SUCCESS, audience_tier="staff",
                # the shipped click opened _PrizeWinnerModal (send_modal)
                # — G-10: the form issues on open, the workflow runs on
                # submit (the xp givexp/resetxp posture; codex on #145 —
                # default AUTO would dispatch grant_access empty).
                defer_mode=DeferMode.MODAL,
                handler=WorkflowRef("proof_channel.grant_access"),
                modal=ModalSpec(
                    modal_id="proof_channel.grant_form",
                    title="Grant prize access",
                    fields=(ModalFieldSpec(field_id="winner_id",
                                           label="Winner user id",
                                           required=True),)),
            ),
            PanelActionSpec(
                action_id="prize_timed", label="⏱️ Timed Access",
                style=ActionStyle.PRIMARY, audience_tier="staff",
                # shipped: the _PrizeWinnerModal(timed=True) →
                # _TimedPrizeModal chain, collapsed to ONE declared form
                # (G-10; same defer posture as prize_grant).
                defer_mode=DeferMode.MODAL,
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
                action_id="prize_end", label="🔒 End Session",
                style=ActionStyle.DANGER, audience_tier="staff",
                handler=WorkflowRef("proof_channel.end_access")),
            PanelActionSpec(
                action_id="prize_refresh", label="🔄 Refresh Status",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                handler=PanelRefLocal(),
                result_render=ResultRender.REFRESH_PANEL),
        ),
        # the shipped view carried ONLY its own buttons (no nav row; a
        # ctx-bound timeout view) — the golden pins exactly two component
        # rows (the cleanup.words / general-menu precedent).
        navigation=NavigationSpec(show_help=False, show_home=False),
        # shipped _PrizeManagerView is an ephemeral timeout view with
        # view-local button decorators (no persistent custom_ids) —
        # session lifecycle: run-minted ids (<cid:1>..<cid:4>), never in
        # panel_anchors (the golden pins the no-anchor-row delta).
        session_lifecycle=True,
        renderer_override=HandlerRef("proof_channel.render_hub"),
        justification=(
            "the shipped hub embed's description is STATE-dependent "
            "(proof_channel_cog.py build_embed: 'Managing {ch.mention}' "
            "when the proof channel resolves, the '⚠️ No `#proof` channel "
            "found. Create one first.' warning otherwise) and its footer "
            "is the literal 'Use buttons below to manage prize access.' "
            "(set_footer) — both outside the grammar's static-TextBlock/"
            "FooterMode vocabulary; goldens/proof_channel/"
            "sweep_prizemenu.json pins both bytes (the cleanup-hub "
            "precedent). The override delegates to the grammar renderer "
            "and adjusts ONLY those two surfaces (description + footer); "
            "actions, layout and frame stay declared. The shipped "
            "bound-branch 'Current Permissions' field renders LIVE "
            "channel overwrites (_format_overwrites(ch.overwrites)) — a "
            "Discord read with no capture twin and no pinning golden; it "
            "lands with the channel-ops slice (under-port note)."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            # the shipped rows verbatim: row 0 grant/timed/end, row 1 the
            # grey in-place refresh (@discord.ui.button(..., row=1)).
            ("prize_grant", "prize_timed", "prize_end"),
            ("prize_refresh",),
        )),)),
    )


async def _render_hub(spec, ctx) -> object:
    """Grammar render + the two shipped adjustments (see the spec's
    justification): the state-dependent description and the footer
    literal."""
    from dataclasses import replace as _dc_replace

    from sb.domain.proof_channel import service
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    cid = await service.bound_proof_channel(gid)
    description = f"Managing <#{cid}>" if cid else _HUB_NO_CHANNEL
    return _dc_replace(
        rendered,
        embed=_dc_replace(rendered.embed, description=description,
                          footer=_HUB_FOOTER))


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
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    if not is_registered(PanelRef("proof_channel.hub")):
        @panel("proof_channel.hub")
        def _factory():
            return prize_hub_spec()
    if not is_registered(HandlerRef("proof_channel.render_hub")):
        handler("proof_channel.render_hub")(_render_hub)


def ensure_handler_refs() -> None:
    _register()
    _register_task_fire()


_register()
_register_task_fire()
ensure_panel_refs()
