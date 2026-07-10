"""UX Lab entry-point handlers — the one front door (the shipped cog was
"thin: !uxlab command + hub creation, nothing else" — the lab's design
plan, verbatim). All read-only: the lab is the shipped ZERO-WRITE gallery
(no ops, no writes, no compensator surface).
"""

from __future__ import annotations

from sb.kernel.interaction.handler_kit import Reply

__all__ = ["Reply", "ensure_handler_refs"]


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("ux_lab.home_view")):
        return

    @handler("ux_lab.home_view")
    async def home_view(req):
        """!uxlab (alias !interfacelab) / /uxlab — the shipped UX Lab home
        panel (UxLabHomeView; goldens/ux_lab/sweep_uxlab.json +
        goldens/uxlab/sweep_slash_uxlab.json)."""
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef("ux_lab.home"), req)
        # the shipped slash path bound its view to the interaction's
        # original response AFTER the send (`view.message = await
        # interaction.original_response()` — ux_lab_cog.uxlab_slash; the
        # slash golden pins the GET as its second call). Optional duck-
        # typed responder port: the parity capture twin records the wire
        # verb; the live discord presenter already performs this fetch
        # inside its own send path, so the live responders don't carry it.
        fetch = getattr(req.responder, "fetch_original_response", None)
        if fetch is not None:
            await fetch()
        return None


def _register_pending() -> None:
    """The shipped wings (8 exhibit browsers + the ⚖️ Compare panel —
    disbot/views/ux_lab/) are their own port slice; every wing click lands
    on the declared + honest refusal terminal (the role/utility-band
    precedent), never a silent stub."""
    from sb.domain.operator_spine import pending_handler

    _PENDING = "'s exhibit browser ports with the lab's wings slice."
    pending_handler("ux_lab.buttons_wing", f"🔘 The Buttons wing{_PENDING}")
    pending_handler("ux_lab.selects_wing", f"📋 The Selects wing{_PENDING}")
    pending_handler("ux_lab.modals_wing", f"⌨️ The Modals wing{_PENDING}")
    pending_handler("ux_lab.embeds_wing", f"\U0001faa7 The Embeds wing{_PENDING}")
    pending_handler("ux_lab.components_v2_wing",
                    f"\U0001f9f1 The Components V2 wing{_PENDING}")
    pending_handler("ux_lab.pil_cards_wing",
                    f"🎨 The PIL cards wing{_PENDING}")
    pending_handler("ux_lab.mock_studio_wing",
                    f"🎭 The Mock studio wing{_PENDING}")
    pending_handler("ux_lab.probe_bench_wing",
                    f"🔬 The Probe bench{_PENDING}")
    pending_handler("ux_lab.compare_wing",
                    "⚖️ The Compare panel ports with the lab's wings slice.")


_register()
_register_pending()


def ensure_handler_refs() -> None:
    _register()
    _register_pending()
