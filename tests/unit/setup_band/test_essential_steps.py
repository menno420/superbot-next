"""Essential Setup steps 2–8 (the essential-steps slice —
sb/domain/setup/essential_steps.py).

DB-free like the wizard-interior suite: the K7 write seams are
monkeypatched at their module functions (``wizard._write_setting``,
``sb.kernel.workflow.engine.run``, the create-channel/create-role
helpers) and the assertions pin the ORACLE bytes the click paths carry
(no golden drives a click on these components — the panels.py module
pin; oracle source: views/setup/essential_setup.py)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run


@pytest.fixture(autouse=True)
def _fresh_state():
    import sb.manifest.setup as m
    from sb.domain.setup import wizard

    m.ENSURE_REFS()
    wizard.reset_wizard_state_for_tests()
    yield
    wizard.reset_wizard_state_for_tests()


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


def _state():
    from sb.domain.setup.essential_steps import flow_state

    return flow_state(99, 42)


class _EngineRecorder:
    """Monkeypatch target for sb.kernel.workflow.engine.run."""

    def __init__(self, outcome=SUCCESS):
        self.calls = []
        self.outcome = outcome

    async def __call__(self, ref, ctx):
        self.calls.append((str(getattr(ref, "name", ref)),
                           dict(getattr(ctx, "params", {}) or {})))
        return SimpleNamespace(outcome=self.outcome, user_message=None,
                               ok=self.outcome == SUCCESS, after={})

    def refs(self):
        return [ref for ref, _ in self.calls]


@pytest.fixture()
def engine_rec(monkeypatch):
    from sb.kernel.workflow import engine

    rec = _EngineRecorder()
    monkeypatch.setattr(engine, "run", rec)
    return rec


@pytest.fixture()
def shown(monkeypatch):
    from sb.domain.setup import essential_steps

    seen = []

    async def fake_show(req, state):
        seen.append(state.index)

    monkeypatch.setattr(essential_steps, "_show_current", fake_show)
    return seen


@pytest.fixture()
def writes(monkeypatch):
    from sb.domain.setup import wizard

    out = []

    async def fake_write(req, subsystem, name, value):
        out.append((subsystem, name, value))
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wizard, "_write_setting", fake_write)
    return out


@pytest.fixture()
def refreshed(monkeypatch):
    from sb.domain.setup import wizard

    seen = []

    async def fake_refresh(req, params):
        seen.append(dict(params))
        return True

    monkeypatch.setattr(wizard, "_refresh_own_panel", fake_refresh)
    return seen


# --- the shipped data, verbatim spot-checks -------------------------------------------


def test_shipped_step_spine_and_defaults():
    from sb.domain.setup import essential_steps as es

    assert es.STEP_TITLES == (
        "What kind of server is this?", "Greet new members",
        "Set your moderators", "Block spam and bad links",
        "Choose a log channel", "Reward active members",
        "Set up a help desk", "Where can people use commands?")
    state = _state()
    assert state.total == 8
    # BlockSpamStep: everything on by default.
    assert state.spam_filters == {"spam_enabled", "invites_enabled",
                                  "caps_enabled", "mentions_enabled"}
    # LogChannelStep: message logging defaults OFF (the privacy note).
    assert state.log_activity == {"members_enabled", "roles_enabled"}
    assert state.cmd_mode == "all_channels"
    assert state.reward_xp_rate == "keep"
    assert state.reward_role_source == "recommended"


def test_shipped_cmd_access_choices_mirror_the_stored_modes():
    from sb.domain.setup.essential_steps import _CMD_ACCESS_CHOICES
    from sb.kernel.authority.channel_access import AccessMode

    assert [mode for mode, _, _ in _CMD_ACCESS_CHOICES] == [
        m.value for m in AccessMode]
    assert _CMD_ACCESS_CHOICES[2][1] == "Off for members — admins only"


def test_shipped_extras_menu_bytes():
    from sb.domain.setup.essential_steps import _EXTRAS

    assert _EXTRAS[0] == ("🏆", "Hall of Fame",
                          "pin the messages your members love the most",
                          "!starboard")
    assert len(_EXTRAS) == 7          # native giveaways deliberately absent


# --- panel roster ----------------------------------------------------------------------


def test_step_panels_carry_the_shipped_labels():
    from sb.domain.setup import essential_steps as es

    greet = es.greet_spec()
    assert greet.title == "👋 Greet new members"
    labels = {a.action_id: a.label for a in greet.actions}
    assert labels == {"greet_save": "Save & continue",
                      "greet_back": "Back", "greet_skip": "Skip greetings"}
    assert [s.placeholder for s in greet.selectors] == [
        "Where should the welcome message appear?",
        "Give newcomers a role (optional)…"]

    commands = es.commands_spec()
    skip = next(a for a in commands.actions if a.action_id == "cmd_skip")
    assert skip.label == "Skip — leave as is"


def test_resume_panel_pins_the_static_custom_id():
    from sb.domain.setup import essential_steps as es

    resume = es.resume_spec()
    (action,) = resume.actions
    assert action.custom_id_override == "essential_setup:resume"
    assert action.label == "Resume setup"
    assert action.emoji == "▶"


# --- navigation: back / skip / persist ---------------------------------------------------


def test_back_floors_at_zero_and_steps_back(shown):
    state = _state()
    state.index = 3
    run(_resolve("setup.essential_back")(_req()))
    assert state.index == 2
    state.index = 0
    run(_resolve("setup.essential_back")(_req()))
    assert state.index == 0
    assert shown == [2, 0]


def test_skip_records_the_step_title_and_advances(shown):
    state = _state()
    state.index = 3
    run(_resolve("setup.essential_spam_skip")(_req()))
    assert state.skipped == ["Block spam and bad links"]
    assert state.index == 4
    assert shown == [4]


def test_persist_progress_rides_the_k7_ops(engine_rec):
    from sb.domain.setup import essential_steps as es

    state = _state()
    state.index = 4
    run(es.persist_progress(_req(), state))
    assert engine_rec.calls == [("setup.set_essential_step", {"step": 4})]
    engine_rec.calls.clear()
    state.index = 8            # done → clear anchor + mark complete
    run(es.persist_progress(_req(), state))
    assert engine_rec.refs() == ["setup.clear_essential_anchor",
                                 "setup.mark_complete"]


# --- step 2 — greet ----------------------------------------------------------------------


def test_greet_save_requires_a_channel(writes):
    reply = run(_resolve("setup.essential_greet_save")(_req()))
    assert reply.outcome == BLOCKED
    # shipped guard copy, verbatim.
    assert reply.user_message == ("Pick a **channel** for the welcome "
                                  "message first.")
    assert writes == []


def test_greet_save_writes_scalars_and_bindings(writes, engine_rec, shown):
    state = _state()
    state.index = 1
    state.greet_channel_id = 1234
    state.greet_role_id = 555
    reply = run(_resolve("setup.essential_greet_save")(_req()))
    assert reply is None
    assert writes == [("welcome", "enabled", True),
                      ("welcome", "join_enabled", True)]
    # the channel/entry-role pair rides the audited bind lane (module
    # docstring: BindingSpec rows in this architecture).
    assert engine_rec.calls == [
        ("settings.bind", {"subsystem": "welcome", "name": "channel",
                           "kind": "channel", "resource_id": 1234}),
        ("settings.bind", {"subsystem": "welcome", "name": "entry_role",
                           "kind": "role", "resource_id": 555}),
    ]
    # the shipped applied line, verbatim.
    assert state.applied == [
        "Greetings on, posting in <#1234> · newcomers get <@&555>"]
    assert state.index == 2 and shown == [2]


def test_greet_save_failure_answers_the_shipped_copy(monkeypatch, shown):
    from sb.domain.setup import wizard

    async def boom(req, subsystem, name, value):
        raise RuntimeError("boom")

    monkeypatch.setattr(wizard, "_write_setting", boom)
    state = _state()
    state.greet_channel_id = 1234
    reply = run(_resolve("setup.essential_greet_save")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim.
    assert reply.user_message == ("Something went wrong turning on "
                                  "greetings — please try again.")
    assert shown == []


# --- step 3 — moderators -----------------------------------------------------------------


def test_mods_save_requires_a_role():
    reply = run(_resolve("setup.essential_mods_save")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "Pick a **moderator role** first."


def test_mods_save_writes_the_tier_grant_and_dm_flag(writes, shown):
    state = _state()
    state.index = 2
    state.mod_role_id = 777
    state.mod_dm_on = True
    reply = run(_resolve("setup.essential_mods_save")(_req()))
    assert reply is None
    # the ADR-008 vocabulary adaptation (module docstring).
    assert writes == [("governance", "moderator_tier_role_id", 777),
                      ("moderation", "dm_on_action", True)]
    assert state.applied == [
        "Moderator role set to <@&777> · members told why"]
    assert state.index == 3 and shown == [3]


def test_mods_dm_toggle_flips_state(refreshed):
    state = _state()
    assert state.mod_dm_on is True
    run(_resolve("setup.essential_mods_dm_toggle")(_req()))
    assert state.mod_dm_on is False
    assert len(refreshed) == 1


# --- step 4 — spam -----------------------------------------------------------------------


def test_spam_save_applies_the_ticked_filters(writes, shown):
    state = _state()
    state.index = 3
    state.spam_filters = {"spam_enabled", "mentions_enabled"}
    reply = run(_resolve("setup.essential_spam_save")(_req()))
    assert reply is None
    assert ("automod", "enabled", True) in writes
    assert ("automod", "spam_enabled", True) in writes
    assert ("automod", "invites_enabled", False) in writes
    assert ("automod", "caps_enabled", False) in writes
    assert ("automod", "mentions_enabled", True) in writes
    # the shipped applied line (labels lowercased, shipped order).
    assert state.applied == ["Spam protection on · repeated spam, "
                             "mass pings"]
    assert shown == [4]


# --- step 5 — log channels ---------------------------------------------------------------


def test_log_save_creates_missing_channels_and_binds(monkeypatch, writes,
                                                     engine_rec, shown):
    from sb.domain.setup import essential_steps as es

    created = []

    async def fake_create(req, name):
        created.append(name)
        return 9000 + len(created)

    monkeypatch.setattr(es, "_create_channel", fake_create)
    state = _state()
    state.index = 4
    reply = run(_resolve("setup.essential_log_save")(_req()))
    assert reply is None
    # both channels auto-created with the shipped default names.
    assert created == ["mod-log", "server-log"]
    assert ("logging", "enabled", True) in writes
    assert ("logging", "members_enabled", True) in writes
    assert ("logging", "roles_enabled", True) in writes
    assert ("logging", "messages_enabled", False) in writes
    assert engine_rec.calls == [
        ("settings.bind", {"subsystem": "logging", "name": "mod_channel",
                           "kind": "channel", "resource_id": 9001}),
        ("settings.bind", {"subsystem": "logging", "name": "events_channel",
                           "kind": "channel", "resource_id": 9002}),
    ]
    # the shipped summary line, verbatim shape.
    assert state.applied == [
        "Logging on · moderation → <#9001> · activity (members joining & "
        "leaving, role changes) → <#9002> · created #mod-log, #server-log"]
    assert shown == [5]


def test_log_save_create_failure_answers_the_shipped_copy(monkeypatch):
    from sb.domain.setup import essential_steps as es

    async def no_create(req, name):
        return None

    monkeypatch.setattr(es, "_create_channel", no_create)
    reply = run(_resolve("setup.essential_log_save")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim.
    assert reply.user_message == ("Couldn't make a channel — please pick "
                                  "existing ones instead.")


def test_log_names_modal_stashes_the_typed_names(refreshed):
    state = _state()
    run(_resolve("setup.essential_log_names")(
        _req(args={"mod_name": " audit-log ", "activity_name": ""})))
    assert state.log_mod_name == "audit-log"
    assert state.log_activity_name is None
    assert len(refreshed) == 1


# --- step 6 — rewards --------------------------------------------------------------------


def test_reward_next_without_rewards_applies_rate_and_finishes(
        writes, engine_rec, shown):
    state = _state()
    state.index = 5
    state.reward_xp_rate = "active"
    reply = run(_resolve("setup.essential_reward_next")(_req()))
    assert reply is None
    assert writes == [("xp", "xp_min", 20), ("xp", "xp_max", 40),
                      ("xp", "xp_cooldown", 30)]
    assert engine_rec.calls == []        # no threshold write
    # the shipped summary line, verbatim.
    assert state.applied == ["Rewards on · XP rate active"]
    assert state.index == 6 and shown == [6]


def test_reward_next_with_rewards_swaps_to_the_roles_screen(monkeypatch):
    from sb.domain.setup import wizard

    opened = []

    async def fake_open(req, panel_id, args=None):
        opened.append(panel_id)

    monkeypatch.setattr(wizard, "_open", fake_open)
    state = _state()
    state.index = 5
    state.reward_types = {"level"}
    reply = run(_resolve("setup.essential_reward_next")(_req()))
    assert reply is None
    assert state.reward_phase == "roles"
    assert opened == ["setup.essential_reward_role"]


def test_reward_save_existing_requires_a_pick():
    state = _state()
    state.reward_role_source = "existing"
    reply = run(_resolve("setup.essential_reward_save")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim.
    assert reply.user_message == ("Pick a role to grant, or switch to "
                                  "**Recommended** to make one.")


def test_reward_save_creates_the_role_and_folds_both_thresholds(
        monkeypatch, writes, engine_rec, shown):
    from sb.domain.setup import essential_steps as es

    async def fake_create_role(req, name):
        assert name == "Regular"       # the recommended default
        return 4242

    monkeypatch.setattr(es, "_create_role", fake_create_role)
    state = _state()
    state.index = 5
    state.reward_phase = "roles"
    state.reward_types = {"level", "time"}
    reply = run(_resolve("setup.essential_reward_save")(_req()))
    assert reply is None
    # ONE full-row threshold upsert carrying BOTH triggers (module
    # docstring: the K7 leg overwrites the whole row).
    assert engine_rec.calls == [("role.set_threshold", {
        "role_name": "Regular", "display_name": "Regular",
        "role_id": 4242, "days_required": 30, "level_required": 10,
        "xp_auto_assign": True})]
    # the shipped summary line, verbatim.
    assert state.applied == [
        "Rewards on · new role <@&4242> at level 10 / 30 days"]
    assert state.reward_phase == "config"
    assert state.index == 6 and shown == [6]


def test_reward_create_failure_answers_the_shipped_copy(monkeypatch):
    from sb.domain.setup import essential_steps as es

    async def no_role(req, name):
        return None

    monkeypatch.setattr(es, "_create_role", no_role)
    state = _state()
    state.reward_types = {"level"}
    reply = run(_resolve("setup.essential_reward_save")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim.
    assert reply.user_message == ("Couldn't make the role — please reuse "
                                  "an existing one instead.")


def test_reward_typed_name_flips_source_to_create(refreshed):
    state = _state()
    run(_resolve("setup.essential_reward_typed_name")(
        _req(args={"role_name": " Champion "})))
    assert state.reward_new_role_name == "Champion"
    assert state.reward_role_source == "create"


def test_reward_back_returns_to_the_config_screen(monkeypatch):
    from sb.domain.setup import wizard

    opened = []

    async def fake_open(req, panel_id, args=None):
        opened.append(panel_id)

    monkeypatch.setattr(wizard, "_open", fake_open)
    state = _state()
    state.index = 5
    state.reward_phase = "roles"
    run(_resolve("setup.essential_reward_back")(_req()))
    assert state.reward_phase == "config"
    assert state.index == 5             # Back on screen 2 stays in the step
    assert opened == ["setup.essential_reward"]


# --- step 7 — help desk ------------------------------------------------------------------


def test_helpdesk_save_requires_the_staff_role():
    reply = run(_resolve("setup.essential_helpdesk_save")(_req()))
    assert reply.outcome == BLOCKED
    # shipped guard copy, verbatim.
    assert reply.user_message == ("Pick a **staff role** first — it's who "
                                  "can see and answer requests.")


def test_helpdesk_save_rides_the_ticket_config_op(engine_rec, shown):
    state = _state()
    state.index = 6
    state.helpdesk_staff_role_id = 313
    state.helpdesk_log_channel_id = 414
    reply = run(_resolve("setup.essential_helpdesk_save")(_req()))
    assert reply is None
    assert engine_rec.calls == [("ticket.update_config", {
        "enabled": True, "staff_role_id": 313, "log_channel_id": 414})]
    assert state.applied == ["Help desk on, answered by <@&313>"]
    assert state.index == 7 and shown == [7]


# --- step 8 — command access ------------------------------------------------------------


def test_commands_save_guards_the_empty_allowlist():
    state = _state()
    state.cmd_mode = "selected_channels"
    reply = run(_resolve("setup.essential_commands_save")(_req()))
    assert reply.outcome == BLOCKED
    # shipped guard copy, verbatim.
    assert reply.user_message == ("Pick at least one channel where commands "
                                  "should work — or choose **Anywhere on "
                                  "the server**.")


def test_commands_save_writes_mode_and_allowlist(monkeypatch, shown):
    from sb.domain.platform import command_access

    calls = []

    async def fake_mode(ctx, *, mode):
        calls.append(("mode", mode))
        return SimpleNamespace(outcome=SUCCESS)

    async def fake_channels(ctx, *, channel_ids, allow_empty=False):
        calls.append(("channels", channel_ids))
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(command_access, "set_access_mode", fake_mode)
    monkeypatch.setattr(command_access, "set_access_channels", fake_channels)
    state = _state()
    state.index = 7
    state.cmd_mode = "selected_channels"
    state.cmd_channel_ids = [11, 22]
    reply = run(_resolve("setup.essential_commands_save")(_req()))
    assert reply is None
    assert calls == [("mode", "selected_channels"), ("channels", (11, 22))]
    assert state.applied == ["Commands limited to 2 channels"]
    assert state.index == 8 and shown == [8]


def test_commands_save_admins_only_line(monkeypatch, shown):
    from sb.domain.platform import command_access

    async def fake_mode(ctx, *, mode):
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(command_access, "set_access_mode", fake_mode)
    state = _state()
    state.index = 7
    state.cmd_mode = "disabled_except_bootstrap"
    run(_resolve("setup.essential_commands_save")(_req()))
    # the shipped summary line, verbatim.
    assert state.applied == [
        "Commands off for members (admins keep access)"]


# --- summary / extras / check-my-setup ----------------------------------------------------


def test_summary_render_recaps_applied_and_skipped():
    from sb.domain.setup import essential_steps as es

    state = _state()
    state.applied = ["Spam protection on"]
    state.skipped = ["Greet new members"]
    rendered = run(_resolve("setup.essential_summary_render")(
        es.summary_spec(), _ctx()))
    assert rendered.embed.title == "✅ Setup complete"
    assert rendered.embed.description == (
        "Here's what you switched on. You can change any of it later.")
    fields = {f[0]: f[1] for f in rendered.embed.fields}
    assert fields["Turned on"] == "• Spam protection on"
    assert fields["Skipped (you can do these later)"] == (
        "• Greet new members")
    assert "✨ **More to set up**" in fields["What next?"]


def test_summary_render_skipped_everything_branch():
    from sb.domain.setup import essential_steps as es

    rendered = run(_resolve("setup.essential_summary_render")(
        es.summary_spec(), _ctx()))
    # shipped copy, verbatim.
    assert rendered.embed.description == (
        "You skipped every step — nothing was changed. Run setup again "
        "any time.")


def test_summary_done_answers_the_terminal_copy():
    state = _state()
    reply = run(_resolve("setup.essential_summary_done")(_req()))
    assert reply.outcome == SUCCESS
    assert "nothing was changed" in reply.user_message
    state.applied = ["x"]
    reply = run(_resolve("setup.essential_summary_done")(_req()))
    assert reply.user_message.startswith("✅ Setup complete")


def test_extras_render_carries_the_shipped_fields():
    from sb.domain.setup import essential_steps as es

    rendered = run(_resolve("setup.essential_extras_render")(
        es.extras_spec(), _ctx()))
    fields = {f[0]: f[1] for f in rendered.embed.fields}
    assert fields["🏆 Hall of Fame"] == (
        "pin the messages your members love the most\nOpen with "
        "`!starboard`")
    assert len(fields) == 7


def test_check_setup_text_headlines(monkeypatch):
    from sb.domain.setup import essential_steps as es

    async def some(guild_id):
        return {"welcome", "automod"}

    monkeypatch.setattr(es, "_configured_subsystems", some)
    text = run(es.build_check_setup_text(99))
    assert "You've set up **2 of 6** essentials so far." in text
    assert "✅ Greeting new members" in text
    assert "➖ Help desk" in text
    assert "Want to finish the rest?" in text

    async def none(guild_id):
        return set()

    monkeypatch.setattr(es, "_configured_subsystems", none)
    text = run(es.build_check_setup_text(99))
    assert ("Nothing essential is set up yet — run setup to get started."
            in text)

    async def full(guild_id):
        return {k for k, _ in es._CHECK_ESSENTIALS}

    monkeypatch.setattr(es, "_configured_subsystems", full)
    text = run(es.build_check_setup_text(99))
    assert "🎉 Everything essential is set up — nice work!" in text
    assert "Want to finish the rest?" not in text


# --- the resume lane ----------------------------------------------------------------------


def test_resume_click_is_gated(monkeypatch):
    from sb.domain.setup import wizard

    async def deny(req):
        return False

    monkeypatch.setattr(wizard, "can_apply_setup", deny)
    reply = run(_resolve("setup.essential_resume_click")(_req()))
    assert reply.outcome == BLOCKED
    # shipped refusal copy, verbatim.
    assert reply.user_message == (
        "Only the server owner, an administrator, or a delegated setup "
        "admin can resume setup.")


def test_resume_click_rebuilds_at_the_saved_step(monkeypatch, shown):
    from sb.domain.setup import store, wizard

    async def allow(req):
        return True

    async def fake_session(guild_id, conn=None):
        return {"essential_step": 4}

    monkeypatch.setattr(wizard, "can_apply_setup", allow)
    monkeypatch.setattr(store, "get_session_row", fake_session)
    reply = run(_resolve("setup.essential_resume_click")(_req()))
    assert reply is None
    assert _state().index == 4
    assert shown == [4]


def test_resume_click_clamps_a_stale_step(monkeypatch, shown):
    from sb.domain.setup import store, wizard

    async def allow(req):
        return True

    async def fake_session(guild_id, conn=None):
        return {"essential_step": 99}

    monkeypatch.setattr(wizard, "can_apply_setup", allow)
    monkeypatch.setattr(store, "get_session_row", fake_session)
    run(_resolve("setup.essential_resume_click")(_req()))
    assert _state().index == 8          # clamped to total


def test_resume_render_names_the_next_step(monkeypatch):
    from sb.domain.setup import essential_steps as es
    from sb.domain.setup import store

    async def fake_session(guild_id, conn=None):
        return {"essential_step": 3}

    monkeypatch.setattr(store, "get_session_row", fake_session)
    rendered = run(_resolve("setup.essential_resume_render")(
        es.resume_spec(), _ctx()))
    assert rendered.embed.title == "⏸️ Setup paused"
    # shipped copy, verbatim (the 1-based step pointer).
    assert "pick up where you left off (step 4)" in rendered.embed.description
    assert "**Nothing you saved was lost**" in rendered.embed.description


# --- renderer state reads ------------------------------------------------------------------


def test_greet_render_carries_footer_and_picked_fields():
    from sb.domain.setup import essential_steps as es

    state = _state()
    state.greet_channel_id = 1234
    rendered = run(_resolve("setup.essential_greet_render")(
        es.greet_spec(), _ctx()))
    assert rendered.embed.footer == "Step 2 of 8"
    fields = {f[0]: f[1] for f in rendered.embed.fields}
    assert fields["Welcome message channel"] == "<#1234>"
    assert fields["Role for newcomers"] == "_none_"


def test_mods_render_patches_the_dm_toggle_label():
    from sb.domain.setup import essential_steps as es

    state = _state()
    state.mod_dm_on = False
    rendered = run(_resolve("setup.essential_mods_render")(
        es.mods_spec(), _ctx()))
    toggle = next(c for c in rendered.components
                  if c.custom_id.endswith("mods_dm_toggle"))
    assert toggle.label == "Tell members why: OFF"
    assert toggle.style == "secondary"


def test_reward_role_render_filters_by_source():
    from sb.domain.setup import essential_steps as es

    state = _state()
    state.reward_types = {"level"}
    # recommended: neither the name select nor the role select shows.
    rendered = run(_resolve("setup.essential_reward_role_render")(
        es.reward_role_spec(), _ctx()))
    ids = {c.custom_id.rsplit(".", 1)[-1] for c in rendered.components}
    assert "reward_name" not in ids and "reward_existing" not in ids
    state.reward_role_source = "create"
    rendered = run(_resolve("setup.essential_reward_role_render")(
        es.reward_role_spec(), _ctx()))
    ids = {c.custom_id.rsplit(".", 1)[-1] for c in rendered.components}
    assert "reward_name" in ids and "reward_type_name" in ids
    fields = {f[0]: f[1] for f in rendered.embed.fields}
    assert fields["Reward role"] == "a new **@Regular**"
    assert fields["Granted"] == "at level 10"


def test_commands_render_shows_the_allowlist_only_when_limiting():
    from sb.domain.setup import essential_steps as es

    state = _state()
    rendered = run(_resolve("setup.essential_commands_render")(
        es.commands_spec(), _ctx()))
    ids = {c.custom_id.rsplit(".", 1)[-1] for c in rendered.components}
    assert "cmd_channels" not in ids
    state.cmd_mode = "selected_channels"
    rendered = run(_resolve("setup.essential_commands_render")(
        es.commands_spec(), _ctx()))
    ids = {c.custom_id.rsplit(".", 1)[-1] for c in rendered.components}
    assert "cmd_channels" in ids
    fields = {f[0]: f[1] for f in rendered.embed.fields}
    assert fields["Allowed channels"] == "_pick at least one channel above_"


def test_reward_render_patches_the_next_label():
    from sb.domain.setup import essential_steps as es

    state = _state()
    rendered = run(_resolve("setup.essential_reward_render")(
        es.reward_spec(), _ctx()))
    button = next(c for c in rendered.components
                  if c.custom_id.endswith("reward_next"))
    assert button.label == "Save & continue"
    state.reward_types = {"time"}
    rendered = run(_resolve("setup.essential_reward_render")(
        es.reward_spec(), _ctx()))
    button = next(c for c in rendered.components
                  if c.custom_id.endswith("reward_next"))
    assert button.label == "Next"
