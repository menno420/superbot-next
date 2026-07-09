"""The `g1:` dynamic-session seam (band 6) — the games-band half of the
§3.4 versioned custom-id scheme.

The K8 router already parses ``g1:<game_key>:<session_id>:<action>``
(sb/kernel/panels/router.parse_g1) and the COMPONENT adapter exposes the
``install_dynamic_dispatcher`` port (S9b). This module is the port's real
implementation:

* each game REGISTERS its session-action table
  (:func:`register_session_actions`) — ``game_key`` must be the declaring
  manifest's subsystem key, and a second claim on the same key is refused
  (two games can never mint overlapping session ids: the prefix
  reservation of design-spec §3.4, enforced by construction; the K1
  custom_id-prefix rows ride the Stage-2 harvest);
* the dispatcher parses the route, resolves the claiming game's declared
  ``PanelActionSpec`` for the action token, and RE-ENTERS ``resolve()``
  with ``session_id``/``session_action`` in args — authority, cooldown,
  audit, and the K7 lanes all apply exactly as for a static component;
* an unclaimed game key or unknown action token yields the polite-expiry
  response (schema evolution can never crash routing or strand a
  clickable corpse).

``session_id`` is the game_state checkpoint key rendered as
``<guild_id>.<user_id>.<channel_id>`` — the id ROUTES to a recovered
session, it is never itself the authority (the row is; ownership is
re-checked in the leg against the checkpoint row).
"""

from __future__ import annotations

import logging
from typing import Mapping

from sb.kernel.interaction.adapters import actor_from_member
from sb.kernel.interaction.adapters.component import install_dynamic_dispatcher
from sb.kernel.interaction.request import ResolveRequest, Surface, TargetRef
from sb.kernel.panels.router import DynamicRoute

logger = logging.getLogger("sb.domain.games.session")

__all__ = [
    "install_games_dispatcher",
    "mint_session_id",
    "mint_custom_id",
    "parse_session_id",
    "register_session_actions",
    "registered_session_games",
    "reset_session_registry_for_tests",
]

# game_key -> {action_token: PanelActionSpec-shaped spec}
_REGISTRY: dict[str, Mapping[str, object]] = {}

EXPIRED_MESSAGE = "This session has expired — start a new one."


def register_session_actions(game_key: str,
                             actions: Mapping[str, object]) -> None:
    """Claim *game_key*'s ``g1:<game_key>:`` prefix with its action table.

    Idempotent for an identical re-registration (ENSURE_REFS re-arm); a
    DIFFERING second claim raises — the §3.4 prefix-collision refusal."""
    prior = _REGISTRY.get(game_key)
    if prior is not None:
        if set(prior.keys()) == set(actions.keys()):
            _REGISTRY[game_key] = dict(actions)
            return
        raise ValueError(
            f"g1 prefix {game_key!r} already claimed with a differing "
            f"action table")
    _REGISTRY[game_key] = dict(actions)


def registered_session_games() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def reset_session_registry_for_tests() -> None:
    _REGISTRY.clear()


def mint_session_id(guild_id: int, user_id: int, channel_id: int) -> str:
    return f"{int(guild_id)}.{int(user_id)}.{int(channel_id)}"


def parse_session_id(session_id: str) -> tuple[int, int, int] | None:
    parts = session_id.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return None
    return int(parts[0]), int(parts[1]), int(parts[2])


def mint_custom_id(game_key: str, session_id: str, action: str) -> str:
    """``g1:<game_key>:<session_id>:<action>`` — ≤100 chars by
    construction (snowflake triple ≈ 77 with the longest action)."""
    custom_id = f"g1:{game_key}:{session_id}:{action}"
    if len(custom_id) > 100:
        raise ValueError(f"custom_id over the 100-char budget: {custom_id!r}")
    return custom_id


async def _dispatch(route: DynamicRoute, interaction: object,
                    responder: object) -> object | None:
    """The installed DynamicDispatcher — re-enters resolve() with the
    claiming game's declared action spec."""
    from sb.kernel.interaction.resolve import resolve

    table = _REGISTRY.get(route.key)
    spec = None if table is None else table.get(route.action)
    if spec is None:
        if responder is not None:
            await responder.deny(EXPIRED_MESSAGE, ephemeral=True)
        return None
    guild = getattr(interaction, "guild", None)
    req = ResolveRequest(
        surface=Surface.COMPONENT,
        target=TargetRef(key=f"g1:{route.key}.{route.action}", spec=spec),
        actor=actor_from_member(getattr(interaction, "user", None),
                                guild_owner_id=getattr(guild, "owner_id",
                                                       None),
                                is_dm=guild is None),
        guild_id=getattr(guild, "id", None),
        channel_id=getattr(interaction, "channel_id", None),
        args={"session_id": route.session_id,
              "session_action": route.action,
              "interaction_id": getattr(interaction, "id", None)},
        responder=responder,
        origin=interaction,
    )
    return await resolve(req)


def install_games_dispatcher() -> None:
    """Arm the COMPONENT adapter's g<N>: fall-through with this registry.
    Called at games-manifest import + ENSURE_REFS (idempotent)."""
    install_dynamic_dispatcher(_dispatch)
