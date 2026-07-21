"""D5.1 breadth 2 — a SLASH command driven end-to-end through the REAL adapter.

Every prior e2e flow drove a `!`-prefix command (or the emitter directly). This
one exercises the distinct SLASH surface: `invoke_slash("economy")` dispatches
through the real slash / app_commands path (`dispatch_interaction`), and its
`economy.hub` PanelRef route is materialized by the REAL
`sb/adapters/discord/panel_view.py` into a real `discord.Embed` PLUS a real
`PanelRuntimeView` carrying the hub's `Button` action grid — proving the tier
covers the interaction surface, not just prefix messages. `/economy` is a
stable, well-covered command outside the claimed test-depth scopes.
"""

from __future__ import annotations

import asyncio

from tests.e2e.conftest import boot_e2e_harness


def test_slash_economy_renders_real_embed_and_button_view_through_adapter() -> None:
    async def _body() -> None:
        harness, recorder = await boot_e2e_harness()
        try:
            import discord

            await harness.invoke_slash("economy", persona="member")

            cap = recorder.panel("economy.hub")

            # the REAL adapter built a real discord.Embed off the SLASH
            # dispatch — the shipped Economy Panel.
            assert isinstance(cap.embed, discord.Embed)
            assert cap.embed.title == "💰 Economy Panel"

            # ...and a real PanelRuntimeView (discord.ui.View) carrying the
            # hub's real Button action grid (no Select — the hub is buttons).
            assert isinstance(cap.view, discord.ui.View)
            assert type(cap.view).__name__ == "PanelRuntimeView"
            assert type(cap.view).__module__ == "sb.adapters.discord.panel_view"
            buttons = [c for c in cap.view.children
                       if isinstance(c, discord.ui.Button)]
            assert len(buttons) >= 3
            # the shipped custom-id-override front door is present on the wire.
            assert any(getattr(b, "custom_id", None) == "economy:daily"
                       for b in buttons)
        finally:
            await harness.close()

    asyncio.run(_body())
