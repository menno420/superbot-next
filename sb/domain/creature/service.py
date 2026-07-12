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
  Accept is a declared pending terminal (combat engine = successor
  slice; see panels.py's under-port ledger).
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
        # UNDER-PORT: the shipped `opponent.bot` guard ('🤖 You can't
        # battle a bot…') needs a member bot-flag read the
        # guild-directory port does not carry — the guard cannot fire
        # until the seam grows (no invented data).
        await _open(req, "creature.challenge",
                    {"cb_challenger_id": challenger,
                     "cb_opponent_id": opponent})
        return Reply(SUCCESS, None)

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
