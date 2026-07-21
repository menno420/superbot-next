"""D5.1 breadth 1 — a WRITE command driven end-to-end through the REAL adapter.

The prior four e2e flows all render READS (`!help`, `!ping`) or drive the
emitter directly (S11). This one closes the write gap: `!daily` runs the
audited `economy.daily` K7 WRITE op (a real Postgres balance grant on a fresh
tracking row), then the REAL `sb/adapters/discord/panel_view.py` materializes
the `economy.daily_card` result embed. We assert the real `discord.Embed`'s
claim-parameterized fields (`Coins earned` / `Balance`) reflect the mutation —
so the whole command → real domain op → real egress chain is exercised, not
just the render. Economy's daily write is a stable, well-covered path outside
the claimed test-depth scopes.
"""

from __future__ import annotations

import asyncio

from tests.e2e.conftest import boot_e2e_harness


def test_daily_write_command_renders_real_embed_reflecting_the_grant() -> None:
    async def _body() -> None:
        harness, recorder = await boot_e2e_harness()
        try:
            import discord

            # a fresh member's FIRST daily claim: the audited economy.daily
            # workflow writes a new balance row, then the result card renders.
            await harness.send_command("!daily", persona="member")

            cap = recorder.panel("economy.daily_card")

            # the REAL adapter built a real discord.Embed (not the parity
            # wire-dict) — the shipped Daily Reward card.
            assert isinstance(cap.embed, discord.Embed)
            assert cap.embed.title == "🎁 Daily Reward"

            # the embed's claim-parameterized fields reflect the K7 WRITE:
            # a fresh claim grants a positive amount and the persisted balance
            # equals it (streak 1, one total claim).
            fields = {f.name: f.value for f in cap.embed.fields}
            assert set(fields) == {
                "Coins earned", "Balance", "Streak", "Total claims"}
            earned = int(fields["Coins earned"].strip("*+ 🪙"))
            balance = int(fields["Balance"].strip("* 🪙"))
            assert earned > 0
            assert balance == earned          # fresh row: balance == the grant
            assert fields["Streak"] == "🔥 **1** days"
            assert fields["Total claims"] == "1"
        finally:
            await harness.close()

    asyncio.run(_body())
