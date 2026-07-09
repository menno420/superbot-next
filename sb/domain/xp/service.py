"""XP policy/ports + the chat-award engine + fan-outs (band 4).

* ``handle_chat_message`` is the shipped on_message hot path
  (cogs/xp/listener.py) as a headless core: cooldown via the row's
  ``last_xp`` + the guild's xp config, the PR-9 participation gate as an
  installable port (default ALLOW — the shipped flag-off behaviour),
  random amount in [xp_min, xp_max], then the audited K7 ``xp.award`` op
  with source="chat". The MESSAGE FEED that calls it arms with the
  message band (the automod/image_moderation precedent) — the parity
  harness and the future composition root are the callers.
* The level-up announce fan-out mirrors the band-2/3 log fan-outs:
  subscribe(bus) routes ``xp.level_up`` to the bound ``xp.announce_channel``
  through the RC-21 emitter. The shipped announce-in-place fallback
  (message.channel when unbound) needs the origin message context — that
  in-place half is the MESSAGE SHELL's obligation (documented deviation;
  the event payload is compat-frozen and carries no channel id).
* Threshold-role grants on level-up ride ``install_level_role_granter``
  — the role-automation seam is band-5 work (roles band); the default
  records nothing and never fakes a grant.
* THIS MODULE FILLS THE BAND-3 WAITING PORTS: ``install_economy_ports()``
  (called at manifest import) installs the real level reader (xp row →
  level) and the real xp awarder (economy.work's XP leg → the audited
  ``xp.award`` op, source="work:<job>") into sb.domain.economy.service.
"""

from __future__ import annotations

import random
from typing import Awaitable, Callable

__all__ = [
    "handle_chat_message",
    "install_economy_ports",
    "install_level_role_granter",
    "install_levelup_history_scanner",
    "install_participation_gate",
    "reset_xp_ports_for_tests",
    "set_rng_for_tests",
    "subscribe",
    "xp_config",
]

# --- config read (band-1 settings seam; shipped defaults) ----------------------------

_DEFAULTS = {"xp_min": 15, "xp_max": 25, "xp_cooldown": 60}


async def xp_config(guild_id: int) -> tuple[int, int, int]:
    """(xp_min, xp_max, cooldown_seconds) — the K7 resolve seam with the
    shipped defaults as the headless fallback (undeclared => defaults)."""
    from sb.kernel import settings as ksettings

    out = []
    for name in ("xp_min", "xp_max", "xp_cooldown"):
        try:
            value = await ksettings.resolve(guild_id, "xp", name)
        except LookupError:
            value = _DEFAULTS[name]
        try:
            out.append(int(value))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            out.append(_DEFAULTS[name])
    return out[0], out[1], out[2]


# --- installable ports ----------------------------------------------------------------

ParticipationGate = Callable[[int, int], Awaitable[bool]]     # (user, guild) -> allow
RoleGranter = Callable[..., Awaitable[None]]                  # (guild_id, user_id, new_level)
HistoryScanner = Callable[..., Awaitable[list]]               # xpimport channel scan


async def _default_participation_gate(user_id: int, guild_id: int) -> bool:
    """Shipped default: participation.enabled is OFF => every award
    proceeds (the PR-9 gate falls open; the participation band installs
    the real read)."""
    return True


async def _default_role_granter(guild_id: int, user_id: int,
                                new_level: int) -> None:
    """Band-5 waiting port: threshold-role grants need the audited
    role-automation seam (roles band). Never fakes a grant."""
    return None


_participation_gate: ParticipationGate = _default_participation_gate
_role_granter: RoleGranter = _default_role_granter
_history_scanner: HistoryScanner | None = None
# None => the chat draw falls back to the MODULE-GLOBAL random — the
# instance the parity harness seeds per case (`random.seed(case.seed)`),
# so a fresh replay reproduces the captured amount (the economy-daily
# D-0060 precedent; a private unseeded Random() here made every chat
# award diverge from its golden).
_rng: random.Random | None = None


def install_participation_gate(gate: ParticipationGate) -> None:
    global _participation_gate
    _participation_gate = gate


def install_level_role_granter(granter: RoleGranter) -> None:
    global _role_granter
    _role_granter = granter


def install_levelup_history_scanner(scanner: HistoryScanner) -> None:
    """The !xpimport channel scan needs Discord message history — the
    scanner port arms with the message band / live adapter."""
    global _history_scanner
    _history_scanner = scanner


def active_history_scanner() -> HistoryScanner | None:
    return _history_scanner


def set_rng_for_tests(rng: random.Random | None) -> None:
    global _rng
    _rng = rng


def reset_xp_ports_for_tests() -> None:
    global _participation_gate, _role_granter, _history_scanner, _rng
    _participation_gate = _default_participation_gate
    _role_granter = _default_role_granter
    _history_scanner = None
    _rng = None


# --- the chat hot path -----------------------------------------------------------------

async def handle_chat_message(user_id: int, guild_id: int, *,
                              now: int) -> object | None:
    """The on_message XP flow (cogs/xp/listener.handle_message, headless).

    Returns the K7 WorkflowResult when an award ran, ``None`` when the
    cooldown or the participation gate skipped it. The caller (message
    shell / harness) is a bot-message/no-guild pre-filter, exactly like
    the shipped listener's early drop.
    """
    from sb.domain.economy.service import check_cooldown
    from sb.domain.xp import store

    xp_min, xp_max, cooldown = await xp_config(guild_id)
    row = await store.get_xp(user_id, guild_id)
    on_cd, _ = check_cooldown(int(row["last_xp"]), cooldown, now=now)
    if on_cd:
        return None
    if not await _participation_gate(user_id, guild_id):
        return None

    amount = (_rng or random).randint(xp_min, xp_max)
    return await _run_award(user_id=user_id, guild_id=guild_id,
                            amount=amount, source="chat", now=now)


async def _run_award(*, user_id: int, guild_id: int, amount: int,
                     source: str, now: int, actor_id: int | None = None):
    """One audited award — builds the ctx and runs the K7 op."""
    from types import SimpleNamespace

    from sb.kernel.workflow import engine
    from sb.kernel.workflow.context import WorkflowContext
    from sb.spec.refs import WorkflowRef

    ctx = WorkflowContext(
        actor=SimpleNamespace(user_id=actor_id or user_id, actor_type="user"),
        guild_id=guild_id,
        request_id=f"xp:{source}:{user_id}:{now}",
        confirmed=True,
        params={"target_id": user_id, "amount": amount, "source": source,
                "now": now})
    return await engine.run(WorkflowRef("xp.award"), ctx)


# --- the band-3 economy waiting ports, FILLED -------------------------------------------

async def _level_reader(user_id: int, guild_id: int) -> int:
    """The REAL level source: tier-gated jobs unlock (D-0031 boundary)."""
    from sb.domain.xp import store

    row = await store.get_xp(user_id, guild_id)
    return int(row["level"])


async def _xp_awarder(**kwargs) -> dict | None:
    """economy.work's XP leg (shipped xp_service.award signature): runs
    the audited xp.award op; returns the award dict or ``None`` on any
    non-success (the leg records xp_awarded=None, never a fake)."""
    guild_id = int(kwargs.get("guild_id", 0) or 0)
    user_id = int(kwargs.get("user_id", 0) or 0)
    amount = int(kwargs.get("amount", 0) or 0)
    source = str(kwargs.get("source", "") or "work")
    now = int(kwargs.get("now", 0) or 0)
    if amount <= 0:
        return None
    from sb.spec.outcomes import SUCCESS

    result = await _run_award(user_id=user_id, guild_id=guild_id,
                              amount=amount, source=source, now=now)
    after = getattr(result, "after", None) or {}
    award = after.get("award") if isinstance(after, dict) else None
    if getattr(result, "outcome", None) != SUCCESS or not isinstance(award, dict):
        return None
    return dict(award)


def install_economy_ports() -> None:
    """Fill sb.domain.economy.service's band-4 waiting ports (D-0031)."""
    from sb.domain.economy import service as economy_service

    economy_service.install_level_reader(_level_reader)
    economy_service.install_xp_awarder(_xp_awarder)


# --- the level-up fan-outs (announce + threshold roles) ---------------------------------

async def bound_announce_channel(guild_id: int) -> int | None:
    from sb.kernel.db.settings import get_binding

    try:
        return await get_binding(guild_id, "xp", "announce_channel")
    except Exception:  # noqa: BLE001 — headless/no-DB reads as unbound
        return None


async def _route_level_up(**payload: object) -> None:
    from sb.kernel.interaction.egress import (
        OutboundContent,
        TrustLevel,
        active_channel_emitter,
    )

    guild_id = int(payload.get("guild_id", 0) or 0)
    user_id = int(payload.get("user_id", 0) or 0)
    new_level = int(payload.get("new_level", 0) or 0)

    channel_id = await bound_announce_channel(guild_id)
    if channel_id is not None:
        emitter = active_channel_emitter()
        await emitter.send(
            channel_id,
            OutboundContent(
                body=f"🎉 **Level Up!** <@{user_id}> reached "
                     f"**Level {new_level}**!",
                trust=TrustLevel.TRUSTED),
            guild_id=guild_id)

    try:
        await _role_granter(guild_id, user_id, new_level)
    except Exception:  # noqa: BLE001 — a role-grant failure never kills the fan-out
        pass


def subscribe(bus: object) -> None:
    """Arm the level-up fan-out on THE bus (composition-root / harness
    obligation — the shipped announce_level_up analog)."""
    bus.on("xp.level_up", _route_level_up)
