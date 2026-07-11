"""WELCOME domain service (parity flip) — the shipped effective-policy
read set (disbot services/welcome_config.py ``load_policy`` +
``split_message_variants``) behind the kernel settings/binding seams.

The v1 slice is READ-ONLY: `!welcome` renders the effective policy
(cogs/welcome_cog.py ``welcome_status``); the member-join/leave feeds
(greeting send, entry-role grant, DM) arm with the member band — their
templates and toggles already live in the declared settings, so this
module carries the whole read vocabulary now and the writers later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "WelcomePolicy",
    "bound_channel",
    "bound_entry_role",
    "load_policy",
    "split_message_variants",
]

#: The shipped variant separator (services/welcome_config.py
#: ``_VARIANT_SEPARATOR_RE`` verbatim) — a ``---`` line splits a message
#: setting into random-pick variants.
_VARIANT_SEPARATOR_RE = re.compile(r"^\s*-{3,}\s*$", re.MULTILINE)


def split_message_variants(template: str) -> list[str]:
    """Split a message setting into its non-empty, stripped variants
    (shipped ``split_message_variants`` verbatim: ``---`` separator
    lines, empties dropped)."""
    parts = _VARIANT_SEPARATOR_RE.split(template or "")
    return [p.strip() for p in parts if p and p.strip()]


@dataclass(frozen=True)
class WelcomePolicy:
    """The shipped effective welcome policy (welcome_config.WelcomePolicy
    read set — the fields the status embed renders)."""

    enabled: bool
    join_enabled: bool
    leave_enabled: bool
    dm_enabled: bool
    join_message: str
    leave_message: str
    dm_message: str
    delete_after_seconds: int


def _as_bool(value: object, fallback: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _as_int(value: object, fallback: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return fallback


async def load_policy(guild_id: int) -> WelcomePolicy:
    """Effective policy through THE kernel settings seam (declared
    defaults are the shipped defaults — sb/manifest/welcome.py carries
    services/welcome_config.py's values verbatim)."""
    from sb.domain.welcome import DEFAULT_JOIN_MESSAGE, DEFAULT_LEAVE_MESSAGE
    from sb.kernel.settings import resolve

    return WelcomePolicy(
        enabled=_as_bool(await resolve(guild_id, "welcome", "enabled"), False),
        join_enabled=_as_bool(
            await resolve(guild_id, "welcome", "join_enabled"), True),
        leave_enabled=_as_bool(
            await resolve(guild_id, "welcome", "leave_enabled"), False),
        dm_enabled=_as_bool(
            await resolve(guild_id, "welcome", "dm_enabled"), False),
        join_message=str(await resolve(guild_id, "welcome", "join_message")
                         or DEFAULT_JOIN_MESSAGE),
        leave_message=str(await resolve(guild_id, "welcome", "leave_message")
                          or DEFAULT_LEAVE_MESSAGE),
        dm_message=str(await resolve(guild_id, "welcome", "dm_message") or ""),
        delete_after_seconds=_as_int(
            await resolve(guild_id, "welcome", "delete_after_seconds"), 0),
    )


async def bound_channel(guild_id: int) -> int | None:
    """The greeting/farewell channel binding (subsystem_bindings
    route-truth; the server_logging ``bound_channel`` posture — headless
    reads as unbound, never a raise)."""
    from sb.kernel.db.settings import get_binding

    try:
        return await get_binding(guild_id, "welcome", "channel")
    except Exception:  # noqa: BLE001 — no DB (headless) reads as unbound
        return None


async def bound_entry_role(guild_id: int) -> int | None:
    """The A-14 entry-role binding (same lane as :func:`bound_channel`)."""
    from sb.kernel.db.settings import get_binding

    try:
        return await get_binding(guild_id, "welcome", "entry_role")
    except Exception:  # noqa: BLE001
        return None
