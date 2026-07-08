"""The component adapter (spec 02 §3.7) — buttons AND selects (replaces the
shipped `interaction_router.dispatch` second resolver; GAINS cooldown, L-5).
`target = "<panel_id>.<action_id|selector_id>"` from the custom_id. Also
carries the confirm re-entry (`sb.confirm:<target_key>:<request_id>` ⇒
`confirmed=True` on the SAME target — authority re-resolves structurally,
`re_check_actor` satisfied).

S9b: when the target index has no entry, the custom_id falls through to the
§3.4 panel router with its FIXED precedence — static table (panel component
bindings + engine nav slots) → versioned `g<N>:` dynamic parse → the polite
expiry terminal. Panel component clicks re-enter `resolve()` with the
binding's spec as the target; nav slots dispatch to the panel engine
(re-resolved from the registry at click time, §2.4)."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from sb.kernel.interaction.adapters import actor_from_member, lookup_target
from sb.kernel.interaction.request import ResolveRequest, Surface, TargetRef
from sb.kernel.interaction.resolve import resolve
from sb.kernel.panels import engine as panel_engine
from sb.kernel.panels.registry import ComponentBinding, NavBinding
from sb.kernel.panels.router import DynamicRoute, ExpiredRoute, route as route_custom_id

logger = logging.getLogger("sb.kernel.interaction.adapters.component")

CONFIRM_PREFIX = "sb.confirm:"

# g<N>: dynamic-session dispatch port — the games band installs the real
# session dispatcher; until then a dynamic id gets the polite expiry.
DynamicDispatcher = Callable[[DynamicRoute, object], Awaitable[object]]
_dynamic_dispatcher: DynamicDispatcher | None = None


def install_dynamic_dispatcher(dispatcher: DynamicDispatcher) -> None:
    global _dynamic_dispatcher
    _dynamic_dispatcher = dispatcher


def reset_dynamic_dispatcher_for_tests() -> None:
    global _dynamic_dispatcher
    _dynamic_dispatcher = None


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
        routed = route_custom_id(target_key)
        if isinstance(routed, ComponentBinding):
            target = TargetRef(key=f"{routed.panel_id}.{routed.component_id}",
                               spec=routed.spec)
        else:
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
    if req is not None:
        return await resolve(req)

    # not a target-index or panel-component id: nav slot, dynamic session,
    # or the polite-expiry terminal (§3.4 precedence, in order).
    data = getattr(interaction, "data", None) or {}
    custom_id = str(data.get("custom_id", "") if isinstance(data, dict)
                    else getattr(data, "custom_id", ""))
    routed = route_custom_id(custom_id)
    if isinstance(routed, NavBinding):
        guild = getattr(interaction, "guild", None)
        nav_req = ResolveRequest(
            surface=Surface.COMPONENT,
            target=TargetRef(key=custom_id, spec=routed),
            actor=actor_from_member(getattr(interaction, "user", None),
                                    guild_owner_id=getattr(guild, "owner_id", None),
                                    is_dm=guild is None),
            guild_id=getattr(guild, "id", None),
            channel_id=getattr(interaction, "channel_id", None),
            args={}, responder=responder, origin=interaction,
        )
        try:
            await panel_engine.handle_nav(routed, nav_req)
        except Exception:  # noqa: BLE001 — nav must never crash the gateway task
            logger.warning("nav dispatch failed for %r", custom_id, exc_info=True)
            await responder.deny("Couldn't open that panel — try again.", ephemeral=True)
        return None
    if isinstance(routed, DynamicRoute) and _dynamic_dispatcher is not None:
        return await _dynamic_dispatcher(routed, interaction)
    expiry = routed if isinstance(routed, ExpiredRoute) else ExpiredRoute(custom_id)
    await responder.deny(expiry.message, ephemeral=True)
    return None
