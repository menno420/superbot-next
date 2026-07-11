"""Karma command handlers (band 4) — thin HandlerRef routes over the
audited seam. The bot-recipient check needs a Discord member object —
that pre-filter is the live adapter's (the shipped cog kept it cog-side
too); the data-level rules all enforce in the K7 leg.

The typed-refusal try/except mirrors cogs/karma_cog.py ``_grant``
verbatim: the SERVICE raises typed errors, the COG composes the user
copy and sends the ``utils/embeds.error`` red envelope — here the
``karma.error_card`` panel (goldens/karma/karma_self_grant_rejected +
karma_repeat_cooldown pin the bytes). The cooldown copy interpolates the
recipient's ``display_name`` — read through the guild-directory port
(the economy author-line precedent), degrading to the mention when no
directory is armed.
"""

from __future__ import annotations

import dataclasses

from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs"]


def _target_id(argv: tuple) -> int | None:
    for token in argv:
        stripped = str(token).strip("<@!>")
        if stripped.isdigit():
            return int(stripped)
    return None


async def _open_card(req, panel_id: str, params: dict) -> None:
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef(panel_id),
                     dataclasses.replace(req, args={**dict(req.args), **params}))


async def _display_name(user_id: int, guild_id: int) -> str:
    from sb.domain.karma.panels import _member_display

    name, _avatar = await _member_display(user_id, guild_id)
    return name


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("karma.thanks")):
        return

    @handler("karma.thanks")
    async def thanks(req) -> Reply:
        """!thanks @user [reason] (aliases rep/thank; also !karma add)."""
        from sb.domain.economy.service import format_remaining
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            return Reply(BLOCKED, "Usage: `!thanks @user [reason]`")

        async def _refuse(message: str) -> Reply:
            # the shipped cog's except-arm: ctx.send(embed=em.error(...))
            # — the red envelope rides karma.error_card; the honest
            # refusal outcome carries NO extra text reply
            await _open_card(req, "karma.error_card", {"error_text": message})
            return Reply(BLOCKED, None)

        ctx = _ctx_from_req(req, {"argv": argv, "source": "command"})
        result = await engine.run(WorkflowRef("karma.give"), ctx)
        if result.outcome != SUCCESS:
            # the typed-refusal marker (ops._mark_refusal — the engine
            # classifies leg exceptions into results, so the class
            # identity never reaches this frame); copy composition stays
            # cog-side, the shipped karma_cog.py except-arms verbatim
            refusal = ctx.params.get("_karma_refusal")
            if isinstance(refusal, dict):
                kind = refusal.get("kind")
                if kind == "self":
                    return await _refuse("You can't give karma to yourself.")
                if kind == "disabled":
                    return await _refuse("Karma is disabled on this server.")
                if kind == "cooldown":
                    name = await _display_name(
                        int(refusal.get("target_id", 0) or 0),
                        int(req.guild_id or 0))
                    return await _refuse(
                        f"You've already thanked {name} recently — try "
                        f"again in "
                        f"{format_remaining(int(refusal.get('retry_after', 0) or 0))}.")
                if kind == "cap":
                    return await _refuse(
                        f"You've reached your daily limit of "
                        f"{int(refusal.get('cap', 0) or 0)} karma grants. "
                        "Come back tomorrow!")
            return Reply(result.outcome,
                         result.user_message or "Could not give karma.")
        after = (result.after or {}).get("give", {})
        actor = int(getattr(req.actor, "user_id", 0) or 0)
        return Reply(SUCCESS,
                     f"✨ <@{actor}> gave karma to "
                     f"<@{after.get('to_user', 0)}> — they now have "
                     f"**{after.get('new_total', 0)}** karma.")

    @handler("karma.card_view")
    async def card_view(req) -> None:
        """!karma [@user] / /karma — the shipped karma standing card
        (karma.card renders the _karma_card embed; the open IS the
        terminal render, pure read)."""
        target = _target_id(tuple(req.args.get("argv", ()) or ()))
        if target is None:
            target = int(getattr(req.actor, "user_id", 0) or 0)
        await _open_card(req, "karma.card", {"karma_target": target})


_register()


def ensure_handler_refs() -> None:
    _register()
