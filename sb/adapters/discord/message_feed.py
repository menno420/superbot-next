"""The live MESSAGE FEED adapter (CUT-1, completion-report flag 30 /
§4.2's "message feeds"): gateway ``on_message`` → prefix-command dispatch.

The ONE armed consumer is the prefix twin — a human-typed ``!command``
reaches ``dispatch_prefix`` → ``resolve()`` (the no-skip fence, spec 02
§7) and responds via :class:`MessageResponder`. Everything else on the
message band stays DORMANT here, exactly as ledgered: the fuzzy typo
re-dispatch (its band ports the corpus), the passive on_message hooks
(xp chat award, counting, chain — their live feeds are named successors),
and the NL shell (AI arming is flag 7/52 owner work).

Shipped old-bot contract carried verbatim: bot/self-authored messages are
ignored before anything else; non-prefix content is not consumed. The
message_content intent rail (spec 14 §2.B) is honored by the COMPOSITION
ROOT: it arms this feed only when the ``prefix`` capability class is not
degraded — absent approval, the feed is simply never registered.

Duck-typed against discord.py (no discord import — the objects arrive from
the gateway at runtime), like sb/adapters/discord/responders.py; the token
match mirrors the parity harness's ``send_command`` (longest qualified
match, up to 3 tokens, over the installed target index).
"""

from __future__ import annotations

import logging

from sb.adapters.discord.responders import MessageResponder
from sb.kernel.interaction.adapters import lookup_target
from sb.kernel.interaction.adapters.prefix import dispatch_prefix
from sb.kernel.interaction.errors import from_exception
from sb.kernel.interaction.request import Surface

logger = logging.getLogger("sb.adapters.discord.message_feed")

__all__ = ["arm_message_feed", "handle_prefix_message", "match_prefix_target"]

#: The deepest qualified command path ("group sub sub") the matcher tries —
#: the parity harness's exact bound.
_MAX_PATH_TOKENS = 3


def match_prefix_target(content: str, *, prefix: str) -> tuple[str, list[str]] | None:
    """Longest qualified-name match over the installed PREFIX index:
    ``"!karma add @u"`` → ``("karma add", ["@u"])``. None = not a prefix
    command / unknown target (the fuzzy adapter's future input)."""
    if not content.startswith(prefix):
        return None
    tokens = content[len(prefix):].split()
    if not tokens:
        return None
    for n in range(min(_MAX_PATH_TOKENS, len(tokens)), 0, -1):
        candidate = " ".join(tokens[:n])
        if lookup_target(candidate, Surface.PREFIX) is not None:
            return candidate, tokens[n:]
    return None


class _PrefixContext:
    """The ctx shape ``request_from_prefix_ctx`` + ``MessageResponder``
    duck-read, built from a raw gateway Message (spec 02 §3.7)."""

    __slots__ = ("command", "author", "guild", "channel", "message", "kwargs")

    def __init__(self, message: object, *, target_key: str, rest: list[str]) -> None:
        class _Cmd:
            qualified_name = target_key

        self.command = _Cmd()
        self.author = getattr(message, "author", None)
        self.guild = getattr(message, "guild", None)
        self.channel = getattr(message, "channel", None)
        self.message = message
        self.kwargs = {"argv": tuple(rest), "text": " ".join(rest)}

    async def reply(self, content: str | None = None, **kwargs: object) -> object:
        # content is OPTIONAL: DiscordPanelPresenter replies embed/view-only
        # (panel_view.py origin.reply(embed=..., view=...)).
        return await self.message.reply(content, **kwargs)


async def handle_prefix_message(message: object, *, prefix: str) -> object | None:
    """One inbound gateway message: ignore bot/self authors (shipped
    contract), match a prefix command, dispatch through the real spine.
    Returns the resolve() Result, or None when not consumed. Never raises —
    a dispatch fault renders the K8 error envelope (spec 02 §6)."""
    author = getattr(message, "author", None)
    if author is None or bool(getattr(author, "bot", False)):
        return None
    content = str(getattr(message, "content", "") or "")
    match = match_prefix_target(content, prefix=prefix)
    if match is None:
        return None
    target_key, rest = match
    ctx = _PrefixContext(message, target_key=target_key, rest=rest)
    responder = MessageResponder(ctx, surface=Surface.PREFIX)
    try:
        return await dispatch_prefix(ctx, responder=responder)
    except Exception as exc:  # noqa: BLE001 — the feed never breaks the event loop
        envelope = from_exception(exc, surface=Surface.PREFIX, target=None)
        try:
            await ctx.reply(envelope.user_message)
        except Exception:  # noqa: BLE001
            logger.warning("prefix feed: error render failed", exc_info=True)
        logger.warning("prefix feed: dispatch fault on %r", target_key,
                       exc_info=True)
        return None


def arm_message_feed(bot: object, *, prefix: str) -> None:
    """Register the on_message listener (``bot.add_listener`` — additive,
    never replaces the Bot's own event). The composition root calls this
    ONLY after the intent-degrade markers cleared the ``prefix`` class."""

    async def on_message(message: object) -> None:
        await handle_prefix_message(message, prefix=prefix)

    bot.add_listener(on_message, "on_message")
