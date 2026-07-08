"""The send-egress port (S11 — frozen L0 spec 10 §2.A class 13 / §8.1;
RC-21, the registered Q-D26 spec-02/K8 seam correction).

TWO egress surfaces, both DEFAULT-DENY:
  - REPLY (interaction ack/reply): the frozen ``SurfaceResponder.render/
    deny`` chokepoint (spec 02) — already landed; neutralization is a
    property of the concrete responders.
  - SEND (service-initiated ``channel.send`` — the X-1 mass-ping vector,
    reachable by NO frozen primitive until now): THIS port. Every
    service-initiated send routes through ONE ``ChannelEmitter.send``;
    the concrete ``DiscordChannelEmitter`` (adapters/discord/egress.py) is
    the ONLY module that constructs ``discord.AllowedMentions`` — UNTRUSTED
    ⇒ ``AllowedMentions.none()`` + markdown escape, so ``@everyone`` from
    user-authored template text is STRUCTURALLY impossible.

The AST fence (tools/check_egress.py) makes a raw ``.send``/``.reply``/
Discord state mutation outside sb/adapters a SEMANTIC_VIOLATION (A-5 widens
the fence beyond sends to raw Discord state mutations).
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

__all__ = [
    "ChannelEmitter",
    "EmitResult",
    "OutboundContent",
    "TrustLevel",
    "active_channel_emitter",
    "install_channel_emitter",
    "neutralize_untrusted",
    "reset_channel_emitter_for_tests",
]


class TrustLevel(str, enum.Enum):
    """The content-trust tag — DEFAULT-DENY."""

    UNTRUSTED = "untrusted"   # member-supplied text ⇒ mentions ALWAYS suppressed + markdown escaped (DEFAULT)
    TRUSTED = "trusted"       # operator/owner-authored ⇒ mentions gated to an explicit allowlist
    SYSTEM = "system"         # bot constant copy ⇒ mentions only if statically declared


@dataclass(frozen=True)
class OutboundContent:
    body: str
    trust: TrustLevel = TrustLevel.UNTRUSTED      # [S] default-deny
    allow_mentions: tuple[str, ...] = ()          # ("everyone"|"here"|"role:<id>"|"user:<id>") — TRUSTED/SYSTEM only


@dataclass(frozen=True)
class EmitResult:
    sent: bool
    message_id: int | None = None
    error: str | None = None


@runtime_checkable
class ChannelEmitter(Protocol):
    """The send-egress port — sibling to SurfaceResponder (kernel-defined,
    adapter-implemented)."""

    async def send(self, channel_id: int, content: OutboundContent, *,
                   guild_id: int) -> EmitResult: ...


_MARKDOWN_CHARS = re.compile(r"([\\`*_~|>])")
_MENTION_TOKENS = re.compile(r"@(everyone|here)")


def neutralize_untrusted(body: str) -> str:
    """The kernel-side UNTRUSTED text neutralization (pure — the adapter
    ALSO passes AllowedMentions.none(); safety does not depend on one layer):
    escape markdown + break @everyone/@here with a zero-width space."""
    escaped = _MARKDOWN_CHARS.sub(r"\\\1", body)
    return _MENTION_TOKENS.sub("@​\\1", escaped)


class _NoEmitter:
    """The not-installed default: a service send with no emitter is a LOUD
    error (never a silent drop, never a raw fallback send)."""

    async def send(self, channel_id: int, content: OutboundContent, *,
                   guild_id: int) -> EmitResult:
        raise RuntimeError(
            "ChannelEmitter not installed — service-initiated sends require "
            "the composition root to install the discord adapter's emitter")


_emitter: ChannelEmitter = _NoEmitter()


def install_channel_emitter(emitter: ChannelEmitter) -> None:
    global _emitter
    _emitter = emitter


def active_channel_emitter() -> ChannelEmitter:
    return _emitter


def reset_channel_emitter_for_tests() -> None:
    global _emitter
    _emitter = _NoEmitter()
