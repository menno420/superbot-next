"""Band 7 — the ORDER-004 walking-skeleton drive for the ai REVIEW-LOOP +
PRESETS surface: boot the replay composition root (DB-free) and drive the
shipped `!aireview` family through the REAL pipeline — dispatch → handler →
card panel / typed op → presenter — asserting the golden-pinned wire bytes,
plus the review-loop listener seams (👎 reaction consumer + the
correction-reply observer over the in-memory answer registry).

The same drives replay against real Postgres via the golden corpus
(the re-homed goldens/ai/sweep_aireview* family, 11/11 green —
tools/run_golden_parity.py)."""

from __future__ import annotations

import asyncio
import time

import pytest

run = asyncio.run

DARK_RED = 10038562   # discord.Color.dark_red() — the shipped review accent
STATUS_FOOTER = ("!aireview channel #chan · !aireview list "
                 "[unknown|correction] · !aireview export · "
                 "!aireview resolve <id> · !aireview off")


@pytest.fixture()
def skeleton():
    """The replay composition root, DB-free (the ai skeleton pattern —
    the shipped review reads are fail-safe, so the empty/miss bytes
    render without a store)."""
    from sb.adapters.parity.boot import Harness
    from sb.domain.ai import review
    from sb.kernel.interaction.resolve import (
        install_access_policy_reader,
        install_visibility_reader,
    )

    h = run(Harness.start(require_db=False))

    async def _no_policy(guild_id):
        return None

    async def _all_visible(guild_id, subsystem):
        return True

    install_access_policy_reader(_no_policy)
    install_visibility_reader(_all_visible)
    review.reset_registry_for_tests()
    yield h
    review.reset_registry_for_tests()
    run(h.close())


def test_walking_skeleton_bare_aireview_status(skeleton):
    """bare `!aireview` → the shipped 🔎 status embed: dark-red accent,
    the not-set channel line, the 0/0 unreviewed counts, the shipped
    footer (goldens/ai/sweep_aireview pins every byte)."""
    run(skeleton.send_command("!aireview", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    (embed,) = calls[0].payload["embeds"]
    assert embed["title"] == "🔎 AI answer review log"
    assert embed["color"] == DARK_RED
    assert embed["description"] == (
        "Review channel: *(not set)*\n"
        "Unreviewed — **0** didn't-know · **0** corrections")
    assert embed["footer"]["text"] == STATUS_FOOTER
    assert calls[0].payload["components"] == []


def test_walking_skeleton_channel_usage_and_off(skeleton):
    """`!aireview channel` (no argument) → the shipped usage byte
    (goldens/ai/sweep_aireview_channel); `!aireview resolve 3` DB-free →
    the shipped miss byte (the shipped get_entry read is fail-safe)."""
    run(skeleton.send_command("!aireview channel", persona="admin"))
    calls = skeleton.take_calls()
    assert calls[0].payload["content"] == (
        "Usage: `!aireview channel #channel` (or `!aireview off` to "
        "clear).")
    run(skeleton.send_command("!aireview resolve 3", persona="admin"))
    calls = skeleton.take_calls()
    assert calls[0].payload["content"] == "⚠️ No entry `#3` in this server."


def test_walking_skeleton_preset_usage_byte(skeleton):
    """bare `!aireview preset` → the shipped usage copy
    (goldens/ai/sweep_aireview_preset)."""
    run(skeleton.send_command("!aireview preset", persona="admin"))
    calls = skeleton.take_calls()
    assert calls[0].payload["content"] == (
        "Vetted answer presets — the bot serves these verbatim, no AI "
        "call:\n"
        '`!aireview preset add "<question>" <answer>` · '
        "`!aireview preset from <entry_id> <answer>` · "
        "`!aireview preset list` · `!aireview preset remove <id>`")


def test_walking_skeleton_preset_add_validation_byte(skeleton):
    """`!aireview preset add "?!" x` — a question that normalizes to
    empty → the shipped ⚠️ couldn't-store byte (the shipped service
    ValueError string), before any store write."""
    run(skeleton.send_command('!aireview preset add "?!" x',
                              persona="admin"))
    calls = skeleton.take_calls()
    assert calls[0].payload["content"] == (
        "⚠️ Couldn't store that preset: question is empty after "
        "normalization.")


def test_walking_skeleton_preset_miss_bytes(skeleton):
    """`preset from` / `preset remove` misses → the shipped ⚠️ bytes
    (goldens/ai/sweep_aireview_preset_from / _preset_remove)."""
    run(skeleton.send_command("!aireview preset from 3 test",
                              persona="admin"))
    calls = skeleton.take_calls()
    assert calls[0].payload["content"] == (
        "⚠️ No review entry `#3` in this server.")
    run(skeleton.send_command("!aireview preset remove 3",
                              persona="admin"))
    calls = skeleton.take_calls()
    assert calls[0].payload["content"] == (
        "⚠️ No preset `#3` in this server.")


def test_quote_aware_question_split():
    """The shipped `preset add "<question>" <answer>` converter split —
    discord.py StringView quote handling on the first argument."""
    from sb.domain.ai.service import _split_leading_token

    assert _split_leading_token("test test") == ("test", "test")
    assert _split_leading_token('"what is x" it is y') == (
        "what is x", "it is y")
    assert _split_leading_token("“what is x” it is y") == (
        "what is x", "it is y")
    assert _split_leading_token("solo") == ("solo", "")
    assert _split_leading_token("") == ("", "")


def test_correction_cues_shipped_heuristic():
    """utils/ai_correction_cues.looks_like_correction, ported verbatim:
    corrections fire, follow-ups and thanks do not."""
    from sb.domain.ai.correction_cues import looks_like_correction

    assert looks_like_correction("no, it's actually 42")
    assert looks_like_correction("that's wrong")
    assert looks_like_correction("Actually it launched in 2011")
    assert not looks_like_correction("thanks!")
    assert not looks_like_correction("tell me more")
    assert not looks_like_correction("nobody knows")
    assert not looks_like_correction("")
    assert not looks_like_correction(None)


def _remember(reply_message_id: int) -> None:
    from sb.domain.ai import review

    review.remember_answer(reply_message_id, review.AnswerContext(
        guild_id=1, channel_id=2, user_id=3, message_id=4,
        question="q", answer="a", task="general.nl_answer",
        route="general.nl_answer", provider="deterministic", model=None,
        recorded_at=time.monotonic()))


def test_thumbs_down_consumer_registered_and_dedupes(skeleton):
    """The 👎 reaction consumer is bound to the kernel reaction seam at
    import (the tournament sign-up precedent) and flags a REMEMBERED
    answer exactly once per (message, flagger) — the shipped
    on_raw_reaction_add semantics. The DB record leg is fail-safe."""
    from sb.domain.ai import review
    from sb.kernel.interaction.reactions import (
        ReactionEvent,
        dispatch_reaction,
        registered_reaction_consumers,
    )

    assert "ai.review_thumbs_down" in registered_reaction_consumers()
    _remember(9001)
    event = ReactionEvent(guild_id=1, channel_id=2, message_id=9001,
                          user_id=77, emoji="👎")
    run(dispatch_reaction(event))
    assert review.already_flagged(9001, 77)
    # the wrong emoji / an unremembered message never flag.
    _remember(9002)
    run(dispatch_reaction(ReactionEvent(guild_id=1, channel_id=2,
                                        message_id=9002, user_id=77,
                                        emoji="👍")))
    assert not review.already_flagged(9002, 77)


def test_correction_reply_observer(skeleton):
    """The correction-reply observer (shipped AICorrectionStage): a reply
    to a remembered AI answer whose text reads as a correction is flagged;
    non-correction replies and unremembered targets are not."""
    from types import SimpleNamespace

    from sb.domain.ai import review

    _remember(9100)

    def msg(ref_id, content):
        return SimpleNamespace(
            author=SimpleNamespace(id=55, bot=False),
            guild=SimpleNamespace(id=1),
            channel=SimpleNamespace(id=2),
            reference=SimpleNamespace(message_id=ref_id),
            content=content)

    run(review.observe_correction_reply(msg(9100, "tell me more")))
    assert not review.already_flagged(9100, 55)
    run(review.observe_correction_reply(msg(9100, "no, that's wrong")))
    assert review.already_flagged(9100, 55)
    # unremembered reply target → never flagged.
    run(review.observe_correction_reply(msg(9999, "that's wrong")))
    assert not review.already_flagged(9999, 55)


def test_suppress_mentions_wire_byte():
    """Reply.suppress_mentions → the shipped ``allowed_mentions:
    {"parse": []}`` body key on the capture wire (the preset-add
    confirmation's golden-pinned shape)."""
    from types import SimpleNamespace

    from sb.adapters.parity.transport import ParityResponder, ParityTransport
    from sb.kernel.interaction.handler_kit import Reply
    from sb.kernel.interaction.request import Surface
    from sb.spec.outcomes import ReplyVisibility

    class _Ids:
        def __init__(self):
            self.n = 0

        def allocate(self):
            self.n += 1
            return self.n

    transport = ParityTransport(ids=_Ids(), clock=None)
    responder = ParityResponder(transport, surface=Surface.PREFIX,
                                channel_id=123)
    result = SimpleNamespace(
        user_message="✅ Preset `#1` stored",
        reply_visibility=ReplyVisibility.PUBLIC,
        workflow=Reply("success", "✅ Preset `#1` stored",
                       suppress_mentions=True))
    run(responder.render(result))
    (call,) = transport.calls
    assert call.payload["allowed_mentions"] == {"parse": []}
    # the default Reply keeps the plain wire shape (no key at all).
    transport.calls.clear()
    result.workflow = Reply("success", "plain")
    run(responder.render(result))
    (call,) = transport.calls
    assert "allowed_mentions" not in call.payload
