"""D5.1 breadth — a CROSS-USER karma WRITE + the standing-card READ that
reflects it, end-to-end through the REAL discord adapter.

The tier's other write flow (`!daily`) grants the invoker's OWN balance; this
one moves state BETWEEN members: `!thanks @other` runs the audited `karma.give`
K7 workflow (a real Postgres grant on a fresh peer-reputation row), then
`!karma @other` and `!karma` (self) open the shipped `karma.card` — materialized
by the REAL `sb/adapters/discord/panel_view.py` into a real `discord.Embed`. We
assert BOTH sides of the grant off the persisted read: the recipient's
Karma/Rank/Activity trio (`received 1 · given 0`, rank #1) and the giver's
mirror (`received 0 · given 1`), plus the shipped card surface — display-name
title, avatar thumbnail, the INLINE Karma/Rank pair, the non-inline Activity
field, the footer literal, and zero components (a component-less result card, a
surface no other e2e flow exercises). Karma is a stable, unclaimed
peer-reputation domain outside the claimed test-depth scopes.
"""

from __future__ import annotations

import asyncio

from tests.e2e.conftest import boot_e2e_harness

#: parity/harness/world.py DEFAULT_PERSONAS — the giver (MemberActor) and the
#: recipient (OtherActor), two distinct non-admin members in the capture world.
_GIVER = 900_000_000_000_000_102
_RECIPIENT = 900_000_000_000_000_103


def test_thanks_write_then_card_reflects_the_grant_through_real_adapter() -> None:
    async def _body() -> None:
        harness, recorder = await boot_e2e_harness()
        try:
            import discord

            from sb.domain.karma import service

            guild_id = harness.world.guild_id

            # 1) the CROSS-USER write: MemberActor thanks OtherActor. This runs
            #    the audited karma.give K7 workflow (a real Postgres grant); the
            #    handler's SUCCESS path is a text reply, so no panel is captured
            #    here — the mutation is what we assert next.
            await harness.send_command(f"!thanks <@{_RECIPIENT}>",
                                       persona="member")

            # 1a) the real persisted write: the recipient now holds one karma
            #     point, received once, given none — a fresh rank-#1 row.
            record = await service.get_record(guild_id, _RECIPIENT)
            assert record.points == 1
            assert record.received_count == 1
            assert record.given_count == 0
            assert record.rank == 1

            # 2) the recipient's standing card — the REAL adapter builds a real
            #    discord.Embed off the persisted read (not the parity wire-dict).
            await harness.send_command(f"!karma <@{_RECIPIENT}>",
                                       persona="member")
            recipient_card = recorder.panel("karma.card")
            assert isinstance(recipient_card.embed, discord.Embed)
            assert recipient_card.embed.title == "✨ Karma — OtherActor"
            # the shipped Karma/Rank inline pair + the non-inline Activity field,
            # all reflecting the K7 grant.
            fields = {f.name: (f.value, f.inline)
                      for f in recipient_card.embed.fields}
            assert fields["Karma"] == ("**1** ✨", True)
            assert fields["Rank"] == ("#1", True)
            assert fields["Activity"] == (
                "received **1** · given **0**", False)
            # the shipped footer literal + avatar thumbnail; a component-less
            # result card (no View children) — the surface no other flow drives.
            assert (recipient_card.embed.footer.text
                    == "Thank helpful members with !thanks @user")
            assert recipient_card.embed.thumbnail.url
            assert recipient_card.view.children == []

            # 3) the GIVER's mirror card — the same persisted grant, other side:
            #    received 0, given 1 (MemberActor never received karma).
            await harness.send_command("!karma", persona="member")
            giver_card = [c for c in recorder.panels
                          if c.panel_id == "karma.card"][-1]
            assert giver_card.embed.title == "✨ Karma — MemberActor"
            giver_fields = {f.name: f.value for f in giver_card.embed.fields}
            assert giver_fields["Karma"] == "**0** ✨"
            assert giver_fields["Activity"] == "received **0** · given **1**"
        finally:
            await harness.close()

    asyncio.run(_body())
