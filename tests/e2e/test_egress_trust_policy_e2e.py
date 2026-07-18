"""D5.1 exemplar 3 — the S11 egress trust policy through the REAL adapter.

Service-initiated sends route through ONE `ChannelEmitter.send`; the real
`sb/adapters/discord/egress.py:DiscordChannelEmitter` is the ONLY module that
constructs `discord.AllowedMentions` (the default-deny mass-ping fence, D-0021
S11). The golden-parity `ParityChannelEmitter` re-implements the neutralization
but never builds the real `discord.AllowedMentions`/`discord.Object` — so this
policy is byte-invisible to parity (D5 doc P1). Here the e2e recorder installs
the REAL emitter, and we drive the real send seam end-to-end, asserting on the
real discord types that reach the (recording) channel.
"""

from __future__ import annotations

import asyncio

from tests.e2e.conftest import boot_e2e_harness


def test_untrusted_send_suppresses_mentions_through_real_adapter() -> None:
    async def _body() -> None:
        harness, recorder = await boot_e2e_harness()
        try:
            import discord
            from sb.kernel.interaction.egress import (
                OutboundContent,
                TrustLevel,
                active_channel_emitter,
            )

            emitter = active_channel_emitter()  # the real DiscordChannelEmitter
            result = await emitter.send(
                4242,
                OutboundContent(body="hey @everyone **bold**",
                                trust=TrustLevel.UNTRUSTED),
                guild_id=int(harness.world.guild_id))

            assert result.sent is True
            assert len(recorder.sends) == 1
            send = recorder.sends[0]
            assert send.channel_id == 4242

            # UNTRUSTED body is kernel-side neutralized (markdown escaped +
            # @everyone broken with a zero-width space).
            body = send.args[0]
            assert body == "hey @​everyone \\*\\*bold\\*\\*"

            # ...AND the real adapter passes a real discord.AllowedMentions
            # equal to .none() (belt-and-suspenders default-deny).
            am = send.kwargs["allowed_mentions"]
            assert isinstance(am, discord.AllowedMentions)
            none = discord.AllowedMentions.none()
            assert (am.everyone, am.roles, am.users) == (
                none.everyone, none.roles, none.users)
        finally:
            await harness.close()

    asyncio.run(_body())


def test_trusted_send_honors_explicit_allowlist_through_real_adapter() -> None:
    async def _body() -> None:
        harness, recorder = await boot_e2e_harness()
        try:
            import discord
            from sb.kernel.interaction.egress import (
                OutboundContent,
                TrustLevel,
                active_channel_emitter,
            )

            emitter = active_channel_emitter()
            await emitter.send(
                4243,
                OutboundContent(body="ping the owner",
                                trust=TrustLevel.SYSTEM,
                                allow_mentions=("user:777",)),
                guild_id=int(harness.world.guild_id))

            am = recorder.sends[0].kwargs["allowed_mentions"]
            assert isinstance(am, discord.AllowedMentions)
            # the explicit allowlist maps to a real discord.Object, @everyone
            # stays denied.
            assert am.everyone is False
            assert len(am.users) == 1
            assert isinstance(am.users[0], discord.Object)
            assert am.users[0].id == 777
        finally:
            await harness.close()

    asyncio.run(_body())
