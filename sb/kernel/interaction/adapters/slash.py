"""The slash adapter (spec 02 §3.7 — generalizes `from_interaction`,
`command_access.py:462`). `args = interaction.namespace`."""

from __future__ import annotations

from sb.kernel.interaction.adapters import actor_from_member, lookup_target
from sb.kernel.interaction.request import ResolveRequest, Surface
from sb.kernel.interaction.resolve import resolve


def request_from_interaction(interaction: object, *, responder) -> ResolveRequest | None:
    """Build the ResolveRequest for an app-command interaction. None =>
    unknown command (the caller renders NOT_FOUND)."""
    command = getattr(interaction, "command", None)
    key = getattr(command, "qualified_name", None) or getattr(command, "name", "")
    target = lookup_target(str(key), Surface.SLASH)
    if target is None:
        return None
    guild = getattr(interaction, "guild", None)
    namespace = getattr(interaction, "namespace", None)
    args = dict(vars(namespace)) if namespace is not None else {}
    args.setdefault("interaction_id", getattr(interaction, "id", None))
    args.setdefault("user_id", getattr(getattr(interaction, "user", None), "id", None))
    return ResolveRequest(
        surface=Surface.SLASH,
        target=target,
        actor=actor_from_member(
            getattr(interaction, "user", None),
            guild_owner_id=getattr(guild, "owner_id", None),
            is_dm=guild is None,
        ),
        guild_id=getattr(guild, "id", None),
        channel_id=getattr(interaction, "channel_id", None),
        args=args,
        responder=responder,
        origin=interaction,
    )


async def dispatch_interaction(interaction: object, *, responder) -> object | None:
    """The entry the composition root wires under the app-command callback —
    every slash command funnels through resolve()."""
    req = request_from_interaction(interaction, responder=responder)
    if req is None:
        await responder.deny("Unknown command.", ephemeral=True)
        return None
    return await resolve(req)
