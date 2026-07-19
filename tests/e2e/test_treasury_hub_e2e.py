"""D5.1 breadth — the treasury hub, a PROVIDER-fed embed driven end-to-end
through the REAL discord adapter.

The tier's other opening renders carry static or renderer-composed fields; this
one exercises a distinct surface: a `FieldsBlock(provider=…)` whose rows come
from a LIVE read of TWO domain stores (`treasury.store.get_treasury` +
`economy.store.get_coins`). `!treasury` opens `treasury.hub` — materialized by
the REAL `sb/adapters/discord/panel_view.py` into a real `discord.Embed` (gold
accent, the provider's Treasury / Your-wallet fields, the renderer_override's
inline-field + literal-footer adjustments) PLUS a real `PanelRuntimeView`
carrying the shipped Contribute + Refresh button pair. On a fresh world both
stores read empty, so we assert the shipped zero-state bytes — an honest
provider read, not an invented balance. Treasury is a stable, unclaimed
economy-adjacent domain outside the claimed test-depth scopes.
"""

from __future__ import annotations

import asyncio

from tests.e2e.conftest import boot_e2e_harness


def test_treasury_hub_renders_provider_fields_and_buttons_through_adapter() -> None:
    async def _body() -> None:
        harness, recorder = await boot_e2e_harness()
        try:
            import discord

            await harness.send_command("!treasury", persona="member")

            cap = recorder.panel("treasury.hub")

            # the REAL adapter built a real discord.Embed — the shipped gold
            # Server Treasury card with the renderer_override's footer literal.
            assert isinstance(cap.embed, discord.Embed)
            assert cap.embed.title == "🏛️ Server Treasury"
            assert cap.embed.color == discord.Color.gold()
            assert cap.embed.footer.text == "➕ Contribute · 🔄 Refresh"

            # the FieldsBlock provider read BOTH stores (treasury pool + the
            # invoker's wallet) live; a fresh world reads empty, and the shipped
            # renderer_override renders both fields inline=True.
            fields = {f.name: (f.value, f.inline) for f in cap.embed.fields}
            assert fields["Treasury"] == ("🏛️ **0** 🪙 in the pool", True)
            assert fields["Your wallet"] == ("🪙 **0** 🪙", True)

            # ...and a real PanelRuntimeView carrying the shipped two-button row
            # (Contribute opens the modal; Refresh re-reads) — no nav, no Select.
            assert isinstance(cap.view, discord.ui.View)
            assert type(cap.view).__name__ == "PanelRuntimeView"
            labels = {getattr(c, "label", None) for c in cap.view.children
                      if isinstance(c, discord.ui.Button)}
            assert labels == {"Contribute", "Refresh"}
            assert not any(isinstance(c, discord.ui.Select)
                           for c in cap.view.children)
        finally:
            await harness.close()

    asyncio.run(_body())
