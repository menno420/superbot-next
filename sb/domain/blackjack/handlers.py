"""Blackjack command handlers (band 6) — thin HandlerRef routes over the
audited K7 lanes: !blackjack/!bj (solo deal or PvP challenge by mention),
!bjstatus (tournament read), and honest pending terminals for the
tournament orchestration (private round channels + reaction registration
= live-adapter successor work; the money lanes are real and tested).
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
        """!bjstatus — entered-players read over the tournament rows."""
        from sb.domain.blackjack.ops import TOURNAMENT_SUBSYSTEM
        from sb.domain.games import store

        rows = await store.list_active(TOURNAMENT_SUBSYSTEM,
                                       guild_id=int(req.guild_id or 0))
        if not rows:
            return Reply(SUCCESS, "No active tournament.")
        players = ", ".join(f"<@{r['user_id']}>" for r in rows)
        pot = sum(int((r.get("state") or {}).get("bet", 0) or 0)
                  for r in rows)
        return Reply(SUCCESS,
                     f"🃏 **Blackjack Tournament** — {len(rows)} paid "
                     f"entrant(s), pot **{pot}** 🪙.\nPlayers: {players}")


def _register_pending() -> None:
    """The polite pending terminals. Registered at MODULE IMPORT
    (declaring IS reserving) — the live root imports and dispatches
    without ever running the manifest ENSURE_REFS hooks when zero
    plugins are admitted, so an ensure-only registration leaves
    `!bjtournament`/`!bjstart` dying in RefUnresolved BUG envelopes
    live (BUG A class, band-5 live-drive ledger bug 1 — same fix as
    sb/domain/role/handlers.py)."""
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
