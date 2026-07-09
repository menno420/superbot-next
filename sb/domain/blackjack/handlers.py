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
            bet = int(after.get("bet", 0) or 0)
            bet_str = f"**{bet}** 🪙" if bet else "free play"
            return Reply(SUCCESS,
                         f"🃏 Blackjack Challenge! <@{uid}> challenges "
                         f"<@{int(target)}> ({bet_str}). "
                         f"<@{int(target)}>, do you accept?")
        result = await engine.run(WorkflowRef("blackjack.solo_start"),
                                  _ctx_from_req(req, {"argv": argv}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not deal.")
        after = (result.after or {}).get("solo_start", {})
        return Reply(SUCCESS, "🃏 **Blackjack**\n" +
                     "\n".join(_hand_lines(after)))

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


def ensure_handler_refs() -> None:
    _register()
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


_register()
