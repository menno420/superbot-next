"""Four-twenty read handlers — thin HandlerRef routes over the content
pools (the shipped four_twenty_cog.py button actions: random.choice over
the four_twenty_content.json pools). All read-only: no ops, no writes.

Under-port note (no golden pins any click): the shipped wisdom/fact
buttons EDITED the panel message in place with a fresh leafy-green embed
(``interaction.response.edit_message(embed=..., view=self)``, footer
"Click ↩ Overview to return."); the port renders the picked line through
the kernel result grammar (the general subsystem's shipped-sibling lane).
The in-place embed edit joins when a golden pins its bytes.
"""

from __future__ import annotations

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import SUCCESS

__all__ = ["Reply", "ensure_handler_refs"]


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("four_twenty.panel_view")):
        return

    @handler("four_twenty.panel_view")
    async def panel_view(req):
        """!420 (aliases !fourtwenty, !fourtwenty420) — the shipped 420
        overview panel (_FourTwentyPanelView;
        parity/goldens/four_twenty/sweep_420.json)."""
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef("four_twenty.overview"), req)
        return None

    @handler("four_twenty.wisdom_view")
    async def wisdom_view(req) -> Reply:
        from sb.domain.four_twenty.content import WISDOM, pick

        return Reply(SUCCESS, f"🍃 {pick(WISDOM, 'wisdom')}")

    @handler("four_twenty.fact_view")
    async def fact_view(req) -> Reply:
        from sb.domain.four_twenty.content import FACTS, pick

        return Reply(SUCCESS, f"🔢 {pick(FACTS, 'facts')}")


_register()


def ensure_handler_refs() -> None:
    _register()
