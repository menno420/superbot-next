"""The prefix adapter (spec 02 §3.7 — generalizes `from_prefix_ctx`,
`command_access.py:441`). K1 exact name; the fuzzy adapter owns the miss."""

from __future__ import annotations

from sb.kernel.interaction.adapters import actor_from_member, lookup_target
from sb.kernel.interaction.request import ResolveRequest, Surface
from sb.kernel.interaction.resolve import resolve


def request_from_prefix_ctx(ctx: object, *, responder) -> ResolveRequest | None:
    command = getattr(ctx, "command", None)
    key = getattr(command, "qualified_name", None) or getattr(command, "name", "")
    target = lookup_target(str(key), Surface.PREFIX)
    if target is None:
        return None
    guild = getattr(ctx, "guild", None)
    message = getattr(ctx, "message", None)
    args = dict(getattr(ctx, "kwargs", None) or {})
    args.setdefault("message_id", getattr(message, "id", None))
    args.setdefault("user_id", getattr(getattr(ctx, "author", None), "id", None))
    return ResolveRequest(
        surface=Surface.PREFIX,
        target=target,
        actor=actor_from_member(
            getattr(ctx, "author", None),
            guild_owner_id=getattr(guild, "owner_id", None),
            is_dm=guild is None,
        ),
        guild_id=getattr(guild, "id", None),
        channel_id=getattr(getattr(ctx, "channel", None), "id", None),
        args=args,
        responder=responder,
        origin=ctx,
    )


async def dispatch_prefix(ctx: object, *, responder) -> object | None:
    req = request_from_prefix_ctx(ctx, responder=responder)
    if req is None:
        return None            # CommandNotFound — the fuzzy adapter's input
    return await resolve(req)
