"""Live responders chunk over-limit success copy (found live, band-2
slice 2: `!coglist`'s manifest listing is >2000 chars — Discord 400s the
send and the invoker sees NOTHING). Hermetic + roster-free — duck-typed
ctx/interaction, no discord import, no sb.manifest import."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from sb.adapters.discord.responders import (
    InteractionResponder,
    MessageResponder,
    _content_chunks,
)
from sb.spec.outcomes import ReplyVisibility


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def _result(message: str):
    return SimpleNamespace(user_message=message,
                           reply_visibility=ReplyVisibility.PUBLIC)


class TestContentChunks:
    def test_short_text_is_one_chunk(self):
        assert _content_chunks("hello") == ["hello"]

    def test_exactly_at_limit_is_one_chunk(self):
        text = "x" * 2000
        assert _content_chunks(text) == [text]

    def test_splits_on_line_boundaries(self):
        lines = [f"• line {i:04d} " + "y" * 60 for i in range(40)]
        text = "\n".join(lines)
        chunks = _content_chunks(text)
        assert len(chunks) > 1
        assert all(len(c) <= 2000 for c in chunks)
        # no line is torn across chunks; nothing is lost
        assert [ln for c in chunks for ln in c.splitlines()] == lines

    def test_single_pathological_line_hard_splits(self):
        text = "z" * 4500
        chunks = _content_chunks(text)
        assert all(len(c) <= 2000 for c in chunks)
        assert "".join(chunks) == text


class TestMessageResponderChunking:
    def test_long_render_sends_every_chunk(self):
        sent: list[str] = []

        async def reply(content, **kwargs):
            assert len(content) <= 2000
            sent.append(content)

        ctx = SimpleNamespace(reply=reply)
        text = "\n".join(f"• subsystem {i:03d} — details" for i in range(120))
        assert len(text) > 2000
        run(MessageResponder(ctx).render(_result(text)))
        assert len(sent) > 1
        assert [ln for c in sent for ln in c.splitlines()] == text.splitlines()

    def test_short_render_single_send(self):
        sent: list[str] = []

        async def reply(content, **kwargs):
            sent.append(content)

        run(MessageResponder(SimpleNamespace(reply=reply)).render(
            _result("ok")))
        assert sent == ["ok"]


class TestInteractionResponderChunking:
    def test_first_chunk_via_response_rest_via_followup(self):
        first: list[str] = []
        follow: list[str] = []

        class Response:
            def is_done(self):
                return bool(first)

            async def send_message(self, content, *, ephemeral):
                assert len(content) <= 2000
                first.append(content)

        class Followup:
            async def send(self, content, *, ephemeral):
                assert len(content) <= 2000
                follow.append(content)

        interaction = SimpleNamespace(response=Response(), followup=Followup())
        text = "\n".join(f"row {i:04d} " + "w" * 50 for i in range(80))
        assert len(text) > 2000
        run(InteractionResponder(interaction).render(_result(text)))
        assert len(first) == 1
        assert follow, "remaining chunks go out as followups"
        assert [ln for c in first + follow for ln in c.splitlines()] \
            == text.splitlines()
