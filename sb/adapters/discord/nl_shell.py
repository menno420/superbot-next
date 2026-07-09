"""The NL message-event SHELL (band 7) — the K10 band map's last leg:
mention detection/stripping → :class:`NLMessage` build →
``nl_engine.handle_message`` → deliver via the RC-21 ChannelEmitter →
``note_reply_delivered`` (the allowance/cooldown is charged per
DELIVERED reply, never per attempt) → ``remember_answer`` (so a 👎 /
correction reply can recover the Q&A) → the fail-safe review-log
writers.

Headless by design: the live composition root feeds it message-shaped
dicts/objects from the gateway event and installs the real emitter; the
parity harness feeds it directly. The discord HISTORY SCANNER
(``memory.install_history_scanner``) also lives here — over an
installable channel-history port so the module stays import-safe."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Awaitable, Callable
from typing import Any

from sb.kernel.ai import memory, nl_engine
from sb.kernel.interaction import egress

logger = logging.getLogger("sb.adapters.discord.nl_shell")

__all__ = [
    "handle_gateway_message",
    "install_channel_history_reader",
    "install_history_scanner",
    "reset_history_reader_for_tests",
]

_MENTION_RE_TMPL = r"<@!?{bot_id}>"


def _strip_mention(text: str, bot_user_id: int | None) -> tuple[str, bool]:
    if not bot_user_id:
        return text, False
    pattern = re.compile(_MENTION_RE_TMPL.format(bot_id=bot_user_id))
    if not pattern.search(text or ""):
        return text, False
    return pattern.sub("", text or "").strip(), True


async def handle_gateway_message(
    message: Any,
    *,
    bot_user_id: int | None,
    gateway: Any = None,
) -> nl_engine.NLOutcome | None:
    """One inbound guild message through the NL pipeline.

    ``message`` is duck-read (guild_id/channel_id/category_id/user_id/
    message_id/content/user_level/user_role_ids/is_fresh_user/
    author_is_bot/display_name). Returns the NLOutcome, or None when the
    shell pre-filtered (bot author / empty). Never raises."""
    try:
        content = str(getattr(message, "content", "") or "")
        if getattr(message, "author_is_bot", False):
            return None
        text, is_mention = _strip_mention(content, bot_user_id)
        if not content.strip():
            return None
        msg = nl_engine.NLMessage(
            guild_id=int(getattr(message, "guild_id", 0) or 0),
            channel_id=int(getattr(message, "channel_id", 0) or 0),
            category_id=getattr(message, "category_id", None),
            user_id=int(getattr(message, "user_id", 0) or 0),
            message_id=getattr(message, "message_id", None),
            text=text,
            raw_text=content,
            is_mention=is_mention,
            user_level=int(getattr(message, "user_level", 0) or 0),
            user_role_ids=tuple(getattr(message, "user_role_ids", ()) or ()),
            is_fresh_user=bool(getattr(message, "is_fresh_user", False)),
            author_is_bot=False,
            display_name=getattr(message, "display_name", None),
            bot_user_id=bot_user_id,
        )
        outcome = await nl_engine.handle_message(msg, gateway=gateway)
        if outcome.reply_text:
            result = await egress.active_channel_emitter().send(
                msg.channel_id,
                egress.OutboundContent(body=outcome.reply_text),
                guild_id=msg.guild_id,
            )
            if result.sent:
                nl_engine.note_reply_delivered(
                    msg.guild_id, msg.user_id,
                    used_fresh_allowance=outcome.used_fresh_allowance)
                if result.message_id:
                    from sb.domain.ai import review

                    review.remember_answer(result.message_id, review.AnswerContext(
                        guild_id=msg.guild_id, channel_id=msg.channel_id,
                        user_id=msg.user_id, message_id=msg.message_id,
                        question=msg.raw_text, answer=outcome.reply_text,
                        task=outcome.task, route=outcome.route,
                        provider=outcome.provider, model=outcome.model,
                        recorded_at=time.monotonic()))
        if outcome.decision in ("degraded", "denied") and outcome.reason in (
            "provider_unavailable", "grounding_failed", "no_route_matched",
        ):
            from sb.domain.ai import review

            await review.record_unknown(
                guild_id=msg.guild_id, channel_id=msg.channel_id,
                user_id=msg.user_id, message_id=msg.message_id,
                reason_code=outcome.reason, task=outcome.task,
                route=outcome.route, question=msg.raw_text,
                answer=outcome.reply_text,
                provider=outcome.provider, model=outcome.model)
        return outcome
    except Exception:  # noqa: BLE001 — the shell never breaks the event loop
        logger.warning("nl shell: handle_gateway_message failed", exc_info=True)
        return None


# --- the discord history scanner (memory.install_history_scanner) -------------------

#: reader(guild_id, channel_id) -> [(user_id, display_name, text,
#: author_is_bot), ...] oldest-first. The live composition root installs
#: a discord.TextChannel.history-backed reader.
ChannelHistoryReader = Callable[
    [int, int], Awaitable[list[tuple[int, str | None, str, bool]]],
]

_history_reader: ChannelHistoryReader | None = None


def install_channel_history_reader(reader: ChannelHistoryReader) -> None:
    global _history_reader
    _history_reader = reader


def reset_history_reader_for_tests() -> None:
    global _history_reader
    _history_reader = None


async def _scan(guild_id: int, channel_id: int) -> int:
    """The scanner memory.install_history_scanner expects: seed the
    in-process buffer from channel history (bodies never persisted)."""
    if _history_reader is None:
        return 0
    from sb.kernel.ai import conversation

    try:
        turns = await _history_reader(guild_id, channel_id)
    except Exception:  # noqa: BLE001 — a scan fault = no seeding
        logger.debug("nl shell: history scan failed", exc_info=True)
        return 0
    count = 0
    for user_id, display_name, text, author_is_bot in turns:
        conversation.append(
            guild_id, channel_id, user_id=user_id,
            role=("assistant" if author_is_bot else "user"),
            text=text, display_name=display_name)
        count += 1
    return count


def install_history_scanner() -> None:
    """Arm memory's discord leg (composition root, after the reader)."""
    memory.install_history_scanner(_scan)
