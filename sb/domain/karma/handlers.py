"""Karma command handlers (band 4) — thin HandlerRef routes over the
audited seam. The bot-recipient check needs a Discord member object —
that pre-filter is the live adapter's (the shipped cog kept it cog-side
too); the data-level rules all enforce in the K7 leg.
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["Reply", "ensure_handler_refs"]


@dataclass(frozen=True)
class Reply:
    outcome: str
    user_message: str


def _ctx_from_req(req, params: dict):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=req.actor, guild_id=int(req.guild_id or 0),
        request_id=req.request_id, confirmed=req.confirmed, params=params)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("karma.thanks")):
        return

    @handler("karma.thanks")
    async def thanks(req) -> Reply:
        """!thanks @user [reason] (aliases rep/thank; also !karma add)."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            return Reply(BLOCKED, "Usage: `!thanks @user [reason]`")
        result = await engine.run(
            WorkflowRef("karma.give"),
            _ctx_from_req(req, {"argv": argv, "source": "command"}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not give karma.")
        after = (result.after or {}).get("give", {})
        actor = int(getattr(req.actor, "user_id", 0) or 0)
        return Reply(SUCCESS,
                     f"✨ <@{actor}> gave karma to "
                     f"<@{after.get('to_user', 0)}> — they now have "
                     f"**{after.get('new_total', 0)}** karma.")

    @handler("karma.card_view")
    async def card_view(req) -> Reply:
        """!karma [@user] / /karma — the karma standing card."""
        from sb.domain.karma import service

        gid = int(req.guild_id or 0)
        target = int(getattr(req.actor, "user_id", 0) or 0)
        for token in tuple(req.args.get("argv", ()) or ()):
            stripped = str(token).strip("<@!>")
            if stripped.isdigit():
                target = int(stripped)
                break
        record = await service.get_record(gid, target)
        return Reply(SUCCESS, service.karma_card_text(target, record))


_register()


def ensure_handler_refs() -> None:
    _register()
