"""The six surface adapters (frozen L0 spec 02 §3.7) — each builds a
`ResolveRequest` and funnels it through `resolve()`. NOTHING dispatches any
other way (the no-skip fence, `tools/check_no_skip.py`).

Shared here: the actor builder (computes `member_tier` via the ONE
discord-aware read + `role_ids` fresh per interaction — RC-12/A-12) and the
target-index port (key → `TargetRef`), installed by the runtime builder
(`sb.app.build_runtime`).
"""

from __future__ import annotations

from typing import Callable

from sb.kernel.authority.owner import is_platform_owner
from sb.kernel.interaction.request import ActorRef, Surface, TargetRef

__all__ = [
    "actor_from_member",
    "install_target_index",
    "lookup_target",
    "reset_adapter_ports_for_tests",
]

TargetIndex = Callable[[str, Surface], "TargetRef | None"]


def _no_index(key: str, surface: Surface) -> TargetRef | None:
    return None


_target_index: TargetIndex = _no_index


def install_target_index(index: TargetIndex) -> None:
    global _target_index
    _target_index = index


def lookup_target(key: str, surface: Surface) -> TargetRef | None:
    return _target_index(key, surface)


def reset_adapter_ports_for_tests() -> None:
    global _target_index
    _target_index = _no_index


def actor_from_member(member: object, *, guild_owner_id: int | None,
                      is_dm: bool = False) -> ActorRef:
    """Build the discord-free ActorRef from a Member/User (RC-12 batch)."""
    from sb.adapters.discord.member_tier import (
        member_tier_from_member,
        role_ids_from_member,
    )
    user_id = getattr(member, "id", None)
    if is_dm or guild_owner_id is None:
        return ActorRef(user_id=user_id, is_guild_operator=False,
                        is_bot_owner=is_platform_owner(user_id), is_dm=True)
    tier = member_tier_from_member(member, guild_owner_id)
    return ActorRef(
        user_id=user_id,
        is_guild_operator=tier in ("staff", "moderator", "administrator", "owner"),
        is_bot_owner=is_platform_owner(user_id),
        is_dm=False,
        member_tier=tier,
        role_ids=role_ids_from_member(member),
    )
