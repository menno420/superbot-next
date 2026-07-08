"""Economy policy/ports + the log fan-out (band 3).

* Cooldown helpers ported verbatim (utils/cooldowns.py) with an explicit
  ``now`` so the K7 legs use the ctx clock.
* The XP seam: work pays coins AND awards XP in the shipped bot
  (services/xp_service.award). XP is band 4 — ``install_xp_awarder`` is the
  waiting port; the default records ``xp_pending`` honestly instead of
  faking a level. The job-eligibility LEVEL read rides the same boundary
  (``install_level_reader``; default level 0 => tier-1 jobs only until
  band 4 installs the real read).
* The economy-log fan-out mirrors the band-2 server_logging engine:
  subscribe(bus) routes economy.balance_changed lines to the bound
  ``economy.log_channel`` through the RC-21 emitter. The shipped on-ready
  auto-provision of #economy-log is a resource-provision-port consumer
  (declared via the manifest ResourceRequirement; wiring = the
  server_management provisioning slice).
"""

from __future__ import annotations

from typing import Awaitable, Callable

from sb.kernel.interaction.errors import ValidatorError

__all__ = [
    "InsufficientFundsError",
    "available_jobs",
    "check_cooldown",
    "format_remaining",
    "install_level_reader",
    "install_xp_awarder",
    "reset_economy_ports_for_tests",
    "subscribe",
]


class InsufficientFundsError(ValidatorError):
    """A debit/transfer would overdraw — classifies USER_ERROR/BLOCKED with
    the message as user copy (shipped copy built at the raise site)."""


class CooldownActiveError(ValidatorError):
    """Daily/work claimed while the domain cooldown is still running."""


class AlreadyOwnedError(ValidatorError):
    """Unique shop item purchase while already owned."""


# --- cooldown helpers (utils/cooldowns.py verbatim; explicit now) ------------------

def check_cooldown(last_ts: int, cooldown_seconds: int, *,
                   now: int) -> tuple[bool, int]:
    """(on_cooldown, remaining_seconds); remaining is 0 when expired."""
    elapsed = now - last_ts
    if elapsed < cooldown_seconds:
        return True, cooldown_seconds - elapsed
    return False, 0


def format_remaining(seconds: int) -> str:
    """Human-readable cooldown duration, e.g. '1h 30m' or '45s'."""
    if seconds <= 0:
        return "0s"
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    parts: list[str] = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s and not h:
        parts.append(f"{s}s")
    return " ".join(parts)


# --- the band-4 XP boundary (installable ports) -------------------------------------

LevelReader = Callable[[int, int], Awaitable[int]]           # (user, guild) -> level
XpAwarder = Callable[..., Awaitable[dict | None]]            # kwargs per shipped award()


async def _default_level_reader(user_id: int, guild_id: int) -> int:
    """No XP band yet: level 0 (tier-1 jobs only) — honest floor, never a
    fabricated level."""
    return 0


async def _default_xp_awarder(**kwargs) -> dict | None:
    """No XP band yet: award nothing, report nothing — the op result carries
    xp_pending=True so the surface can say 'XP arrives with the XP band'."""
    return None


_level_reader: LevelReader = _default_level_reader
_xp_awarder: XpAwarder = _default_xp_awarder


def install_level_reader(reader: LevelReader) -> None:
    global _level_reader
    _level_reader = reader


def install_xp_awarder(awarder: XpAwarder) -> None:
    global _xp_awarder
    _xp_awarder = awarder


def active_level_reader() -> LevelReader:
    return _level_reader


def active_xp_awarder() -> XpAwarder:
    return _xp_awarder


def xp_installed() -> bool:
    return _xp_awarder is not _default_xp_awarder


def reset_economy_ports_for_tests() -> None:
    global _level_reader, _xp_awarder
    _level_reader = _default_level_reader
    _xp_awarder = _default_xp_awarder


async def available_jobs(user_id: int, guild_id: int) -> list[str]:
    """Shipped eligibility: level floor + required items owned."""
    from sb.domain.economy import store
    from sb.domain.economy.catalogue import JOBS

    level = await _level_reader(user_id, guild_id)
    inv = await store.get_inventory(user_id, guild_id)
    return [name for name, data in JOBS.items()
            if level >= data["level"]
            and all(item in inv and inv[item] > 0 for item in data["items"])]


# --- the economy-log fan-out (server_logging engine pattern) ------------------------

async def bound_log_channel(guild_id: int) -> int | None:
    from sb.kernel.db.settings import get_binding

    try:
        return await get_binding(guild_id, "economy", "log_channel")
    except Exception:  # noqa: BLE001 — headless/no-DB reads as unbound
        return None


_REASON_LINES = {
    "daily": "🎁 Daily claimed",
    "gift": "💸 Coins transferred",
}


def _line_for(payload: dict) -> str:
    reason = str(payload.get("reason", "") or "")
    if reason.startswith("work:"):
        title = "💼 Work completed"
    elif reason.startswith("shop:"):
        title = "🛒 Shop purchase"
    elif reason.startswith("treasury:"):
        title = "🏛️ Treasury movement"
    else:
        title = _REASON_LINES.get(reason, "🪙 Balance changed")
    delta = int(payload.get("delta", 0) or 0)
    sign = "+" if delta >= 0 else ""
    return (f"{title} — <@{payload.get('user_id')}> {sign}{delta} 🪙 "
            f"(balance {payload.get('new_balance')}, {reason})")


async def _route_balance_changed(**payload: object) -> None:
    from sb.kernel.interaction.egress import (
        OutboundContent,
        TrustLevel,
        active_channel_emitter,
    )

    guild_id = int(payload.get("guild_id", 0) or 0)
    channel_id = await bound_log_channel(guild_id)
    if channel_id is None:
        return
    emitter = active_channel_emitter()
    await emitter.send(
        channel_id,
        OutboundContent(body=_line_for(dict(payload)), trust=TrustLevel.TRUSTED),
        guild_id=guild_id)


def subscribe(bus: object) -> None:
    """Arm the fan-out on THE bus (composition-root / harness obligation —
    the shipped post_log_embed analog)."""
    bus.on("economy.balance_changed", _route_balance_changed)
