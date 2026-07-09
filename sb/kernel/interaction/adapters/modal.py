"""The modal adapter (spec 02 §3.7): a modal submit is an ACK/entry mechanism
of an EXISTING action (the PanelActionSpec that declared defer_mode=MODAL or
opened a typed-phrase confirm) — no new spec primitive. `args` = the
submitted modal fields."""

from __future__ import annotations

from sb.kernel.interaction.adapters import actor_from_member, lookup_target
from sb.kernel.interaction.adapters.component import parse_custom_id
from sb.kernel.interaction.request import ResolveRequest, Surface, TargetRef
from sb.kernel.interaction.resolve import resolve
from sb.kernel.panels.registry import ComponentBinding
from sb.kernel.panels.router import route as route_custom_id


def _modal_fields(data: object) -> dict:
    """Flatten the modal submit component rows into {custom_id: value}."""
    fields: dict = {}
    rows = (data.get("components") if isinstance(data, dict)
            else getattr(data, "components", None)) or ()
    for row in rows:
        inner = (row.get("components") if isinstance(row, dict)
                 else getattr(row, "components", None)) or ()
        for comp in inner:
            cid = (comp.get("custom_id") if isinstance(comp, dict)
                   else getattr(comp, "custom_id", None))
            value = (comp.get("value") if isinstance(comp, dict)
                     else getattr(comp, "value", None))
            if cid:
                fields[str(cid)] = value
    return fields


def request_from_modal(interaction: object, *, responder) -> ResolveRequest | None:
    data = getattr(interaction, "data", None) or {}
    custom_id = str(data.get("custom_id", "") if isinstance(data, dict)
                    else getattr(data, "custom_id", ""))
    target_key, confirmed, request_id = parse_custom_id(custom_id)
    target = lookup_target(target_key, Surface.MODAL) or lookup_target(
        target_key, Surface.COMPONENT)
    if target is None:
        # G-10 fallthrough (the component adapter's precedence, mirrored):
        # a panel-declared modal's custom-id root routes back to the
        # declaring PanelActionSpec via the §3.4 static table.
        routed = route_custom_id(target_key)
        if isinstance(routed, ComponentBinding):
            target = TargetRef(key=f"{routed.panel_id}.{routed.component_id}",
                               spec=routed.spec)
        else:
            return None
    guild = getattr(interaction, "guild", None)
    args = _modal_fields(data)
    args.setdefault("interaction_id", getattr(interaction, "id", None))
    kwargs = dict(
        surface=Surface.MODAL, target=target,
        actor=actor_from_member(getattr(interaction, "user", None),
                                guild_owner_id=getattr(guild, "owner_id", None),
                                is_dm=guild is None),
        guild_id=getattr(guild, "id", None),
        channel_id=getattr(interaction, "channel_id", None),
        args=args, responder=responder, origin=interaction,
        confirmed=confirmed,
    )
    if request_id:
        kwargs["request_id"] = request_id
    return ResolveRequest(**kwargs)


async def dispatch_modal(interaction: object, *, responder) -> object | None:
    req = request_from_modal(interaction, responder=responder)
    if req is None:
        await responder.deny("This form is no longer available.", ephemeral=True)
        return None
    return await resolve(req)
