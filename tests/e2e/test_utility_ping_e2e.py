"""D5.1 exemplar 2 — `!ping` driven end-to-end through the REAL discord adapter.

A second command in a different, stable domain (utility) — proves the tier
generalizes past a single command: `!ping` dispatches through the real pipeline
and its `utility.pong` panel is materialized by the REAL `panel_view.build_embed`
into a real `discord.Embed`. Utility reads are outside the claimed test-depth
scopes.
"""

from __future__ import annotations

import asyncio

from tests.e2e.conftest import boot_e2e_harness


def test_ping_command_renders_real_embed_through_adapter() -> None:
    async def _body() -> None:
        harness, recorder = await boot_e2e_harness()
        try:
            import discord

            await harness.send_command("!ping", persona="member")

            cap = recorder.panel("utility.pong")
            assert isinstance(cap.embed, discord.Embed)
            assert cap.embed.title == "🏓 Pong!"
        finally:
            await harness.close()

    asyncio.run(_body())
