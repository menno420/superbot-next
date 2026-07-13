"""Operator-hub edits slice B (ORDER 017 item 1, Top-gaps 6): the
channel hub's five shipped sub-panels (disbot/views/channels/
create/delete/restrict/move/visibility_panel.py) as declared grammar
over the LIVE ChannelActions/Directory ports + the audited governance
visibility op — the D-0030 named successor; the five
`channel.*_pending` hub terminals are retired.

Golden safety: the bare `!channelmenu` open keeps every pinned byte
(goldens/channel/sweep_channelmenu — labels, styles, separate-emoji
wire shape, layout rows, nav row unchanged; only the click TARGETS
moved from the pending terminals to the sub-panels)."""

from __future__ import annotations

import asyncio
import dataclasses
from types import SimpleNamespace

import pytest

run = asyncio.run


def _ensure():
    import sb.manifest.channel as m

    m.ENSURE_REFS()


def _handler(name: str):
    from sb.spec.refs import HandlerRef, resolve as resolve_ref

    _ensure()
    return resolve_ref(HandlerRef(name))


@dataclasses.dataclass
class Req:
    args: dict
    guild_id: int | None = 42
    channel_id: int | None = 7
    request_id: str = "req-1"
    confirmed: bool = True
    actor: object = dataclasses.field(default_factory=lambda: SimpleNamespace(
        user_id=7, member_tier="administrator"))


@pytest.fixture(autouse=True)
def _clean_picks():
    from sb.domain.channel import handlers

    handlers._panel_picks.clear()
    yield
    handlers._panel_picks.clear()


@pytest.fixture()
def fake_ports():
    """A live-shaped ChannelActions + Directory pair (the band-6
    channel-hub test family's fake pattern)."""
    from sb.domain.channel import service
    from sb.domain.channel.service import ChannelSnapshot

    class Ports:
        def __init__(self):
            self.snaps = [
                ChannelSnapshot(channel_id=1, name="general", kind="text"),
                ChannelSnapshot(channel_id=2, name="events", kind="text"),
                ChannelSnapshot(channel_id=9, name="Gaming", kind="category"),
            ]
            self.created: list[tuple] = []
            self.deleted: list[int] = []
            self.overwrites: list[tuple] = []
            self.moved: list[tuple] = []
            self.fail_ids: set[int] = set()
            self.fail_error = "missing permission"

        async def list_channels(self, guild_id):
            return tuple(self.snaps)

        async def get_channel(self, guild_id, channel_id):
            for s in self.snaps:
                if s.channel_id == int(channel_id):
                    return s
            return None

        async def list_roles(self, guild_id):
            return ()

        async def create_text_channel(self, guild_id, *, name, overwrites,
                                      parent_id, reason):
            self.created.append((guild_id, name, parent_id))
            return 100 + len(self.created)

        async def delete_channel(self, channel_id, *, reason):
            if int(channel_id) in self.fail_ids:
                raise RuntimeError(self.fail_error)
            self.deleted.append(int(channel_id))

        async def set_overwrite(self, channel_id, *, target_id, allow,
                                deny, target_type, reason):
            if int(channel_id) in self.fail_ids:
                raise RuntimeError(self.fail_error)
            self.overwrites.append((int(channel_id), allow, deny))

        async def move_channel(self, channel_id, *, category_id, reason):
            if int(channel_id) in self.fail_ids:
                raise RuntimeError(self.fail_error)
            self.moved.append((int(channel_id), int(category_id)))

    ports = Ports()
    prior_actions = service.active_actions()
    prior_directory = service.active_directory()
    service.install_channel_actions(ports)
    service.install_channel_directory(ports)
    yield ports
    service.install_channel_actions(prior_actions)
    service.install_channel_directory(prior_directory)


# --- the hub: click targets moved, bytes unchanged ---------------------------------


def test_hub_buttons_open_the_subpanels_and_keep_the_pinned_bytes():
    from sb.domain.channel.panels import channel_hub_spec
    from sb.spec.refs import PanelRef

    spec = channel_hub_spec()
    actions = {a.action_id: a for a in spec.actions}
    for aid, label, emoji in (
            ("create", "Create Channel", "➕"),
            ("delete", "Delete Channel", "🗑️"),
            ("restrict", "Manage Restrictions", "🔒"),
            ("move", "Move / Reorder", "↔️"),
            ("visibility", "Subsystem Visibility", "🔍")):
        assert actions[aid].handler == PanelRef(f"channel.{aid}"), aid
        # golden safety (sweep_channelmenu): label + separate-emoji wire
        # shape unchanged.
        assert actions[aid].label == label, aid
        assert actions[aid].emoji == emoji, aid
    assert spec.layout.pages[0].rows == (
        ("create", "delete", "restrict"), ("move", "visibility"))


def test_all_six_subpanels_register():
    from sb.spec.refs import PanelRef, is_registered

    _ensure()
    for pid in ("channel.create", "channel.delete", "channel.restrict",
                "channel.move", "channel.visibility",
                "channel.visibility_grid"):
        assert is_registered(PanelRef(pid)), pid


def test_channel_pending_terminals_are_retired():
    import sb.domain.channel.handlers as h

    src = open(h.__file__, encoding="utf-8").read()
    assert "_register_pending" not in src
    assert "channel.create_pending" not in src


# --- ➕ create --------------------------------------------------------------------


def test_create_flow_batch_creates_under_the_picked_category(fake_ports,
                                                             monkeypatch):
    from sb.kernel.panels import engine as panels_engine

    async def fake_open(ref, req, **kw):
        return None

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)

    run(_handler("channel.create_pick_names")(
        Req(args={"values": ("general", "events")})))
    run(_handler("channel.create_pick_category")(Req(args={"values": ("9",)})))
    run(_handler("channel.create_name_form_submit")(
        Req(args={"channel_name": "  My Channel "})))

    reply = run(_handler("channel.create_commit")(Req(args={})))
    assert reply.outcome == "success"
    # collision-safe: 'general' and 'events' are taken → suffixed; the
    # custom name normalized (strip/lower/hyphenate — the shipped modal).
    assert [c[1] for c in fake_ports.created] == [
        "general-2", "events-2", "my-channel"]
    assert all(c[2] == 9 for c in fake_ports.created)
    assert reply.user_message.startswith("✅ Created in **Gaming**: ")
    assert "my-channel" in reply.user_message


def test_create_commit_guards_empty_selection():
    reply = run(_handler("channel.create_commit")(Req(args={})))
    assert reply.outcome == "blocked"
    # the shipped guard, verbatim (_CreateSubView.create_btn)
    assert reply.user_message == ("Please select or enter at least one "
                                  "channel name first.")


def test_create_commit_unarmed_directory_refuses_honestly():
    from sb.domain.channel import handlers

    handlers._panel_picks[(42, 7, "create")] = {"presets": ["general"]}
    reply = run(_handler("channel.create_commit")(Req(args={})))
    assert reply.outcome == "blocked"
    assert reply.user_message.startswith("❌ Could not create channels:")


# --- 🗑️ delete --------------------------------------------------------------------


def test_delete_commit_deletes_the_picked_batch(fake_ports, monkeypatch):
    from sb.kernel.panels import engine as panels_engine

    async def fake_open(ref, req, **kw):
        return None

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    run(_handler("channel.delete_pick")(Req(args={"values": ("1", "2")})))
    reply = run(_handler("channel.delete_commit")(Req(args={})))
    assert reply.outcome == "success"
    assert fake_ports.deleted == [1, 2]
    assert reply.user_message == "✅ Deleted: #general, #events."


def test_delete_commit_buckets_partial_failures(fake_ports, monkeypatch):
    from sb.kernel.panels import engine as panels_engine

    async def fake_open(ref, req, **kw):
        return None

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    fake_ports.fail_ids = {2}
    run(_handler("channel.delete_pick")(Req(args={"values": ("1", "2")})))
    reply = run(_handler("channel.delete_commit")(Req(args={})))
    assert reply.outcome == "success"
    assert "✅ Deleted: #general." in reply.user_message
    # the shipped permission bucket (_DeleteConfirmView result embed)
    assert "🚫 Permission denied: `#events`." in reply.user_message


def test_delete_commit_guards_empty_selection():
    reply = run(_handler("channel.delete_commit")(Req(args={})))
    assert reply.outcome == "blocked"
    assert reply.user_message == "Please select at least one channel first."


def test_delete_commit_declares_the_irreversible_confirm():
    from sb.domain.channel.panels import delete_spec

    action = {a.action_id: a for a in delete_spec().actions}["delete_commit"]
    assert action.confirm is not None
    assert action.confirm.reversibility == "irreversible"
    assert action.destructive is True


# --- 🔒 restrict ------------------------------------------------------------------


def test_restrict_lock_and_unlock_apply_the_twin_masks(fake_ports,
                                                       monkeypatch):
    from sb.domain.channel.service import SEND_MESSAGES_BIT
    from sb.kernel.panels import engine as panels_engine

    async def fake_open(ref, req, **kw):
        return None

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    run(_handler("channel.restrict_pick")(Req(args={"values": ("1", "2")})))
    reply = run(_handler("channel.restrict_lock")(Req(args={})))
    assert reply.outcome == "success"
    assert fake_ports.overwrites == [(1, 0, SEND_MESSAGES_BIT),
                                     (2, 0, SEND_MESSAGES_BIT)]
    # the shipped past-tense copy, verbatim
    assert reply.user_message == (
        "✅ Locked (send messages disabled for @everyone): "
        "`#general`, `#events`.")

    fake_ports.overwrites.clear()
    run(_handler("channel.restrict_pick")(Req(args={"values": ("1",)})))
    reply = run(_handler("channel.restrict_unlock")(Req(args={})))
    assert fake_ports.overwrites == [(1, SEND_MESSAGES_BIT, 0)]
    assert reply.user_message == (
        "✅ Unlocked (send messages restored for @everyone): `#general`.")


# --- ↔️ move ----------------------------------------------------------------------


def test_move_commit_moves_the_batch_to_the_picked_category(fake_ports,
                                                            monkeypatch):
    from sb.kernel.panels import engine as panels_engine

    async def fake_open(ref, req, **kw):
        return None

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    run(_handler("channel.move_pick_channels")(
        Req(args={"values": ("1", "2")})))
    run(_handler("channel.move_pick_category")(Req(args={"values": ("9",)})))
    reply = run(_handler("channel.move_commit")(Req(args={})))
    assert reply.outcome == "success"
    assert fake_ports.moved == [(1, 9), (2, 9)]
    assert reply.user_message == ('✅ Moved to "Gaming": '
                                  "`#general`, `#events`.")


def test_move_commit_guards_missing_category(fake_ports, monkeypatch):
    from sb.kernel.panels import engine as panels_engine

    async def fake_open(ref, req, **kw):
        return None

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    run(_handler("channel.move_pick_channels")(Req(args={"values": ("1",)})))
    reply = run(_handler("channel.move_commit")(Req(args={})))
    assert reply.outcome == "blocked"
    # the shipped guard, verbatim (_MoveSubView.move_btn)
    assert reply.user_message == "Pick a destination category above first."


def test_move_reorder_answers_the_honest_port_refusal():
    reply = run(_handler("channel.move_reorder")(Req(args={})))
    assert reply.outcome == "blocked"
    assert "reorder verb" in reply.user_message
    assert "📁 Move to Category is live" in reply.user_message


# --- 🔍 visibility ----------------------------------------------------------------


def test_visibility_configure_guards_then_opens_the_grid(monkeypatch):
    from sb.kernel.panels import engine as panels_engine

    reply = run(_handler("channel.visibility_configure")(Req(args={})))
    assert reply.outcome == "blocked"
    assert reply.user_message == "Please select at least one channel first."

    opened = []

    async def fake_open(ref, req, **kw):
        opened.append(ref.name)

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    run(_handler("channel.visibility_pick")(Req(args={"values": ("1",)})))
    reply = run(_handler("channel.visibility_configure")(Req(args={})))
    assert reply.outcome == "success"
    assert opened[-1] == "channel.visibility_grid"


def test_vis_toggle_cycles_and_writes_per_channel(fake_ports, monkeypatch):
    """The shipped force-uniform cycle: inherit → on; each write rides
    the audited governance visibility op per picked channel."""
    from sb.domain.channel import visibility as vis
    from sb.domain.governance import service as governance
    from sb.kernel.panels import engine as panels_engine

    async def fake_open(ref, req, **kw):
        return None

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)

    state: dict[tuple[int, str], bool | None] = {}

    async def fake_rows(guild_id, channel_ids):
        return [{k[1]: v for k, v in state.items() if k[0] == int(cid)}
                for cid in channel_ids]

    writes = []

    async def fake_set(ctx, *, scope_type, scope_id, subsystem, enabled):
        writes.append((scope_type, scope_id, subsystem, enabled))
        state[(scope_id, subsystem)] = enabled
        return SimpleNamespace(outcome="success")

    monkeypatch.setattr(vis, "channel_visibility_rows", fake_rows)
    monkeypatch.setattr(governance, "set_subsystem_visibility", fake_set)

    run(_handler("channel.visibility_pick")(Req(args={"values": ("1", "2")})))
    toggle = _handler("channel.vis_toggle_games")

    reply = run(toggle(Req(args={})))          # inherit → force ON
    assert reply.outcome == "success"
    assert writes == [("channel", 1, "games", True),
                      ("channel", 2, "games", True)]

    writes.clear()
    run(toggle(Req(args={})))                  # on → force OFF
    assert writes == [("channel", 1, "games", False),
                      ("channel", 2, "games", False)]

    writes.clear()
    run(toggle(Req(args={})))                  # off → inherit (None)
    assert writes == [("channel", 1, "games", None),
                      ("channel", 2, "games", None)]


def test_vis_toggle_reports_partial_failures(monkeypatch):
    from sb.domain.channel import visibility as vis
    from sb.domain.governance import service as governance
    from sb.kernel.panels import engine as panels_engine

    async def fake_open(ref, req, **kw):
        return None

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)

    async def fake_rows(guild_id, channel_ids):
        return [{} for _ in channel_ids]

    async def fake_set(ctx, **kw):
        if kw["scope_id"] == 2:
            raise RuntimeError("nope")
        return SimpleNamespace(outcome="success")

    monkeypatch.setattr(vis, "channel_visibility_rows", fake_rows)
    monkeypatch.setattr(governance, "set_subsystem_visibility", fake_set)

    run(_handler("channel.visibility_pick")(Req(args={"values": ("1", "2")})))
    reply = run(_handler("channel.vis_toggle_help")(Req(args={})))
    assert reply.outcome == "blocked"
    # the shipped partial-failure followup shape, verbatim
    assert reply.user_message == "⚠️ Couldn't update **help** for: `2`"


def test_grid_roster_is_the_oracle_capture_literal():
    from sb.domain.channel.visibility import GRID_SUBSYSTEMS, grid_label

    assert len(GRID_SUBSYSTEMS) == 20
    assert GRID_SUBSYSTEMS[0] == ("help", "Help")
    assert GRID_SUBSYSTEMS[-1] == ("welcome", "Welcome")
    assert ("ticket", "Support Tickets") in GRID_SUBSYSTEMS
    # the shipped glyph/style mapping
    assert grid_label("Games", True) == ("✓ Games", "success")
    assert grid_label("Games", False) == ("✗ Games", "danger")
    assert grid_label("Games", "mixed") == ("± Games", "primary")
    assert grid_label("Games", None) == ("~ Games", "secondary")


def test_aggregate_state_matches_the_shipped_semantics():
    from sb.domain.channel.visibility import aggregate_state

    assert aggregate_state([{"xp": True}, {"xp": True}], "xp") is True
    assert aggregate_state([{"xp": True}, {"xp": False}], "xp") == "mixed"
    assert aggregate_state([{}, {}], "xp") is None
    assert aggregate_state([{"xp": None}, {}], "xp") is None


# --- renderers: state fields off the pick memory ----------------------------------


def _ctx(guild_id=42, user_id=7):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=guild_id,
        actor=SimpleNamespace(user_id=user_id,
                              member_tier="administrator"),
        channel_id=7, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(), params={})


def test_delete_renderer_adds_the_selected_field(fake_ports):
    from sb.domain.channel import handlers
    from sb.domain.channel.panels import delete_spec
    from sb.spec.refs import HandlerRef, resolve

    handlers._panel_picks[(42, 7, "delete")] = {"ids": [1, 2]}
    rendered = run(resolve(HandlerRef("channel.delete_render"))(
        delete_spec(), _ctx()))
    assert rendered.embed.fields[-1] == (
        "Selected channels", "`#general`, `#events`")


def test_grid_renderer_recolors_toggles_off_live_aggregate(fake_ports,
                                                           monkeypatch):
    from sb.domain.channel import handlers
    from sb.domain.channel import visibility as vis
    from sb.domain.channel.panels import visibility_grid_spec
    from sb.spec.refs import HandlerRef, resolve

    handlers._panel_picks[(42, 7, "visibility")] = {"ids": [1]}

    async def fake_rows(guild_id, channel_ids):
        return [{"games": True, "xp": False}]

    monkeypatch.setattr(vis, "channel_visibility_rows", fake_rows)
    rendered = run(resolve(HandlerRef("channel.visibility_grid_render"))(
        visibility_grid_spec(), _ctx()))
    by_leaf = {c.custom_id.rsplit(".", 1)[-1]: c
               for c in rendered.components}
    assert by_leaf["vis_games"].label == "✓ Games"
    assert by_leaf["vis_games"].style == "success"
    assert by_leaf["vis_xp"].label == "✗ XP & Levels"
    assert by_leaf["vis_xp"].style == "danger"
    assert by_leaf["vis_help"].label == "~ Help"       # inherit
    assert rendered.embed.title == "🔍 Subsystem Visibility — 1 channel"
    assert "`#general`" in rendered.embed.description
