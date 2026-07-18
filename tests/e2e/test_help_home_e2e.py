"""D5.1 exemplar 1 — `!help` driven end-to-end through the REAL discord adapter.

The headline command→adapter→response flow: a real prefix command dispatches
through the real interaction pipeline, produces a kernel `RenderedPanel`, and is
materialized by the REAL `sb/adapters/discord/panel_view.py` into a real
`discord.Embed` + a real `discord.ui.View` (`PanelRuntimeView`) — the exact
"real panel-view render" the golden-parity fake transport can never exercise
(D5 doc P1). `help`/`help.home` is a stable, well-covered read domain, chosen to
avoid the claimed test-depth scopes.
"""

from __future__ import annotations

import asyncio

from tests.e2e.conftest import boot_e2e_harness


def test_help_command_renders_real_embed_and_view_through_adapter() -> None:
    async def _body() -> None:
        harness, recorder = await boot_e2e_harness()
        try:
            import discord

            await harness.send_command("!help", persona="member")

            cap = recorder.panel("help.home")

            # the REAL adapter built a real discord.Embed (not the parity
            # presenter's wire-dict) — title + a non-trivial field set.
            assert isinstance(cap.embed, discord.Embed)
            assert cap.embed.title == "📚 Help Menu"
            assert len(cap.embed.fields) == 6

            # the REAL adapter built the one PanelRuntimeView — a real
            # discord.ui.View (panel_view.py's per-call nested class) — with a
            # real component child.
            assert isinstance(cap.view, discord.ui.View)
            assert type(cap.view).__name__ == "PanelRuntimeView"
            assert type(cap.view).__module__ == "sb.adapters.discord.panel_view"
            assert len(cap.view.children) == 1
            assert isinstance(cap.view.children[0], discord.ui.Select)
        finally:
            await harness.close()

    asyncio.run(_body())
