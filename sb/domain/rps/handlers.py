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
        from sb.domain.rps.ops import FREE_WIN
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
            bet = int(after.get("bet", 0) or 0)
            bet_str = f"**{bet}** 🪙" if bet else "free play"
            return Reply(SUCCESS,
                         f"✂️ RPS Challenge! <@{uid}> challenges "
                         f"<@{int(target)}> ({bet_str}). "
                         f"<@{int(target)}>, do you accept?")
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
            after = (result.after or {}).get("solo_play", {})
            return Reply(SUCCESS,
                         f"{after.get('emoji', '')} vs "
                         f"{after.get('bot_emoji', '')} (bot)\n"
                         f"{after.get('result', '')}")
        bet_tokens = [t for t in argv if str(t).isdigit()]
        bet = int(bet_tokens[0]) if bet_tokens else 0
        bet_str = (f"**{bet}** 🪙" if bet
                   else f"Free play (win = +{FREE_WIN} 🪙)")
        return Reply(SUCCESS,
                     f"✂️ Rock · Paper · Scissors\nBet: {bet_str}\n"
                     "Choose your move — `!rps rock|paper|scissors "
                     "[bet]`, or use the picker on the RPS panel.")

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
