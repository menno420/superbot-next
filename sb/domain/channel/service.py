"""Channel-state mutations (the `_unmapped` strays re-home) — the shipped
`ChannelLifecycleService` seam's golden-pinned slice.

The oracle routed every operator channel mutation through ONE service
(disbot/services/channel_lifecycle_service.py): the Discord edit, then a
best-effort ``audit.action_recorded`` companion + the advisory
``channel.lifecycle_changed`` event (shared ``mutation_id``,
services/lifecycle/contracts.py: ``mutation_type=f"{domain}_{operation}"``).
This module carries the slice the goldens pin (``set_slowmode`` +
``set_overwrite`` — goldens/channel/sweep_slowmode + sweep_lock +
sweep_unlock) as:

* the :class:`ChannelStateActions` PORT — Discord channel-state edits are
  adapter work, so the domain never touches discord; the composition root
  installs the implementation and the not-installed default raises LOUDLY
  (the moderation guild-action posture: an uninstalled port is the
  caller's honest BLOCKED refusal, never a silent success);
* the channel NAME lookup port (the shipped TextChannelConverter's
  gateway-cache name leg — the xp `!xpimport` resolver posture);
* the two best-effort event emitters, verbatim payload shapes.

The D-0030 successor slice's ENABLER half (D-0077) armed the port's
create/delete surface: ``create_text_channel`` (overwrites passed AT
creation — the oracle's guild_resources.ensure_channel create path) and
``delete_channel`` (NotFound-as-success adapter contract; name/id guards
stay in the calling domain — the oracle's delete_setup_channel). The
remaining lifecycle operations (rename/move/reorder/clone/set_topic)
stay on their pending terminals until their own slices port them.

These handlers write NO db rows (the oracle's channel ops were pure
Discord state + events) — there is no DB leg, so no effect-after-record
reversibility question arises and the compensator allowlist stays EMPTY.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

__all__ = [
    "ChannelOverwrite",
    "ChannelStateActions",
    "EVT_CHANNEL_LIFECYCLE",
    "SEND_MESSAGES_BIT",
    "active_actions",
    "emit_channel_audit",
    "emit_channel_lifecycle",
    "install_channel_actions",
    "install_channel_lookup",
    "overwrite_summary",
    "reset_channel_ports_for_tests",
    "resolve_channel",
    "slowmode_summary",
    "subscribe",
]

logger = logging.getLogger(__name__)

#: shipped event name, verbatim (services/channel_lifecycle_service.py
#: EVT_CHANNEL_LIFECYCLE)
EVT_CHANNEL_LIFECYCLE = "channel.lifecycle_changed"

#: discord.Permissions.send_messages bit — the shipped lock/unlock
#: overwrite pair's only permission key (goldens/channel/sweep_lock pins
#: allow "0"/deny "2048"; sweep_unlock the inverse).
SEND_MESSAGES_BIT = 2048


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


# --- the channel-state port -------------------------------------------------------


@dataclass(frozen=True)
class ChannelOverwrite:
    """One permission-overwrite entry handed to channel CREATION
    (Discord's overwrite object: ``type`` 0 = role, 1 = member;
    allow/deny are raw permission bitmasks — goldens/_unmapped/
    sweep_setup.json pins the wire shape ``{allow, deny, id, type}``
    with INT masks, unlike the stringified edit_channel_permissions
    PUT)."""

    target_id: int
    target_type: int
    allow: int
    deny: int


@runtime_checkable
class ChannelStateActions(Protocol):
    """Adapter-implemented Discord channel-state edits (kernel-defined
    port). Wire twins record the goldens' verbs: ``set_slowmode`` is the
    channel-edit PATCH (fake_http ``edit_channel`` with
    ``rate_limit_per_user``), ``set_overwrite`` the permission-overwrite
    PUT (fake_http ``edit_channel_permissions``),
    ``create_text_channel`` the guild-channel POST (fake_http
    ``create_channel`` — overwrites ride IN the create payload, the
    oracle's guild_resources.ensure_channel create path; returns the new
    channel id), ``delete_channel`` the channel DELETE (fake_http
    ``delete_channel``).

    Contracts the callers rely on (D-0077): get-before-create/idempotent
    reuse is DOMAIN logic (the oracle's ensure_setup_channel), never the
    port's — ``create_text_channel`` always creates. A live
    ``delete_channel`` MUST treat Discord NotFound as success
    (already-gone is the goal state — the oracle's delete_setup_channel
    ``except discord.NotFound: return True``); name/id guards stay in
    the calling domain."""

    async def set_slowmode(self, channel_id: int, *, seconds: int,
                           reason: str | None) -> None: ...
    async def set_overwrite(self, channel_id: int, *, target_id: int,
                            allow: int, deny: int, target_type: int,
                            reason: str | None) -> None: ...
    async def create_text_channel(
            self, guild_id: int, *, name: str,
            overwrites: tuple[ChannelOverwrite, ...],
            parent_id: int | None, reason: str | None) -> int: ...
    async def delete_channel(self, channel_id: int, *,
                             reason: str | None) -> None: ...


class _NoActions:
    async def _refuse(self, *_a, **_k) -> None:
        raise RuntimeError(
            "ChannelStateActions not installed — the composition root "
            "must install the discord adapter's implementation "
            "(sb/domain/channel/service.install_channel_actions)")

    set_slowmode = set_overwrite = _refuse
    create_text_channel = delete_channel = _refuse


_actions: ChannelStateActions = _NoActions()  # type: ignore[assignment]
_lookup = None                                # async (guild_id, name) -> int|None
_bus = None


def install_channel_actions(actions: ChannelStateActions) -> None:
    global _actions
    _actions = actions


def active_actions() -> ChannelStateActions:
    return _actions


def install_channel_lookup(lookup) -> None:
    """lookup: async (guild_id, name) -> channel id | None — the shipped
    TextChannelConverter name leg over the gateway guild cache."""
    global _lookup
    _lookup = lookup


async def resolve_channel(guild_id: int, token: str) -> int | None:
    """Resolve a command channel token: ``<#id>`` mention, bare id, or
    cached name (the converter's ladder, name leg last)."""
    token = str(token).strip()
    if token.startswith("<#") and token.endswith(">"):
        body = token[2:-1]
        if body.isdigit():
            return int(body)
    if token.isdigit():
        return int(token)
    if _lookup is None:
        return None
    return await _lookup(int(guild_id), token)


def subscribe(bus) -> None:
    """Composition-root/harness obligation (the band-2 fan-out roster):
    gives this module the bus its audit/lifecycle facts ride."""
    global _bus
    _bus = bus


def reset_channel_ports_for_tests() -> None:
    global _actions, _lookup, _bus
    _actions = _NoActions()  # type: ignore[assignment]
    _lookup = None
    _bus = None


# --- the shipped summary phrases (channel_lifecycle_service._summary) --------------


def _suffix(applied: int, total: int) -> str:
    return f" ({applied}/{total} applied)"


def slowmode_summary(seconds: int, name: str, *, applied: int = 1,
                     total: int = 1) -> str:
    """``set slowmode {seconds}s on channel {name!r}{suffix}`` verbatim
    (goldens/channel/sweep_slowmode pins the byte)."""
    return f"set slowmode {seconds}s on channel {name!r}{_suffix(applied, total)}"


def overwrite_summary(perm_keys: tuple[str, ...], target_id: int, *,
                      channels: int = 1, applied: int = 1,
                      total: int = 1,
                      target_type: str = "role") -> str:
    """``set overwrite [{keys}] on {n} channel(s) for {who}{suffix}``
    verbatim (goldens/channel/sweep_lock + sweep_unlock pin the byte)."""
    keys = ", ".join(sorted(perm_keys)) or "(none)"
    who = f"{target_type} {target_id}"
    return (f"set overwrite [{keys}] on {channels} channel(s) "
            f"for {who}{_suffix(applied, total)}")


# --- the best-effort event companions ----------------------------------------------


async def emit_channel_audit(guild_id: int, *, mutation_id: str,
                             operation: str, target: str,
                             new_value: str | None, actor_id: int | None,
                             actor_type: str) -> None:
    """``audit.action_recorded`` fact for a channel mutation performed
    OUTSIDE a K7 lane (the shipped lifecycle contracts emit twin —
    ``mutation_type=f"channel_{operation}"``, best-effort in-process;
    disbot/services/lifecycle/contracts.py)."""
    if _bus is None:
        return
    try:
        await _bus.emit("audit.action_recorded", **{
            "mutation_id": mutation_id, "subsystem": "channel",
            "mutation_type": f"channel_{operation}", "target": target,
            "scope": "guild", "guild_id": guild_id, "prev_value": None,
            "new_value": new_value, "actor_id": actor_id,
            "actor_type": actor_type,
            "occurred_at": _utcnow().isoformat()})
    except Exception:  # noqa: BLE001 — audit fact is best-effort (shipped)
        logger.warning("channel: audit fact emit failed", exc_info=True)


async def emit_channel_lifecycle(guild_id: int, *, mutation_id: str,
                                 operation: str, outcome: str,
                                 applied: list, failed: list) -> None:
    """The shipped ``channel.lifecycle_changed`` advisory event verbatim
    (services/channel_lifecycle_service.py — best-effort, shares its
    mutation_id with the audit companion; goldens/channel/sweep_slowmode
    + sweep_lock + sweep_unlock pin the payload)."""
    if _bus is None:
        return
    try:
        await _bus.emit(EVT_CHANNEL_LIFECYCLE, **{
            "mutation_id": mutation_id, "guild_id": guild_id,
            "operation": operation, "outcome": outcome,
            "applied": applied, "failed": failed,
            "occurred_at": _utcnow().isoformat()})
    except Exception:  # noqa: BLE001 — advisory event is best-effort (shipped)
        logger.warning("channel: lifecycle event emit failed", exc_info=True)
