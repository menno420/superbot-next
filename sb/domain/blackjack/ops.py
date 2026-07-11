"""Blackjack K7 lanes (band 6) — solo vs dealer, PvP escrow matches, and
the tournament money legs, over the games-substrate checkpoint store.

Shipped semantics carried verbatim (cogs/blackjack_cog.py +
views/blackjack/solo_view.py @7f7628e1): the settle table (natural 1.5×,
win 1×, push 0, loss −effective with the overdraft-tolerant floor; free
play wins pay FREE_WIN_COINS), the double-down funding check, the
stand-on-17 dealer, one solo game per (user, guild), the D1
escrow-at-accept PvP flow with row-consumption settle-once.

DEVIATION (ledgered D-0042, flip-review material): shipped PvP hands ALSO
ran the solo house credit/debit at each player's finish (_finish's
tournament_chips-is-None branch) on top of the escrowed pot settle —
minting house coins in a player-vs-player match. The port settles PvP
from the POT ONLY (the game_wager_workflow docstring's own D1 design);
PvP double-down is disabled (it would need mid-match re-escrow).

Checkpoint rows (game_state, SESSION):
* solo — (guild, user, 0, "blackjack_solo"): bet/doubled/deck/player/dealer.
* pvp match — (guild, p1, channel, "blackjack_pvp"): per-player decks+hands.
* pvp escrow — one row per player, "blackjack_pvp_escrow" (bet convention).
* pending challenge — (guild, challenger, channel, "blackjack_pvp_pending").
* tournament entry — "blackjack_tournament" rows via the wager primitives.
"""

from __future__ import annotations

import random

from sb.domain.blackjack import engine as bj
from sb.domain.games import session as games_session
from sb.domain.games import store as games_store
from sb.domain.games import wager
from sb.kernel.interaction.errors import ValidatorError
from sb.kernel.workflow.context import LegOutcome, WorkflowContext
from sb.kernel.workflow.registry import REGISTRY
from sb.kernel.workflow.result import StepResult
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    EventEmitSpec,
    IdempotencyPosture,
    LegKind,
    LegSpec,
    WorkflowLane,
)
from sb.spec.events import DeliveryClass
from sb.spec.refs import WorkflowRef, workflow

__all__ = [
    "FREE_WIN_COINS",
    "SOLO_SUBSYSTEM",
    "PVP_SUBSYSTEM",
    "PVP_ESCROW_SUBSYSTEM",
    "PVP_PENDING_SUBSYSTEM",
    "TOURNAMENT_SUBSYSTEM",
    "register_ops",
    "set_rng_for_tests",
]

# shipped constants / subsystem keys, verbatim (blackjack_state.py)
FREE_WIN_COINS = 50
TOURN_START_CHIPS = 1000
TOURN_BET_PER_ROUND = 200
SOLO_SUBSYSTEM = "blackjack_solo"
SOLO_VERSION = 1
PVP_SUBSYSTEM = "blackjack_pvp"
PVP_VERSION = 1
PVP_ESCROW_SUBSYSTEM = "blackjack_pvp_escrow"
PVP_ESCROW_VERSION = 1
PVP_PENDING_SUBSYSTEM = "blackjack_pvp_pending"
PVP_PENDING_VERSION = 1
TOURNAMENT_SUBSYSTEM = "blackjack_tournament"
TOURNAMENT_VERSION = 1

# None ⇒ the GLOBAL random stream (the shipped bot shuffled through
# `random.shuffle`; the parity harness seeds `random.seed(case.seed)`, so
# only the module-global stream reproduces the goldens' decks).
_rng: random.Random | None = None


def set_rng_for_tests(rng: random.Random) -> None:
    global _rng
    _rng = rng


def _actor_id(ctx: WorkflowContext) -> int:
    return int(getattr(ctx.actor, "user_id", 0) or 0)


def _now(ctx: WorkflowContext) -> int:
    return int(ctx.clock().timestamp())


def _bet_from(ctx: WorkflowContext) -> int:
    bet = ctx.params.get("bet")
    if bet is None:
        for token in tuple(ctx.params.get("argv", ()) or ()):
            if str(token).lstrip("-").isdigit():
                bet = int(token)
                break
    bet = int(bet or 0)
    if bet < 0:
        raise ValidatorError("Bet must be 0 or a positive number.")
    return bet


def _components(session_id: str, *actions: str) -> list[str]:
    return [games_session.mint_custom_id("blackjack", session_id, a)
            for a in actions]


def _hands_view(match: dict) -> dict:
    """Deck-free render view of a PvP match (both hands are PUBLIC — the
    shipped per-player tables were plain channel messages)."""
    hands = {}
    for uid_s, h in match["hands"].items():
        hands[uid_s] = {"cards": [str(c) for c in h["hand"]],
                        "value": bj.hand_value(h["hand"]),
                        "done": bool(h["done"])}
    return {"p1": int(match["p1"]), "p2": int(match["p2"]),
            "bet": int(match.get("bet", 0) or 0), "hands": hands}


def _hand_payload(state: dict, *, reveal: bool) -> dict:
    return {
        "player": list(state["player"]),
        "player_value": bj.hand_value(state["player"]),
        "dealer": (list(state["dealer"]) if reveal
                   else [state["dealer"][0], "?"]),
        "dealer_value": (bj.hand_value(state["dealer"]) if reveal else None),
        "bet": state["bet"], "doubled": bool(state.get("doubled")),
    }


async def _settle_solo(conn, ctx: WorkflowContext, state: dict,
                       result: str, delta: int) -> dict:
    """Apply the outcome delta (shipped sign semantics), clear the row,
    stamp _balance_changes. Returns the result payload."""
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    changes: list[tuple[int, int, int, str]] = []
    if delta > 0:
        balance = await wager.credit_in_txn(
            conn, guild_id=gid, user_id=uid, amount=delta,
            reason="blackjack:solo_win", actor_id=uid)
        changes.append((uid, delta, balance, "blackjack:solo_win"))
    elif delta < 0:
        actual, balance = await wager.debit_floor_in_txn(
            conn, guild_id=gid, user_id=uid, amount=-delta,
            reason="blackjack:solo_loss", actor_id=uid)
        if actual:
            changes.append((uid, actual, balance, "blackjack:solo_loss"))
    else:
        from sb.domain.economy.store import get_coins

        balance = await get_coins(uid, gid, conn=conn)
    await games_store.delete_user_checkpoint(
        conn, guild_id=gid, user_id=uid, subsystem=SOLO_SUBSYSTEM)
    ctx.params["_balance_changes"] = changes
    return {"result": result, "delta": delta, "balance": balance,
            **_hand_payload(state, reveal=True), "terminal": True}


def _resolve_solo_result(state: dict) -> tuple[str, int]:
    """The shipped _resolve settle table (dealer already played)."""
    effective = state["bet"] * 2 if state.get("doubled") else state["bet"]
    pv = bj.hand_value(state["player"])
    dv = bj.hand_value(state["dealer"])
    if bj.is_blackjack(state["player"]):
        return "🎉 Blackjack!", (int(effective * 1.5) if effective
                                 else FREE_WIN_COINS)
    if dv > 21:
        return "🎉 Dealer busts — you win!", (effective or FREE_WIN_COINS)
    if pv > dv:
        return "🎉 You win!", (effective or FREE_WIN_COINS)
    if pv == dv:
        return "🤝 Push — tie.", 0
    return "😞 Dealer wins.", (-effective if effective else 0)


async def _load_solo(conn, ctx: WorkflowContext) -> tuple[dict, int]:
    """(state, channel_id) — the solo game is keyed (user, guild) like the
    shipped `_active` dict; the row remembers the channel it was dealt in."""
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    row = await games_store.fetch_user_checkpoint(gid, uid, SOLO_SUBSYSTEM,
                                                  conn=conn)
    if row is None:
        raise ValidatorError(games_session.EXPIRED_MESSAGE)
    return row["state"], int(row["channel_id"] or 0)


# --- solo legs ---------------------------------------------------------------------------


@workflow("blackjack.record_solo_start")
async def _record_solo_start(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    cid = int(ctx.params.get("channel_id") or 0)
    bet = _bet_from(ctx)
    now = _now(ctx)
    if await games_store.fetch_user_checkpoint(gid, uid, SOLO_SUBSYSTEM,
                                               conn=conn) is not None:
        raise ValidatorError("You already have a game running!")
    if bet > 0:
        from sb.domain.economy.store import get_coins

        held = await get_coins(uid, gid, conn=conn)
        if bet > held:
            raise ValidatorError(f"❌ You only have **{held}** 🪙.")
    deck = bj.new_deck(_rng)
    state = {"bet": bet, "doubled": False, "deck": deck,
             "player": [deck.pop(), deck.pop()],
             "dealer": [deck.pop(), deck.pop()]}
    changes: list[tuple[int, int, int, str]] = []
    if bj.is_blackjack(state["player"]):
        payout = int(bet * 1.5) if bet else FREE_WIN_COINS
        balance = await wager.credit_in_txn(
            conn, guild_id=gid, user_id=uid, amount=payout,
            reason="blackjack:natural_blackjack", actor_id=uid)
        changes.append((uid, payout, balance,
                        "blackjack:natural_blackjack"))
        ctx.params["_balance_changes"] = changes
        payload = {"result": "🎉 Blackjack!", "delta": payout,
                   "balance": balance, "terminal": True,
                   **_hand_payload(state, reveal=True)}
        return LegOutcome(step=StepResult(uid, "solo_start", True),
                          before={}, after=dict(payload, natural=True))
    await games_store.upsert_checkpoint(
        conn, guild_id=gid, user_id=uid, channel_id=cid,
        subsystem=SOLO_SUBSYSTEM, state=state, version=SOLO_VERSION,
        now=now)
    ctx.params["_balance_changes"] = changes
    payload = {**_hand_payload(state, reveal=False), "terminal": False}
    return LegOutcome(step=StepResult(uid, "solo_start", True), before={},
                      after=payload)


@workflow("blackjack.record_solo_hit")
async def _record_solo_hit(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    state, cid = await _load_solo(conn, ctx)
    state["player"].append(state["deck"].pop())
    if bj.hand_value(state["player"]) > 21:
        effective = (state["bet"] * 2 if state.get("doubled")
                     else state["bet"])
        payload = await _settle_solo(conn, ctx, state,
                                     "💥 Bust — you lose!",
                                     -effective if effective else 0)
        return LegOutcome(step=StepResult(uid, "solo_hit", True), before={},
                          after=payload)
    await games_store.upsert_checkpoint(
        conn, guild_id=gid, user_id=uid, channel_id=cid,
        subsystem=SOLO_SUBSYSTEM, state=state, version=SOLO_VERSION,
        now=_now(ctx))
    ctx.params["_balance_changes"] = []
    payload = {**_hand_payload(state, reveal=False), "terminal": False}
    return LegOutcome(step=StepResult(uid, "solo_hit", True), before={},
                      after=payload)


@workflow("blackjack.record_solo_stand")
async def _record_solo_stand(conn, ctx: WorkflowContext) -> LegOutcome:
    uid = _actor_id(ctx)
    state, _ = await _load_solo(conn, ctx)
    bj.dealer_play(state["deck"], state["dealer"])
    result, delta = _resolve_solo_result(state)
    payload = await _settle_solo(conn, ctx, state, result, delta)
    return LegOutcome(step=StepResult(uid, "solo_stand", True), before={},
                      after=payload)


@workflow("blackjack.record_solo_double")
async def _record_solo_double(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    state, _ = await _load_solo(conn, ctx)
    if not state["bet"]:
        raise ValidatorError("Double down needs a bet on the table.")
    from sb.domain.economy.store import get_coins

    held = await get_coins(uid, gid, conn=conn)
    if held < state["bet"] * 2:
        raise ValidatorError(
            f"❌ Need {state['bet'] * 2} 🪙 to double (you have {held}).")
    state["player"].append(state["deck"].pop())
    state["doubled"] = True
    if bj.hand_value(state["player"]) > 21:
        payload = await _settle_solo(conn, ctx, state,
                                     "💥 Bust — you lose!",
                                     -(state["bet"] * 2))
        return LegOutcome(step=StepResult(uid, "solo_double", True),
                          before={}, after=payload)
    bj.dealer_play(state["deck"], state["dealer"])
    result, delta = _resolve_solo_result(state)
    payload = await _settle_solo(conn, ctx, state, result, delta)
    return LegOutcome(step=StepResult(uid, "solo_double", True), before={},
                      after=payload)


# --- PvP legs ----------------------------------------------------------------------------


@workflow("blackjack.record_pvp_challenge")
async def _record_pvp_challenge(conn, ctx: WorkflowContext) -> LegOutcome:
    """!bj @player [bet] — record the pending challenge; the opponent's
    Accept/Decline ride g1 session components keyed on the challenger."""
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    cid = int(ctx.params.get("channel_id") or 0)
    target = int(ctx.params["target_id"])
    bet = _bet_from(ctx)
    if target == uid:
        raise ValidatorError("You can't challenge yourself.")
    existing = await games_store.fetch_checkpoint(
        gid, uid, cid, PVP_PENDING_SUBSYSTEM, conn=conn)
    if existing is not None:
        raise ValidatorError(
            "There's already a PvP game between these players.")
    if bet > 0:
        from sb.domain.economy.store import get_coins

        held = await get_coins(uid, gid, conn=conn)
        if bet > held:
            raise ValidatorError(f"❌ You only have **{held}** 🪙.")
    await games_store.upsert_checkpoint(
        conn, guild_id=gid, user_id=uid, channel_id=cid,
        subsystem=PVP_PENDING_SUBSYSTEM,
        state={"peer": target, "bet": bet}, version=PVP_PENDING_VERSION,
        now=_now(ctx))
    ctx.params["_balance_changes"] = []
    sid = games_session.mint_session_id(gid, uid, cid)
    payload = {"challenger": uid, "target": target, "bet": bet,
               "session_id": sid,
               "components": _components(sid, "accept", "decline")}
    return LegOutcome(step=StepResult(uid, "pvp_challenge", True),
                      before={}, after=payload)


async def _load_pending(conn, gid: int, sid: str) -> tuple[int, int, int, dict]:
    parsed = games_session.parse_session_id(sid)
    if parsed is None or parsed[0] != gid:
        raise ValidatorError(games_session.EXPIRED_MESSAGE)
    _, challenger, cid = parsed
    state = await games_store.fetch_checkpoint(
        gid, challenger, cid, PVP_PENDING_SUBSYSTEM, conn=conn)
    if state is None:
        raise ValidatorError(games_session.EXPIRED_MESSAGE)
    return challenger, cid, int(state.get("bet", 0)), state


@workflow("blackjack.record_pvp_accept")
async def _record_pvp_accept(conn, ctx: WorkflowContext) -> LegOutcome:
    """Opponent accepts: escrow BOTH stakes (D1) + deal both hands in ONE
    txn. Only the challenged player may accept (shipped invoker lock)."""
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    sid = str(ctx.params.get("session_id") or "")
    challenger, cid, bet, pending = await _load_pending(conn, gid, sid)
    if uid != int(pending.get("peer", 0)):
        raise ValidatorError("This challenge isn't for you.")
    now = _now(ctx)
    escrow = await wager.escrow_pvp_in_txn(
        conn, guild_id=gid, channel_id=cid,
        subsystem=PVP_ESCROW_SUBSYSTEM, version=PVP_ESCROW_VERSION,
        p1_id=challenger, p2_id=uid, stake=bet,
        reason="blackjack:pvp_escrow", now=now)
    hands: dict[str, dict] = {}
    for player in (challenger, uid):
        deck = bj.new_deck(_rng)
        hand = [deck.pop(), deck.pop()]
        hands[str(player)] = {
            "deck": deck, "hand": hand,
            "done": bj.is_blackjack(hand),
            "value": bj.hand_value(hand) if bj.is_blackjack(hand) else None}
    match = {"p1": challenger, "p2": uid, "bet": bet, "hands": hands}
    await games_store.delete_checkpoint(
        conn, guild_id=gid, user_id=challenger, channel_id=cid,
        subsystem=PVP_PENDING_SUBSYSTEM)
    escrow_changes = [(u, d, b, "blackjack:pvp_escrow")
                      for (u, d, b) in escrow.balance_changes]
    if all(h["done"] for h in hands.values()):
        # both dealt naturals — settle in the SAME txn (the shipped
        # ``_resolve_pvp`` "or both natural-blackjack out" branch); no
        # match row is ever written, so no move could get stuck on two
        # finished hands.
        settled = await _maybe_settle_pvp(conn, ctx, gid, cid, match)
        ctx.params["_balance_changes"] = (
            escrow_changes + list(ctx.params.get("_balance_changes") or ()))
        payload = {**(settled or {}), "session_id": sid,
                   "escrowed": escrow.escrowed, **_hands_view(match)}
        return LegOutcome(step=StepResult(uid, "pvp_accept", True),
                          before={}, after=payload)
    await games_store.upsert_checkpoint(
        conn, guild_id=gid, user_id=challenger, channel_id=cid,
        subsystem=PVP_SUBSYSTEM, state=match, version=PVP_VERSION, now=now)
    ctx.params["_balance_changes"] = escrow_changes
    payload = {"session_id": sid, "escrowed": escrow.escrowed,
               **_hands_view(match),
               "components": _components(sid, "hit", "stand"),
               "terminal": False}
    return LegOutcome(step=StepResult(uid, "pvp_accept", True), before={},
                      after=payload)


@workflow("blackjack.record_pvp_decline")
async def _record_pvp_decline(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    sid = str(ctx.params.get("session_id") or "")
    challenger, cid, _, pending = await _load_pending(conn, gid, sid)
    if uid != int(pending.get("peer", 0)):
        raise ValidatorError("This challenge isn't for you.")
    await games_store.delete_checkpoint(
        conn, guild_id=gid, user_id=challenger, channel_id=cid,
        subsystem=PVP_PENDING_SUBSYSTEM)
    ctx.params["_balance_changes"] = []
    return LegOutcome(step=StepResult(uid, "pvp_decline", True), before={},
                      after={"declined": True, "terminal": True})


async def _load_match(conn, gid: int, sid: str) -> tuple[int, int, dict]:
    parsed = games_session.parse_session_id(sid)
    if parsed is None or parsed[0] != gid:
        raise ValidatorError(games_session.EXPIRED_MESSAGE)
    _, p1, cid = parsed
    match = await games_store.fetch_checkpoint(gid, p1, cid, PVP_SUBSYSTEM,
                                               conn=conn)
    if match is None:
        raise ValidatorError(games_session.EXPIRED_MESSAGE)
    return p1, cid, match


async def _maybe_settle_pvp(conn, ctx: WorkflowContext, gid: int, cid: int,
                            match: dict) -> dict | None:
    """When both hands are done: hand-vs-hand result, pot settle/refund
    (POT ONLY — the D-0042 deviation), match row cleared."""
    hands = match["hands"]
    if not all(h["done"] for h in hands.values()):
        return None
    p1, p2 = int(match["p1"]), int(match["p2"])
    v1 = hands[str(p1)]["value"] if hands[str(p1)]["value"] is not None else -1
    v2 = hands[str(p2)]["value"] if hands[str(p2)]["value"] is not None else -1
    if v1 == v2:
        winner = None
        text = ("🤝 Both busted — tie! No coins exchanged." if v1 == -1
                else f"🤝 Tie — both had **{v1}**. No coins exchanged.")
    elif v1 > v2:
        winner = p1
        text = (f"<@{p1}> wins (opponent busted)!" if v2 == -1
                else f"<@{p1}> wins with **{v1}** vs **{v2}**!")
    else:
        winner = p2
        text = (f"<@{p2}> wins (opponent busted)!" if v1 == -1
                else f"<@{p2}> wins with **{v2}** vs **{v1}**!")
    changes: list[tuple[int, int, int, str]] = []
    if int(match.get("bet", 0)) > 0:
        if winner is not None:
            settle = await wager.settle_pvp_in_txn(
                conn, guild_id=gid, channel_id=cid,
                subsystem=PVP_ESCROW_SUBSYSTEM, p1_id=p1, p2_id=p2,
                winner_id=winner, reason="blackjack:pvp_win")
            changes = [(u, d, b, "blackjack:pvp_win")
                       for (u, d, b) in settle.balance_changes]
        else:
            refund = await wager.refund_pvp_in_txn(
                conn, guild_id=gid, channel_id=cid,
                subsystem=PVP_ESCROW_SUBSYSTEM, p1_id=p1, p2_id=p2,
                reason="blackjack:pvp_refund")
            changes = [(u, d, b, "blackjack:pvp_refund")
                       for (u, d, b) in refund.balance_changes]
    await games_store.delete_checkpoint(
        conn, guild_id=gid, user_id=p1, channel_id=cid,
        subsystem=PVP_SUBSYSTEM)
    ctx.params["_balance_changes"] = changes
    return {"result": text, "winner": winner,
            "values": {str(p1): v1, str(p2): v2}, "terminal": True,
            **_hands_view(match)}


@workflow("blackjack.record_pvp_move")
async def _record_pvp_move(conn, ctx: WorkflowContext) -> LegOutcome:
    """hit | stand on the actor's OWN hand inside the match row."""
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    sid = str(ctx.params.get("session_id") or "")
    action = str(ctx.params.get("session_action") or
                 ctx.params.get("move") or "")
    p1, cid, match = await _load_match(conn, gid, sid)
    hand = match["hands"].get(str(uid))
    if hand is None:
        raise ValidatorError("This isn't your hand.")
    if hand["done"]:
        raise ValidatorError("Your hand is already finished — waiting "
                             "for your opponent.")
    if action == "hit":
        hand["hand"].append(hand["deck"].pop())
        if bj.hand_value(hand["hand"]) > 21:
            hand["done"], hand["value"] = True, None   # None → bust (-1)
    elif action == "stand":
        hand["done"], hand["value"] = True, bj.hand_value(hand["hand"])
    else:
        raise ValidatorError(games_session.EXPIRED_MESSAGE)
    settled = await _maybe_settle_pvp(conn, ctx, gid, cid, match)
    if settled is not None:
        return LegOutcome(step=StepResult(uid, "pvp_move", True), before={},
                          after=settled)
    await games_store.upsert_checkpoint(
        conn, guild_id=gid, user_id=p1, channel_id=cid,
        subsystem=PVP_SUBSYSTEM, state=match, version=PVP_VERSION,
        now=_now(ctx))
    ctx.params["_balance_changes"] = []
    payload = {"hand": list(hand["hand"]),
               "hand_value": bj.hand_value(hand["hand"]),
               "done": hand["done"], "terminal": False,
               "session_id": sid, **_hands_view(match),
               "components": _components(sid, "hit", "stand")}
    return LegOutcome(step=StepResult(uid, "pvp_move", True), before={},
                      after=payload)


# --- tournament money legs ----------------------------------------------------------------


@workflow("blackjack.record_tournament_open")
async def _record_tournament_open(conn, ctx: WorkflowContext) -> LegOutcome:
    """Registration opens: write the shipped ACTIVE_TOURNAMENT runtime flag
    (guild_settings {key: active_tournament, value: blackjack} — the row
    the bjtournament golden pins). The registration window itself is
    in-memory orchestration state (sb/domain/blackjack/tournament.py),
    exactly the shipped cog's posture."""
    from sb.domain.games import tournament_flag

    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    await tournament_flag.set_active(conn, guild_id=gid, game="blackjack")
    ctx.params["_balance_changes"] = []
    return LegOutcome(step=StepResult(uid, "tournament_open", True),
                      before={}, after={"flag": "blackjack"})


@workflow("blackjack.record_tournament_abort")
async def _record_tournament_abort(conn, ctx: WorkflowContext) -> LegOutcome:
    """Tournament cancelled (no players / nobody could afford the fee):
    clear the runtime flag and refund any entry rows atomically (the
    defensive twin of the boot escrow recovery)."""
    from sb.domain.games import tournament_flag

    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    await tournament_flag.clear_active(conn, guild_id=gid)
    rows = await games_store.lock_rows_for_settlement(
        conn, guild_id=gid, subsystem=TOURNAMENT_SUBSYSTEM)
    changes: list[tuple[int, int, int, str]] = []
    for row in rows:
        stake = int((row.get("state") or {}).get("bet", 0) or 0)
        entrant = int(row["user_id"])
        await games_store.delete_checkpoint_by_id(conn, row_id=row["id"])
        if stake > 0:
            balance = await wager.credit_in_txn(
                conn, guild_id=gid, user_id=entrant, amount=stake,
                reason="blackjack:entry_refund", actor_id=entrant)
            changes.append((entrant, stake, balance,
                            "blackjack:entry_refund"))
    ctx.params["_balance_changes"] = changes
    return LegOutcome(step=StepResult(uid, "tournament_abort", True),
                      before={}, after={"refunded": len(changes)})


@workflow("blackjack.record_tournament_enter")
async def _record_tournament_enter(conn, ctx: WorkflowContext) -> LegOutcome:
    """One paid entry at LAUNCH (the shipped ``_launch_tournament`` loop's
    per-player ``enter_tournament`` call — reason string verbatim)."""
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    fee = int(ctx.params.get("fee", 0) or 0)
    rounds = int(ctx.params.get("rounds", 5) or 5)
    balance = await wager.enter_tournament_in_txn(
        conn, guild_id=gid, user_id=uid, channel_id=0,
        subsystem=TOURNAMENT_SUBSYSTEM, version=TOURNAMENT_VERSION,
        fee=fee, reason="tournament:entry_fee", now=_now(ctx),
        extra_state={"rounds": rounds})
    ctx.params["_balance_changes"] = (
        [(uid, -fee, balance, "tournament:entry_fee")] if fee > 0 else [])
    return LegOutcome(step=StepResult(uid, "tournament_enter", True),
                      before={}, after={"fee": fee, "balance": balance})


@workflow("blackjack.record_tournament_payout")
async def _record_tournament_payout(conn, ctx: WorkflowContext) -> LegOutcome:
    """The champion settle — shipped call site verbatim
    (``blackjack:tournament_win`` pot / ``free_reward=200`` under
    ``blackjack:tournament_free_reward``) + the shipped end-of-tournament
    ``clear_active`` in the SAME txn.

    SETTLE-ONCE (the #130 free-branch race, closed by construction): the
    flag-row delete runs FIRST and is the check-and-set — the free branch
    has no escrow rows to consume, so a second racing payout would re-pay
    the consolation; keying settle on the atomic row-deletion count makes
    it fire exactly once (the loser of the race deletes zero rows and
    pays nothing)."""
    from sb.domain.games import tournament_flag

    gid = int(ctx.guild_id or 0)
    winner = ctx.params.get("winner_id")
    winner = int(winner) if winner is not None else None
    cleared = await tournament_flag.clear_active(conn, guild_id=gid)
    if not cleared:
        ctx.params["_balance_changes"] = []
        return LegOutcome(step=StepResult(winner or 0, "tournament_payout",
                                          False),
                          before={}, after={"paid": False, "amount": 0})
    settle = await wager.payout_tournament_in_txn(
        conn, guild_id=gid, subsystem=TOURNAMENT_SUBSYSTEM,
        winner_id=winner, reason="blackjack:tournament_win",
        free_reward=int(ctx.params.get("free_reward", 0) or 0),
        free_reason="blackjack:tournament_free_reward")
    reason = ("blackjack:tournament_win"
              if int(ctx.params.get("entry_fee", 0) or 0) > 0
              else "blackjack:tournament_free_reward")
    ctx.params["_balance_changes"] = [
        (u, d, b, reason) for (u, d, b) in settle.balance_changes]
    return LegOutcome(step=StepResult(winner or 0, "tournament_payout",
                                      settle.paid),
                      before={},
                      after={"paid": settle.paid, "amount": settle.amount,
                             "balance": settle.new_winner_balance})


# --- op table ----------------------------------------------------------------------------

_BALANCE_EMITS = (
    EventEmitSpec("economy.balance_changed",
                  WorkflowRef("games.balance_payload_0"),
                  DeliveryClass.BEST_EFFORT),
    EventEmitSpec("economy.balance_changed",
                  WorkflowRef("games.balance_payload_1"),
                  DeliveryClass.BEST_EFFORT),
)


def _op(op_key: str, verb: str, leg_ref: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="blackjack", lane=WorkflowLane.DOMAIN,
        authority_ref="user",
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(leg_ref),
                      "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=_BALANCE_EMITS)


SOLO_START = _op("blackjack.solo_start", "blackjack_dealt",
                 "blackjack.record_solo_start")
SOLO_HIT = _op("blackjack.solo_hit", "blackjack_hit",
               "blackjack.record_solo_hit")
SOLO_STAND = _op("blackjack.solo_stand", "blackjack_settled",
                 "blackjack.record_solo_stand")
SOLO_DOUBLE = _op("blackjack.solo_double", "blackjack_settled",
                  "blackjack.record_solo_double")
PVP_CHALLENGE = _op("blackjack.pvp_challenge", "blackjack_challenge",
                    "blackjack.record_pvp_challenge")
PVP_ACCEPT = _op("blackjack.pvp_accept", "blackjack_pvp_escrowed",
                 "blackjack.record_pvp_accept")
PVP_DECLINE = _op("blackjack.pvp_decline", "blackjack_pvp_declined",
                  "blackjack.record_pvp_decline")
PVP_MOVE = _op("blackjack.pvp_move", "blackjack_pvp_move",
               "blackjack.record_pvp_move")
TOURN_OPEN = _op("blackjack.tournament_open", "tournament_opened",
                 "blackjack.record_tournament_open")
TOURN_ABORT = _op("blackjack.tournament_abort", "tournament_aborted",
                  "blackjack.record_tournament_abort")
TOURN_ENTER = _op("blackjack.tournament_enter", "tournament_entered",
                  "blackjack.record_tournament_enter")
TOURN_PAYOUT = _op("blackjack.tournament_payout", "tournament_paid",
                   "blackjack.record_tournament_payout")

_OPS = (SOLO_START, SOLO_HIT, SOLO_STAND, SOLO_DOUBLE, PVP_CHALLENGE,
        PVP_ACCEPT, PVP_DECLINE, PVP_MOVE, TOURN_OPEN, TOURN_ABORT,
        TOURN_ENTER, TOURN_PAYOUT)

_REF_TABLE = (
    ("blackjack.record_solo_start", _record_solo_start),
    ("blackjack.record_solo_hit", _record_solo_hit),
    ("blackjack.record_solo_stand", _record_solo_stand),
    ("blackjack.record_solo_double", _record_solo_double),
    ("blackjack.record_pvp_challenge", _record_pvp_challenge),
    ("blackjack.record_pvp_accept", _record_pvp_accept),
    ("blackjack.record_pvp_decline", _record_pvp_decline),
    ("blackjack.record_pvp_move", _record_pvp_move),
    ("blackjack.record_tournament_open", _record_tournament_open),
    ("blackjack.record_tournament_abort", _record_tournament_abort),
    ("blackjack.record_tournament_enter", _record_tournament_enter),
    ("blackjack.record_tournament_payout", _record_tournament_payout),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):  # P2-resolution marker; the engine resolves via REGISTRY
        from sb.kernel.workflow import engine

        return await engine.run(op, ctx)
    return _run


def _register_op_markers() -> None:
    from sb.spec.refs import is_registered, workflow as _workflow

    for op in _OPS:
        if not is_registered(WorkflowRef(op.op_key)):
            _workflow(op.op_key)(_op_runner(op))


def register_ops() -> None:
    for op in _OPS:
        try:
            REGISTRY.register(op)
        except ValueError as exc:
            if "duplicate CompoundOpSpec" not in str(exc):
                raise
    _register_op_markers()


def ensure_ops_refs() -> None:
    from sb.spec.refs import is_registered, workflow as _workflow

    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    _register_op_markers()
