"""Curation rework 2026-07-13 — panel nav/handler wiring (ORDER 017
item 2; evidence docs/review/curation-report-2026-07-13.md).

Three shipped buttons whose clicks landed on pending terminals while
their live destinations already existed at HEAD now route to those
destinations. All three swaps are byte-neutral on the wire: every
affected button's label/style/custom_id stays exactly as the goldens
pin it — only the server-side handler route moved. The retired refs
(`server_management.{moderation,roles,cleanup}_pending`,
`mining.workshop_hub_pending`, `utility.invite_pending`) must stay
gone — a re-registration means a regression re-parked a live surface.
The server_management trio's nav pins live with the hub's own suite
(tests/unit/band6/test_band6_server_management_hub.py); this module
pins the mining + utility swaps and the retirement sweep.
"""

from __future__ import annotations


def test_workshop_back_navigates_to_the_live_mining_hub():
    from sb.domain.mining.panels import mining_workshop_spec
    from sb.spec.refs import PanelRef

    by_id = {a.action_id: a for a in mining_workshop_spec().actions}
    # the sk_hub / vault / forge back-button pattern — never a terminal.
    assert by_id["ws_back"].handler == PanelRef("mining.hub")
    # the shipped bytes survive (session panels mint <cid:N> ids; the
    # golden pins label + style only).
    assert by_id["ws_back"].label == "↩ Workshop"


def test_utility_invite_button_routes_to_the_live_handler():
    from sb.domain.utility.panels import utility_panel_spec
    from sb.spec.refs import HandlerRef

    by_id = {a.action_id: a for a in utility_panel_spec().actions}
    # the argless `!invite` route (D-0077 channel-ops port) — the same
    # handler the manifest command declares.
    assert by_id["invite"].handler == HandlerRef("utility.invite_view")
    assert by_id["invite"].label == "🔗 Invite"

    from sb.manifest.utility import MANIFEST

    invite_cmds = [c for c in MANIFEST.commands if c.name == "invite"]
    assert invite_cmds and all(
        c.route == HandlerRef("utility.invite_view") for c in invite_cmds)


def test_the_retired_pending_refs_stay_gone():
    """Import the touched surfaces + run their ensure hooks, then sweep:
    none of the five retired terminals may re-register."""
    from sb.domain.mining import panels as mining_panels
    from sb.domain.server_management import handlers as sm_handlers
    from sb.domain.utility import handlers as utility_handlers
    from sb.spec.refs import HandlerRef, is_registered

    sm_handlers.ensure_handler_refs()
    utility_handlers.ensure_handler_refs()
    mining_panels.ensure_panel_refs()
    for name in ("server_management.moderation_pending",
                 "server_management.roles_pending",
                 "server_management.cleanup_pending",
                 "mining.workshop_hub_pending",
                 "utility.invite_pending"):
        assert not is_registered(HandlerRef(name)), name
