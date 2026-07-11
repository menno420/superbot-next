"""Blackjack command handlers (band 6) — thin HandlerRef routes over the
audited K7 lanes: !blackjack/!bj (solo deal or PvP challenge by mention),
!bjstatus (tournament read), and the tournament orchestration
(!bjtournament registration on the reaction seam + Join button,
!bjstart launch with per-player fee debits, chips-space round views,
champion payout — the #130 rps shape; private round channels + the
autostart timer are the ledgered deviations).
"""

from __future__ import annotations


from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs"]


def _mention_token(argv) -> int | None:
    for tok in argv:
        stripped = str(tok).strip("<@!>")
        if stripped.isdigit() and len(stripped) >= 15:
            return int(stripped)
    return None


def _hand_lines(after: dict) -> list[str]:
    lines = []
    if "player" in after:
        lines.append(f"Your hand: {'  '.join(after['player'])} "
                     f"(**{after['player_value']}**)")
    if "dealer" in after:
        dv = after.get("dealer_value")
        shown = "  ".join(str(c) for c in after["dealer"])
        lines.append(f"Dealer: {shown}" + (f" (**{dv}**)" if dv else ""))
    if after.get("result"):
        delta = after.get("delta", 0)
        delta_str = f"+{delta}" if delta >= 0 else str(delta)
        lines.append(f"{after['result']}  {delta_str} 🪙  |  "
                     f"Balance: **{after.get('balance', '?')}** 🪙")
    return lines


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("blackjack.play")):
        return

    @handler("blackjack.play")
    async def play(req) -> Reply:
        """!blackjack [bet] or !blackjack @player [bet] (alias !bj)."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        target = req.args.get("target_id") or _mention_token(argv)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        if target and int(target) != uid:
            result = await engine.run(
                WorkflowRef("blackjack.pvp_challenge"),
                _ctx_from_req(req, {
                    "target_id": int(target), "argv": argv,
                    "channel_id": int(req.channel_id or 0)}))
            if result.outcome != SUCCESS:
                return Reply(result.outcome,
                             result.user_message or "Could not challenge.")
            after = (result.after or {}).get("pvp_challenge", {})
            # the shipped challenge embed + Accept/Decline buttons
            # (views/blackjack/pvp_view._ChallengeView) — the PvP session
            # panel opens on the challenge stage; every later stage EDITS
            # this message.
            import dataclasses

            from sb.domain.blackjack.panels import PVP_PANEL_ID
            from sb.kernel.panels.engine import open_panel
            from sb.spec.refs import PanelRef

            pvp_req = dataclasses.replace(req, args={
                **dict(req.args), "stage": "challenge",
                "session_id": str(after.get("session_id") or ""),
                "challenger": uid, "target": int(target),
                "bet": int(after.get("bet", 0) or 0)})
            await open_panel(PanelRef(PVP_PANEL_ID), pvp_req)
            return Reply(SUCCESS, None)
        result = await engine.run(
            WorkflowRef("blackjack.solo_start"),
            _ctx_from_req(req, {"argv": argv,
                                "channel_id": int(req.channel_id or 0)}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not deal.")
        after = (result.after or {}).get("solo_start", {})
        # the shipped solo table view (embed + Hit/Stand/Double) as a
        # session-lifecycle panel rendered from the deal payload; a
        # natural at deal renders the terminal shape (all buttons
        # disabled — the shipped _finish look).
        import dataclasses

        from sb.domain.blackjack.panels import TABLE_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        table_req = dataclasses.replace(
            req, args={**dict(req.args), **after})
        await open_panel(PanelRef(TABLE_PANEL_ID), table_req)
        return Reply(SUCCESS, None)

    @handler("blackjack.table_click")
    async def table_click(req) -> Reply:
        """A solo-table button (session-lifecycle binding → resolve() →
        here): run the audited move op, then refresh the table message IN
        PLACE (the shipped safe_defer + safe_edit loop). Terminal results
        expire the session (the shipped ``view.stop()``)."""
        from sb.kernel.panels.engine import refresh_session_view
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        action = str(req.args.get("session_action") or "")
        op_key = {"hit": "blackjack.solo_hit",
                  "stand": "blackjack.solo_stand",
                  "double": "blackjack.solo_double"}.get(action)
        if op_key is None:
            from sb.domain.games.session import EXPIRED_MESSAGE

            return Reply(BLOCKED, EXPIRED_MESSAGE)
        result = await engine.run(WorkflowRef(op_key),
                                  _ctx_from_req(req, dict(req.args)))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Couldn't play that move.")
        after = (result.after or {}).get(f"solo_{action}", {})
        message = getattr(req.origin, "message", None)
        message_key = str(getattr(message, "id", "") or "")
        refreshed = await refresh_session_view(
            req, message_key=message_key, params=after,
            expire=bool(after.get("terminal")))
        if not refreshed:
            # session evicted/restarted mid-game: the state row is still
            # authoritative — degrade to the text result.
            return Reply(SUCCESS,
                         "🃏 **Blackjack**\n" + "\n".join(_hand_lines(after)))
        return Reply(SUCCESS, None)

    @handler("blackjack.pvp_click")
    async def pvp_click(req) -> Reply:
        """A PvP g1 button (challenge Accept/Decline or the clicker's own
        Hit/Stand) — run the audited op, then EDIT the match message onto
        the next stage. The ops own every lock (peer, own-hand,
        hand-finished); a vanished live session (restart/eviction)
        degrades to the text result — the checkpoint row stayed
        authoritative."""
        from sb.domain.games.session import EXPIRED_MESSAGE
        from sb.kernel.panels.engine import refresh_session_view
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        action = str(req.args.get("session_action") or "")
        sid = str(req.args.get("session_id") or "")
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        op_key = {"accept": "blackjack.pvp_accept",
                  "decline": "blackjack.pvp_decline",
                  "hit": "blackjack.pvp_move",
                  "stand": "blackjack.pvp_move"}.get(action)
        if op_key is None:
            return Reply(BLOCKED, EXPIRED_MESSAGE)
        leg = op_key.rsplit(".", 1)[1]
        result = await engine.run(WorkflowRef(op_key),
                                  _ctx_from_req(req, dict(req.args)))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Couldn't do that.")
        after = (result.after or {}).get(leg, {})
        hands_params = {k: after.get(k)
                        for k in ("p1", "p2", "bet", "hands")}
        if action == "decline":
            params = {"stage": "declined", "session_id": sid,
                      "decliner": uid}
            fallback = f"❌ <@{uid}> declined the challenge."
            expire = True
        elif after.get("terminal"):
            # a terminal accept (both dealt naturals) or the final move.
            params = {"stage": "result", "session_id": sid,
                      **hands_params,
                      "winner": after.get("winner"),
                      "result": after.get("result") or ""}
            fallback = str(after.get("result") or "")
            expire = True
        elif action == "accept":
            params = {"stage": "match", "session_id": sid, **hands_params}
            fallback = "✅ Challenge accepted — dealing hands…"
            expire = False
        else:
            params = {"stage": "match", "session_id": sid, **hands_params}
            fallback = (f"✋ Locked in at **{after.get('hand_value')}** — "
                        "waiting for your opponent."
                        if after.get("done") else
                        f"👊 {'  '.join(after.get('hand') or ())} "
                        f"(**{after.get('hand_value')}**)")
            expire = False
        message = getattr(req.origin, "message", None)
        message_key = str(getattr(message, "id", "") or "")
        refreshed = await refresh_session_view(
            req, message_key=message_key, params=params, expire=expire)
        if not refreshed:
            return Reply(SUCCESS, fallback)
        return Reply(SUCCESS, None)

    @handler("blackjack.status_view")
    async def status_view(req) -> Reply:
        """!bjstatus — the shipped in-memory tournament read: none → the
        pinned "No active tournament."; otherwise the _tourn_embed fields
        as a text card (the embed shape is unpinned — ledgered)."""
        from sb.domain.blackjack import tournament

        state = tournament.state_or_none(int(req.guild_id or 0))
        if state is None:
            return Reply(SUCCESS, "No active tournament.")
        fee_str = f"**{state.entry_fee}** 🪙" if state.entry_fee else "Free"
        phase = "running" if state.started else "registration open"
        return Reply(SUCCESS,
                     f"🃏 **Blackjack Tournament** ({phase})\n"
                     f"Entry Fee: {fee_str} · Rounds: {state.rounds} · "
                     f"Duration: {state.duration_mins} min\n"
                     f"Players: {len(state.players)} · Pot: "
                     f"{state.pot} 🪙")

    # --- tournament orchestration (band-6 slice 6) -------------------------

    async def _fee_default(gid: int) -> int:
        from sb.kernel.settings import resolve

        value = await resolve(gid, "blackjack", "default_entry_fee")
        try:
            return int(getattr(value, "value", value) or 0)
        except (TypeError, ValueError):
            return 0

    def _display_name(req) -> str | None:
        user = getattr(req.origin, "user", None)
        if user is None:
            message = getattr(req.origin, "message", None)
            user = getattr(message, "author", None)
        name = (getattr(user, "display_name", None)
                or getattr(user, "name", None))
        return str(name) if name else None

    async def _announce(req, text: str) -> None:
        """A channel line from the orchestrator (the shipped ctx.send /
        announce-channel sends) — rides the RC-21 emitter so live and
        parity speak the same wire verb."""
        from sb.kernel.interaction.egress import (
            OutboundContent,
            TrustLevel,
            active_channel_emitter,
        )

        emitter = active_channel_emitter()
        await emitter.send(int(req.channel_id or 0),
                           OutboundContent(body=text,
                                           trust=TrustLevel.TRUSTED),
                           guild_id=int(req.guild_id or 0))

    async def _run_op(op_key: str, req, params: dict, *,
                      actor: object | None = None):
        from sb.kernel.workflow import engine
        from sb.kernel.workflow.context import WorkflowContext
        from sb.spec.refs import WorkflowRef

        if actor is None:
            return await engine.run(WorkflowRef(op_key),
                                    _ctx_from_req(req, params))
        import uuid

        ctx = WorkflowContext(actor=actor, guild_id=int(req.guild_id or 0),
                              request_id=f"bj-tournament-{uuid.uuid4()}",
                              params=params)
        return await engine.run(WorkflowRef(op_key), ctx)

    async def _open_round_view(req, state, uid: int) -> None:
        """Deal the entrant's next round and open its table view (fresh
        channel send — CHANNEL_ANCHOR, the #130 presenter seam)."""
        import dataclasses

        from sb.domain.blackjack import tournament
        from sb.domain.blackjack.panels import TOURN_TABLE_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        view = tournament.deal_round(state, uid)
        view["rounds"] = state.rounds
        round_req = dataclasses.replace(req, args={**view,
                                                   "terminal": False})
        message_key = await open_panel(PanelRef(TOURN_TABLE_PANEL_ID),
                                       round_req)
        state.entrants[str(uid)].message_key = str(message_key or "")

    async def _finish_tournament(req, state) -> None:
        """Every entrant finished (the shipped ``_check_tourn_done``):
        rank, pay the champion on the audited lane (settle-once by the
        flag-row check-and-set inside the op), render the results embed,
        drop the in-memory state."""
        import dataclasses

        from sb.domain.blackjack import tournament
        from sb.domain.blackjack.panels import RESULTS_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        ranked = tournament.ranking(state)
        winner = ranked[0][0] if ranked else None
        result = await _run_op("blackjack.tournament_payout", req, {
            "winner_id": winner, "entry_fee": int(state.entry_fee or 0),
            "free_reward": tournament.FREE_TOURNAMENT_REWARD})
        after = (result.after or {}).get("tournament_payout", {})
        results_req = dataclasses.replace(req, args={
            "ranking": [list(pair) for pair in ranked],
            "names": dict(state.names), "winner": winner,
            "entry_fee": int(state.entry_fee or 0),
            "paid": bool(after.get("paid")),
            "amount": after.get("amount"),
            "balance": after.get("balance")})
        await open_panel(PanelRef(RESULTS_PANEL_ID), results_req)
        tournament.end_tournament(state.guild_id)

    @handler("blackjack.tournament_open_route")
    async def tournament_open_route(req) -> Reply:
        """!bjtournament [entry_fee] [rounds] [mins] — the shipped
        registration open: guards verbatim, the ACTIVE_TOURNAMENT flag row
        (audited op), the pinned registration embed + 🃏 Join button + ✅
        primer. (The shipped autostart timer is time-driven — ledgered;
        `!bjstart` starts the pending tournament.)"""
        from sb.domain.blackjack import tournament
        from sb.domain.games.tournament_flag import get_active

        gid, cid = int(req.guild_id or 0), int(req.channel_id or 0)
        if tournament.state_or_none(gid) is not None:
            # shipped copy, verbatim
            return Reply(BLOCKED, "A tournament is already running.")
        existing = await get_active(gid)
        if existing and existing != "blackjack":
            # shipped cross-game guard, verbatim; a stale "blackjack" flag
            # (crash before settle — entries were refunded at boot) is
            # reclaimable, the shipped boot flag-sweep posture.
            return Reply(BLOCKED, f"A **{existing}** tournament is already "
                                  "active in this server.")
        argv = [str(a) for a in (req.args.get("argv", ()) or ())]
        digits = [int(t) for t in argv if t.isdigit()]
        fee = digits[0] if digits else await _fee_default(gid)
        rounds = digits[1] if len(digits) > 1 else tournament.DEFAULT_ROUNDS
        mins = (digits[2] if len(digits) > 2
                else tournament.DEFAULT_DURATION_MINS)
        result = await _run_op("blackjack.tournament_open", req, {})
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message
                         or "Couldn't open registration.")
        state = tournament.get_state(gid)
        state.channel_id = cid
        state.entry_fee = int(fee or 0)
        state.rounds = max(1, int(rounds))
        state.duration_mins = max(1, int(mins))
        state.started = False
        state.players = []
        state.names = {}
        import dataclasses

        from sb.domain.blackjack.panels import REGISTRATION_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        reg_req = dataclasses.replace(req, args={
            **dict(req.args), "entry_fee": state.entry_fee,
            "rounds": state.rounds, "duration_mins": state.duration_mins,
            "players": 0})
        message_ref = await open_panel(PanelRef(REGISTRATION_PANEL_ID),
                                       reg_req)
        try:
            state.reg_message_id = int(str(message_ref))
        except (TypeError, ValueError):
            state.reg_message_id = None
        return Reply(SUCCESS, None)

    @handler("blackjack.tournament_join")
    async def tournament_join(req) -> Reply:
        """The Join Tournament button — the shipped try_join body (guards
        + copy verbatim; NO fee debit — fees collect at launch)."""
        from sb.domain.blackjack import tournament

        gid = int(req.guild_id or 0)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        ok, detail = await tournament.register_player(
            gid, uid, display_name=_display_name(req))
        return Reply(SUCCESS if ok else BLOCKED, detail)

    @handler("blackjack.tournament_start_route")
    async def tournament_start_route(req) -> Reply:
        """!bjstart — the shipped guard verbatim, then the launch: per-
        player fee debits on the audited lane (a broke player is silently
        skipped — shipped), the cancel branches, and each paid entrant's
        first round view."""
        from sb.domain.blackjack import tournament
        from sb.domain.blackjack.ops import TOURN_START_CHIPS
        from sb.kernel.interaction.request import ActorRef

        gid = int(req.guild_id or 0)
        state = tournament.state_or_none(gid)
        if state is None or state.started:
            # shipped copy, pinned by the bjstart sweep
            return Reply(BLOCKED, "No pending tournament.")
        state.started = True
        if not state.players:
            # shipped _launch_tournament copy, verbatim
            await _announce(req, "❌ Tournament cancelled — no players "
                                 "registered.")
            await _run_op("blackjack.tournament_abort", req, {})
            tournament.end_tournament(gid)
            return Reply(SUCCESS, None)
        fee = int(state.entry_fee or 0)
        paid: list[int] = []
        for uid in state.players:
            if fee > 0:
                actor = ActorRef(user_id=int(uid), is_guild_operator=False,
                                 is_bot_owner=False, is_dm=False)
                result = await _run_op(
                    "blackjack.tournament_enter", req,
                    {"fee": fee, "rounds": state.rounds}, actor=actor)
                if result.outcome != SUCCESS:
                    continue                    # shipped: skip a broke player
            paid.append(int(uid))
        if not paid:
            # shipped _launch_tournament copy, verbatim
            await _announce(req, "❌ Tournament cancelled — no players "
                                 "could afford the entry fee.")
            await _run_op("blackjack.tournament_abort", req, {})
            tournament.end_tournament(gid)
            return Reply(SUCCESS, None)
        state.entrants = {
            str(uid): tournament.TournPlayer(user_id=uid,
                                             rounds_left=state.rounds)
            for uid in paid}
        for uid in paid:
            # the shipped welcome line (home channel — the private round
            # channels are the ledgered deviation)
            await _announce(req, f"Welcome, <@{uid}>! You have "
                                 f"**{state.rounds}** rounds and start "
                                 f"with **{TOURN_START_CHIPS}** chips. "
                                 "Good luck! 🃏")
            await _open_round_view(req, state, uid)
        return Reply(SUCCESS, None)

    @handler("blackjack.tournament_click")
    async def tournament_click(req) -> Reply:
        """Hit/Stand on a tournament round view: in-memory chips move,
        the view edits IN PLACE (type-6 ack + edit); a finished round
        opens the next one (fresh CHANNEL_ANCHOR send) or — once every
        entrant is done — pays the champion and renders the results."""
        from sb.domain.blackjack import tournament
        from sb.domain.games.session import EXPIRED_MESSAGE
        from sb.kernel.panels.engine import refresh_session_view

        gid = int(req.guild_id or 0)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        state = tournament.state_or_none(gid)
        if state is None or not state.started:
            return Reply(BLOCKED, EXPIRED_MESSAGE)
        action = str(req.args.get("session_action")
                     or "").removeprefix("tourn_")
        outcome = tournament.round_move(state, uid, action)
        stage = outcome.pop("stage")
        if stage == "expired":
            return Reply(BLOCKED, EXPIRED_MESSAGE)
        if stage == "not_yours":
            return Reply(BLOCKED, "This isn't your table.")
        if _display_name(req):
            state.names[str(uid)] = _display_name(req)
        message = getattr(req.origin, "message", None)
        message_key = str(getattr(message, "id", "") or "")
        outcome["rounds"] = state.rounds
        refreshed = await refresh_session_view(
            req, message_key=message_key, params=outcome,
            expire=stage == "round_done")
        if stage == "hand":
            return Reply(SUCCESS, None if refreshed
                         else "Move recorded — waiting for the table view.")
        entrant = state.entrants[str(uid)]
        if entrant.done:
            # shipped end-of-run line, verbatim
            await _announce(req, f"✅ You finished the tournament with "
                                 f"**{entrant.chips}** chips!")
            if tournament.all_done(state):
                await _finish_tournament(req, state)
        else:
            await _open_round_view(req, state, uid)
        return Reply(SUCCESS, None)


def _register_pending() -> None:
    """The (now unrouted) pending terminals. STILL registered at MODULE
    IMPORT: tests/unit/invariants/test_composition_parity.py pins
    ``handler:blackjack.tournament_open_pending`` in the import roster
    (the rps precedent — #130 kept its 4 pending refs the same way);
    the command table routes to the real tournament handlers now."""
    from sb.domain.operator_spine import pending_handler

    pending_handler(
        "blackjack.tournament_open_pending",
        "🃏 Tournament registration needs the live orchestration "
        "(private round channels + reaction sign-up — arms with the "
        "live adapter at CUT-1; entry/payout money lanes are live).")
    pending_handler(
        "blackjack.tournament_start_pending",
        "🃏 Manual tournament start needs the live orchestration "
        "(arms with the live adapter at CUT-1).")


def ensure_handler_refs() -> None:
    _register()
    _register_pending()


_register()
_register_pending()
