"""The routing-ticket section flows (the FINAL section-flow slice —
sb/domain/setup/cog_routing.py · ticket.py).

DB-free like the section-flows suite: the K7/K9 write seams are
monkeypatched at their module functions and the assertions pin the
ORACLE bytes the click paths carry (no golden drives a click on these
components — the panels.py module pin; oracle sources:
views/setup/sections/cog_routing.py, services/cog_routing_profiles.py,
views/setup/sections/ticket.py, utils/channel_classify.py)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run


@pytest.fixture(autouse=True)
def _fresh_state():
    import sb.manifest.setup as m
    from sb.domain.setup import cog_routing, wizard, wizard_nav
    from sb.domain.setup.plan import install_channel_index

    m.ENSURE_REFS()
    wizard.reset_wizard_state_for_tests()
    wizard_nav.reset_wizard_nav_state_for_tests()
    cog_routing.reset_cog_routing_state_for_tests()
    yield
    install_channel_index(None)
    wizard.reset_wizard_state_for_tests()
    wizard_nav.reset_wizard_nav_state_for_tests()
    cog_routing.reset_cog_routing_state_for_tests()


def _req(*, user_id=42, guild_id=99, args=None, message_id=777):
    return SimpleNamespace(
        actor=SimpleNamespace(user_id=user_id),
        guild_id=guild_id,
        args=dict(args or {}),
        origin=SimpleNamespace(message=SimpleNamespace(id=message_id)),
        request_id="req-1",
        confirmed=False,
    )


def _resolve(name):
    from sb.spec.refs import HandlerRef, resolve

    return resolve(HandlerRef(name))


def _ctx(*, guild_id=99, user_id=42, params=None):
    from sb.kernel.interaction.request import ActorRef
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=guild_id,
        actor=ActorRef(user_id=user_id, is_guild_operator=True,
                       is_bot_owner=False, is_dm=False),
        channel_id=1, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, params=dict(params or {}))


class _Gate:
    def __init__(self, allow: bool) -> None:
        self.allow = allow

    async def __call__(self, req) -> bool:
        del req
        return self.allow


class _FakeStore:
    def __init__(self, drafts=()):
        self.drafts = list(drafts)
        self.removed: list[tuple[str, int]] = []
        self.added: list = []
        self.created = 0

    async def list_open(self, scope):
        return tuple(self.drafts)

    async def create(self, *, producer, owner_scope):
        self.created += 1
        draft = SimpleNamespace(draft_id="d-new", operations=())
        self.drafts.append(draft)
        return draft

    async def remove(self, draft_id, op_seq):
        self.removed.append((draft_id, op_seq))

    async def add(self, draft_id, op):
        self.added.append((draft_id, op))


def _patch_store(monkeypatch, store):
    from sb.kernel.draft import store as draft_store_module

    monkeypatch.setattr(draft_store_module, "DraftStore", lambda: store)


def _patch_write_seams(monkeypatch, *, pending=1):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def fake_run(ref, ctx):
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)

    async def fake_count(guild_id):
        return pending

    monkeypatch.setattr(wizard, "staged_ops_count", fake_count)

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)


def _pick_walk(guild_id=99, user_id=42, *, scope, target=None, cog=None):
    from sb.domain.setup import cog_routing

    key = f"{guild_id}:{user_id}"
    cog_routing._PICKED_SCOPE[key] = scope
    if target is not None:
        cog_routing._PICKED_TARGET[key] = target
    if cog is not None:
        cog_routing._PICKED_COG[key] = cog


# =======================================================================================
# cog_routing — the entry embed / catalogue bytes
# =======================================================================================


def test_cog_routing_embed_pins_the_shipped_bytes():
    from sb.domain.setup.cog_routing import build_cog_routing_embed

    embed = build_cog_routing_embed()
    assert embed.title == "🧭 Cog routing"
    assert embed.description == (
        "Enable or disable cogs per scope.  The resolver walks "
        "**channel → category → server → default-true** — a fresh "
        "server has every cog enabled and routing only restricts.  "
        "Each pick stages a `set_cog_routing` operation; nothing "
        "applies until Final review.")
    assert embed.fields == (
        ("How to use",
         ("1. Pick a scope.\n"
          "2. (Category / channel scopes) pick the target.\n"
          "3. Pick the cog.\n"
          "4. Pick Enable or Disable."),
         False),
    )
    assert embed.footer == ("Cogs default to enabled; this section creates "
                            "exceptions.")


def test_scope_options_are_the_shipped_bytes():
    from sb.domain.setup.cog_routing import _SCOPE_OPTIONS_PROVIDER
    from sb.spec.refs import ProviderRef, resolve

    options = run(resolve(ProviderRef(_SCOPE_OPTIONS_PROVIDER))(_ctx()))
    assert [(o["label"], o["value"], o["description"], o["emoji"])
            for o in options] == [
        ("Server default", "guild",
         "Enable / disable a cog server-wide.", "🌐"),
        ("Category override", "category",
         "Override one category; channels inherit unless overridden.",
         "📁"),
        ("Channel override", "channel",
         "Override one specific channel.", "📡"),
    ]


def test_profile_catalogue_carries_the_shipped_bundles():
    from sb.domain.setup.cog_routing import PROFILES

    assert list(PROFILES) == [
        "games_in_game_channels", "economy_in_economy_channels",
        "moderation_to_staff", "recommended_by_name"]
    assert PROFILES["games_in_game_channels"].display_name == \
        "Games → game channels only"
    assert PROFILES["recommended_by_name"].description == (
        "Apply games / economy / moderation routing in one pass — "
        "each cog disabled at guild scope and re-enabled only in "
        "channels whose name matches its intent.")


def test_cog_options_window_the_visible_harvest_at_25():
    from sb.domain.setup.cog_routing import (
        _COG_OPTIONS_PROVIDER, operator_visible_cogs,
    )
    from sb.spec.refs import ProviderRef, resolve

    cogs = operator_visible_cogs()
    assert len(cogs) == 43              # the shipped 43-row harvest
    assert cogs == tuple(sorted(cogs))  # the shipped sorted contract
    options = run(resolve(ProviderRef(_COG_OPTIONS_PROVIDER))(_ctx()))
    # the access_map first-25 window precedent (module docstring
    # ledger; the windowed-select grammar successor is the follow-up).
    assert len(options) == 25
    assert [o["value"] for o in options] == list(cogs[:25])
    # the shipped presentation rides display_name + emoji.
    admin = options[0]
    assert admin["label"] == "Administration"
    assert admin["emoji"] == "⚙️"


def test_flag_buttons_carry_the_shipped_option_labels():
    """The oracle _EnableDisableSelect options ride as the declared
    Enable / Disable button faces (module docstring ledger)."""
    from sb.domain.setup.cog_routing import cog_routing_detail_spec

    spec = cog_routing_detail_spec()
    labels = {a.action_id: a.label for a in spec.actions}
    assert labels["routing_enable"] == "Enable"
    assert labels["routing_disable"] == "Disable"


# =======================================================================================
# cog_routing — the profile builders
# =======================================================================================


def test_profile_builders_carry_the_shipped_semantics():
    from sb.domain.setup.cog_routing import PROFILES, routing_profile_ops
    from sb.domain.setup.plan import GuildChannel, install_channel_index

    async def index(guild_id):
        return (GuildChannel(id=1, name="games-corner"),
                GuildChannel(id=2, name="mining-pit"),
                GuildChannel(id=3, name="mod-log"),
                GuildChannel(id=4, name="general"))

    install_channel_index(index)
    ops = run(routing_profile_ops(PROFILES["games_in_game_channels"], 99))
    assert [(op.payload["scope_type"], op.payload["cog_name"],
             op.payload["enabled"]) for op in ops] == [
        ("guild", "games", False), ("channel", "games", True)]
    assert ops[1].payload["scope_id"] == 1
    # the shipped profile staging label, verbatim.
    assert ops[0].label_body == (
        "[profile:games_in_game_channels] cog_routing.guild(guild).games "
        "= disabled")
    # economy dedups across the game/mining tag pair.
    ops = run(routing_profile_ops(PROFILES["economy_in_economy_channels"], 99))
    assert [op.payload.get("scope_id") for op in ops] == [None, 1, 2]
    # moderation targets the staff channels.
    ops = run(routing_profile_ops(PROFILES["moderation_to_staff"], 99))
    assert [op.payload.get("scope_id") for op in ops] == [None, 3]
    # recommended = the three bundles in one pass.
    ops = run(routing_profile_ops(PROFILES["recommended_by_name"], 99))
    assert len(ops) == 2 + 3 + 2


def test_profile_builders_degrade_headless_to_the_guild_row():
    from sb.domain.setup.cog_routing import PROFILES, routing_profile_ops

    ops = run(routing_profile_ops(PROFILES["games_in_game_channels"], 99))
    assert [(op.payload["scope_type"], op.payload["enabled"])
            for op in ops] == [("guild", False)]


# =======================================================================================
# cog_routing — the click lanes
# =======================================================================================


def test_open_section_gate_and_landing(monkeypatch):
    from sb.domain.setup import section_card, wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    reply = run(_resolve("setup.open_section_cog_routing")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == wizard.GATE_MSG_WIZARD

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    opened = []

    async def fake_open(req, panel_id, args=None):
        opened.append(panel_id)

    monkeypatch.setattr(wizard, "_open", fake_open)

    async def fake_mark(req, step):
        return None

    monkeypatch.setattr(section_card, "mark_step_in_progress", fake_mark)
    assert run(_resolve("setup.open_section_cog_routing")(_req())) is None
    assert opened == ["setup.section_cog_routing"]


def test_scope_pick_stashes_and_unknown_refuses(monkeypatch):
    _patch_write_seams(monkeypatch)
    from sb.domain.setup import cog_routing

    reply = run(_resolve("setup.cog_routing_scope_pick")(
        _req(args={"values": ["nope"]})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "Unknown scope `nope`."
    assert run(_resolve("setup.cog_routing_scope_pick")(
        _req(args={"values": ["guild"]}))) is None
    assert cog_routing._PICKED_SCOPE["99:42"] == "guild"


def test_target_pick_needs_an_override_scope(monkeypatch):
    _patch_write_seams(monkeypatch)
    reply = run(_resolve("setup.cog_routing_target_pick")(
        _req(args={"values": ["1234"]})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Pick a scope first — see **How to use** above.")


def test_cog_pick_guards_are_the_shipped_bytes(monkeypatch):
    _patch_write_seams(monkeypatch)
    # the shipped empty branch, verbatim (_on_cog_picked).
    reply = run(_resolve("setup.cog_routing_cog_pick")(
        _req(args={"values": []})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "No visible subsystems registered."
    reply = run(_resolve("setup.cog_routing_cog_pick")(
        _req(args={"values": ["not_a_cog"]})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "Unknown cog `not_a_cog`."


def test_flag_click_stages_guild_scope_and_answers(monkeypatch):
    _patch_write_seams(monkeypatch, pending=3)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)
    _pick_walk(scope="guild", cog="games")
    reply = run(_resolve("setup.cog_routing_disable")(_req()))
    assert reply.outcome == SUCCESS
    # shipped confirmation, verbatim (the double space included).
    assert reply.user_message == (
        "✅ Staged for Final review: "
        "`cog_routing.guild(guild).games = disabled`.  "
        "Pending operations: **3**.")
    assert len(store.added) == 1
    op = store.added[0][1]
    assert op.op_kind == "set_cog_routing"
    assert op.subsystem == "cog_routing"
    # the [<slug>] provenance prefix + the shipped label bytes.
    assert op.label == ("[cog_routing] cog_routing.guild(guild).games = "
                        "disabled")
    assert op.payload == {"name": "guild:guild:games",
                          "scope_type": "guild", "scope_id": None,
                          "cog_name": "games", "enabled": False,
                          "target_name": "guild"}


def test_flag_click_stages_channel_scope(monkeypatch):
    _patch_write_seams(monkeypatch, pending=1)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)
    _pick_walk(scope="channel", target=(1234, "arcade"), cog="games")
    reply = run(_resolve("setup.cog_routing_enable")(_req()))
    assert reply.outcome == SUCCESS
    op = store.added[0][1]
    assert op.payload["name"] == "channel:1234:games"
    assert op.payload["scope_id"] == 1234
    assert op.payload["enabled"] is True
    assert op.payload["target_name"] == "arcade"


def test_flag_click_gate_refusal_is_the_card_copy(monkeypatch):
    from sb.domain.setup import section_card, wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    _pick_walk(scope="guild", cog="games")
    reply = run(_resolve("setup.cog_routing_enable")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == section_card.GATE_MSG_CARD


def test_flag_click_without_a_walk_answers_the_stale_guard(monkeypatch):
    _patch_write_seams(monkeypatch)
    reply = run(_resolve("setup.cog_routing_enable")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Pick a scope first — see **How to use** above.")


def test_profile_pick_stages_every_op_and_answers(monkeypatch):
    _patch_write_seams(monkeypatch, pending=2)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)
    from sb.domain.setup.plan import GuildChannel, install_channel_index

    async def index(guild_id):
        return (GuildChannel(id=1, name="games-corner"),)

    install_channel_index(index)
    reply = run(_resolve("setup.cog_routing_profile_pick")(
        _req(args={"values": ["games_in_game_channels"]})))
    assert reply.outcome == SUCCESS
    # shipped summary, verbatim (_RoutingProfileSelect.callback).
    assert reply.user_message == (
        "✅ Staged **2 operations** for profile "
        "`Games → game channels only`. Pending operations: **2**.")
    assert len(store.added) == 2
    labels = [op.label for _d, op in store.added]
    assert labels[0].startswith(
        "[cog_routing] [profile:games_in_game_channels] ")


def test_profile_pick_unknown_answers_the_shipped_copy(monkeypatch):
    _patch_write_seams(monkeypatch)
    reply = run(_resolve("setup.cog_routing_profile_pick")(
        _req(args={"values": ["nope"]})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "Unknown cog routing profile `nope`."


def test_set_cog_routing_stays_fail_closed():
    """No live routing resolver exists in this build (the
    access_projection axis-3 ledger) — the op kind must stay
    UN-registered so apply surfaces the rows as skipped."""
    from sb.kernel.draft.registry import OP_KINDS

    assert OP_KINDS.get("set_cog_routing") is None


# =======================================================================================
# cog_routing — the detail renderer
# =======================================================================================


def _leafs(rendered, panel_id):
    return [c.custom_id.removeprefix(f"{panel_id}.")
            for c in rendered.components]


def test_detail_render_reveals_stepwise(monkeypatch):
    from sb.domain.setup.cog_routing import (
        COG_ROUTING_DETAIL_PANEL_ID, _render_cog_routing_detail,
        cog_routing_detail_spec,
    )

    spec = cog_routing_detail_spec()
    # nothing picked: scope + profile only.
    rendered = run(_render_cog_routing_detail(spec, _ctx()))
    assert _leafs(rendered, COG_ROUTING_DETAIL_PANEL_ID) == [
        "routing_scope", "cog_routing_section_profile"]
    assert rendered.embed.title == "🧭 Cog routing"
    # guild scope: the cog select reveals with the shipped placeholder.
    _pick_walk(scope="guild")
    rendered = run(_render_cog_routing_detail(spec, _ctx()))
    leafs = _leafs(rendered, COG_ROUTING_DETAIL_PANEL_ID)
    assert leafs == ["routing_scope", "cog_routing_section_profile",
                     "routing_cog"]
    cog_select = rendered.components[-1]
    assert cog_select.placeholder == "Pick a cog for guild scope…"
    # override scope: the target picker reveals first.
    _pick_walk(scope="category")
    rendered = run(_render_cog_routing_detail(spec, _ctx()))
    leafs = _leafs(rendered, COG_ROUTING_DETAIL_PANEL_ID)
    assert leafs == ["routing_scope", "cog_routing_section_profile",
                     "routing_target"]
    assert rendered.components[-1].placeholder == "Pick a category…"
    # target picked: the cog select joins.
    _pick_walk(scope="channel", target=(1234, "arcade"))
    rendered = run(_render_cog_routing_detail(spec, _ctx()))
    leafs = _leafs(rendered, COG_ROUTING_DETAIL_PANEL_ID)
    assert leafs == ["routing_scope", "cog_routing_section_profile",
                     "routing_target", "routing_cog"]
    assert rendered.components[2].placeholder == "Pick a channel…"


def test_detail_render_reveals_the_flag_pair_after_a_cog_pick(monkeypatch):
    """Once a cog is picked the Enable/Disable button pair reveals
    (the oracle's third ephemeral view — the declared button faces,
    module docstring ledger); the full walk stays within the
    compiler's five-row page."""
    from sb.domain.setup import wizard_nav
    from sb.domain.setup.cog_routing import (
        COG_ROUTING_DETAIL_PANEL_ID, _render_cog_routing_detail,
        cog_routing_detail_spec,
    )

    spec = cog_routing_detail_spec()
    _pick_walk(scope="channel", target=(1234, "arcade"), cog="games")
    wizard_nav.mark_detail_from_wizard(99, 42)
    rendered = run(_render_cog_routing_detail(spec, _ctx()))
    leafs = _leafs(rendered, COG_ROUTING_DETAIL_PANEL_ID)
    assert leafs == ["routing_scope", "cog_routing_section_profile",
                     "routing_target", "routing_cog",
                     "routing_enable", "routing_disable",
                     "routing_back_step"]
    # the cog select carries the shipped per-scope placeholder.
    assert rendered.components[3].placeholder == \
        "Pick a cog for channel scope…"


def test_detail_back_step_rides_only_the_wizard_origin():
    from sb.domain.setup.cog_routing import (
        COG_ROUTING_DETAIL_PANEL_ID, _render_cog_routing_detail,
        cog_routing_detail_spec,
    )

    rendered = run(_render_cog_routing_detail(cog_routing_detail_spec(),
                                              _ctx()))
    assert "routing_back_step" not in _leafs(rendered,
                                             COG_ROUTING_DETAIL_PANEL_ID)


# =======================================================================================
# ticket — the thin adapter
# =======================================================================================


def test_ticket_open_gate_refusal_is_the_hub_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    reply = run(_resolve("setup.open_section_ticket")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == wizard.GATE_MSG_WIZARD


def test_ticket_open_lands_on_the_shipped_panel(monkeypatch):
    from sb.domain.setup import section_card, wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    opened = []

    async def fake_open(req, panel_id, args=None):
        opened.append(panel_id)

    monkeypatch.setattr(wizard, "_open", fake_open)
    marked = []

    async def fake_mark(req, step):
        marked.append(step)

    monkeypatch.setattr(section_card, "mark_step_in_progress", fake_mark)
    assert run(_resolve("setup.open_section_ticket")(_req())) is None
    # the ALREADY-SHIPPED ticket config panel is the destination
    # (ticket._open_panel → open_ticket_config_panel, the thin-adapter
    # posture) and the step marker records AFTER (the shipped order).
    assert opened == ["ticket.setup"]
    assert marked == ["ticket"]


def test_ticket_open_guild_guard_is_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    reply = run(_resolve("setup.open_section_ticket")(_req(guild_id=0)))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (ticket._open_panel's guild guard).
    assert reply.user_message == "This can only be used in a server."


def test_ticket_customize_destination_is_the_shipped_panel():
    from sb.domain.setup import section_card

    assert section_card.customize_panel("ticket") == "ticket.setup"
    # NO recommended builder and NO staged op kind — the oracle
    # sections.py declaration (op_kinds=()) reconciles.
    assert section_card.recommended_builder("ticket") is None
    from sb.domain.setup.sections import REGISTRY

    assert REGISTRY.get("ticket").op_kinds == ()


# =======================================================================================
# wiring — the lane is closed
# =======================================================================================


def test_every_routing_ticket_route_resolves():
    from sb.spec.refs import HandlerRef, resolve

    for name in (
            "setup.open_section_cog_routing",
            "setup.cog_routing_scope_pick",
            "setup.cog_routing_target_pick",
            "setup.cog_routing_cog_pick",
            "setup.cog_routing_enable",
            "setup.cog_routing_disable",
            "setup.cog_routing_profile_pick",
            "setup.section_apply_cog_routing",
            "setup.section_customize_cog_routing",
            "setup.section_skip_cog_routing",
            "setup.section_hub_cog_routing",
            "setup.open_section_ticket"):
        assert resolve(HandlerRef(name)) is not None
