"""The armed `!ticketsetup` wizard (ORDER 017 night-run fix slice B) —
the `ticket.setup_pending` terminal retired: role/log picks re-render the
panel in place, 🪄 Auto-create runs the audited channel-create op,
✅ Enable runs the audited config write, 📋 Post panel posts the
persistent launcher; the shipped guard/ack copy verbatim (ORACLE
menno420/superbot views/tickets/config_panel.py +
services/ticket_mutation.py). The open lane adopts the shipped
eligibility gate order/copy (services/ticket_service.py
check_open_eligibility) now that a guild can actually enable tickets.

goldens/ticket/sweep_ticketsetup pins the config-absent open bytes —
the renderer's default path must stay byte-identical."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from sb.domain.ticket import setup_panel as sp
from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run

UID, GID = 42, 1


@dataclass
class FakeReq:
    args: dict = field(default_factory=dict)
    actor: object = None
    guild_id: int = GID
    channel_id: int = 9
    origin: object = None
    request_id: str = "r1"
    confirmed: bool = False
    surface: object = None


def _req(args: dict | None = None, *, message_id: int = 555,
         guild_id: int = GID) -> FakeReq:
    return FakeReq(
        args=dict(args or {}), guild_id=guild_id,
        actor=SimpleNamespace(user_id=UID, actor_type="user",
                              is_guild_operator=True),
        origin=SimpleNamespace(message=SimpleNamespace(id=message_id)))


@pytest.fixture(autouse=True)
def _clean_state():
    sp._STATE.clear()
    yield
    sp._STATE.clear()


@pytest.fixture()
def captured_refresh(monkeypatch):
    from sb.kernel.panels import engine

    calls = []

    async def refresh_session_view(req, *, message_key, params,
                                   expire=False):
        calls.append((message_key, dict(params)))
        return True

    monkeypatch.setattr(engine, "refresh_session_view",
                        refresh_session_view)
    return calls


@pytest.fixture()
def captured_ops(monkeypatch):
    """Capture engine.run calls; each returns a canned OK result."""
    from sb.kernel.workflow import engine as wf_engine

    calls = []
    canned = {"ticket.create_log_channel": {
        "create_log_channel": {"log_channel_id": 777}}}

    async def fake_run(ref, ctx):
        calls.append((ref.name, dict(ctx.params)))
        return SimpleNamespace(ok=True, outcome=SUCCESS,
                               after=canned.get(ref.name, {}),
                               user_message=None)

    monkeypatch.setattr(wf_engine, "run", fake_run)
    return calls


# --- the armed spec ------------------------------------------------------------


def test_setup_spec_is_armed_and_pending_retired():
    from sb.domain.ticket import handlers
    from sb.spec.refs import HandlerRef, is_registered

    handlers.ensure_handler_refs()
    spec = handlers.ticket_setup_spec()
    by_sel = {s.selector_id: s.on_select for s in spec.selectors}
    assert by_sel == {
        "setup_staff_role": HandlerRef("ticket.setup_select"),
        "setup_log_channel": HandlerRef("ticket.setup_select")}
    by_act = {a.action_id: a.handler for a in spec.actions}
    assert by_act == {
        "setup_autocreate_log": HandlerRef("ticket.setup_autocreate"),
        "setup_enable": HandlerRef("ticket.setup_enable"),
        "setup_post_panel": HandlerRef("ticket.setup_post_panel")}
    assert not is_registered(HandlerRef("ticket.setup_pending"))


def test_setup_spec_passes_the_compile_fence():
    from sb.domain.ticket.handlers import ticket_setup_spec
    from sb.kernel.panels.compile import check_panel

    assert check_panel(ticket_setup_spec()) is None


# --- the renderer: golden default + pending-state overlay -----------------------


def _ctx(params: dict | None = None):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=GID, actor=SimpleNamespace(user_id=UID),
        channel_id=9, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(),
        params=dict(params or {}))


@pytest.fixture()
def _no_config(monkeypatch):
    from sb.domain.ticket import store

    async def get_config_row(guild_id, conn=None):
        return None

    monkeypatch.setattr(store, "get_config_row", get_config_row)


def _render_setup():
    from sb.domain.ticket.handlers import _render_setup, ticket_setup_spec

    return _render_setup, ticket_setup_spec()


def test_render_default_matches_the_golden_bytes(_no_config):
    render, spec = _render_setup()
    rendered = run(render(spec, _ctx()))
    (name, value) = rendered.embed.fields[-1][:2]
    assert name == "Selected"
    assert value == ("• Status: **not enabled yet**\n"
                     "• Staff role: _(not set — required)_\n"
                     "• Transcript log: _(none — tap Auto-create or pick "
                     "one)_\n"
                     "• Max open per user: **3**")
    assert rendered.embed.footer == (
        "Tune limits / blacklist later with !ticketlimit and "
        "!ticketblacklist.")


def test_render_overlays_the_pending_picks(_no_config):
    render, spec = _render_setup()
    rendered = run(render(spec, _ctx({"staff_role_id": 1234,
                                      "log_channel_id": 5678})))
    value = rendered.embed.fields[-1][1]
    assert "• Staff role: <@&1234>" in value
    assert "• Transcript log: <#5678>" in value
    assert "**not enabled yet**" in value


def test_render_enabled_flips_current_green_and_live_footer(_no_config):
    render, spec = _render_setup()
    rendered = run(render(spec, _ctx({
        "staff_role_id": 1234, "enabled": True,
        "footer": sp.FOOTER_LIVE, "accent": "green"})))
    assert rendered.embed.fields[-1][0] == "Current"
    assert "• Status: **enabled**" in rendered.embed.fields[-1][1]
    assert rendered.embed.footer == (
        "Tickets are live. Tap Post panel so members can open one.")
    assert rendered.embed.style_token == "green"


# --- the select handlers ---------------------------------------------------------


def test_selects_update_state_and_refresh(captured_refresh):
    run(sp.setup_select(_req({"session_action": "setup_staff_role",
                              "values": ("1234",)})))
    run(sp.setup_select(_req({"session_action": "setup_log_channel",
                              "values": ("5678",)})))
    assert sp._STATE["555"] == {"staff_role_id": 1234,
                                "log_channel_id": 5678}
    assert captured_refresh[-1][0] == "555"
    assert captured_refresh[-1][1]["log_channel_id"] == 5678


# --- enable ----------------------------------------------------------------------


def test_enable_guards_the_staff_role_first(captured_ops, captured_refresh):
    reply = run(sp.setup_enable(_req({})))
    assert reply.outcome is BLOCKED
    assert reply.user_message == ("Pick a **staff role** first — it's who "
                                  "can see and handle tickets.")
    assert not captured_ops


def test_enable_guards_the_guild(captured_ops):
    reply = run(sp.setup_enable(_req({}, guild_id=0)))
    assert reply.outcome is BLOCKED
    assert reply.user_message == ("Tickets can only be configured inside "
                                  "a server.")


def test_enable_writes_the_audited_config_and_goes_green(captured_ops,
                                                         captured_refresh):
    sp._store_state("555", {"staff_role_id": 1234, "log_channel_id": 5678})
    reply = run(sp.setup_enable(_req({})))
    assert reply.user_message is None
    op, params = captured_ops[-1]
    assert op == "ticket.update_config"
    assert params == {"enabled": True, "staff_role_id": 1234,
                      "log_channel_id": 5678}
    state = sp._STATE["555"]
    assert state["enabled"] is True
    assert state["footer"] == sp.FOOTER_LIVE
    assert state["accent"] == "green"
    assert captured_refresh[-1][1]["enabled"] is True


# --- auto-create -----------------------------------------------------------------


def test_autocreate_runs_the_op_and_acks_the_channel(captured_ops,
                                                     captured_refresh):
    sp._store_state("555", {"staff_role_id": 1234})
    reply = run(sp.setup_autocreate(_req({})))
    op, params = captured_ops[-1]
    assert op == "ticket.create_log_channel"
    assert params == {"staff_role_id": 1234}
    assert reply.outcome is SUCCESS
    assert reply.user_message == ("✅ Created <#777> for ticket "
                                  "transcripts.")
    assert sp._STATE["555"]["log_channel_id"] == 777


def test_autocreate_failure_answers_the_manage_channels_copy(monkeypatch):
    from sb.kernel.workflow import engine as wf_engine

    async def fail_run(ref, ctx):
        raise RuntimeError("ChannelStateActions not installed")

    monkeypatch.setattr(wf_engine, "run", fail_run)
    reply = run(sp.setup_autocreate(_req({})))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "I couldn't create the log channel — I may be missing the "
        "**Manage Channels** permission.")


# --- post panel ------------------------------------------------------------------


def test_post_panel_guards_enable_first(monkeypatch):
    from sb.domain.ticket import service

    async def get_config(gid):
        return None

    monkeypatch.setattr(service, "get_config", get_config)
    reply = run(sp.setup_post_panel(_req({})))
    assert reply.outcome is BLOCKED
    assert reply.user_message == ("Enable tickets first, then post the "
                                  "panel.")


def test_post_panel_posts_the_launcher_and_flips_the_footer(
        monkeypatch, captured_refresh):
    from sb.kernel.panels import engine

    posted = []

    async def open_panel(ref, req):
        posted.append(ref.name)
        return "999"

    monkeypatch.setattr(engine, "open_panel", open_panel)
    sp._store_state("555", {"enabled": True, "staff_role_id": 1234})
    reply = run(sp.setup_post_panel(_req({})))
    assert posted == ["ticket.launcher"]
    assert reply.user_message is None
    # headless channel directory ⇒ the raw-id fallback name.
    assert sp._STATE["555"]["footer"] == \
        "📮 Open-ticket panel posted in #9."


def test_post_panel_forbidden_answers_the_shipped_copy(monkeypatch):
    from sb.kernel.panels import engine

    async def open_panel(ref, req):
        raise RuntimeError("Forbidden")

    monkeypatch.setattr(engine, "open_panel", open_panel)
    sp._store_state("555", {"enabled": True})
    reply = run(sp.setup_post_panel(_req({})))
    assert reply.outcome is BLOCKED
    assert reply.user_message == ("I need permission to send messages in "
                                  "this channel.")


# --- the ops legs ----------------------------------------------------------------


def test_update_config_leg_upserts_exactly_the_given_fields(monkeypatch):
    from sb.domain.ticket import ops, store
    from sb.kernel.workflow.context import WorkflowContext

    writes = []

    async def get_config_row(gid, conn=None):
        return {"enabled": False, "staff_role_id": None}

    async def upsert_config_fields(conn, *, guild_id, now, **fields):
        writes.append((guild_id, fields))

    monkeypatch.setattr(store, "get_config_row", get_config_row)
    monkeypatch.setattr(store, "upsert_config_fields", upsert_config_fields)
    ctx = WorkflowContext(actor=SimpleNamespace(user_id=UID), guild_id=GID,
                          request_id="r1", confirmed=False,
                          params={"enabled": True, "staff_role_id": 1234,
                                  "log_channel_id": None})
    out = run(ops._record_update_config(None, ctx))
    assert writes == [(GID, {"enabled": True, "staff_role_id": 1234})]
    assert out.after == {"enabled": True, "staff_role_id": 1234}


def test_create_log_channel_leg_creates_then_upserts(monkeypatch):
    from sb.domain.channel import service as channel_service
    from sb.domain.ticket import ops, store
    from sb.kernel.workflow.context import WorkflowContext

    created = []
    writes = []

    class FakeActions:
        async def create_text_channel(self, guild_id, *, name, overwrites,
                                      parent_id, reason):
            created.append((guild_id, name, tuple(overwrites), reason))
            return 777

    async def upsert_config_fields(conn, *, guild_id, now, **fields):
        writes.append((guild_id, fields))

    monkeypatch.setattr(channel_service, "active_actions",
                        lambda: FakeActions())
    monkeypatch.setattr(store, "upsert_config_fields", upsert_config_fields)
    ctx = WorkflowContext(actor=SimpleNamespace(user_id=UID), guild_id=GID,
                          request_id="r1", confirmed=False,
                          params={"staff_role_id": 1234})
    out = run(ops._record_create_log_channel(None, ctx))
    gid, name, overwrites, reason = created[0]
    assert (gid, name) == (GID, "ticket-transcripts")
    assert reason == "Ticket transcript log (auto-created via setup)"
    # @everyone deny view + the staff allow (view|history).
    assert (overwrites[0].target_id, overwrites[0].deny) == (GID, 1024)
    assert (overwrites[1].target_id, overwrites[1].allow) == (1234, 66560)
    assert writes == [(GID, {"log_channel_id": 777})]
    assert out.after == {"log_channel_id": 777}
    assert ctx.params["_created_channel_id"] == 777


# --- the open-lane eligibility (shipped order + copy) ------------------------------


def _eligibility(monkeypatch, cfg, blacklisted=False):
    from sb.domain.ticket import service, store

    async def get_config(gid):
        return cfg

    async def is_blacklisted(gid, uid, conn=None):
        return blacklisted

    monkeypatch.setattr(service, "get_config", get_config)
    monkeypatch.setattr(store, "is_blacklisted", is_blacklisted)
    return service


def test_eligibility_disabled_copy(monkeypatch):
    service = _eligibility(monkeypatch, None)
    allowed, msg = run(service.check_open_eligibility(GID, UID))
    assert not allowed
    assert msg == "The ticket system isn't enabled on this server."


def test_eligibility_not_configured_copy(monkeypatch):
    service = _eligibility(monkeypatch, {"enabled": True,
                                         "staff_role_id": None})
    allowed, msg = run(service.check_open_eligibility(GID, UID))
    assert not allowed
    assert msg == service.NOT_CONFIGURED_MSG


def test_eligibility_blacklisted_copy(monkeypatch):
    service = _eligibility(monkeypatch,
                           {"enabled": True, "staff_role_id": 1234,
                            "max_open_per_user": 3}, blacklisted=True)
    allowed, msg = run(service.check_open_eligibility(GID, UID))
    assert not allowed
    assert msg == "You can't open tickets on this server."


def test_eligible_open_answers_the_provisioning_pending_terminal(
        monkeypatch):
    from sb.domain.ticket import handlers
    from sb.spec.refs import HandlerRef, resolve

    service = _eligibility(monkeypatch,
                           {"enabled": True, "staff_role_id": 1234,
                            "max_open_per_user": 3})
    handlers.ensure_handler_refs()
    route = resolve(HandlerRef("ticket.new"))
    reply = run(route(_req({"argv": ("help", "me")})))
    assert reply.outcome is BLOCKED
    assert reply.user_message == service.OPEN_PROVISION_PENDING_MSG


# --- the hub configured branch ------------------------------------------------------


def test_hub_renders_the_configured_branch(monkeypatch):
    from sb.domain.ticket import handlers, service

    async def get_config(gid):
        return {"enabled": True, "staff_role_id": 1234,
                "log_channel_id": 5678, "max_open_per_user": 3}

    monkeypatch.setattr(service, "get_config", get_config)
    rendered = run(handlers._render_hub(handlers.ticket_hub_spec(), _ctx()))
    assert rendered.embed.description == (
        "Open a private support ticket and the staff team will help you "
        "out.")
    fields = {f[0]: f[1] for f in rendered.embed.fields}
    assert fields["Staff role"] == "<@&1234>"
    assert fields["Transcript log"] == "<#5678>"
    assert fields["Your open tickets"] == "0 / 3"


def test_hub_keeps_the_golden_not_set_up_bytes(monkeypatch):
    from sb.domain.ticket import handlers, service

    async def get_config(gid):
        return None

    monkeypatch.setattr(service, "get_config", get_config)
    rendered = run(handlers._render_hub(handlers.ticket_hub_spec(), _ctx()))
    assert rendered.embed.description == (
        "The ticket system isn't set up yet.\n"
        "An admin can run **`!ticketsetup @StaffRole`** to enable it.")
