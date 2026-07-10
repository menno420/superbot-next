"""RPS command handlers (band 6) — !rps quick-play / challenge routing,
the rpshelp text (shipped verbatim), the rpssettings read view (§4.1:
edits ride the band-1 settings hub — the xpconfig precedent), and honest
pending terminals for the tournament orchestration (registration
reactions + round channels + no-prefix move parsing = live-adapter /
message-band successor work; entry/payout money lanes are live)."""

from __future__ import annotations


from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs"]


_HELP_TEXT = (
    "**Rock Paper Scissors Commands:**\n"
    "`!rps` - Open the RPS panel (quick play, bet match, challenge a "
    "player, tournament, rules).\n"
    "`!rpsregister [@role]` - Start tournament registration. Optionally "
    "mention a role to notify.\n"
    "`!rpsstart [mode] [best_of]` - Start the tournament (Admin only). "
    "Modes: classic, lizard_spock, chess, elemental.\n"
    "`!rpsbot [mode] [best_of] [@members/@roles]` - Play against the bot.\n"
    "`!rpssettings [setting] [value]` - Update RPS settings (Admin only).\n"
    "`!rpshelp` - Show this help message.\n"
    "During tournament/bot matches, type your move in the match channel "
    "without any prefix.\n"
    "Valid moves depend on the game mode selected."
)


def _mention_token(argv) -> int | None:
    for tok in argv:
        stripped = str(tok).strip("<@!>")
        if stripped.isdigit() and len(stripped) >= 15:
            return int(stripped)
    return None


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("rps.play")):
        return

    @handler("rps.play")
    async def play(req) -> Reply:
        """!rps [bet] or !rps @player [bet] — quick play / challenge."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        target = req.args.get("target_id") or _mention_token(argv)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        if target and int(target) != uid:
            result = await engine.run(
                WorkflowRef("rps.pvp_challenge"),
                _ctx_from_req(req, {
                    "target_id": int(target), "argv": argv,
                    "channel_id": int(req.channel_id or 0)}))
            if result.outcome != SUCCESS:
                return Reply(result.outcome,
                             result.user_message or "Could not challenge.")
            after = (result.after or {}).get("pvp_challenge", {})
            # the shipped challenge embed + Accept/Decline buttons
            # (views/rps/pvp_challenge) — the PvP session panel opens on
            # the challenge stage; every later stage EDITS this message.
            import dataclasses

            from sb.domain.rps.panels import PVP_PANEL_ID
            from sb.kernel.panels.engine import open_panel
            from sb.spec.refs import PanelRef

            pvp_req = dataclasses.replace(req, args={
                **dict(req.args), "stage": "challenge",
                "session_id": str(after.get("session_id") or ""),
                "challenger": uid, "target": int(target),
                "bet": int(after.get("bet", 0) or 0)})
            await open_panel(PanelRef(PVP_PANEL_ID), pvp_req)
            return Reply(SUCCESS, None)
        # solo: a move token plays immediately (`!rps rock 25`); a bare
        # !rps surfaces the move picker (the hub panel's selector runs
        # the same op with args["values"]).
        from sb.domain.rps import rules

        move_tok = next(
            (str(t) for t in argv
             if rules.normalize_move(str(t), "classic") is not None), None)
        if move_tok is not None:
            result = await engine.run(
                WorkflowRef("rps.solo_play"),
                _ctx_from_req(req, {"move": move_tok, "argv": argv}))
            if result.outcome != SUCCESS:
                return Reply(result.outcome,
                             result.user_message or "Could not play.")
            # the leg speaks its own result copy (one source for the
            # prefix path AND the picker-click path).
            return Reply(SUCCESS, result.user_message or "")
        # bare / bet-only !rps: the shipped quick-play view (embed + move
        # buttons — views/rps/solo_play._RpsView) as a session-lifecycle
        # panel. Balance-gate the bet BEFORE the view opens (the shipped
        # construction-site check); no state is written until a move runs
        # the audited rps.solo_play op.
        bet_tokens = [t for t in argv if str(t).isdigit()]
        bet = int(bet_tokens[0]) if bet_tokens else 0
        if bet > 0:
            from sb.domain.economy.store import get_coins

            held = await get_coins(uid, int(req.guild_id or 0))
            if bet > held:
                return Reply(BLOCKED, f"❌ You only have **{held}** 🪙.")
        from sb.domain.rps.panels import QUICKPLAY_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef(QUICKPLAY_PANEL_ID), req)
        return Reply(SUCCESS, None)

    @handler("rps.pvp_click")
    async def pvp_click(req) -> Reply:
        """A PvP g1 button (challenge Accept/Decline or a move) — run the
        audited op, then EDIT the challenge message onto the next stage
        (the shipped safe_edit loop). The ops own every lock (peer,
        already-accepted, already-picked); a vanished live session
        (restart/eviction) degrades to the text result — the checkpoint
        row stayed authoritative."""
        from sb.domain.games.session import EXPIRED_MESSAGE
        from sb.kernel.panels.engine import refresh_session_view
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        action = str(req.args.get("session_action") or "")
        sid = str(req.args.get("session_id") or "")
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        op_key = {"accept": "rps.pvp_accept",
                  "decline": "rps.pvp_decline"}.get(action)
        if op_key is None and action.startswith("move_"):
            op_key = "rps.pvp_move"
        if op_key is None:
            return Reply(BLOCKED, EXPIRED_MESSAGE)
        leg = op_key.rsplit(".", 1)[1]
        result = await engine.run(WorkflowRef(op_key),
                                  _ctx_from_req(req, dict(req.args)))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Couldn't do that.")
        after = (result.after or {}).get(leg, {})
        if action == "accept":
            params = {"stage": "match", "session_id": sid}
            fallback = ("✅ Challenge accepted — both players, choose "
                        "your move!")
            expire = False
        elif action == "decline":
            params = {"stage": "declined", "session_id": sid,
                      "decliner": uid}
            fallback = f"❌ <@{uid}> declined the challenge."
            expire = True
        elif after.get("terminal"):
            params = {"stage": "result", "session_id": sid,
                      "p1": after.get("challenger"),
                      "p2": after.get("peer"),
                      "moves": after.get("moves") or {},
                      "winner": after.get("winner"),
                      "result": after.get("result") or ""}
            fallback = str(after.get("result") or "")
            expire = True
        else:
            params = {"stage": "match", "session_id": sid,
                      "waiting": True}
            fallback = "✅ Move locked in — waiting for your opponent."
            expire = False
        message = getattr(req.origin, "message", None)
        message_key = str(getattr(message, "id", "") or "")
        refreshed = await refresh_session_view(
            req, message_key=message_key, params=params, expire=expire)
        if not refreshed:
            return Reply(SUCCESS, fallback)
        return Reply(SUCCESS, None)

    @handler("rps.help_view")
    async def help_view(req) -> Reply:
        return Reply(SUCCESS, _HELP_TEXT)

    @handler("rps.settings_view")
    async def settings_view(req) -> Reply:
        """!rpssettings — read view; edits ride the settings hub (§4.1)."""
        from sb.kernel.settings import resolve

        gid = int(req.guild_id or 0)
        mode = await resolve(gid, "rps_tournament", "default_mode")
        best = await resolve(gid, "rps_tournament", "default_best_of")
        fee = await resolve(gid, "rps_tournament", "default_entry_fee")
        return Reply(SUCCESS,
                     "⚙️ **RPS settings** (edit in the settings hub):\n"
                     f"default_mode: `{getattr(mode, 'value', mode)}`\n"
                     f"default_best_of: `{getattr(best, 'value', best)}`\n"
                     f"default_entry_fee: `{getattr(fee, 'value', fee)}`")


def _register_pending() -> None:
    """The polite pending terminals. Registered at MODULE IMPORT
    (declaring IS reserving) — the live root imports and dispatches
    without ever running the manifest ENSURE_REFS hooks when zero
    plugins are admitted, so an ensure-only registration leaves
    `!rpsregister`/`!rpsstart`/`!rpsbot` and the tournament matchup
    click dying in RefUnresolved BUG envelopes live (BUG A class,
    band-5 live-drive ledger bug 1 — same fix as
    sb/domain/role/handlers.py)."""
    from sb.domain.operator_spine import pending_handler

    pending_handler(
        "rps.register_pending",
        "✂️ Tournament registration needs the live orchestration "
        "(reaction sign-up + announce embeds — arms with the live "
        "adapter at CUT-1; entry-fee money lanes are live).")
    pending_handler(
        "rps.start_pending",
        "✂️ Tournament rounds need the live orchestration (match "
        "channels + no-prefix move parsing — arms with the live "
        "adapter / message band).")
    pending_handler(
        "rps.bot_pending",
        "🤖 Bot matches need the live orchestration (match channels + "
        "no-prefix move parsing — arms with the message band).")
    pending_handler(
        "rps.matchup_pending",
        "✂️ Manual matchups need the live tournament orchestration "
        "(arms with the live adapter).")


def ensure_handler_refs() -> None:
    _register()
    _register_pending()


_register()
_register_pending()
