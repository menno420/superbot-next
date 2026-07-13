"""Creature handlers (band 6 / parity flip) — the shipped cog semantics
over the ported panels (sb/domain/creature/panels.py):

* ``!catch`` (alias ``hunt``) + the hub's Catch button — one outing
  through the audited ``creature.catch`` K7 lane (sweep-SKIPPED in the
  imported corpus: 'unseeded private RNG in creature spawn selection' —
  parity/goldens/_sweep_skips.json; no golden gates the reply bytes).
* ``!dex`` / ``!dextop`` / ``!cbrecord`` / ``!cbattletop`` — the four
  shipped embed cards, opened as component-less result panels (the
  karma-card lane; the sweep goldens pin the empty-state bytes).
* ``!cbattle @member`` — the shipped guards (self / bot) + the
  CONTENT-only Accept/Decline challenge panel
  (goldens/creature/sweep_cbattle pins the open bytes). The shipped
  bot guard needs a member-flag read the guild-directory port does not
  carry yet — ledgered under-port (the avatar-fetch degradation
  posture: no invented data, the guard simply cannot fire).
* Decline — the shipped '❌ {name} declined the challenge.' in-place
  edit (refresh_session_view, buttons disabled, session expired).
* Accept — the shipped AUTO-RESOLVE (D-0079): build both teams,
  run the pure engine (sb/domain/creature/battle.py), write the W/L
  pair + battle-win xp through the audited creature.record_battle_result
  lane, and re-render the card as the outcome embed (settle-once via
  the session teardown; the deathmatch challenge-card lineage).
"""

from __future__ import annotations

import dataclasses

from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["Reply", "ensure_handler_refs"]

_MENTION_CHARS = "<@!>"


def _parse_target(argv: tuple) -> int | None:
    """First-arg member id from the prefix argv (``<@id>`` or bare id —
    the moderation parse posture)."""
    if not argv:
        return None
    token = str(argv[0]).strip()
    bare = token.strip(_MENTION_CHARS)
    if bare.isdigit():
        return int(bare)
    return None


async def _opponent_is_bot(req, opponent: int) -> bool:
    """True iff the opponent is a bot member, read through the guild
    directory bot-flag seam (MemberInfo.is_bot). Degrades to False when the
    directory is absent/headless (the avatar-fetch degradation posture — the
    guard cannot invent data, so it simply cannot fire)."""
    try:
        from sb.domain.utility.service import guild_directory

        info = await guild_directory().member_info(
            int(req.guild_id or 0), int(opponent))
    except Exception:  # noqa: BLE001 — no directory ⇒ the guard degrades
        return False
    return bool(getattr(info, "is_bot", False))


async def _open(req, panel_id: str, params: dict | None = None) -> None:
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(
        PanelRef(panel_id),
        dataclasses.replace(req, args={**dict(req.args),
                                       **dict(params or {})}))


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("creature.catch_route")):
        return

    @handler("creature.catch_route")
    async def catch_route(req) -> Reply:
        """!catch (alias hunt) + the hub's Catch button — one outing
        through the audited lane. Sweep-skipped in the corpus (unseeded
        RNG), so no golden gates the reply bytes; the shipped result
        embed (build_catch_result_embed) is ledgered under-port — the
        op's own message line carries the outcome."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        result = await engine.run(WorkflowRef("creature.catch"),
                                  _ctx_from_req(req, {}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "The wilds are quiet.")
        after = (result.after or {}).get("catch", {})
        return Reply(SUCCESS, after.get("message", ""))

    @handler("creature.dex_view")
    async def dex_view(req) -> Reply:
        """!dex (alias collection) + the hub's Dex button — the shipped
        per-element collection embed (creature.dex_card renders it)."""
        await _open(req, "creature.dex_card")
        return Reply(SUCCESS, None)

    @handler("creature.dextop_view")
    async def dextop_view(req) -> Reply:
        """!dextop (alias topcatchers) — the shipped 🐾 Top Collectors
        board (goldens/creature/sweep_dextop pins the empty state)."""
        await _open(req, "creature.collectors_card")
        return Reply(SUCCESS, None)

    @handler("creature.battle_record_view")
    async def battle_record_view(req) -> Reply:
        """!cbrecord [member] (alias battlerecord) — the shipped W/L
        record card; the target defaults to the invoker."""
        target = _parse_target(tuple(req.args.get("argv", ()) or ()))
        params = {"record_target": target} if target else {}
        await _open(req, "creature.record_card", params)
        return Reply(SUCCESS, None)

    @handler("creature.battletop_view")
    async def battletop_view(req) -> Reply:
        """!cbattletop (aliases pvptop, battletop) + the hub's Ladder
        button — the shipped ⚔️ Top Trainers ladder."""
        await _open(req, "creature.battletop_card")
        return Reply(SUCCESS, None)

    @handler("creature.rules_view")
    async def rules_view(req) -> Reply:
        """The hub's 📖 How-to-play affordance — the shipped static
        rules card (creature.rules_card, grammar-rendered)."""
        await _open(req, "creature.rules_card")
        return Reply(SUCCESS, None)

    @handler("creature.cbattle_route")
    async def cbattle_route(req) -> Reply:
        """!cbattle @member (alias creaturebattle) — the shipped guards
        + the Accept/Decline challenge send
        (cogs/creature_battle_cog.py; goldens/creature/sweep_cbattle
        pins the open bytes)."""
        from sb.kernel.interaction.errors import ValidatorError

        challenger = int(getattr(req.actor, "user_id", 0) or 0)
        opponent = _parse_target(tuple(req.args.get("argv", ()) or ()))
        if opponent is None:
            # the shipped MemberConverter miss — a polite user_error
            # denial (the moderation parse posture; no golden pins the
            # missing-arg byte, the sweep drove the argful form).
            raise ValidatorError(
                "member", "no opponent supplied (mention or user id)")
        if opponent == challenger:
            # cogs/creature_battle_cog.py, verbatim.
            return Reply(BLOCKED, "🪞 You can't battle yourself — "
                                  "challenge someone else!")
        # the shipped `opponent.bot` guard (cogs/creature_battle_cog.py,
        # verbatim) — now live over the guild-directory bot-flag seam
        # (MemberInfo.is_bot). Read through the directory (never the
        # interaction payload) so the kernel stays Member-free and ONE
        # bot-flag read site serves both the prefix and picker paths; a
        # headless/absent directory degrades to no-block (the avatar-fetch
        # degradation posture — no invented data).
        if await _opponent_is_bot(req, opponent):
            return Reply(BLOCKED, "🤖 You can't battle a bot — "
                                  "challenge a real trainer!")
        await _open(req, "creature.challenge",
                    {"cb_challenger_id": challenger,
                     "cb_opponent_id": opponent})
        return Reply(SUCCESS, None)

    @handler("creature.challenge_pick")
    async def challenge_pick(req) -> Reply:
        """The native user-select opponent picker's selection
        (_OpponentSelect.callback, verbatim): the three shipped guards —
        non-member ('Both trainers must be server members.'), bot ('🤖 You
        can't battle a bot…'), self ('🪞 You can't battle yourself — pick
        someone else!') — then open the challenge card. The chosen id
        arrives on the ordinary select ``values`` round-trip (the kernel
        never dereferences the interaction's resolved members)."""
        from sb.domain.utility.service import guild_directory

        values = tuple(req.args.get("values", ()) or ())
        if not values:
            # an empty select round-trip — nothing to open (the picker
            # stays up); never an error byte.
            return Reply(SUCCESS, None)
        opponent = _parse_target((str(values[0]),))
        challenger = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        if opponent is None:
            return Reply(BLOCKED, "Both trainers must be server members.")
        # non-member guard: the opponent must resolve as a guild member
        # through the directory (the shipped isinstance(..., Member) check).
        try:
            info = await guild_directory().member_info(gid, opponent)
        except Exception:  # noqa: BLE001 — unresolvable ⇒ not a member
            info = None
        if info is None:
            return Reply(BLOCKED, "Both trainers must be server members.")
        if bool(getattr(info, "is_bot", False)):
            return Reply(BLOCKED, "🤖 You can't battle a bot — "
                                  "challenge a real trainer!")
        if opponent == challenger:
            # the shipped picker copy ('pick someone else!') — distinct
            # from the prefix cog's 'challenge someone else!'.
            return Reply(BLOCKED, "🪞 You can't battle yourself — "
                                  "pick someone else!")
        await _open(req, "creature.challenge",
                    {"cb_challenger_id": challenger,
                     "cb_opponent_id": opponent})
        return Reply(SUCCESS, None)

    @handler("creature.challenge_rematch")
    async def challenge_rematch(req) -> Reply:
        """The shipped 🔄 Rematch (CreatureRematchView.rematch): either
        fighter may click; the clicker re-challenges (becomes challenger),
        the other fighter becomes the opponent who Accepts/Declines. No new
        battle logic — it re-issues a fresh challenge card (the shipped
        re-challenge copy rides the ``cb_rematch`` flag)."""
        clicker = int(getattr(req.actor, "user_id", 0) or 0)
        fighter_a = int(req.args.get("cb_challenger_id") or 0)
        fighter_b = int(req.args.get("cb_opponent_id") or 0)
        if clicker not in (fighter_a, fighter_b):
            # CreatureRematchView.interaction_check, verbatim.
            return Reply(BLOCKED,
                         "Only the two fighters can start a rematch — "
                         "challenge with `!cbattle` to play your own.")
        challenger = clicker
        opponent = fighter_b if challenger == fighter_a else fighter_a
        await _open(req, "creature.challenge",
                    {"cb_challenger_id": challenger,
                     "cb_opponent_id": opponent,
                     "cb_rematch": True})
        return Reply(SUCCESS, None)

    @handler("creature.challenge_accept")
    async def challenge_accept(req) -> Reply:
        """The shipped Accept click — the oracle AUTO-RESOLVES on Accept (no
        turn buttons): build both teams from each player's collection at a
        normalized level, run the pure engine, then in the already-live
        audited record lane (creature.record_battle_result) write the W/L
        pair + the winner's battle-win game-xp in ONE txn, and re-render the
        challenge card in place as the outcome embed (settle-once via the
        session teardown — the deathmatch challenge-card lineage; D-0079).

        The battle RNG is seeded deterministically from the battle inputs so
        the resolution is replayable/goldenable (the oracle's injectable-rng
        seam), while each live battle still varies with the clock."""
        import random
        import time

        from sb.domain.creature import battle_service, panels, store
        from sb.kernel.panels.engine import refresh_session_view
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        gid = int(req.guild_id or 0)
        challenger = int(req.args.get("cb_challenger_id") or 0)
        opponent = int(req.args.get("cb_opponent_id")
                       or getattr(req.actor, "user_id", 0) or 0)
        message = getattr(req.origin, "message", None)
        message_key = str(getattr(message, "id", "") or "")

        now = int(time.time())
        rng = random.Random(f"cbattle:{gid}:{challenger}:{opponent}:{now}")
        result = await battle_service.resolve_pvp(
            challenger, opponent, gid, rng=rng)

        if result is None:
            # neither/one fighter has a usable team — settle with the nudge.
            params = {**dict(req.args), "stage": "resolved",
                      "cb_no_team": True}
            if message_key and await refresh_session_view(
                    req, message_key=message_key, params=params, expire=True):
                return Reply(SUCCESS, None)
            return Reply(SUCCESS, battle_service.NO_TEAM_MSG)

        if result.a_won:
            winner_id, loser_id = challenger, opponent
        else:
            winner_id, loser_id = opponent, challenger

        # the audited W/L + battle-win xp write (one txn, xp events after
        # commit) — the engine feeds the record lane that was live + waiting.
        op_result = await engine.run(
            WorkflowRef("creature.record_battle_result"),
            _ctx_from_req(req, {"winner_id": winner_id,
                                "loser_id": loser_id}))
        if op_result.outcome != SUCCESS:
            return Reply(op_result.outcome,
                         op_result.user_message
                         or "The battle couldn't be recorded.")
        after = next(iter((op_result.after or {}).values()), {})
        xp_note = (f"🎉 Reached game level **{after['new_level']}**!"
                   if after.get("leveled_up") else None)

        winner_rec = await store.get_battle_record(winner_id, gid)
        loser_rec = await store.get_battle_record(loser_id, gid)
        records = {winner_id: winner_rec, loser_id: loser_rec}
        challenger_name = await panels._member_display(challenger, gid)
        opponent_name = await panels._member_display(opponent, gid)
        description, fields = battle_service.build_result_view(
            challenger_name, opponent_name, challenger, opponent, result,
            winner_id=winner_id, records=records, xp_note=xp_note)

        params = {**dict(req.args), "stage": "resolved",
                  "cb_desc": description, "cb_fields": [list(f) for f in fields]}
        if message_key and await refresh_session_view(
                req, message_key=message_key, params=params, expire=True):
            return Reply(SUCCESS, None)
        # vanished session (restart/eviction) — the record is authoritative;
        # degrade to a text line naming the winner.
        return Reply(SUCCESS, f"⚔️ Creature battle resolved — 🏆 <@{winner_id}> wins!")

    @handler("creature.challenge_decline")
    async def challenge_decline(req) -> Reply:
        """The shipped Decline click — edit the challenge message in
        place ('❌ {name} declined the challenge.', both buttons
        disabled) and stop the view (challenge.py, verbatim)."""
        from sb.kernel.panels.engine import refresh_session_view

        message = getattr(req.origin, "message", None)
        message_key = str(getattr(message, "id", "") or "")
        params = {**dict(req.args), "stage": "declined"}
        if message_key and await refresh_session_view(
                req, message_key=message_key, params=params, expire=True):
            return Reply(SUCCESS, None)
        # vanished session (restart/eviction) — degrade to a text reply.
        return Reply(SUCCESS, "❌ Challenge declined.")


def ensure_handler_refs() -> None:
    _register()


_register()
