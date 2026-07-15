"""Mining — the grid Mine navigator + hub How-to port (curation rework
rows 45/59/60, PR #434): the hub's ⛏️ Mine / 📖 How-to buttons repoint
``mining.grid_view_pending`` / ``mining.how_to_pending`` → the live
``mining.grid`` / ``mining.howto`` PanelSpecs (oracle
``views/mining/grid_mine_view.py`` / ``how_to_panel.py`` @ 9c16365);
both retired pendings no longer register (trap 12a). ``sweep_minemenu``
stays byte-neutral (labels/styles/custom_id_overrides untouched) and
``sweep_mine`` keeps its capture-artifact byte on the prefix lane
(``mining.mine_route`` — the required golden-parity gate replays ported
subsystems green, so that byte rides the golden's retirement)."""

from __future__ import annotations


def test_hub_buttons_repoint_to_the_live_panels_byte_neutrally():
    from sb.domain.mining.panels import (
        GRID_PANEL_ID,
        HOWTO_PANEL_ID,
        mining_hub_spec,
    )
    from sb.spec.refs import PanelRef

    hub = mining_hub_spec()
    by_id = {a.action_id: a for a in hub.actions}
    mine = by_id["mi_mine"]
    assert mine.handler == PanelRef(GRID_PANEL_ID)
    # byte-neutral vs goldens/mining/sweep_minemenu: label/style/custom_id
    assert mine.label == "⛏️ Mine"
    assert mine.custom_id_override == "mining:mine"
    how_to = by_id["mi_how_to"]
    assert how_to.handler == PanelRef(HOWTO_PANEL_ID)
    assert how_to.label == "📖 How-to"
    assert how_to.custom_id_override == "mining:how_to"


def test_grid_spec_is_the_oracle_dpad():
    """MineGridView verbatim: the six dig buttons on the shipped rows
    (N 0 · W/E 1 · S 2 · Deeper/Up 3 · ↩ Mining Menu + 📚 Help 4), the
    shipped styles (primary laterals, success verticals), the 120s
    timeout, the invoker lock, the session lifecycle (run-minted
    ``<cid:N>`` ids — the shipped auto-id view shape)."""
    from sb.domain.mining.panels import GRID_PANEL_ID, mining_grid_spec
    from sb.spec.panels import ActionStyle, Audience, FooterMode
    from sb.spec.refs import HandlerRef, PanelRef

    spec = mining_grid_spec()
    assert spec.panel_id == GRID_PANEL_ID == "mining.grid"
    assert spec.title == "⛏️ Mine"
    assert spec.audience is Audience.INVOKER
    assert spec.session_lifecycle is True
    assert spec.timeout_s == 120                    # the shipped timeout
    assert spec.frame.style_token == "dark_grey"    # MINING_COLOR
    assert spec.frame.footer_mode is FooterMode.NONE
    by_id = {a.action_id: a for a in spec.actions}
    for action_id, label, style, direction in (
            ("gr_north", "⛏️ North", ActionStyle.PRIMARY, "north"),
            ("gr_west", "⛏️ West", ActionStyle.PRIMARY, "west"),
            ("gr_east", "⛏️ East", ActionStyle.PRIMARY, "east"),
            ("gr_south", "⛏️ South", ActionStyle.PRIMARY, "south"),
            ("gr_down", "⛏️ Deeper", ActionStyle.SUCCESS, "down"),
            ("gr_up", "⛏️ Up", ActionStyle.SUCCESS, "up")):
        action = by_id[action_id]
        assert action.label == label
        assert action.style is style
        assert action.handler == HandlerRef(f"mining.{action_id}")
        assert action.custom_id_override == ""      # session-minted ids
    menu = by_id["gr_menu"]
    assert menu.label == "↩ Mining Menu"
    assert menu.handler == PanelRef("mining.hub")
    assert spec.navigation.show_help is True        # 📚 Help, row 4
    assert spec.navigation.show_home is False       # no ↩ Games (oracle)
    assert spec.layout.pages[0].rows == (
        ("gr_north",),
        ("gr_west", "gr_east"),
        ("gr_south",),
        ("gr_down", "gr_up"),
        ("gr_menu",),
    )
    assert spec.renderer_override == HandlerRef("mining.render_grid")


def test_howto_spec_is_the_oracle_guide_verbatim():
    from sb.domain.mining.panels import (
        HOWTO_PANEL_ID,
        _HOW_TO,
        mining_howto_spec,
    )
    from sb.spec.panels import Audience, TextBlock
    from sb.spec.refs import PanelRef

    spec = mining_howto_spec()
    assert spec.panel_id == HOWTO_PANEL_ID == "mining.howto"
    assert spec.title == "📖 How mining works"
    assert spec.audience is Audience.INVOKER
    assert spec.session_lifecycle is True
    assert spec.frame.style_token == "dark_grey"    # MINING_COLOR
    (block,) = spec.body
    assert isinstance(block, TextBlock)
    # views/mining/how_to_panel.py _HOW_TO, verbatim — anchor bytes from
    # both ends of the shipped copy
    assert block.text is _HOW_TO
    assert block.text.startswith(
        "New to mining? Here's the whole loop in one screen.\n\n"
        "**1. ⛏️ Mine** — open the grid and roam the underground")
    assert block.text.endswith(
        "Level up by mining and harvesting to unlock deeper ladders and "
        "skill points.")
    (back,) = spec.actions
    assert back.action_id == "hw_hub"
    assert back.label == "↩ Mining Hub"
    assert back.handler == PanelRef("mining.hub")
    # the oracle How-to carried ONLY its back button
    assert spec.navigation.show_help is False
    assert spec.navigation.show_home is False


def test_both_new_specs_pass_the_compile_fences():
    from sb.domain.mining.panels import mining_grid_spec, mining_howto_spec
    from sb.kernel.panels.compile import check_panel

    check_panel(mining_grid_spec())
    check_panel(mining_howto_spec())


def test_manifest_declares_the_panels_and_the_pendings_are_retired():
    from sb.domain.mining import panels, service
    from sb.manifest.mining import MANIFEST
    from sb.spec.refs import HandlerRef, PanelRef, is_registered

    declared = {p.panel_id for p in MANIFEST.panels}
    assert {"mining.grid", "mining.howto"} <= declared
    panels.ensure_panel_refs()
    service.ensure_handler_refs()
    assert is_registered(PanelRef("mining.grid"))
    assert is_registered(PanelRef("mining.howto"))
    assert is_registered(HandlerRef("mining.render_grid"))
    assert is_registered(HandlerRef("mining.render_howto"))
    for direction in ("north", "west", "east", "south", "down", "up"):
        assert is_registered(HandlerRef(f"mining.gr_{direction}"))
    # the two retired hub pendings no longer register (trap 12a)
    assert not is_registered(HandlerRef("mining.grid_view_pending"))
    assert not is_registered(HandlerRef("mining.how_to_pending"))


def test_dig_op_registered_and_prefix_mine_still_carries_the_pinned_byte():
    """Row 45 honesty: the dig SYSTEM is live (mining.dig registered with
    its record leg) while `!mine` keeps the sweep_mine capture-artifact
    byte until the golden retires (the required gate replays mining
    green)."""
    import asyncio

    from sb.domain.mining import ops, service
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, is_registered
    from sb.spec.refs import resolve as resolve_ref

    ops.register_ops()
    ops.ensure_ops_refs()
    from sb.spec.refs import WorkflowRef
    assert is_registered(WorkflowRef("mining.dig"))
    assert is_registered(WorkflowRef("mining.record_dig"))

    service.ensure_handler_refs()
    assert is_registered(HandlerRef("mining.mine_route"))

    class _Req:
        actor = type("A", (), {"user_id": 1})()
        guild_id = 1
        channel_id = 1
        request_id = "t-mine"
        confirmed = False
        args: dict = {}
        origin = None

    reply = asyncio.run(resolve_ref(HandlerRef("mining.mine_route"))(_Req()))
    assert reply.outcome == BLOCKED
    # goldens/mining/sweep_mine pins this exact byte (trap 11b)
    assert reply.user_message == ("⚠️ An unexpected error occurred. "
                             "Please try again.")


def test_grid_note_degrades_to_text_when_no_session(monkeypatch):
    """The settings access-explorer posture: a refresh miss (restart /
    eviction / no message handle) degrades to an honest text reply."""
    import asyncio

    from sb.domain.mining import panels
    from sb.spec.outcomes import SUCCESS

    class _Req:
        origin = None
        args: dict = {}

    reply = asyncio.run(panels._grid_note(_Req(), "You dig **north**!",
                                          "success"))
    assert reply.outcome == SUCCESS
    assert reply.user_message == "You dig **north**!"
