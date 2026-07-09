"""The live gateway adapter (CUT-1): intents computed from the typed Config
approvals, the ``commands.Bot`` construction, and the connect/ready driver
the composition root (``sb/app/main.py``) awaits.

This is the ONE module that instantiates the discord client — the layer rule
(`check_no_skip` assertion 2) keeps discord types out of ``sb/app``/kernel,
so ``main()`` drives this adapter duck-typed. Import-guarded like every
discord adapter (discord absent in CI containers by design).

Intents (spec 14 §2.B / L-17): ``Intents.default()`` plus the two privileged
intents ONLY when their approval envs assert Discord-side approval
(``SB_INTENT_MSGCONTENT_OK`` / ``SB_INTENT_MEMBERS_OK``). Absent approval is
a DEGRADE marker read by the composition root — never a connect refusal.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger("sb.adapters.discord.gateway")

try:  # pragma: no cover — discord is absent in CI containers by design
    import discord
    from discord.ext import commands

    DISCORD_AVAILABLE = True
except ImportError:
    discord = None       # type: ignore[assignment]
    commands = None      # type: ignore[assignment]
    DISCORD_AVAILABLE = False

__all__ = [
    "DISCORD_AVAILABLE",
    "GatewayConnectError",
    "build_bot",
    "build_intents",
    "connect_gateway",
]

#: Bound on login + READY (Discord's READY can lag on large bots; the test
#: bot is small — a stuck token/network fails the boot instead of hanging).
READY_TIMEOUT_S = 75.0


class GatewayConnectError(RuntimeError):
    """The gateway could not reach READY (bad token, network, timeout).
    The composition root maps this to FAILED_STARTUP."""


def build_intents(cfg: object):
    """Intents.default() + the two privileged intents iff approved."""
    if not DISCORD_AVAILABLE:
        raise RuntimeError("discord is not installed — no gateway in this container")
    intents = discord.Intents.default()
    intents.message_content = bool(getattr(cfg, "SB_INTENT_MSGCONTENT_OK", False))
    intents.members = bool(getattr(cfg, "SB_INTENT_MEMBERS_OK", False))
    return intents


def build_bot(cfg: object):
    """The gateway client. ``commands.Bot`` (not bare Client) because the
    K8 error shims register on ``bot.tree`` + ``bot.add_listener``
    (sb/app/error_handlers.py) and leg C reads ``bot.tree``. No cogs, no
    default help — dispatch belongs to the kernel resolve() spine."""
    intents = build_intents(cfg)
    return commands.Bot(
        command_prefix=str(getattr(cfg, "BOT_PREFIX", "!") or "!"),
        intents=intents,
        help_command=None,
    )


async def connect_gateway(
    bot: object,
    token: str,
    *,
    ready_timeout_s: float = READY_TIMEOUT_S,
) -> "asyncio.Task":
    """Start login+connect as a background task and wait for READY.

    Returns the running gateway task (the composition root supervises it —
    its death while RUNNING is the shutdown trigger). Raises
    GatewayConnectError if the gateway dies or READY does not arrive within
    the timeout; the failed task is awaited/cleaned before raising.
    """
    ready = asyncio.Event()

    @bot.event
    async def on_ready() -> None:  # pragma: no cover — needs a live gateway
        user = getattr(bot, "user", None)
        logger.info("gateway READY: logged in as %s (id=%s), %d guild(s)",
                    user, getattr(user, "id", None), len(getattr(bot, "guilds", ())))
        ready.set()

    gateway_task = asyncio.create_task(bot.start(token), name="sb-gateway")
    waiter = asyncio.create_task(ready.wait(), name="sb-gateway-ready")
    done, _pending = await asyncio.wait(
        {gateway_task, waiter},
        timeout=ready_timeout_s,
        return_when=asyncio.FIRST_COMPLETED,
    )
    if waiter in done:
        return gateway_task
    waiter.cancel()
    if gateway_task in done:
        exc = gateway_task.exception()
        raise GatewayConnectError(f"gateway died before READY: {exc!r}") from exc
    gateway_task.cancel()
    try:
        await gateway_task
    except (asyncio.CancelledError, Exception):  # noqa: BLE001 — already failing
        pass
    raise GatewayConnectError(f"gateway READY not received within {ready_timeout_s}s")
