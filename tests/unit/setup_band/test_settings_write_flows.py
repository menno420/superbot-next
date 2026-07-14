"""The settings-write section flows (the settings-write slice —
sb/domain/setup/logging_presets.py · moderation.py · cleanup.py).

DB-free like the section-flows suite: the K7/K9 write seams are
monkeypatched at their module functions and the assertions pin the
ORACLE bytes the click paths carry (no golden drives a click on these
components — the panels.py module pin; oracle sources:
views/setup/sections/logging_presets.py, views/setup/sections/
moderation.py, views/setup/sections/cleanup.py,
services/cleanup_levels.py, services/cleanup_profiles.py,
utils/channel_classify.py)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run


@pytest.fixture(autouse=True)
def _fresh_state():
    import sb.manifest.governance as mgov
    import sb.manifest.moderation as mmod
    import sb.manifest.setup as m
    from sb.domain.setup import channels, cleanup, preset_select, wizard
    from sb.domain.setup import wizard_nav
    from sb.kernel import settings as ksettings

    m.ENSURE_REFS()
    # the composition root registers every manifest's settings at boot;
    # the staged payloads' persisted keys ride that registry (the
    # band2/band4 test precedent).
    for manifest in (mmod.MANIFEST, mgov.MANIFEST):
        try:
            ksettings.register_manifest_settings(manifest)
        except ValueError:
            pass    # already declared by an earlier test
    wizard.reset_wizard_state_for_tests()
    wizard_nav.reset_wizard_nav_state_for_tests()
    preset_select.reset_preset_state_for_tests()
    channels.reset_channels_state_for_tests()
    cleanup.reset_cleanup_state_for_tests()
    yield
    wizard.reset_wizard_state_for_tests()
    wizard_nav.reset_wizard_nav_state_for_tests()
    preset_select.reset_preset_state_for_tests()
    channels.reset_channels_state_for_tests()
    cleanup.reset_cleanup_state_for_tests()


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
    """Gate open + K7 engine no-op + count + refresh, the shared
    staging-path harness."""
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


# =======================================================================================
# logging_presets
# =======================================================================================


def test_logging_catalogue_is_the_shipped_data():
    from sb.domain.setup.logging_presets import _LOGGING_BINDINGS

    rows = [(b.subsystem, b.binding_name, b.intent, b.detailed_channel_name)
            for b in _LOGGING_BINDINGS]
    assert rows == [
        ("moderation", "mod_channel", "mod_logs", "mod-logs"),
        ("logging", "cleanup_channel", "general_logs", "cleanup-logs"),
        ("logging", "debug_channel", "general_logs", "debug-logs"),
        ("logging", "info_channel", "general_logs", "info-logs"),
        ("logging", "warning_channel", "general_logs", "warning-logs"),
        ("logging", "error_channel", "general_logs", "error-logs"),
        ("logging", "audit_channel", "general_logs", "audit-logs"),
        ("economy", "log_channel", "general_logs", "economy-logs"),
    ]


def test_preset_builders_carry_the_shipped_semantics():
    from sb.domain.setup.logging_presets import _LOGGING_BINDINGS, preset_ops

    single = preset_ops("single", _LOGGING_BINDINGS)
    assert len(single) == 8
    assert {op.payload["resource_name"] for op in single} == {"superbot-logs"}
    assert all(op.op_kind == "create_channel" for op in single)

    balanced = preset_ops("balanced", _LOGGING_BINDINGS)
    names = {(op.subsystem, op.payload["name"]): op.payload["resource_name"]
             for op in balanced}
    assert names[("moderation", "mod_channel")] == "mod-logs"
    assert names[("logging", "audit_channel")] == "bot-logs"
    assert names[("economy", "log_channel")] == "bot-logs"

    detailed = preset_ops("detailed", _LOGGING_BINDINGS)
    assert ({op.payload["resource_name"] for op in detailed}
            == {b.detailed_channel_name for b in _LOGGING_BINDINGS})
    # the shipped per-op label tail rides the label_body.
    assert any(op.label_body == "[detailed] logging.audit_channel "
                                "→ #audit-logs" for op in detailed)


def test_recommended_logging_ops_default_to_balanced(monkeypatch):
    from sb.domain.setup import logging_presets as lp

    monkeypatch.setattr(lp, "supported_bindings",
                        lambda: lp._LOGGING_BINDINGS)
    ops = run(lp.recommended_logging_ops(99))
    assert {op.payload["resource_name"] for op in ops} == {"bot-logs",
                                                           "mod-logs"}


def test_infer_current_preset_reads_the_recommended_rows():
    from sb.domain.setup.logging_presets import infer_current_preset

    def _row(name, label="[recommended:logging_presets] x"):
        return SimpleNamespace(label=label, op_kind="create_channel",
                               payload={"resource_name": name})

    assert infer_current_preset([]) is None
    assert infer_current_preset([_row("superbot-logs")]) == "single"
    assert infer_current_preset(
        [_row("bot-logs"), _row("mod-logs")]) == "balanced"
    assert infer_current_preset(
        [_row("a"), _row("b"), _row("c")]) == "detailed"
    # custom rows never drive the highlight.
    assert infer_current_preset(
        [_row("bot-logs", label="[channels] x")]) is None


def test_logging_presets_embed_is_the_shipped_bytes():
    from sb.domain.setup.logging_presets import (
        _LOGGING_BINDINGS, build_logging_presets_embed,
    )

    embed = build_logging_presets_embed(_LOGGING_BINDINGS,
                                        current_preset="balanced")
    assert embed.title == "📜 Logging presets"
    assert embed.description == (
        "Pick how SuperBot routes its log channels.  Every preset "
        "stages **`create_channel`** operations only — Final "
        "Review confirms before any channel is touched.  Switching "
        "presets cleanly removes the prior pick's staged rows.")
    names = [f[0] for f in embed.fields]
    assert names == ["Single", "✅ Balanced", "Detailed", "Custom",
                     "🔒 Privacy — server event logging"]
    assert embed.fields[1][1] == (
        "`#bot-logs` for general logs (**7** slot(s)) and "
        "`#mod-logs` for moderation (**1** slot(s)).")
    assert "staff can see the content of messages members" in \
        embed.fields[4][1]
    assert embed.footer == (
        "Nothing applies until Final Review.  Switching presets "
        "replaces the prior pick — your staged custom bindings "
        "stay intact.")


def test_logging_preset_click_gate_refusal_is_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    reply = run(_resolve("setup.logging_preset_balanced")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (logging_presets._gate_apply).
    assert reply.user_message == (
        "Only the server owner or a delegated setup admin can stage "
        "logging presets.  Ask the owner to grant you `/setup-delegate`.")


def test_logging_preset_click_stages_and_answers(monkeypatch):
    from sb.domain.setup import logging_presets as lp

    _patch_write_seams(monkeypatch)
    monkeypatch.setattr(lp, "supported_bindings",
                        lambda: lp._LOGGING_BINDINGS)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)

    reply = run(_resolve("setup.logging_preset_balanced")(_req()))
    assert reply.outcome == SUCCESS
    # shipped confirmation, verbatim.
    assert reply.user_message == (
        "✅ Staged **8 operations** for the **balanced** preset.  "
        "Open Final Review to apply.")
    assert len(store.added) == 8
    _did, first = store.added[0]
    assert first.op_kind == "create_channel"
    assert first.label == ("[recommended:logging_presets] [balanced] "
                           "moderation.mod_channel → #mod-logs")
    assert first.payload == {
        "subsystem": "moderation", "name": "mod_channel",
        "kind": "channel", "resource_name": "mod-logs",
        "resource_mode": "create"}


def test_logging_preset_swap_replaces_the_prior_pick(monkeypatch):
    from sb.domain.setup import logging_presets as lp

    _patch_write_seams(monkeypatch)
    monkeypatch.setattr(lp, "supported_bindings",
                        lambda: lp._LOGGING_BINDINGS)
    prior = SimpleNamespace(
        label=("[recommended:logging_presets] [single] "
               "logging.audit_channel → #superbot-logs"),
        op_kind="create_channel", subsystem="logging",
        payload={"subsystem": "logging", "name": "audit_channel",
                 "resource_name": "superbot-logs"},
        op_seq=3)
    store = _FakeStore([SimpleNamespace(draft_id="d-1",
                                        operations=(prior,))])
    _patch_store(monkeypatch, store)
    reply = run(_resolve("setup.logging_preset_detailed")(_req()))
    assert reply.outcome == SUCCESS
    # the prior recommended row dropped (switching presets cleanly
    # removes the prior pick's staged rows).
    assert ("d-1", 3) in store.removed
    assert len(store.added) == 8


def test_logging_preset_no_bindings_answers_the_shipped_copy(monkeypatch):
    from sb.domain.setup import logging_presets as lp, wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    monkeypatch.setattr(lp, "supported_bindings", lambda: ())
    reply = run(_resolve("setup.logging_preset_single")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == ("No logging bindings are available in "
                                  "this runtime.")


def test_logging_custom_opens_the_channels_detail(monkeypatch):
    from sb.kernel.panels import engine as panels_engine

    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    reply = run(_resolve("setup.logging_preset_custom")(_req()))
    assert reply is None
    assert opened == ["setup.channels_detail"]


def test_logging_cancel_answers_the_close():
    reply = run(_resolve("setup.logging_preset_cancel")(_req()))
    assert reply.outcome == SUCCESS
    assert reply.user_message == "Preset picker closed — draft unchanged."


def test_open_section_logging_presets_lands_on_the_card(monkeypatch):
    from sb.domain.setup import section_card, wizard
    from sb.kernel.panels import engine as panels_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    marked = []

    async def fake_mark(req, step):
        marked.append(step)

    monkeypatch.setattr(section_card, "mark_step_in_progress", fake_mark)
    reply = run(_resolve("setup.open_section_logging_presets")(_req()))
    assert reply is None
    assert opened == ["setup.section_logging_presets"]
    assert marked == ["logging_presets"]


def test_logging_picker_renderer_highlights_and_gates_back_step(monkeypatch):
    from sb.domain.setup import logging_presets as lp
    from sb.domain.setup import section_card, wizard_nav

    async def fake_ops(guild_id):
        return [(None, SimpleNamespace(
            label=("[recommended:logging_presets] [single] x"),
            op_kind="create_channel",
            payload={"resource_name": "superbot-logs"}))]

    monkeypatch.setattr(section_card, "guild_ops", fake_ops)
    spec = lp.logging_picker_spec()
    rendered = run(lp._render_logging_picker(spec, _ctx()))
    by_id = {c.custom_id: c for c in rendered.components}
    # the shipped highlight repaint (success when picked)…
    assert by_id["setup_logging_preset:single"].style == "success"
    assert by_id["setup_logging_preset:balanced"].style == "secondary"
    # …and the back-step button only rides the wizard-native path.
    assert not any(c.custom_id.endswith(".logging_back_step")
                   for c in rendered.components)
    wizard_nav.mark_detail_from_wizard(99, 42)
    rendered = run(lp._render_logging_picker(spec, _ctx()))
    assert any(c.custom_id.endswith(".logging_back_step")
               for c in rendered.components)


def test_create_channel_rows_reach_the_created_resources_callout():
    """final_review._created_resource_names is reachable now: the staged
    create_channel payload carries resource_name (the oracle
    ➕-new-resources call-out)."""
    from sb.domain.setup.final_review import build_final_review_embed

    op = SimpleNamespace(
        op_kind="create_channel", subsystem="logging",
        payload={"subsystem": "logging", "name": "audit_channel",
                 "resource_name": "bot-logs"},
        label="[recommended:logging_presets] x")
    embed = build_final_review_embed([op])
    names = [f[0] for f in embed.fields]
    assert "➕ 1 new resource(s) will be created" in names
    idx = names.index("➕ 1 new resource(s) will be created")
    assert "`bot-logs`" in embed.fields[idx][1]


# =======================================================================================
# moderation
# =======================================================================================


def test_moderation_embed_is_the_shipped_bytes():
    from sb.domain.setup.moderation import build_moderation_embed

    embed = build_moderation_embed()
    assert embed.title == "🛡️ Moderation"
    assert embed.description == (
        "Configure how warns, timeouts, kicks, and bans behave.  Each "
        "pick stages a `set_setting` operation — **Final review** "
        "applies them all through the audited settings pipeline.  "
        "Everything else (DM template, ban message-purge, public log, "
        "…) lives in `!settings → Moderation`.")
    assert [f[0] for f in embed.fields] == ["What you can set here"]
    assert embed.footer == ("Recommended: DM on action + require a reason "
                            "(safe, transparent).")
    # the Detected field renders when current values are readable.
    embed = build_moderation_embed(dm_on_action=True, require_reason=False,
                                   warn_escalation_action=None,
                                   moderator_role_id=555)
    assert [f[0] for f in embed.fields] == ["What you can set here",
                                            "Detected"]
    assert embed.fields[1][1] == (
        "• DM on action: **on**\n"
        "• Require a reason: **off**\n"
        "• Warn escalation: **timeout**\n"
        "• Moderator role: `555`")


def test_moderation_dm_pick_stages_and_answers(monkeypatch):
    _patch_write_seams(monkeypatch)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)
    reply = run(_resolve("setup.moderation_dm_pick")(
        _req(args={"values": ["true"]})))
    assert reply.outcome == SUCCESS
    # shipped confirmation, verbatim (moderation._stage_setting).
    assert reply.user_message == (
        "✅ Staged for Final review: `moderation.dm_on_action = True`.  "
        "Pending operations: **1**.")
    _did, added = store.added[0]
    assert added.op_kind == "set_setting"
    assert added.payload == {
        "subsystem": "moderation", "name": "dm_on_action",
        "key": "moderation_dm_on_action", "value": "true"}
    assert added.label == ("[moderation] moderation.dm_on_action = True")


def test_moderation_reason_off_serializes_false(monkeypatch):
    _patch_write_seams(monkeypatch)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)
    reply = run(_resolve("setup.moderation_reason_pick")(
        _req(args={"values": ["false"]})))
    assert reply.outcome == SUCCESS
    _did, added = store.added[0]
    assert added.payload["key"] == "moderation_require_reason"
    assert added.payload["value"] == "false"
    assert added.label == "[moderation] moderation.require_reason = False"


def test_moderation_escalation_pick_carries_the_vocabulary(monkeypatch):
    _patch_write_seams(monkeypatch)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)
    reply = run(_resolve("setup.moderation_escalation_pick")(
        _req(args={"values": ["kick"]})))
    assert reply.outcome == SUCCESS
    _did, added = store.added[0]
    assert added.payload == {
        "subsystem": "moderation", "name": "warn_escalation_action",
        "key": "moderation_warn_escalation_action", "value": "kick"}
    # the shipped vocabulary is closed.
    reply = run(_resolve("setup.moderation_escalation_pick")(
        _req(args={"values": ["mute"]})))
    assert reply.outcome == BLOCKED


def test_moderation_role_pick_lands_on_the_governance_tier_grant(
        monkeypatch):
    """The ADR-008 divergence, ledgered: the write rides
    governance.moderator_tier_role_id; the label keeps the oracle's
    moderation.moderator_role spelling."""
    _patch_write_seams(monkeypatch)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)
    reply = run(_resolve("setup.moderation_role_pick")(
        _req(args={"values": ["424242"]})))
    assert reply.outcome == SUCCESS
    _did, added = store.added[0]
    assert added.payload == {
        "subsystem": "governance", "name": "moderator_tier_role_id",
        "key": "moderator_tier_role_id", "value": "424242"}
    assert added.label == "[moderation] moderation.moderator_role = @424242"


def test_moderation_pick_gate_refusal_is_the_card_copy(monkeypatch):
    from sb.domain.setup import section_card, wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    reply = run(_resolve("setup.moderation_dm_pick")(
        _req(args={"values": ["true"]})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == section_card.GATE_MSG_CARD


def test_recommended_moderation_ops_are_the_safe_baseline():
    from sb.domain.setup.moderation import recommended_moderation_ops

    ops = run(recommended_moderation_ops(99))
    assert [(op.payload["name"], op.payload["value"]) for op in ops] == [
        ("dm_on_action", "true"), ("require_reason", "true")]
    assert all(op.op_kind == "set_setting" for op in ops)
    assert ops[0].label_body == "moderation.dm_on_action = True"


def test_moderation_escalation_options_are_the_shipped_bytes():
    from sb.spec.refs import ProviderRef, resolve

    options = run(resolve(ProviderRef("setup.moderation_escalation_options"))
                  (_ctx()))
    assert [o["value"] for o in options] == ["timeout", "kick", "ban",
                                             "none"]
    assert options[0]["description"] == (
        "Auto-timeout, then reset the count (today's default).")
    assert options[3]["description"] == (
        "Disable automatic escalation — warnings only accumulate.")


def test_moderation_renderer_gates_the_back_step(monkeypatch):
    from sb.domain.setup import moderation as mod
    from sb.domain.setup import wizard_nav

    async def fake_state(guild_id):
        return (True, None, "timeout", None)

    monkeypatch.setattr(mod, "read_current_state", fake_state)
    spec = mod.moderation_detail_spec()
    rendered = run(mod._render_moderation_detail(spec, _ctx()))
    assert not any(c.custom_id.endswith(".mod_back_step")
                   for c in rendered.components)
    # the Detected field rode the embed.
    assert rendered.embed.fields[1][0] == "Detected"
    wizard_nav.mark_detail_from_wizard(99, 42)
    rendered = run(mod._render_moderation_detail(spec, _ctx()))
    assert any(c.custom_id.endswith(".mod_back_step")
               for c in rendered.components)


# =======================================================================================
# cleanup
# =======================================================================================


def test_cleanup_levels_are_the_shipped_table():
    from sb.domain.setup.cleanup import LEVELS

    assert LEVELS == {
        "Off": {"delete_invalid_commands": False,
                "delete_failed_commands": False,
                "delete_after_seconds": 0},
        "Light": {"delete_invalid_commands": True,
                  "delete_failed_commands": False,
                  "delete_after_seconds": 10},
        "Standard": {"delete_invalid_commands": True,
                     "delete_failed_commands": True,
                     "delete_after_seconds": 5},
        "Strict": {"delete_invalid_commands": True,
                   "delete_failed_commands": True,
                   "delete_after_seconds": 2},
    }


def test_cleanup_scope_id_convention_is_the_shipped_helper():
    from sb.domain.setup.cleanup import cleanup_scope_id

    # a guild-default row keys at guild_id, never 0.
    assert cleanup_scope_id("guild", 99, None) == 99
    assert cleanup_scope_id("channel", 99, 123) == 123
    with pytest.raises(ValueError):
        cleanup_scope_id("category", 99, None)


def test_classify_channel_name_carries_the_consumed_tags():
    from sb.domain.setup.cleanup import classify_channel_name

    assert "likely_bot_cmd" in classify_channel_name("bot-commands")
    assert "likely_bot_cmd" in classify_channel_name("cmds")
    assert "likely_mod" in classify_channel_name("staff")
    assert "likely_admin" in classify_channel_name("admin-chat")
    assert "likely_mod_log" in classify_channel_name("mod-logs")
    assert classify_channel_name("general") == ()
    assert classify_channel_name("") == ()


def test_cleanup_embed_is_the_shipped_bytes():
    from sb.domain.setup.cleanup import build_cleanup_embed

    embed = build_cleanup_embed()
    assert embed.title == "🧹 Cleanup inheritance"
    assert "thread → channel → category → server → default" in \
        embed.description
    assert embed.fields[0][0] == "Levels"
    assert embed.fields[0][1] == (
        "• **Off** — disabled (after=0s)\n"
        "• **Light** — delete invalid commands only (after=10s)\n"
        "• **Standard** — delete invalid + failed (after=5s)\n"
        "• **Strict** — delete invalid + failed (after=2s)")
    assert embed.footer == ("Pick a scope below, then pick a level for "
                            "that scope.")


def test_cleanup_level_options_are_the_shipped_bytes():
    from sb.spec.refs import ProviderRef, resolve

    options = run(resolve(ProviderRef("setup.cleanup_level_options"))
                  (_ctx()))
    assert [o["label"] for o in options] == ["Off", "Light", "Standard",
                                             "Strict"]
    assert options[1]["description"] == "after=10s · invalid=yes · failed=no"
    assert options[3]["description"] == "after=2s · invalid=yes · failed=yes"


def test_set_cleanup_policy_op_kind_binds_the_governance_op():
    from sb.kernel.draft.registry import OP_KINDS

    binding = OP_KINDS.get("set_cleanup_policy")
    assert binding is not None
    assert binding.workflow_ref.name == "governance.set_cleanup"
    assert binding.is_resource_create is False


def test_cleanup_guild_level_pick_stages_and_answers(monkeypatch):
    _patch_write_seams(monkeypatch)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)
    run(_resolve("setup.cleanup_scope_pick")(
        _req(args={"values": ["guild"]})))
    reply = run(_resolve("setup.cleanup_level_pick")(
        _req(args={"values": ["Light"]})))
    assert reply.outcome == SUCCESS
    # shipped confirmation, verbatim (cleanup._stage_cleanup_policy).
    assert reply.user_message == (
        "✅ Staged for Final review: `cleanup.guild(guild) = Light`.  "
        "Pending operations: **1**.")
    _did, added = store.added[0]
    assert added.op_kind == "set_cleanup_policy"
    # the level → columns translation happened at stage time; the
    # guild-default row keys at guild_id (the cleanup_scope_id helper).
    assert added.payload == {
        "name": "guild:99", "scope_type": "guild", "scope_id": 99,
        "delete_invalid_commands": True, "delete_failed_commands": False,
        "delete_after_seconds": 10, "level": "Light",
        "target_name": "guild"}
    assert added.label == "[cleanup] cleanup.guild(guild) = Light"


def test_cleanup_channel_override_flow_stages_the_target(monkeypatch):
    from sb.domain.setup.plan import GuildChannel, install_channel_index

    async def index(guild_id):
        return (GuildChannel(id=555, name="bot-commands"),)

    install_channel_index(index)
    _patch_write_seams(monkeypatch)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)
    run(_resolve("setup.cleanup_scope_pick")(
        _req(args={"values": ["channel"]})))
    run(_resolve("setup.cleanup_target_pick")(
        _req(args={"values": ["555"]})))
    reply = run(_resolve("setup.cleanup_level_pick")(
        _req(args={"values": ["Strict"]})))
    assert reply.outcome == SUCCESS
    assert reply.user_message == (
        "✅ Staged for Final review: `cleanup.channel(#bot-commands) = "
        "Strict`.  Pending operations: **1**.")
    _did, added = store.added[0]
    assert added.payload["scope_type"] == "channel"
    assert added.payload["scope_id"] == 555
    assert added.payload["delete_after_seconds"] == 2


def test_cleanup_unknown_level_answers_the_shipped_copy(monkeypatch):
    _patch_write_seams(monkeypatch)
    run(_resolve("setup.cleanup_scope_pick")(
        _req(args={"values": ["guild"]})))
    reply = run(_resolve("setup.cleanup_level_pick")(
        _req(args={"values": ["Nuclear"]})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "Unknown level `Nuclear`."


def test_cleanup_level_without_scope_answers_the_footer_instruction():
    reply = run(_resolve("setup.cleanup_level_pick")(
        _req(args={"values": ["Light"]})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == ("Pick a scope below, then pick a level "
                                  "for that scope.")


def test_cleanup_profiles_carry_the_shipped_catalogue():
    from sb.domain.setup.cleanup import PROFILES

    assert list(PROFILES) == ["off", "light", "standard", "strict",
                              "silent_bot", "moderation_safe"]
    assert PROFILES["silent_bot"].description == (
        "Strict cleanup on detected bot/command channels, Light "
        "everywhere else. Keeps command spam out of bot channels "
        "without hiding evidence elsewhere.")
    assert PROFILES["moderation_safe"].description == (
        "Standard cleanup everywhere, but Off on detected mod / "
        "admin / staff channels so moderation context and evidence "
        "are preserved.")


def test_silent_bot_profile_targets_detected_bot_channels(monkeypatch):
    from sb.domain.setup.cleanup import PROFILES, profile_ops
    from sb.domain.setup.plan import GuildChannel, install_channel_index

    async def index(guild_id):
        return (GuildChannel(id=1, name="bot-commands"),
                GuildChannel(id=2, name="general"))

    install_channel_index(index)
    ops = run(profile_ops(PROFILES["silent_bot"], 99))
    assert [(op.payload["scope_type"], op.payload["level"]) for op in ops] \
        == [("guild", "Light"), ("channel", "Strict")]
    assert ops[1].payload["scope_id"] == 1
    ops = run(profile_ops(PROFILES["moderation_safe"], 99))
    assert [(op.payload["scope_type"], op.payload["level"])
            for op in ops] == [("guild", "Standard")]


def test_cleanup_profile_pick_stages_and_answers(monkeypatch):
    _patch_write_seams(monkeypatch, pending=1)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)
    reply = run(_resolve("setup.cleanup_profile_pick")(
        _req(args={"values": ["light"]})))
    assert reply.outcome == SUCCESS
    # shipped summary, verbatim (_ProfileSelect.callback).
    assert reply.user_message == (
        "✅ Staged **1 operation** for profile `Light`. "
        "Pending operations: **1**.")
    _did, added = store.added[0]
    assert added.label.startswith("[cleanup] [profile:light] cleanup.guild(")
    assert added.payload["level"] == "Light"


def test_cleanup_profile_unknown_answers_the_shipped_copy(monkeypatch):
    _patch_write_seams(monkeypatch)
    reply = run(_resolve("setup.cleanup_profile_pick")(
        _req(args={"values": ["nope"]})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "Unknown cleanup profile `nope`."


def test_recommended_cleanup_ops_default_to_light_guild_scope():
    from sb.domain.setup.cleanup import recommended_cleanup_ops

    ops = run(recommended_cleanup_ops(99))
    assert len(ops) == 1
    assert ops[0].payload["scope_type"] == "guild"
    assert ops[0].payload["scope_id"] == 99
    assert ops[0].payload["level"] == "Light"


def test_cleanup_renderer_reveals_controls_stepwise(monkeypatch):
    from sb.domain.setup import cleanup as cl

    spec = cl.cleanup_detail_spec()

    def leaves(rendered):
        return {c.custom_id.removeprefix(f"{spec.panel_id}.")
                for c in rendered.components}

    # nothing picked: scope + profile only.
    rendered = run(cl._render_cleanup_detail(spec, _ctx()))
    assert leaves(rendered) == {"cleanup_scope", "cleanup_section_profile"}
    # guild scope: the level select reveals with the shipped placeholder.
    cl._PICKED_SCOPE["99:42"] = "guild"
    rendered = run(cl._render_cleanup_detail(spec, _ctx()))
    by_leaf = {c.custom_id.removeprefix(f"{spec.panel_id}."): c
               for c in rendered.components}
    assert by_leaf["cleanup_level"].placeholder == (
        "Pick the server-wide level…")
    assert "cleanup_target" not in by_leaf
    # category scope: target picker first, then the per-target level.
    cl._PICKED_SCOPE["99:42"] = "category"
    cl._PICKED_TARGET.pop("99:42", None)
    rendered = run(cl._render_cleanup_detail(spec, _ctx()))
    by_leaf = {c.custom_id.removeprefix(f"{spec.panel_id}."): c
               for c in rendered.components}
    assert by_leaf["cleanup_target"].placeholder == "Pick a category…"
    assert "cleanup_level" not in by_leaf
    cl._PICKED_TARGET["99:42"] = (7, "events")
    rendered = run(cl._render_cleanup_detail(spec, _ctx()))
    by_leaf = {c.custom_id.removeprefix(f"{spec.panel_id}."): c
               for c in rendered.components}
    assert by_leaf["cleanup_level"].placeholder == (
        "Level for category events…")


def test_final_review_short_label_carries_the_cleanup_bytes():
    from sb.domain.setup.final_review import _short_label

    op = SimpleNamespace(
        op_kind="set_cleanup_policy", subsystem="cleanup",
        payload={"scope_type": "guild", "target_name": "guild",
                 "level": "Light"})
    assert _short_label(op) == "cleanup.guild(guild) = Light"


# =======================================================================================
# the flipped hub routes + the wizard truth
# =======================================================================================


def test_live_sections_include_the_settings_write_slugs():
    from sb.spec.refs import HandlerRef, is_registered

    for slug in ("logging_presets", "moderation", "cleanup"):
        assert is_registered(HandlerRef(f"setup.open_section_{slug}"))


def test_section_cards_registered_for_the_three_slugs():
    from sb.domain.setup import section_card

    for slug in ("logging_presets", "moderation", "cleanup"):
        spec = section_card.card_spec_for(slug)
        assert [a.custom_id_override for a in spec.actions] == [
            f"setup_card:{slug}:apply_recommended",
            f"setup_card:{slug}:customize",
            f"setup_card:{slug}:skip",
            f"setup_card:{slug}:hub"]
        assert section_card.recommended_builder(slug) is not None
        assert section_card.customize_panel(slug) is not None
