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

    # --- tournament orchestration (band-6 slice 5) -------------------------

    async def _mode_default(gid: int) -> str:
        from sb.kernel.settings import resolve

        value = await resolve(gid, "rps_tournament", "default_mode")
        return str(getattr(value, "value", value) or "classic")

    async def _best_of_default(gid: int) -> int:
        from sb.kernel.settings import resolve

        value = await resolve(gid, "rps_tournament", "default_best_of")
        try:
            return int(getattr(value, "value", value) or 3)
        except (TypeError, ValueError):
            return 3

    async def _fee_default(gid: int) -> int:
        from sb.kernel.settings import resolve

        value = await resolve(gid, "rps_tournament", "default_entry_fee")
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
        match-channel sends) — rides the RC-21 emitter so live and parity
        speak the same wire verb."""
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

    async def _open_match_views(req, state, matches) -> None:
        import dataclasses

        from sb.domain.rps.panels import MATCH_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        for match in matches:
            match_req = dataclasses.replace(req, args={
                "match_id": match.match_id, "p1": match.p1, "p2": match.p2,
                "mode": match.mode, "best_of": match.best_of,
                "round": state.round_num, "stage": "open"})
            await open_panel(PanelRef(MATCH_PANEL_ID), match_req)

    @handler("rps.register_route")
    async def register_route(req) -> Reply:
        """!rpsregister [@role] [entry_fee] — the shipped registration
        open: the ACTIVE_TOURNAMENT flag row (audited op), the pinned
        registration embed + Join button + ✅ primer, in-memory window.
        (The shipped role-ping reminder loop is time-driven — ledgered.)"""
        from sb.domain.rps import tournament
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        gid, cid = int(req.guild_id or 0), int(req.channel_id or 0)
        state = tournament.state_or_none(gid)
        if state is not None and state.registration_active:
            return Reply(BLOCKED, "Registration is already active.")
        if state is not None and state.active:
            return Reply(BLOCKED, "Tournament is already in progress.")
        argv = tuple(str(a) for a in (req.args.get("argv", ()) or ()))
        fee = next((int(t) for t in argv if t.isdigit()), None)
        if fee is None:
            fee = await _fee_default(gid)
        result = await engine.run(WorkflowRef("rps.tournament_open"),
                                  _ctx_from_req(req, {}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message
                         or "Couldn't open registration.")
        state = tournament.get_state(gid)
        state.channel_id = cid
        state.entry_fee = int(fee or 0)
        state.registration_active = True
        state.active = False
        state.players = []
        state.names = {}
        state.matches = {}
        import time as _time

        state.registration_opened_mono = _time.monotonic()
        from sb.domain.rps.panels import REGISTRATION_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        import dataclasses

        mode_label = (await _mode_default(gid)).capitalize()
        reg_req = dataclasses.replace(req, args={
            **dict(req.args), "entry_fee": state.entry_fee,
            "mode_label": mode_label})
        message_ref = await open_panel(PanelRef(REGISTRATION_PANEL_ID),
                                       reg_req)
        try:
            state.registration_message_id = int(str(message_ref))
        except (TypeError, ValueError):
            state.registration_message_id = None
        return Reply(SUCCESS, None)

    @handler("rps.tournament_join")
    async def tournament_join(req) -> Reply:
        """The Join Tournament button — the shipped _RpsRegistrationView
        callback: balance gate, audited fee debit + entry row, roster
        append, the ephemeral confirmation."""
        from sb.domain.rps import tournament

        gid = int(req.guild_id or 0)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        ok, detail = await tournament.register_player(
            gid, uid, display_name=_display_name(req), actor=req.actor)
        if not ok:
            return Reply(BLOCKED, detail)
        state = tournament.get_state(gid)
        # shipped registration.py copy, verbatim
        return Reply(SUCCESS,
                     f"✅ Registered! ({len(state.players)} player(s) "
                     "so far)")

    @handler("rps.start_route")
    async def start_route(req) -> Reply:
        """!rpsstart [mode] [best_of] — the shipped guards verbatim, then
        the bracket: shuffle, pair, one match view per pair (the ledgered
        home-channel deviation), byes advance automatically."""
        from sb.domain.rps import rules as rps_rules
        from sb.domain.rps import tournament
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        gid = int(req.guild_id or 0)
        state = tournament.state_or_none(gid)
        if (state is not None and state.registration_active
                and not state.registration_window_elapsed()):
            # shipped copy, pinned by the rpsstart sweep
            return Reply(BLOCKED, "Cannot start the tournament while "
                                  "registration is still active.")
        if state is not None and state.active:
            return Reply(BLOCKED, "Tournament is already in progress.")
        if (state is not None and state.registration_active
                and state.registration_window_elapsed()):
            # the LAZY close (the shipped end_registration ran on a 600 s
            # timer; deviation ledgered) — the roster is already collected
            # incrementally by button + reaction sign-ups.
            state.registration_active = False
            await _announce(req, f"{len(state.players)} players have "
                                 "registered for the tournament.")
        if state is None or len(state.players) < 2:
            if state is not None and not state.active:
                # the shipped `< 2 ⇒ clear_active` + entry refunds
                await engine.run(WorkflowRef("rps.tournament_abort"),
                                 _ctx_from_req(req, {}))
                tournament.end_tournament(gid)
            return Reply(BLOCKED, "Not enough players registered to start "
                                  "the tournament.")
        argv = [str(a) for a in (req.args.get("argv", ()) or ())]
        mode = argv[0].lower() if argv else await _mode_default(gid)
        if mode not in rps_rules.GAME_MODES:
            return Reply(BLOCKED,
                         "Invalid game mode. Available modes: "
                         + ", ".join(rps_rules.GAME_MODES.keys()))
        best_of = None
        if len(argv) > 1 and argv[1].isdigit():
            best_of = int(argv[1])
        if best_of is None:
            best_of = await _best_of_default(gid)
        # shipped announce, then the round views (wire order preserved)
        await _announce(req, f"Tournament started with game mode: {mode}, "
                             f"Best of {best_of}")
        matches, byes = tournament.start_bracket(state, mode=mode,
                                                 best_of=best_of)
        for bye in byes:
            await _announce(req, f"**<@{bye}>** gets a bye this round.")
        await _open_match_views(req, state, matches)
        return Reply(SUCCESS, None)

    @handler("rps.tournament_move")
    async def tournament_move(req) -> Reply:
        """A move button on a tournament match view: throw, reveal when
        both are in, best-of scoring, stats at match end (audited), then
        the bracket advance — next round's views or the champion payout."""
        from sb.domain.games.session import EXPIRED_MESSAGE
        from sb.domain.rps import tournament
        from sb.kernel.panels.engine import refresh_session_view
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        gid = int(req.guild_id or 0)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        state = tournament.state_or_none(gid)
        if state is None or not state.active:
            return Reply(BLOCKED, "Tournament is not active.")
        match_id = str(req.args.get("match_id") or "")
        action = str(req.args.get("session_action") or "")
        move = action.removeprefix("move_")
        outcome = tournament.record_move(state, match_id, uid, move)
        stage = outcome["stage"]
        if stage == "expired":
            return Reply(BLOCKED, EXPIRED_MESSAGE)
        if stage == "not_yours":
            return Reply(BLOCKED, "You're not part of this match.")
        if stage == "already_picked":
            return Reply(BLOCKED, "You already picked!")
        match = outcome["match"]
        if _display_name(req):
            state.names[str(uid)] = _display_name(req)
        params = {"match_id": match.match_id, "p1": match.p1,
                  "p2": match.p2, "mode": match.mode,
                  "best_of": match.best_of, "round": state.round_num,
                  "scores": dict(match.scores),
                  "moves": dict(outcome.get("moves") or {})}
        if stage == "waiting":
            params["stage"] = "waiting"
        elif stage == "throw_tie":
            params["stage"] = "throw_tie"
        elif stage == "throw_scored":
            params["stage"] = "throw_scored"
            params["throw_winner"] = outcome["throw_winner"]
        else:                                        # match_done
            params["stage"] = "done"
            params["winner"] = outcome["winner"]
        message = getattr(req.origin, "message", None)
        message_key = str(getattr(message, "id", "") or "")
        refreshed = await refresh_session_view(
            req, message_key=message_key, params=params,
            expire=stage == "match_done")
        if stage != "match_done":
            return Reply(SUCCESS, None if refreshed
                         else "Move recorded — waiting for the match view.")
        winner, loser = int(outcome["winner"]), int(outcome["loser"])
        await engine.run(WorkflowRef("rps.tournament_result"),
                         _ctx_from_req(req, {
                             "winner_id": winner, "loser_id": loser,
                             "names": dict(state.names)}))
        advanced = tournament.advance_round(state)
        if advanced["stage"] == "next_round":
            await _announce(req, f"⚔️ Round {advanced['round']} — "
                                 f"{len(advanced['matches'])} match(es). "
                                 "Views below — pick your moves!")
            for bye in advanced["byes"]:
                await _announce(req, f"**<@{bye}>** gets a bye this round.")
            await _open_match_views(req, state, advanced["matches"])
        elif advanced["stage"] == "champion":
            champion = advanced["winner"]
            fee = int(state.entry_fee or 0)
            result = await engine.run(
                WorkflowRef("rps.tournament_payout"),
                _ctx_from_req(req, {
                    "winner_id": champion, "entry_fee": fee,
                    "free_reward": tournament.FREE_TOURNAMENT_REWARD}))
            after = (result.after or {}).get("tournament_payout", {})
            name = state.names.get(str(champion)) or f"<@{champion}>"
            # shipped champion copy, verbatim
            lines = [f"🏆 **{name}** has won the RPS Tournament! 🏆"]
            if after.get("paid") and fee > 0:
                lines.append(f"💰 Payout: **{after.get('amount')}** 🪙")
            await _announce(req, "\n".join(lines))
            tournament.end_tournament(gid)
        return Reply(SUCCESS, None)

    @handler("rps.matchup_route")
    async def matchup_route(req) -> Reply:
        """!rpsmatchup @p1 @p2 — the shipped manual match (guards
        verbatim); the match view opens in the home channel."""
        from sb.domain.rps import tournament

        gid = int(req.guild_id or 0)
        state = tournament.state_or_none(gid)
        if state is None or not state.active:
            return Reply(BLOCKED, "Tournament is not active.")   # shipped
        argv = tuple(str(a) for a in (req.args.get("argv", ()) or ()))
        mentions = [int(str(t).strip("<@!>")) for t in argv
                    if str(t).strip("<@!>").isdigit()
                    and len(str(t).strip("<@!>")) >= 15]
        if len(mentions) < 2:
            return Reply(BLOCKED, "Both players must be registered in the "
                                  "tournament.")
        p1, p2 = mentions[0], mentions[1]
        if p1 not in state.players or p2 not in state.players:
            # shipped copy, verbatim
            return Reply(BLOCKED, "Both players must be registered in the "
                                  "tournament.")
        state._match_seq += 1
        from sb.domain.rps.tournament import Match

        match = Match(match_id=f"r{state.round_num}m{state._match_seq}",
                      p1=p1, p2=p2, best_of=state.best_of,
                      mode=state.game_mode)
        state.matches[match.match_id] = match
        await _open_match_views(req, state, [match])
        return Reply(SUCCESS, None)

    @handler("rps.bot_route")
    async def bot_route(req) -> Reply:
        """!rpsbot [mode] … — the shipped mode guard verbatim; the bot
        match itself (private channel + no-prefix moves) stays an honest
        pending terminal (ledgered successor)."""
        from sb.domain.rps import rules as rps_rules

        argv = [str(a) for a in (req.args.get("argv", ()) or ())]
        mode = None
        for token in argv:
            if not token.isdigit() and not token.startswith("<@"):
                mode = token.lower()
                break
        if mode is None:
            mode = await _mode_default(int(req.guild_id or 0))
        if mode not in rps_rules.GAME_MODES:
            # shipped copy, pinned by the rpsbot sweep
            return Reply(BLOCKED,
                         "Invalid game mode. Available modes: "
                         + ", ".join(rps_rules.GAME_MODES.keys()))
        return Reply(BLOCKED,
                     "🤖 Bot matches need the live orchestration (match "
                     "channels + no-prefix move parsing — arms with the "
                     "message band).")

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
