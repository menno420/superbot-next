"""The on-guild-join setup launcher (sb/domain/setup/launcher.py —
night-tail-2) + the kernel guild-events seam + its feed wiring.

DB-free like the on-ready resume suite: the session read
(``store.get_session_row``), the workspace ensure
(``service.ensure_setup_channel``), the panel-engine post lane
(``post_anchored_panel``), the channel-directory port and the K7 write
seam (``sb.kernel.workflow.engine.run``) are monkeypatched at their
module functions; the assertions pin the ORACLE semantics (no golden
drives the join surface — the panels.py module pin; oracle sources:
disbot/cogs/setup_cog.py ``_handle_join`` /
``_post_launcher_in_setup_channel`` + disbot/views/setup/launcher.py
``SetupLauncherView`` / ``pick_launcher_channel`` / ``post_launcher``
@bbc524e4)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.domain.setup import launcher
from sb.kernel.interaction import guild_events
from sb.kernel.panels import engine as panel_engine

run = asyncio.run

GID = 4242


def _event(**kw):
    defaults = dict(guild_id=GID, guild_name="Test Guild", owner_id=99,
                    system_channel_id=None)
    defaults.update(kw)
    return guild_events.GuildJoinEvent(**defaults)


@pytest.fixture()
def session_row(monkeypatch):
    from sb.domain.setup import store

    holder: dict = {"row": None}

    async def fake_get(guild_id, conn=None):
        return holder["row"]

    monkeypatch.setattr(store, "get_session_row", fake_get)
    return holder


@pytest.fixture()
def workspace(monkeypatch):
    """service.ensure_setup_channel — (channel_id, created) or a raise."""
    from sb.domain.setup import service

    state = {"channel_id": 555, "created": True, "raises": False}

    async def fake_ensure(guild_id, invoker_id, delegated=()):
        if state["raises"]:
            raise RuntimeError("no Manage Channels")
        state["invoker_id"] = invoker_id
        return state["channel_id"], state["created"]

    monkeypatch.setattr(service, "ensure_setup_channel", fake_ensure)
    return state


class _PostRecorder:
    def __init__(self):
        self.calls: list[dict] = []
        self.message_id: int | None = 777

    async def __call__(self, ref, *, guild_id, channel_id, actor,
                       params=None, mention_user_ids=()):
        self.calls.append({"panel": ref.name, "guild_id": guild_id,
                           "channel_id": channel_id, "actor": actor,
                           "params": dict(params or {}),
                           "mentions": tuple(mention_user_ids)})
        return self.message_id


@pytest.fixture()
def posts(monkeypatch):
    rec = _PostRecorder()
    monkeypatch.setattr(panel_engine, "post_anchored_panel", rec)
    return rec


@pytest.fixture()
def k7(monkeypatch):
    from sb.kernel.workflow import engine as workflow_engine
    from sb.spec.outcomes import SUCCESS

    calls: list[tuple[str, int, dict]] = []

    async def fake_run(ref, ctx):
        calls.append((str(getattr(ref, "name", getattr(ref, "op_key", ref))),
                      int(ctx.guild_id), dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS, ok=True, user_message=None)

    monkeypatch.setattr(workflow_engine, "run", fake_run)
    return calls


@pytest.fixture()
def channels(monkeypatch):
    """The channel-directory port's cache view (name → the ladder)."""
    from sb.domain.channel import service as channel_service

    snaps: list = []

    class _Dir:
        async def list_channels(self, guild_id):
            return tuple(snaps)

    monkeypatch.setattr(channel_service, "active_directory", lambda: _Dir())
    return snaps


def _chan(channel_id, name, kind="text"):
    return SimpleNamespace(channel_id=channel_id, name=name, kind=kind)


# --- the kernel guild-events seam ----------------------------------------------------


@pytest.fixture()
def fresh_consumers():
    guild_events.reset_guild_join_consumers_for_tests()
    yield
    guild_events.reset_guild_join_consumers_for_tests()


def test_dispatch_fans_out_and_isolates_faults(fresh_consumers) -> None:
    seen: list[int] = []

    async def good(event):
        seen.append(event.guild_id)

    async def bad(event):
        raise RuntimeError("boom")

    guild_events.register_guild_join_consumer("t.bad", bad)
    guild_events.register_guild_join_consumer("t.good", good)

    ran = run(guild_events.dispatch_guild_join(_event()))

    # the faulting consumer is logged and skipped; the loop continues.
    assert ran == 1
    assert seen == [GID]


def test_registration_is_idempotent_by_name(fresh_consumers) -> None:
    async def one(event):
        pass

    guild_events.register_guild_join_consumer("t.one", one)
    guild_events.register_guild_join_consumer("t.one", one)
    assert guild_events.registered_guild_join_consumers() == ("t.one",)


def test_manifest_ensure_refs_registers_the_consumer(fresh_consumers) -> None:
    import sb.manifest.setup as m

    m.ENSURE_REFS()
    assert launcher.GUILD_JOIN_CONSUMER in (
        guild_events.registered_guild_join_consumers())


def test_adapter_feed_builds_the_duck_event(fresh_consumers) -> None:
    from sb.adapters.discord.guild_feed import handle_gateway_guild_join

    seen: list = []

    async def consumer(event):
        seen.append(event)

    guild_events.register_guild_join_consumer("t.c", consumer)
    guild = SimpleNamespace(id=GID, name="Test Guild", owner_id=99,
                            system_channel=SimpleNamespace(id=321))
    ran = run(handle_gateway_guild_join(guild))
    assert ran == 1
    event = seen[0]
    assert (event.guild_id, event.guild_name, event.owner_id,
            event.system_channel_id) == (GID, "Test Guild", 99, 321)


# --- the join lane: workspace-first --------------------------------------------------


def test_fresh_join_posts_launcher_into_created_workspace(
        session_row, workspace, posts, k7, channels) -> None:
    counts = run(launcher.handle_guild_join(_event()))

    post, = posts.calls
    assert post["panel"] == launcher.LAUNCHER_PANEL_ID
    assert (post["guild_id"], post["channel_id"]) == (GID, 555)
    # bot-initiated post rides the system actor, never a member.
    assert post["actor"].actor_type == "system"
    # the freshly-created workspace carries the owner-ping content line
    # (the oracle's was_created branch) + the explicit mention allowlist.
    assert post["params"]["launcher_fresh"] is True
    content = post["params"]["launcher_content"]
    assert content.startswith("<@99> SuperBot just joined!")
    assert "Click **Start Setup** below" in content
    assert post["mentions"] == (99,)
    # the session upsert rode the K7 op with the minted pointers.
    assert k7 == [("setup.start_session", GID,
                   {"guild_name": "Test Guild", "owner_id": 99,
                    "setup_channel_id": 555, "setup_message_id": 777})]
    assert counts["surface"] == "workspace"


def test_reused_workspace_posts_without_the_owner_ping(
        session_row, workspace, posts, k7, channels) -> None:
    workspace["created"] = False
    run(launcher.handle_guild_join(_event()))

    post, = posts.calls
    assert "launcher_content" not in post["params"]
    assert post["mentions"] == ()


def test_rejoin_with_live_launcher_never_double_posts(
        session_row, workspace, posts, k7, channels) -> None:
    """The oracle's restart/no-double-post guard: an existing channel
    whose row still points at a launcher message keeps the prior ids —
    the on-ready sweep edits that message in place."""
    workspace["created"] = False
    session_row["row"] = {"guild_id": GID, "setup_channel_id": 555,
                          "setup_message_id": 111}

    counts = run(launcher.handle_guild_join(_event()))

    assert posts.calls == []
    assert k7 == [("setup.start_session", GID,
                   {"guild_name": "Test Guild", "owner_id": 99,
                    "setup_channel_id": 555, "setup_message_id": 111})]
    assert counts["surface"] == "workspace"


def test_stale_pointer_at_another_channel_reposts(
        session_row, workspace, posts, k7, channels) -> None:
    # the row points at a DIFFERENT channel — the guard does not hold.
    workspace["created"] = False
    session_row["row"] = {"guild_id": GID, "setup_channel_id": 123,
                          "setup_message_id": 111}
    run(launcher.handle_guild_join(_event()))
    assert len(posts.calls) == 1


# --- the join lane: the fallback ladder ----------------------------------------------


def test_ensure_failure_falls_back_to_system_channel(
        session_row, workspace, posts, k7, channels) -> None:
    workspace["raises"] = True
    channels.extend([_chan(10, "general"), _chan(20, "welcome")])

    counts = run(launcher.handle_guild_join(_event(system_channel_id=20)))

    post, = posts.calls
    assert post["channel_id"] == 20          # ladder rung 1: system channel
    assert "launcher_content" not in post["params"]   # plain post, no ping
    assert counts["surface"] == "fallback"
    assert k7[0][2]["setup_channel_id"] == 20


def test_fallback_prefers_admin_mod_staff_then_bot_names(
        session_row, workspace, posts, k7, channels) -> None:
    workspace["raises"] = True
    channels.extend([_chan(10, "general"), _chan(11, "bot-spam"),
                     _chan(12, "MOD-log"), _chan(13, "staff-room")])

    run(launcher.handle_guild_join(_event()))

    # rung 2 beats rung 3: the first admin/mod/staff name hit in channel
    # order (the oracle's keyword_groups walk, case-insensitive).
    assert posts.calls[0]["channel_id"] == 12


def test_fallback_last_rung_is_the_first_text_channel(
        session_row, workspace, posts, k7, channels) -> None:
    workspace["raises"] = True
    channels.extend([_chan(10, "voice-lounge", kind="voice"),
                     _chan(11, "general")])

    run(launcher.handle_guild_join(_event()))

    assert posts.calls[0]["channel_id"] == 11


def test_no_sendable_channel_still_mints_the_session_row(
        session_row, workspace, posts, k7, channels) -> None:
    """The oracle upserted the row even when nothing was posted (the
    owner-DM last rung is unported — module ledger)."""
    workspace["raises"] = True

    counts = run(launcher.handle_guild_join(_event()))

    assert posts.calls == []
    assert k7 == [("setup.start_session", GID,
                   {"guild_name": "Test Guild", "owner_id": 99,
                    "setup_channel_id": None, "setup_message_id": None})]
    assert counts["surface"] == "none"


def test_headless_poster_degrades_to_pointerless_upsert(
        session_row, workspace, posts, k7, channels) -> None:
    posts.message_id = None          # no poster installed / send refused
    channels.append(_chan(10, "general"))

    counts = run(launcher.handle_guild_join(_event()))

    # workspace post answered None → the ladder tried its pick → None too;
    # the session row still lands, pointer-less.
    assert counts["surface"] == "none"
    assert k7[0][2]["setup_channel_id"] is None


def test_handler_faults_are_isolated(
        session_row, workspace, posts, channels, monkeypatch) -> None:
    from sb.kernel.workflow import engine as workflow_engine

    async def boom(ref, ctx):
        raise RuntimeError("db down")

    monkeypatch.setattr(workflow_engine, "run", boom)
    # never raises — the join must not break the gateway feed (the
    # oracle's _handle_join try/except).
    counts = run(launcher.handle_guild_join(_event()))
    assert counts["guild_id"] == GID


# --- the launcher render (the _build_launcher_embed port) ----------------------------


def _render(params=None, row=None, monkeypatch=None):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin

    if monkeypatch is not None:
        from sb.domain.setup import store

        async def fake_get(guild_id, conn=None):
            return row

        monkeypatch.setattr(store, "get_session_row", fake_get)
    spec = launcher.launcher_spec()
    ctx = PanelContext(bot=None, guild_id=GID, actor=launcher._join_actor(),
                       channel_id=1, origin=PanelOrigin.ANCHOR,
                       audience=spec.audience, locale=LocaleContext(),
                       params=dict(params or {}), surface=None)
    return run(launcher._render_launcher(spec, ctx))


def test_fresh_render_is_the_shipped_card(monkeypatch) -> None:
    rendered = _render(params={"launcher_fresh": True,
                               "launcher_content": "<@99> hi"})
    embed = rendered.embed
    assert embed.title == "🛰 SuperBot setup"
    assert embed.description.startswith(
        "Welcome! I'll help you set SuperBot up for this server.")
    assert "**Status:**" not in embed.description
    assert embed.footer == ("Owner-gated for write actions. Admins can run "
                            "the readiness scan.")
    assert embed.style_token == "blurple"
    assert rendered.content == "<@99> hi"
    assert rendered.timeout_s is None        # persistent — never times out
    # the seven shipped static custom ids, wire order.
    assert [c.custom_id for c in rendered.components] == [
        "setup:start", "setup:readiness", "setup:smart_suggestions",
        "setup:preset", "setup:summary", "setup:repost_launcher",
        "setup:dismiss"]


@pytest.mark.parametrize(
    ("status", "label", "token"),
    [("pending", "Start Setup", "blurple"),
     ("in_progress", "Resume Setup", "blurple"),
     ("complete", "Re-run Setup", "green"),
     ("dismissed", "Start Setup", "dark_grey")])
def test_status_aware_labels_and_accents(status, label, token,
                                         monkeypatch) -> None:
    rendered = _render(
        row={"setup_status": status, "last_readiness_score": None,
             "current_step": None},
        monkeypatch=monkeypatch)
    start = next(c for c in rendered.components
                 if c.custom_id == "setup:start")
    assert start.label == label
    assert rendered.embed.style_token == token
    assert f"**Status:** `{status}`" in rendered.embed.description


def test_session_suffixes_ride_the_description(monkeypatch) -> None:
    rendered = _render(
        row={"setup_status": "in_progress", "last_readiness_score": 40,
             "current_step": "channels"},
        monkeypatch=monkeypatch)
    assert ("**Status:** `in_progress` · readiness `40%` · step `channels`"
            in rendered.embed.description)


# --- the button handlers --------------------------------------------------------------


def _req(operator=False, args=None):
    from sb.kernel.interaction.request import ActorRef

    actor = ActorRef(user_id=7, is_guild_operator=operator,
                     is_bot_owner=False, is_dm=False)
    return SimpleNamespace(actor=actor, guild_id=GID,
                           request_id="req-1", confirmed=False,
                           args=dict(args or {}))


def _handler(name):
    from sb.spec.refs import HandlerRef, resolve

    return resolve(HandlerRef(name))


@pytest.fixture()
def not_owner(monkeypatch):
    from sb.domain.setup import wizard

    async def deny(req):
        return False

    monkeypatch.setattr(wizard, "can_apply_setup", deny)


@pytest.fixture()
def owner(monkeypatch):
    from sb.domain.setup import wizard

    async def allow(req):
        return True

    monkeypatch.setattr(wizard, "can_apply_setup", allow)


def test_start_gate_refuses_non_admins(not_owner) -> None:
    from sb.spec.outcomes import BLOCKED

    reply = run(_handler("setup.launcher_start")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (SetupLauncherView._start).
    assert reply.user_message == (
        "Only the server owner, an administrator, or a delegated setup "
        "admin can start setup.")


def test_dismiss_gate_holds_the_owner_copy(not_owner) -> None:
    from sb.spec.outcomes import BLOCKED

    # a plain administrator is NOT enough for Dismiss (the oracle
    # _gate_owner) — is_guild_operator does not open it.
    reply = run(_handler("setup.launcher_dismiss")(_req(operator=True)))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Only the server owner can start setup or change presets.")


def test_dismiss_rides_the_k7_op(owner, k7) -> None:
    from sb.spec.outcomes import SUCCESS

    reply = run(_handler("setup.launcher_dismiss")(_req()))
    assert [(name, gid) for name, gid, _ in k7] == [
        ("setup.mark_dismissed", GID)]
    assert reply.outcome == SUCCESS
    # shipped copy, verbatim.
    assert reply.user_message == (
        "Setup dismissed. Use the setup launcher later to resume.")


def test_summary_not_complete_holds_the_shipped_refusal(
        owner, session_row) -> None:
    from sb.spec.outcomes import BLOCKED

    session_row["row"] = {"setup_status": "in_progress"}
    reply = run(_handler("setup.launcher_summary")(_req(operator=True)))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (SetupLauncherView._view_summary).
    assert reply.user_message == (
        "Setup is not complete yet. Run **Start Setup** to finish the "
        "wizard before viewing the summary.")


def test_readiness_answers_the_check_setup_read(owner, monkeypatch) -> None:
    from sb.domain.setup import essential_steps
    from sb.spec.outcomes import SUCCESS

    async def fake_text(guild_id):
        return "🔎 **How set up are you?**\nstub"

    monkeypatch.setattr(essential_steps, "build_check_setup_text", fake_text)
    reply = run(_handler("setup.launcher_readiness")(_req(operator=True)))
    assert reply.outcome == SUCCESS
    assert reply.user_message.startswith("🔎 **How set up are you?**")


def test_repost_failure_holds_the_shipped_copy(owner, monkeypatch) -> None:
    from sb.spec.outcomes import BLOCKED

    async def no_channel(guild_id, system_channel_id):
        return None

    monkeypatch.setattr(launcher, "_pick_launcher_channel", no_channel)
    reply = run(_handler("setup.launcher_repost")(_req(operator=True)))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (SetupLauncherView._repost_launcher deny).
    assert reply.user_message == (
        "Could not post the launcher anywhere — bot has no sendable "
        "channel and the owner has DMs closed.")


def test_repost_posts_and_refreshes_the_session(owner, k7,
                                                monkeypatch) -> None:
    from sb.spec.outcomes import SUCCESS

    async def pick(guild_id, system_channel_id):
        return 31

    async def post(guild_id, channel_id, *, content=None,
                   mention_user_ids=()):
        return 888

    async def identity(guild_id):
        return "Test Guild", 99

    from sb.domain.setup import handlers as setup_handlers

    monkeypatch.setattr(launcher, "_pick_launcher_channel", pick)
    monkeypatch.setattr(launcher, "_post_launcher_panel", post)
    monkeypatch.setattr(setup_handlers, "_guild_identity", identity)

    reply = run(_handler("setup.launcher_repost")(_req(operator=True)))

    assert reply.outcome == SUCCESS
    assert reply.user_message == "Launcher reposted in <#31>."
    name, gid, params = k7[0]
    assert (name, gid) == ("setup.start_session", GID)
    assert params["setup_channel_id"] == 31
    assert params["setup_message_id"] == 888


def test_suggestions_gate_holds_the_shipped_copy(not_owner) -> None:
    from sb.spec.outcomes import BLOCKED

    reply = run(_handler("setup.launcher_suggestions")(_req(operator=True)))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (SetupLauncherView._gate_apply).
    assert reply.user_message == (
        "Only the server owner or a delegated setup admin can use this "
        "button. Ask the owner to grant you `/setup-delegate`.")


# --- the K7 legs ----------------------------------------------------------------------


def test_start_session_leg_carries_optional_pointers() -> None:
    """The extended ``setup.record_session_started`` leg: the join lane's
    pointers thread through; the hub entry's pointer-less mint is
    unchanged (goldens/setup/sweep_slash_setup-hub)."""
    from sb.domain.setup import ops as setup_ops
    from sb.kernel.workflow.context import WorkflowContext

    writes: list[dict] = []

    async def fake_upsert(conn, **kw):
        writes.append(kw)

    from sb.domain.setup import store

    original = store.upsert_session
    store.upsert_session = fake_upsert
    try:
        ctx = WorkflowContext(
            actor=launcher._join_actor(), guild_id=GID, request_id="r",
            params={"guild_name": "G", "owner_id": 9,
                    "setup_channel_id": 555, "setup_message_id": 777})
        run(setup_ops._record_session_started(None, ctx))
        ctx2 = WorkflowContext(
            actor=launcher._join_actor(), guild_id=GID, request_id="r2",
            params={"guild_name": "G", "owner_id": 9})
        run(setup_ops._record_session_started(None, ctx2))
    finally:
        store.upsert_session = original

    assert writes[0]["setup_channel_id"] == 555
    assert writes[0]["setup_message_id"] == 777
    assert writes[0]["setup_status"] == "pending"
    assert writes[1]["setup_channel_id"] is None
    assert writes[1]["setup_message_id"] is None


def test_dismissed_leg_writes_the_status() -> None:
    from sb.domain.setup import ops as setup_ops
    from sb.domain.setup import store
    from sb.kernel.workflow.context import WorkflowContext

    writes: list[tuple] = []

    async def fake_set(conn, *, guild_id, status):
        writes.append((guild_id, status))

    original = store.set_session_status
    store.set_session_status = fake_set
    try:
        run(setup_ops._record_session_dismissed(None, WorkflowContext(
            actor=launcher._join_actor(), guild_id=GID, request_id="r",
            params={})))
    finally:
        store.set_session_status = original

    assert writes == [(GID, "dismissed")]
