"""D5.1 breadth 3 — a component CLICK → panel re-render through the REAL adapter.

The initial tier drove opening renders only; this closes the interactive gap.
`!economymenu` opens the real `economy.hub` panel (the REAL adapter builds its
embed + a `PanelRuntimeView` of `Button`s), then a real button click on the
hub's `economy:jobs` control is driven through the live component feed
(`dispatch_component` → the §3.4 static route → `resolve`), whose action handler
opens `economy.joblist_card` — materialized AGAIN by the REAL `panel_view.py`
into a second real `discord.Embed`. So a click round-trips command → component
feed → real panel re-render, the D5 doc's click-contract exercised end-to-end.
"""

from __future__ import annotations

import asyncio

from tests.e2e.conftest import boot_e2e_harness


def test_hub_button_click_rerenders_joblist_through_real_adapter() -> None:
    async def _body() -> None:
        harness, recorder = await boot_e2e_harness()
        try:
            import discord

            # 1) open the hub — the REAL adapter renders it + its button grid.
            await harness.send_command("!economymenu", persona="member")
            hub = recorder.panel("economy.hub")
            assert isinstance(hub.embed, discord.Embed)
            assert isinstance(hub.view, discord.ui.View)
            # the real Button whose custom_id we are about to click.
            assert any(getattr(c, "custom_id", None) == "economy:jobs"
                       for c in hub.view.children)

            # 2) click the hub's 📋 Jobs button through the real component feed
            #    (its static custom_id routes to the joblist action handler).
            #    message_id is not session-looked-up on the static-route path —
            #    the custom_id alone resolves the binding — so any id drives it.
            await harness.click(custom_id="economy:jobs", message_id=1,
                                persona="member")

            # 3) the click re-rendered a SECOND real panel through the adapter.
            card = recorder.panel("economy.joblist_card")
            assert isinstance(card.embed, discord.Embed)
            assert card.embed.title == "📋 All Jobs"
            # the render happened AFTER the hub open (a genuine re-render, not
            # the opening one).
            assert [c.panel_id for c in recorder.panels] == [
                "economy.hub", "economy.joblist_card"]
        finally:
            await harness.close()

    asyncio.run(_body())
