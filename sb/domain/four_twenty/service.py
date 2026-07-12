"""The FOUR_TWENTY passive message trigger — the shipped ``FourTwentyStage``
(disbot/cogs/four_twenty_cog.py, message-pipeline order 50, the "passive"
tier) headless: 🍃-react when a human message mentions 420, occasionally
add a canned one-liner, never consume the message.

Shipped semantics carried VERBATIM (oracle-reconstructed, no drift vs the
corpus capture):

* trigger: ``(?<!\\d)4[:\\-\\s]?20(?!\\d)|blaze\\s*it|four[\\s\\-]?twenty``
  case-insensitive — matches 420 / 4:20 / 4-20 / "blaze it" /
  "four twenty", never look-alikes (1420, 4200, prices, IDs). The stage
  watched EVERY message, command-shaped included — the corpus capture of
  ``!420`` itself fired it (parity/goldens/four_twenty/sweep_420.json pins
  the reaction + one-liner ON the invoking message).
* per-channel cooldown 90s (``_on_cooldown`` check-and-arm over
  ``time.monotonic()``) so the egg can never be spammed into noise.
* effect order: ``message.add_reaction("🍃")`` first, then a 50%%
  ``random.random()`` coin for ``random.choice(_EGG_LINES)`` — the draws
  ride the MODULE-GLOBAL random the parity harness seeds per case, and they
  run AFTER the XP chat award's draw (shipped pipeline order: XP stage 30 <
  four_twenty 50); the golden pins exactly that draw sequence (seed 42 ⇒
  xp 25, coin 0.111 < 0.5, egg line index 2).
* observe-only: never deletes, never blocks, returns nothing the pipeline
  consumes; a Discord failure was caught by the shipped stage
  (``except discord.HTTPException``) — the port's feed callers own that
  never-break-the-loop guard, and the uninstalled ReactionOps port raises
  the honest not-installed refusal (the moderation-actions posture).

The reaction rides the ``ReactionOps`` port (adapter-implemented; the
parity boot arms the capture twin that records fake_http's ``add_reaction``
wire shape — the same twin the role reaction-bind flow uses); the one-liner
rides the RC-21 ``ChannelEmitter`` send-egress port (SYSTEM trust: bot
constant copy, zero user text).
"""

from __future__ import annotations

import logging
import random
import re
import time
from typing import Protocol

logger = logging.getLogger("sb.domain.four_twenty")

__all__ = [
    "ReactionOps",
    "handle_message",
    "install_reaction_ops",
    "reset_four_twenty_ports_for_tests",
]

# Per-channel cooldown (seconds) — shipped constant verbatim
# (four_twenty_cog.py _EGG_COOLDOWN_SECONDS).
_EGG_COOLDOWN_SECONDS = 90.0

_LEAF = "🍃"

# Match a standalone 420 / 4:20 / 4-20, or the phrases "blaze it" /
# "four twenty"; the digit look-arounds avoid firing on 1420, 4200, IDs,
# prices. Case-insensitive. (four_twenty_cog.py _TRIGGER_RE, verbatim.)
_TRIGGER_RE = re.compile(
    r"(?<!\d)4[:\-\s]?20(?!\d)|blaze\s*it|four[\s\-]?twenty",
    re.IGNORECASE,
)

# four_twenty_cog.py _EGG_LINES, verbatim (🍃-prefixed bot constant copy).
_EGG_LINES = (
    f"{_LEAF} Ayy, 420. Stay leafy.",
    f"{_LEAF} 4:20 spotted — take a deep breath.",
    f"{_LEAF} Blaze it (responsibly). Vibes acknowledged.",
    f"{_LEAF} The sacred number appears. Snacks recommended.",
    f"{_LEAF} 420 detected. Keeping it mellow.",
)


class ReactionOps(Protocol):
    """Adapter-implemented reaction write for the passive stage (the
    shipped ``message.add_reaction(_LEAF)`` — fake_http captured it as the
    ``add_reaction`` wire verb; goldens/four_twenty/sweep_420 pins the
    call). Uninstalled ⇒ raise ⇒ the caller's honest never-break-the-loop
    skip (the role MessageOps posture)."""

    async def add_reaction(self, channel_id: int, message_id: int,
                           emoji: str) -> None: ...


class _NoReactionOps:
    async def add_reaction(self, channel_id: int, message_id: int,
                           emoji: str) -> None:
        raise RuntimeError(
            "ReactionOps not installed — the composition root must install "
            "an implementation "
            "(sb.domain.four_twenty.service.install_reaction_ops)")


_reaction_ops: ReactionOps = _NoReactionOps()  # fail-loud default

# channel_id -> monotonic timestamp of last wink (shipped _last_fired;
# in-process state — the parity boot clears it at every case head, trap-20
# mode-independence; the capture world's single matching case never leaned
# on cross-case accumulation).
_last_fired: dict[int, float] = {}


def install_reaction_ops(ops: ReactionOps) -> None:
    global _reaction_ops
    _reaction_ops = ops


def reset_four_twenty_ports_for_tests() -> None:
    global _reaction_ops
    _reaction_ops = _NoReactionOps()
    _last_fired.clear()


def _on_cooldown(channel_id: int) -> bool:
    """Shipped check-and-arm verbatim (four_twenty_cog.py _on_cooldown):
    inside the window ⇒ True; otherwise arm the window and fire."""
    now = time.monotonic()
    last = _last_fired.get(channel_id)
    if last is not None and (now - last) < _EGG_COOLDOWN_SECONDS:
        return True
    _last_fired[channel_id] = now
    return False


async def handle_message(*, guild_id: int, channel_id: int, message_id: int,
                         content: str) -> bool:
    """One inbound human guild message (the caller pre-filters bot/self
    authors and DMs, exactly like the shipped pipeline). Returns True when
    the egg fired (reaction sent). Raises on effect-port failure — the
    feed caller owns the shipped stage's swallow-and-log."""
    if not content or not _TRIGGER_RE.search(content):
        return False
    # Per-channel rate-limit so a chatty channel can't spam winks.
    if _on_cooldown(channel_id):
        return False
    await _reaction_ops.add_reaction(channel_id, message_id, _LEAF)
    # Occasionally add a one-liner; usually just the quiet react.
    if random.random() < 0.5:
        from sb.kernel.interaction.egress import (
            OutboundContent,
            TrustLevel,
            active_channel_emitter,
        )

        emitter = active_channel_emitter()
        await emitter.send(
            channel_id,
            OutboundContent(random.choice(_EGG_LINES),
                            trust=TrustLevel.SYSTEM),
            guild_id=guild_id)
    return True
