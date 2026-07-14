"""The SectionRecoveryView + workspace-notice ride (the
night-recovery-view slice — sb/domain/setup/recovery.py + notices.py,
ORDER 019 item 5b).

DB-free like the wizard-interior suite: the K7/K9 write seams are
monkeypatched at their module functions and the assertions pin the
ORACLE bytes the click paths carry (no golden drives a click on these
components — the panels.py module pin; oracle sources @bbc524e4:
views/setup/recovery.py, views/setup/_anchor.py push_setup_notice,
views/setup/wizard.py _mount_recovery_view /_on_apply_recommended /
_on_apply_all_recommended)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run


@pytest.fixture(autouse=True)
def _fresh_state():
    import sb.manifest.setup as m
    from sb.domain.setup import recovery, wizard, wizard_nav

    m.ENSURE_REFS()
    wizard.reset_wizard_state_for_tests()
    wizard_nav.reset_wizard_nav_state_for_tests()
    recovery.reset_recovery_state_for_tests()
    yield
    wizard.reset_wizard_state_for_tests()
    wizard_nav.reset_wizard_nav_state_for_tests()
    recovery.reset_recovery_state_for_tests()


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


def _section(slug):
    from sb.domain.setup.sections import REGISTRY, register_shipped_sections

    register_shipped_sections()
    section = REGISTRY.get(slug)
    assert section is not None
    return section


def _stash(slug="channels", *, origin="wizard", step_index=1,
           total_steps=3, guild_id=99, user_id=42):
    from sb.domain.setup import recovery

    context = recovery.recovery_context_from_exception(
        section=_section(slug), exc=RuntimeError("boom"),
        origin=origin, step_index=step_index, total_steps=total_steps)
    recovery.set_recovery_context(guild_id, user_id, context)
    return context


def _capture_open(monkeypatch):
    from sb.kernel.panels import engine as panels_engine

    opened = []

    async def fake_open(ref, req):
        opened.append(str(getattr(ref, "name", ref)))
        return "555"

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    return opened


# --- context construction (recovery_context_from_exception) -------------------------------


def test_context_from_exception_pins_the_generic_copy():
    from sb.domain.setup import recovery

    context = recovery.recovery_context_from_exception(
        section=_section("channels"), exc=RuntimeError("boom"),
        origin="wizard", step_index=1, total_steps=3)
    # shipped copy, verbatim (recovery.recovery_context_from_exception).
    assert context.what_happened == (
        "The wizard couldn't complete the **Channels & log routing** "
        "step without an error.")
    assert context.why == "RuntimeError: boom"
    assert context.recommended == (
        "Press **Retry** to try the step again, or **Skip section** to "
        "move past it and revisit later.")
    # the target WizardSectionSpec carries no description_if_skipped —
    # the oracle's own generic fall-through answers (module ledger).
    assert context.if_skipped == (
        "The wizard continues with the section's current state.  You "
        "can return to it any time via the hub.")


def test_context_permission_hint_ladder():
    from sb.domain.setup import recovery

    class Forbidden(Exception):
        pass

    context = recovery.recovery_context_from_exception(
        section=_section("channels"), exc=Forbidden("403"))
    # shipped hint, verbatim.
    assert context.why == ("SuperBot is missing a Discord permission "
                           "for this step.")
    context = recovery.recovery_context_from_exception(
        section=_section("channels"), exc=TimeoutError())
    assert context.why == ("The operation timed out before Discord "
                           "responded.")


# --- the recovery embed (build_recovery_embed) ---------------------------------------------


def test_recovery_render_pins_the_shipped_embed():
    from sb.domain.setup import recovery

    _stash("channels", step_index=1, total_steps=3)
    rendered = run(recovery._render_section_recovery(
        recovery.section_recovery_spec(), _ctx()))
    embed = rendered.embed
    # shipped bytes, verbatim (recovery.build_recovery_embed).
    assert embed.title == "⚠️ Setup issue found · Step 2/3"
    assert embed.description == (
        "While running **Channels & log routing** the wizard hit an "
        "error.  Nothing has changed yet — pick how to proceed from "
        "the buttons below.")
    assert [f[0] for f in embed.fields] == [
        "What happened", "Why", "Recommended", "If skipped"]
    assert embed.fields[1][1] == "RuntimeError: boom"
    assert embed.footer == (
        "Recovery only — Final Review still owns the apply path.  "
        "Nothing on this view stages or applies operations.")
    assert embed.style_token == "gold"
    ids = [c.custom_id for c in rendered.components]
    # oracle custom_ids, verbatim (SectionRecoveryView._populate_buttons).
    assert ids == ["setup_recovery:continue", "setup_recovery:retry",
                   "setup_recovery:skip", "setup_recovery:customize",
                   "setup_recovery:cancel"]


def test_recovery_render_hub_origin_drops_the_step_ordinal():
    from sb.domain.setup import recovery

    _stash("channels", origin="hub", step_index=-1, total_steps=0)
    rendered = run(recovery._render_section_recovery(
        recovery.section_recovery_spec(), _ctx()))
    assert rendered.embed.title == "⚠️ Setup issue found"


def test_recovery_render_customize_disable_follows_the_section():
    from sb.domain.setup import recovery

    # channels: op_kinds present → Customize stays live.
    _stash("channels")
    rendered = run(recovery._render_section_recovery(
        recovery.section_recovery_spec(), _ctx()))
    customize = [c for c in rendered.components
                 if c.custom_id == "setup_recovery:customize"][0]
    assert not customize.disabled

    # preset_select: no builder, no op_kinds → disabled (the shipped
    # read-only guard).
    _stash("preset_select")
    rendered = run(recovery._render_section_recovery(
        recovery.section_recovery_spec(), _ctx()))
    customize = [c for c in rendered.components
                 if c.custom_id == "setup_recovery:customize"][0]
    assert customize.disabled


def test_recovery_render_without_context_degrades():
    from sb.domain.setup import recovery

    rendered = run(recovery._render_section_recovery(
        recovery.section_recovery_spec(), _ctx()))
    assert rendered.embed.description == (
        "This recovery prompt has expired — re-open the wizard with "
        "`/setup-advanced`.")
    assert rendered.embed.style_token == "dark_grey"


# --- the mount (wizard._mount_recovery_view) ------------------------------------------------


def test_mount_stashes_the_context_and_opens_the_panel(monkeypatch):
    from sb.domain.setup import recovery

    opened = _capture_open(monkeypatch)
    run(recovery.mount_section_recovery(
        _req(), section=_section("channels"), exc=RuntimeError("boom"),
        origin="wizard", step_index=1, total_steps=3))
    assert opened == [recovery.SECTION_RECOVERY_PANEL_ID]
    context = recovery.recovery_context(99, 42)
    assert context is not None
    assert (context.slug, context.step_index, context.total_steps) == (
        "channels", 1, 3)


def test_apply_recommended_builder_failure_mounts_recovery(monkeypatch):
    from sb.domain.setup import recovery, section_card as sc
    from sb.domain.setup import store, wizard, wizard_nav

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def fake_row(guild_id, conn=None):
        return {"depth": "quick", "current_step": None,
                "skipped_sections": [], "acknowledged_sections": []}

    monkeypatch.setattr(store, "get_session_row", fake_row)
    wizard_nav._set_step_index(99, 42, 1)   # channels

    async def broken_builder(guild_id):
        raise RuntimeError("scan failed")

    monkeypatch.setitem(sc._RECOMMENDED_BUILDERS, "channels",
                        broken_builder)
    opened = _capture_open(monkeypatch)
    reply = run(_resolve("setup.wizard_apply_recommended")(_req()))
    assert reply is None
    assert opened == [recovery.SECTION_RECOVERY_PANEL_ID]
    context = recovery.recovery_context(99, 42)
    assert context is not None and context.slug == "channels"
    assert context.why == "RuntimeError: scan failed"


# --- the click lanes ------------------------------------------------------------------------


def test_continue_reopens_the_wizard_step_and_clears(monkeypatch):
    from sb.domain.setup import recovery, wizard_nav

    _stash("channels", step_index=2, total_steps=3)
    opened = _capture_open(monkeypatch)
    reply = run(_resolve("setup.section_recovery_continue")(_req()))
    assert reply is None
    assert opened == [wizard_nav.WIZARD_STEP_PANEL_ID]
    assert wizard_nav.step_index(99, 42) == 2
    assert recovery.recovery_context(99, 42) is None


def test_continue_hub_origin_reopens_the_sections_hub(monkeypatch):
    from sb.domain.setup.panels import SECTIONS_HUB_PANEL_ID

    _stash("channels", origin="hub", step_index=-1, total_steps=0)
    opened = _capture_open(monkeypatch)
    run(_resolve("setup.section_recovery_continue")(_req()))
    assert opened == [SECTIONS_HUB_PANEL_ID]


def test_retry_gate_refusal_is_the_recovery_copy(monkeypatch):
    from sb.domain.setup import recovery, wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    _stash("channels")
    reply = run(_resolve("setup.section_recovery_retry")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (recovery._gate_apply).
    assert reply.user_message == (
        "Only the server owner or a delegated setup admin can retry or "
        "skip a setup step.  Ask the owner to grant you "
        "`/setup-delegate`.")
    assert recovery.GATE_MSG_RECOVERY == reply.user_message


def test_retry_reinvokes_the_section_flow(monkeypatch):
    import sb.spec.refs as refs
    from sb.domain.setup import recovery, wizard
    from sb.kernel.interaction.handler_kit import Reply

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _stash("channels")
    calls = []

    async def fake_section_open(req):
        calls.append("open_section_channels")
        return Reply(SUCCESS, "section reopened")

    real_resolve = refs.resolve

    def fake_resolve(ref):
        if getattr(ref, "name", "") == "setup.open_section_channels":
            return fake_section_open
        return real_resolve(ref)

    monkeypatch.setattr(refs, "resolve", fake_resolve)
    reply = run(_resolve("setup.section_recovery_retry")(_req()))
    assert calls == ["open_section_channels"]
    assert reply.outcome == SUCCESS
    assert recovery.recovery_context(99, 42) is None


def test_retry_failure_answers_the_shipped_copy(monkeypatch):
    import sb.spec.refs as refs
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _stash("channels")

    async def broken_section_open(req):
        raise RuntimeError("still broken")

    real_resolve = refs.resolve

    def fake_resolve(ref):
        if getattr(ref, "name", "") == "setup.open_section_channels":
            return broken_section_open
        return real_resolve(ref)

    monkeypatch.setattr(refs, "resolve", fake_resolve)
    reply = run(_resolve("setup.section_recovery_retry")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (recovery._on_retry).
    assert reply.user_message == (
        "Retry of **Channels & log routing** failed again — see logs.  "
        "Use Skip section to move on.")


def test_retry_expired_answers_the_degrade_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    reply = run(_resolve("setup.section_recovery_retry")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "This recovery prompt has expired — re-open the wizard with "
        "`/setup-advanced`.")


def test_skip_records_deletes_and_returns_to_the_wizard(monkeypatch):
    from sb.domain.setup import recovery, section_card as sc, wizard
    from sb.domain.setup import wizard_nav

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _stash("channels", step_index=1, total_steps=3)
    marked = []

    async def fake_mark(req, slug, *, skipped):
        marked.append((slug, skipped))
        return True

    deleted = []

    async def fake_delete(guild_id, slug):
        deleted.append((guild_id, slug))
        return 2

    monkeypatch.setattr(sc, "mark_section_skipped", fake_mark)
    monkeypatch.setattr(sc, "delete_section_rows", fake_delete)
    opened = _capture_open(monkeypatch)
    reply = run(_resolve("setup.section_recovery_skip")(_req()))
    assert marked == [("channels", True)]
    assert deleted == [(99, "channels")]
    assert opened == [wizard_nav.WIZARD_STEP_PANEL_ID]
    assert reply.outcome == SUCCESS
    # shipped copy, verbatim (recovery._on_skip).
    assert reply.user_message == "⏭ Skipped **Channels & log routing**."
    assert recovery.recovery_context(99, 42) is None


def test_skip_mark_failure_answers_the_shipped_copy(monkeypatch):
    from sb.domain.setup import section_card as sc, wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _stash("channels")

    async def fake_mark(req, slug, *, skipped):
        return False

    monkeypatch.setattr(sc, "mark_section_skipped", fake_mark)
    reply = run(_resolve("setup.section_recovery_skip")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim.
    assert reply.user_message == "Could not record the skip — see logs."


def test_customize_opens_the_detail_view(monkeypatch):
    from sb.domain.setup import section_card as sc, wizard, wizard_nav

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _stash("channels", step_index=1, total_steps=3)
    opened = _capture_open(monkeypatch)
    detail_panel = sc.customize_panel("channels")
    assert detail_panel is not None   # channels registers a detail view
    reply = run(_resolve("setup.section_recovery_customize")(_req()))
    assert reply is None
    assert opened == [detail_panel]
    assert wizard_nav.detail_from_wizard(99, 42)


def test_customize_without_detail_falls_back_to_retry(monkeypatch):
    import sb.spec.refs as refs
    from sb.domain.setup import section_card as sc, wizard
    from sb.kernel.interaction.handler_kit import Reply

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _stash("preset_select")
    monkeypatch.setitem(sc._CUSTOMIZE_PANELS, "preset_select", None)
    calls = []

    async def fake_section_open(req):
        calls.append("run")
        return Reply(SUCCESS, "section reopened")

    real_resolve = refs.resolve

    def fake_resolve(ref):
        if getattr(ref, "name", "") == "setup.open_section_preset_select":
            return fake_section_open
        return real_resolve(ref)

    monkeypatch.setattr(refs, "resolve", fake_resolve)
    reply = run(_resolve("setup.section_recovery_customize")(_req()))
    assert calls == ["run"]
    assert reply.outcome == SUCCESS


def test_cancel_answers_the_shipped_copy():
    from sb.domain.setup import recovery

    _stash("channels")
    reply = run(_resolve("setup.section_recovery_cancel")(_req()))
    assert reply.outcome == SUCCESS
    # shipped copy, verbatim (recovery._on_cancel).
    assert reply.user_message == (
        "Recovery cancelled — your wizard / hub anchor above is "
        "unchanged.  Nothing was applied or skipped.")
    assert recovery.recovery_context(99, 42) is None


# --- the workspace-notice ride (push_setup_notice) ------------------------------------------


def test_push_setup_notice_posts_into_the_workspace(monkeypatch):
    from sb.domain.setup import notices, service

    ensured = []

    async def fake_ensure(guild_id, invoker_id, delegated=()):
        ensured.append((guild_id, invoker_id))
        return 1234, False

    posts = []

    async def fake_post(panel_id, req, channel_id, params=None):
        posts.append((panel_id, channel_id, dict(params or {})))
        return 555

    monkeypatch.setattr(service, "ensure_setup_channel", fake_ensure)
    monkeypatch.setattr(service, "post_panel_to_channel", fake_post)
    ok = run(notices.push_setup_notice(
        _req(), title="✅ Recommended staged · Channels & log routing",
        description="Staged **1 operation**."))
    assert ok is True
    assert ensured == [(99, 42)]
    panel_id, channel_id, params = posts[0]
    assert panel_id == notices.NOTICE_PANEL_ID
    assert channel_id == 1234
    assert params["notice_title"] == (
        "✅ Recommended staged · Channels & log routing")
    assert params["notice_description"] == "Staged **1 operation**."


def test_push_setup_notice_never_raises(monkeypatch):
    from sb.domain.setup import notices, service

    async def broken_ensure(guild_id, invoker_id, delegated=()):
        raise RuntimeError("no channel port")

    monkeypatch.setattr(service, "ensure_setup_channel", broken_ensure)
    # the oracle contract: swallow, log, answer False.
    assert run(notices.push_setup_notice(
        _req(), title="t", description="d")) is False


def test_notice_render_composes_the_pushed_embed():
    from sb.domain.setup import notices

    rendered = run(notices._render_workspace_notice(
        notices.workspace_notice_spec(),
        _ctx(params={"notice_title": "⚠️ Section `channels` failed",
                     "notice_description": "See logs for details.",
                     "notice_style": "red"})))
    assert rendered.embed.title == "⚠️ Section `channels` failed"
    assert rendered.embed.description == "See logs for details."
    assert rendered.embed.style_token == "red"
    assert rendered.components == ()


def test_apply_recommended_rides_the_notice(monkeypatch):
    from sb.domain.setup import notices, section_card as sc
    from sb.domain.setup import store, wizard, wizard_nav
    from sb.kernel.panels import engine as panels_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def fake_row(guild_id, conn=None):
        return {"depth": "quick", "current_step": None,
                "skipped_sections": [], "acknowledged_sections": []}

    monkeypatch.setattr(store, "get_session_row", fake_row)
    wizard_nav._set_step_index(99, 42, 1)   # channels

    from sb.kernel.workflow import engine as wf_engine

    async def fake_run(ref, ctx):
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view",
                        fake_refresh)

    async def fake_builder(guild_id):
        return [sc.StagedSectionOp(
            op_kind="bind_channel", subsystem="logging",
            payload={"subsystem": "logging", "name": "mod_channel",
                     "kind": "channel", "resource_id": 1,
                     "target_name": "mod-log"})]

    monkeypatch.setitem(sc._RECOMMENDED_BUILDERS, "channels",
                        fake_builder)

    class _FakeResult:
        inserted = 1
        conflicts = ()

    async def fake_replace(guild_id, slug, ops):
        return _FakeResult()

    monkeypatch.setattr(sc, "replace_recommended_for_section",
                        fake_replace)
    pushed = []

    async def fake_push(req, *, title, description, style_token="green"):
        pushed.append((title, description))
        return True

    monkeypatch.setattr(notices, "push_setup_notice", fake_push)
    reply = run(_resolve("setup.wizard_apply_recommended")(_req()))
    # the shipped notice bytes ride the workspace post…
    assert pushed == [(
        "✅ Recommended staged · Channels & log routing",
        "Staged **1 operation**.")]
    # …and the click-level text ack keeps the same copy (ledgered seam).
    assert reply.outcome == SUCCESS
    assert reply.user_message == (
        "✅ Recommended staged · Channels & log routing — "
        "Staged **1 operation**.")
