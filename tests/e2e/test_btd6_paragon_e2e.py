"""D5.1 breadth — the BTD6 Paragon calculator, a MULTI-SELECT + LINK-button
view driven end-to-end through the REAL discord adapter.

Every prior e2e view is either a single Select (`!help`) or a Button grid
(`economy.hub`). This one exercises the tier's richest component surface:
`!paragon` opens `btd6.paragon` — materialized by the REAL
`sb/adapters/discord/panel_view.py` into a real `discord.Embed` PLUS a real
`PanelRuntimeView` carrying FOUR real `discord.ui.Select`s (paragon / players /
difficulty / extra-T5) and a button row that mixes dispatch buttons with a
`discord.ui.Button` LINK (🌐 Web calculator — a `ButtonStyle.link` child with a
`url` and no `custom_id`, the shipped `render_paragon` injection). It is a
pure-compute landing render (no DB), so we assert the shipped default-state
bytes — the Apex Plasma Master title/description, the three static fields, the
footer literal, and the full component roster. BTD6 is a stable, unclaimed
reference domain; the LINK-button wire shape is exercised by no other e2e flow.
"""

from __future__ import annotations

import asyncio

from tests.e2e.conftest import boot_e2e_harness


def test_paragon_renders_real_multiselect_and_link_button_view() -> None:
    async def _body() -> None:
        harness, recorder = await boot_e2e_harness()
        try:
            import discord

            await harness.send_command("!paragon", persona="member")

            cap = recorder.panel("btd6.paragon")

            # the REAL adapter built a real discord.Embed — the shipped
            # default-state calculator landing (green accent).
            assert isinstance(cap.embed, discord.Embed)
            assert cap.embed.title == "🔮 Paragon Calculator — Apex Plasma Master"
            assert cap.embed.color == discord.Color.green()
            assert cap.embed.description == (
                "**Paragon:** Apex Plasma Master (Dart Monkey)\n"
                "**Players:** 1 (solo)\n"
                "**Difficulty:** Medium\n"
                "**Extra T5s:** 0")
            assert [f.name for f in cap.embed.fields] == [
                "🧮 Calculate degree",
                "🎯 Requirements for a degree",
                "🔗 Web calculator & credits"]
            assert cap.embed.footer.text == (
                "Solo: 1 extra T5 (Dart only) · Co-op: up to 9 · totems "
                "are uncapped")

            # ...and a real PanelRuntimeView carrying the FOUR real
            # discord.ui.Selects (the shipped roster/players/difficulty/extra-T5
            # axes) — the tier's first multi-Select view.
            assert isinstance(cap.view, discord.ui.View)
            assert type(cap.view).__name__ == "PanelRuntimeView"
            selects = [c for c in cap.view.children
                       if isinstance(c, discord.ui.Select)]
            assert len(selects) == 4
            assert [s.placeholder for s in selects] == [
                "Choose a paragon…", "Players…", "Difficulty…", "Extra T5s…"]

            # the button row mixes dispatch buttons with the injected LINK
            # button: a real discord.ui.Button carrying a url + ButtonStyle.link
            # and NO custom_id — the shipped render_paragon injection, a wire
            # shape no other e2e flow exercises.
            buttons = [c for c in cap.view.children
                       if isinstance(c, discord.ui.Button)]
            link = [b for b in buttons if b.style is discord.ButtonStyle.link]
            assert len(link) == 1
            assert link[0].url == "https://paragon-calc.vercel.app/"
            assert link[0].label == "🌐 Web calculator"
            assert link[0].custom_id is None
            # the dispatch buttons (Calculate / Requirements / Stats / BTD6)
            # ride real custom_ids alongside the link.
            dispatch = [b for b in buttons
                        if b.style is not discord.ButtonStyle.link]
            assert len(dispatch) == 4
            assert all(b.custom_id for b in dispatch)
        finally:
            await harness.close()

    asyncio.run(_body())
