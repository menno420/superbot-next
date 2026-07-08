"""The component adapter (spec 02 §3.7) — buttons AND selects (replaces the
shipped `interaction_router.dispatch` second resolver; GAINS cooldown, L-5).
`target = "<panel_id>.<action_id|selector_id>"` from the custom_id. Also
carries the confirm re-entry (`sb.confirm:<target_key>:<request_id>` ⇒
`confirmed=True` on the SAME target — authority re-resolves structurally,
`re_check_actor` satisfied)."""

from __future__ import annotations

from sb.kernel.interaction.adapters import actor_from_member, lookup_target
from sb.kernel.interaction.request import ResolveRequest, Surface
from sb.kernel.interaction.resolve import resolve

CONFIRM_PREFIX = "sb.confirm:"


def parse_custom_id(custom_id: str) -> tuple[str, bool, str | None]:
    """(target_key, confirmed, request_id)."""
    if custom_id.startswith(CONFIRM_PREFIX):
        rest = custom_id[len(CONFIRM_PREFIX):]
        target_key, _, request_id = rest.rpartition(":")
        return target_key, True, (request_id or None)
    return custom_id, False, None


def request_from_component(interaction: object, *, responder,
                           surface: Surface = Surface.COMPONENT) -> ResolveRequest | None:
    data = getattr(interaction, "data", None) or {}
    custom_id = str(data.get("custom_id", "") if isinstance(data, dict)
                    else getattr(data, "custom_id", ""))
    target_key, confirmed, request_id = parse_custom_id(custom_id)
    target = lookup_target(target_key, surface)
    if target is None:
        return None
    guild = getattr(interaction, "guild", None)
    args: dict = {"interaction_id": getattr(interaction, "id", None)}
    values = data.get("values") if isinstance(data, dict) else None
    if values is not None:
        args["values"] = tuple(values)          # select menus carry values
    kwargs = dict(
        surface=surface, target=target,
        actor=actor_from_member(getattr(interaction, "user", None),
                                guild_owner_id=getattr(guild, "owner_id", None),
                                is_dm=guild is None),
        guild_id=getattr(guild, "id", None),
        channel_id=getattr(interaction, "channel_id", None),
        args=args, responder=responder, origin=interaction,
        confirmed=confirmed,
    )
    if request_id:
        kwargs["request_id"] = request_id       # the confirm dedup key
    return ResolveRequest(**kwargs)


async def dispatch_component(interaction: object, *, responder) -> object | None:
    req = request_from_component(interaction, responder=responder)
    if req is None:
        await responder.deny("This control is no longer available.", ephemeral=True)
        return None
    return await resolve(req)
