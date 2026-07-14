"""The CLEANUP panels (the shipped Cleanup Hub + Prohibited Words Manager
as declarative panels): the golden-pinned spec bytes, the compile fences,
the manifest surface, the renderer overrides (footer literals + the
inline Prohibited Words count field), the verbatim persistent
``cleanup:*`` custom_ids, the run-minted words-manager ids, the live
button wiring (the 2026-07-13 curation rework: word add/remove G-10
modals → the audited command twins, Scan History → the live scan,
word-menu refresh → REFRESH_PANEL, hub Logging Status → the ported
``logging.hub``), and the ``!cleanuphistory`` scan handler over the
history-reader port.

Oracle: menno420/superbot disbot/cogs/cleanup/panel.py
(CleanupPanelView) + disbot/cogs/cleanup_cog.py (the word-menu view +
``cleanup_history``); parity/goldens/cleanup/ (sweep_cleanup,
sweep_cleanuphistory, sweep_wordmenu) pins every wire byte.
"""

from __future__ import annotations

import asyncio

run = asyncio.run


# --- the hub spec: golden-pinned bytes -------------------------------------------------


def test_hub_spec_shape_matches_the_golden():
    from sb.domain.cleanup.panels import cleanup_hub_spec
    from sb.spec.panels import ActionStyle, Audience, FooterMode

    spec = cleanup_hub_spec()
    assert spec.panel_id == "cleanup.hub"
    assert spec.subsystem == "cleanup"
    assert spec.title == "🧹 Cleanup Hub"
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "red"        # the shipped ERROR_COLOR
    assert spec.frame.footer_mode is FooterMode.NONE
    # override-pinned persistent ids under session_lifecycle: nothing is
    # run-minted, no panel_anchors row (the golden's db_delta carries none).
    assert spec.session_lifecycle is True
    # the shipped STANDARD nav row: 📚 Help + ↩ Moderation.
    assert spec.navigation.show_help is True
    assert spec.navigation.home_hub == "moderation"

    by_id = {a.action_id: a for a in spec.actions}
    # emoji IN the labels (no separate emoji field in the golden); the
    # shipped persistent custom_id survives verbatim. K1: bare "refresh"
    # is treasury's claim, so the action_id is cl_refresh under the
    # verbatim wire override (the sm_refresh precedent).
    expected = {
        "words": ("🔤 Prohibited Words", ActionStyle.PRIMARY, "cleanup:words"),
        "logging": ("📝 Logging Status", ActionStyle.SECONDARY,
                    "cleanup:logging"),
        "settings": ("⚙️ Settings", ActionStyle.SECONDARY, "cleanup:settings"),
        "policies": ("🧹 Cleanup Policies", ActionStyle.PRIMARY,
                     "cleanup:policies"),
        "cl_refresh": ("🔄 Refresh", ActionStyle.SECONDARY, "cleanup:refresh"),
    }
    assert set(by_id) == set(expected)
    for aid, (label, style, custom_id) in expected.items():
        assert by_id[aid].label == label, aid
        assert by_id[aid].style is style, aid
        assert by_id[aid].custom_id_override == custom_id, aid
        assert by_id[aid].emoji == "", aid
        assert by_id[aid].audience_tier == "administrator", aid

    assert spec.layout.pages[0].rows == (
        ("words", "logging", "settings", "policies"),
        ("cl_refresh",),
    )

    # 📝 Logging Status routes to the PORTED logging.hub (curation
    # rework); ⚙️ Settings routes to the PORTED cleanup.settings page
    # (the 2026-07-13 residue port); 🧹 Cleanup Policies routes to the
    # PORTED cleanup.policies diagnostics view (the cleanup-policy
    # slice — the LAST cleanup pending retired).
    from sb.spec.refs import PanelRef

    assert by_id["logging"].handler == PanelRef("logging.hub")
    assert by_id["settings"].handler == PanelRef("cleanup.settings")
    assert by_id["policies"].handler == PanelRef("cleanup.policies")


def test_hub_registers_and_renders_the_golden_bytes():
    from sb.domain.cleanup.panels import cleanup_hub_spec
    from sb.kernel.panels.compile import check_panel
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.kernel.panels.render import HUB_NAV_LABELS
    from sb.spec.panels import Audience
    from sb.spec.refs import resolve as resolve_ref

    spec = cleanup_hub_spec()
    check_panel(spec)                              # the compile fences hold

    from types import SimpleNamespace

    ctx = PanelContext(
        bot=None, guild_id=1, actor=SimpleNamespace(user_id=42), channel_id=2,
        origin=PanelOrigin.INTERACTION, audience=Audience.INVOKER)
    rendered = run(resolve_ref(spec.renderer_override)(spec, ctx))

    # the override's two adjustments: the shipped footer literal + the
    # inline Prohibited Words count field (everything else declared).
    assert rendered.embed.footer == (
        "Read-only summary. Use the buttons below to manage policies.")
    fields = rendered.embed.fields
    assert fields[0][0] == "Prohibited Words"
    # db-free environment: the live word count degrades to the shipped
    # empty state — exactly the golden's byte (the capture guild had no
    # DB words when `!cleanup` swept).
    assert fields[0][1] == "_None configured_"
    assert fields[0][2] is True                    # inline (the shipped shape)
    assert fields[1][0] == "Auto-Delete"
    assert len(fields[1]) == 2                     # inline=False (2-tuple)

    # the standard nav row renders the shipped ids + the hub-named label.
    nav = {c.custom_id: c.label for c in rendered.components if c.row == 4}
    assert nav == {"nav:help": "📚 Help", "nav:hub:moderation": "↩ Moderation"}
    assert HUB_NAV_LABELS["moderation"] == "Moderation"

    # declared components keep their verbatim overrides.
    declared = [c.custom_id for c in rendered.components if c.row < 4]
    assert declared == ["cleanup:words", "cleanup:logging", "cleanup:settings",
                        "cleanup:policies", "cleanup:refresh"]


# --- the words-manager spec: golden-pinned bytes ---------------------------------------


def test_words_spec_shape_matches_the_golden():
    from sb.domain.cleanup.panels import cleanup_words_spec
    from sb.kernel.panels.compile import check_panel
    from sb.spec.panels import ActionStyle, Audience, FooterMode

    spec = cleanup_words_spec()
    check_panel(spec)
    assert spec.panel_id == "cleanup.words"
    assert spec.title == "🔤 Prohibited Words Manager"
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "red"         # the shipped ADMIN_COLOR
    assert spec.frame.footer_mode is FooterMode.NONE
    # the shipped session view minted discord.py auto-ids — no overrides
    # (the golden pins <cid:1>..<cid:5>); no nav row (the never-strand
    # fence takes the session-view exemption).
    assert spec.session_lifecycle is True
    assert spec.navigation.show_help is False
    assert spec.navigation.show_home is False
    assert all(a.custom_id_override == "" for a in spec.actions)

    by_id = {a.action_id: a for a in spec.actions}
    expected = {
        "word_add": ("➕ Add Word", ActionStyle.SUCCESS),
        "word_remove": ("➖ Remove Word", ActionStyle.DANGER),
        "word_refresh": ("🔄 Refresh", ActionStyle.SECONDARY),
        "scan_history": ("🔍 Scan History", ActionStyle.PRIMARY),
        "anti_evasion": ("🛡️ Anti-evasion", ActionStyle.SECONDARY),
    }
    assert set(by_id) == set(expected)
    for aid, (label, style) in expected.items():
        assert by_id[aid].label == label, aid
        assert by_id[aid].style is style, aid

    # mint order == the golden's <cid:N> order.
    assert spec.layout.pages[0].rows == (
        ("word_add", "word_remove", "word_refresh"),
        ("scan_history", "anti_evasion"),
    )


def test_words_buttons_route_to_their_live_targets():
    """The curation rework (2026-07-13): ➕/➖ open G-10 word modals whose
    submits run the audited command twins (goldens sweep_word_add /
    sweep_word_remove pin the reply copy); 🔄 re-renders the panel in
    place (the hub's cl_refresh pattern); 🔍 runs the live history scan
    (`!cleanuphistory`'s handler). 🛡️ toggles the migration-0053 strict
    flag for real (the residue port)."""
    import sb.manifest.cleanup  # noqa: F401 — register_ops() runs at import
    from sb.domain.cleanup.panels import cleanup_words_spec
    from sb.spec.outcomes import DeferMode
    from sb.spec.panels import ResultRender
    from sb.spec.refs import HandlerRef, PanelRef, WorkflowRef, is_registered

    by_id = {a.action_id: a for a in cleanup_words_spec().actions}

    # ➕/➖ — the moderation.hub.warn modal-ingress precedent: button →
    # declared ModalSpec → the K7 op (field_id "word" feeds ops._word_from).
    for aid, modal_id, op in (
            ("word_add", "cleanup.word_add_form", "cleanup.word_add_op"),
            ("word_remove", "cleanup.word_remove_form",
             "cleanup.word_remove_op")):
        action = by_id[aid]
        assert action.defer_mode is DeferMode.MODAL, aid
        assert action.modal is not None, aid
        assert action.modal.modal_id == modal_id, aid
        assert [f.field_id for f in action.modal.fields] == ["word"], aid
        assert action.modal.on_submit == WorkflowRef(op), aid
        assert action.handler == WorkflowRef(op), aid
        # the command twin is registered at import (the manifest routes
        # `!word add` / `!word remove` through the same op).
        assert is_registered(WorkflowRef(op)), aid

    # 🔄 — the cl_refresh pattern: re-render the words panel in place.
    assert by_id["word_refresh"].handler == PanelRef("cleanup.words")
    assert by_id["word_refresh"].result_render is ResultRender.REFRESH_PANEL

    # 🔍 — the live scan handler (`!cleanuphistory` is the front door).
    assert by_id["scan_history"].handler == HandlerRef("cleanup.history_scan")
    assert is_registered(HandlerRef("cleanup.history_scan"))

    # 🛡️ — the LIVE toggle (the shipped btn_strict flow onto the audited
    # cleanup.wordfilter_strict_op).
    assert by_id["anti_evasion"].handler == HandlerRef(
        "cleanup.anti_evasion_toggle")
    assert is_registered(HandlerRef("cleanup.anti_evasion_toggle"))
    assert is_registered(WorkflowRef("cleanup.wordfilter_strict_op"))


def test_retired_pending_terminals_are_gone():
    """The retired refs must not linger — a stale pending handler hides
    a regression of the same name (the burn-down posture). The
    cleanup-policy slice retired the LAST one (policies_pending) —
    cleanup carries NO pending terminals."""
    from sb.domain.cleanup import handlers
    from sb.spec.refs import HandlerRef, is_registered

    handlers.ensure_handler_refs()
    for name in ("cleanup.word_add_pending", "cleanup.word_remove_pending",
                 "cleanup.word_refresh_pending",
                 "cleanup.scan_history_pending", "cleanup.logging_pending",
                 "cleanup.settings_pending", "cleanup.anti_evasion_pending",
                 "cleanup.policies_pending"):
        assert not is_registered(HandlerRef(name)), name


def test_words_renderer_renders_the_golden_bytes_over_the_seeded_cache():
    """The residue port flipped the words-manager fields LIVE; with the
    capture trajectory seeded (the runner's sweep.wordmenu reseed lane)
    the golden bytes still render: `test` in Current Words, the
    default-off anti-evasion literal, the shipped footer, NO
    description."""
    from sb.domain.cleanup import service
    from sb.domain.cleanup.panels import cleanup_words_spec
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience
    from sb.spec.refs import resolve as resolve_ref

    spec = cleanup_words_spec()
    from types import SimpleNamespace

    ctx = PanelContext(
        bot=None, guild_id=1, actor=SimpleNamespace(user_id=42), channel_id=2,
        origin=PanelOrigin.INTERACTION, audience=Audience.INVOKER)
    service.seed_word_cache_for_replay(1, ("test",))
    try:
        rendered = run(resolve_ref(spec.renderer_override)(spec, ctx))
    finally:
        service.seed_word_cache_for_replay(1, None)
    assert rendered.embed.footer == (
        "Use buttons below to manage prohibited words.")
    # no description (the golden's embed carries no description key).
    assert rendered.embed.description == ""
    # the golden-pinned bytes over the LIVE reads (the strict flag reads
    # default-off in a db-free environment — the shipped no-row posture).
    assert rendered.embed.fields == (
        ("Current Words", "`test`"),
        ("🛡️ Anti-evasion matching", "⚫ **Off** — exact word match only"),
    )


def test_words_renderer_renders_the_shipped_empty_state():
    """No words configured → the shipped view set the DESCRIPTION and
    skipped the Current Words field (cleanup_cog.py build_embed)."""
    from sb.domain.cleanup import service
    from sb.domain.cleanup.panels import cleanup_words_spec
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience
    from sb.spec.refs import resolve as resolve_ref

    spec = cleanup_words_spec()
    from types import SimpleNamespace

    ctx = PanelContext(
        bot=None, guild_id=1, actor=SimpleNamespace(user_id=42), channel_id=2,
        origin=PanelOrigin.INTERACTION, audience=Audience.INVOKER)
    service.seed_word_cache_for_replay(1, None)
    rendered = run(resolve_ref(spec.renderer_override)(spec, ctx))
    assert rendered.embed.description == (
        "No prohibited words are currently set.")
    assert rendered.embed.fields == (
        ("🛡️ Anti-evasion matching", "⚫ **Off** — exact word match only"),
    )


# --- the manifest surface ---------------------------------------------------------------


def test_manifest_routes_match_the_flip():
    from sb.manifest.cleanup import MANIFEST
    from sb.spec.refs import HandlerRef, PanelRef

    by_name = {(c.group, c.name): c for c in MANIFEST.commands}
    assert by_name[("", "cleanup")].route == PanelRef("cleanup.hub")
    assert by_name[("", "cleanup")].audience_tier == "administrator"
    assert by_name[("", "wordmenu")].route == PanelRef("cleanup.words")
    assert by_name[("", "wordmenu")].audience_tier == "administrator"
    # the scan is a REAL handler now (the pending terminal retired); the
    # shipped gate was perms_or_owner(manage_messages) — the moderator tier.
    assert by_name[("", "cleanuphistory")].route == HandlerRef(
        "cleanup.history_scan")
    assert by_name[("", "cleanuphistory")].audience_tier == "moderator"
    panel_ids = [p.panel_id for p in MANIFEST.panels]
    assert panel_ids == ["cleanup.hub", "cleanup.words", "cleanup.settings",
                         "cleanup.settings_edit_presets",
                         # the cleanup-policy slice (the LAST pending
                         # retired): the 🧹 policy panel family.
                         "cleanup.policies", "cleanup.policies_scope",
                         "cleanup.policies_channel_pick",
                         "cleanup.policies_category_pick",
                         "cleanup.policies_level", "cleanup.policies_custom",
                         "cleanup.policies_preview",
                         "cleanup.policies_remove"]
    # the migration-0053 strict-flag table rides the manifest store list.
    assert [s.table for s in MANIFEST.stores] == [
        "prohibited_words", "wordfilter_config"]
    # the settings facet is the shipped CLEANUP_CONFIG_SCHEMA scalar.
    assert [(s.name, s.default, s.input_hint, tuple(s.presets), s.bounds)
            for s in MANIFEST.settings] == [
        ("spam_window_seconds", 15, "numeric_presets", (10, 15, 30),
         (1, 300))]


# --- the history scan -------------------------------------------------------------------


class _Req:
    def __init__(self, argv=()):
        self.args = {"argv": tuple(argv)}
        self.guild_id = 1
        self.channel_id = 42


def test_history_scan_pins_the_golden_copy():
    """The 0-match path — goldens/cleanup/sweep_cleanuphistory.json's
    summary byte-for-byte, with the port's logs_from-shaped read."""
    from sb.domain.cleanup import service
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, resolve as resolve_ref

    reads = []

    async def reader(channel_id, *, limit):
        reads.append((channel_id, limit))
        return ()

    service.install_history_reader(reader)
    try:
        reply = run(resolve_ref(HandlerRef("cleanup.history_scan"))(_Req()))
    finally:
        service.reset_cleanup_ports_for_tests()
    assert reads == [(42, 100)]
    assert reply.outcome == SUCCESS
    assert reply.user_message == (
        "Scanned 0 message(s) (requested 100, effective 100). "
        "Matched 0 messages for `prohibited`.")


def test_history_scan_clamps_to_the_shipped_cap():
    from sb.domain.cleanup import service
    from sb.spec.refs import HandlerRef, resolve as resolve_ref

    reads = []

    async def reader(channel_id, *, limit):
        reads.append(limit)
        return ()

    service.install_history_reader(reader)
    try:
        reply = run(resolve_ref(HandlerRef("cleanup.history_scan"))(
            _Req(argv=("2000", "spam"))))
    finally:
        service.reset_cleanup_ports_for_tests()
    assert reads == [1000]                         # MAX_CLEANUP_HISTORY_LIMIT
    assert reply.user_message == (
        "Scanned 0 message(s) (requested 2000, effective 1000). "
        "Matched 0 messages for `spam`.")


def test_history_scan_degrades_honestly_without_the_port():
    from sb.domain.cleanup import service
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve as resolve_ref

    service.reset_cleanup_ports_for_tests()
    reply = run(resolve_ref(HandlerRef("cleanup.history_scan"))(_Req()))
    assert reply.outcome == BLOCKED
    assert "channel-ops port" in reply.user_message


def test_history_scan_refuses_the_unported_deletion_leg():
    from sb.domain.cleanup import service
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve as resolve_ref
    from types import SimpleNamespace

    async def reader(channel_id, *, limit):
        return (SimpleNamespace(content="a BADWORD here"),
                SimpleNamespace(content="clean"))

    async def fake_words(guild_id):
        return ["badword"]

    from sb.domain.cleanup import store
    original = store.get_words
    store.get_words = fake_words
    service.install_history_reader(reader)
    try:
        reply = run(resolve_ref(HandlerRef("cleanup.history_scan"))(_Req()))
    finally:
        store.get_words = original
        service.reset_cleanup_ports_for_tests()
    assert reply.outcome == BLOCKED
    assert "Matched 1 of 2" in reply.user_message


def test_history_scan_refuses_unported_mode_matchers():
    """A non-`prohibited` mode over a NON-empty backlog must refuse
    honestly — only the prohibited matcher is ported (codex review,
    PR #140); the empty-backlog "Matched 0" stays factually true for
    every mode (the golden path)."""
    from types import SimpleNamespace

    from sb.domain.cleanup import service
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve as resolve_ref

    async def reader(channel_id, *, limit):
        return (SimpleNamespace(content="hello"),)

    service.install_history_reader(reader)
    try:
        reply = run(resolve_ref(HandlerRef("cleanup.history_scan"))(
            _Req(argv=("50", "links"))))
    finally:
        service.reset_cleanup_ports_for_tests()
    assert reply.outcome == BLOCKED
    assert "`links` matcher ports with the channel-ops slice" in reply.user_message


def test_scan_arg_parse_matches_the_shipped_signature():
    from sb.domain.cleanup.handlers import _parse_scan_args

    assert _parse_scan_args(()) == (100, "prohibited")
    assert _parse_scan_args(("50",)) == (50, "prohibited")
    assert _parse_scan_args(("50", "links")) == (50, "links")
    assert _parse_scan_args(("hello", "there")) == (100, "keyword")
    assert _parse_scan_args(("250", "some", "text")) == (250, "keyword")


# --- the settings page (the residue port: the shipped SubsystemSettingsView
# for `cleanup` — the ai.settings precedent) ---------------------------------------------


def test_settings_spec_shape_matches_the_shipped_page():
    from sb.domain.cleanup.panels import cleanup_settings_spec
    from sb.kernel.panels.compile import check_panel
    from sb.spec.panels import ActionStyle, Audience, FooterMode, SelectorKind
    from sb.spec.refs import HandlerRef, PanelRef

    spec = cleanup_settings_spec()
    check_panel(spec)
    assert spec.panel_id == "cleanup.settings"
    assert spec.subsystem == "cleanup"
    # the shipped header: meta emoji + display_name; blurple accent.
    assert spec.title == "🧹 Cleanup"
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "blurple"
    assert spec.frame.footer_mode is FooterMode.NONE
    assert spec.session_lifecycle is True
    assert spec.navigation.show_help is False
    assert spec.navigation.show_home is False

    by_id = {a.action_id: a for a in spec.actions}
    assert by_id["cl_back_to_hub"].label == "Back to Hub"
    assert by_id["cl_back_to_hub"].emoji == "↩"
    assert by_id["cl_back_to_hub"].style is ActionStyle.SECONDARY
    assert by_id["cl_back_to_hub"].handler == PanelRef("settings.hub")
    assert by_id["cl_open_panel"].label == "Open Panel"
    assert by_id["cl_open_panel"].emoji == "🪟"
    assert by_id["cl_open_panel"].style is ActionStyle.PRIMARY
    assert by_id["cl_open_panel"].handler == PanelRef("cleanup.hub")

    by_sel = {s.selector_id: s for s in spec.selectors}
    assert by_sel["edit_setting"].kind is SelectorKind.ENUM
    assert by_sel["edit_setting"].placeholder == "Edit a setting…"
    assert by_sel["edit_setting"].on_select == HandlerRef(
        "cleanup.settings_edit_route")
    assert by_sel["reset_setting"].placeholder == (
        "Reset a setting to its default…")
    assert by_sel["reset_setting"].on_select == HandlerRef(
        "cleanup.settings_reset_route")
    # ONE declared scalar → one option per select (the shipped S6 roster;
    # option values are the shipped spec.name bytes).
    assert [o["value"] for o in by_sel["edit_setting"].options_source] == [
        "spam_window_seconds"]
    assert [o["label"] for o in by_sel["reset_setting"].options_source] == [
        "Reset spam_window_seconds"]

    assert spec.layout.pages[0].rows == (
        ("cl_back_to_hub", "cl_open_panel"),
        ("edit_setting",),
        ("reset_setting",),
    )


def _declare_cleanup_settings():
    """Idempotently register the cleanup manifest settings facet into THE
    declaration registry (band-1 boot does this in the live root)."""
    from sb.kernel import settings as ksettings
    from sb.manifest.cleanup import MANIFEST

    try:
        ksettings.register_manifest_settings(MANIFEST)
    except ValueError:
        pass                                    # already declared


def test_settings_renderer_stamps_the_dynamic_footer():
    from types import SimpleNamespace

    from sb.domain.cleanup.panels import cleanup_settings_spec
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience
    from sb.spec.refs import resolve as resolve_ref

    _declare_cleanup_settings()
    spec = cleanup_settings_spec()
    ctx = PanelContext(
        bot=None, guild_id=7, actor=SimpleNamespace(user_id=42), channel_id=2,
        origin=PanelOrigin.INTERACTION, audience=Audience.INVOKER)
    rendered = run(resolve_ref(spec.renderer_override)(spec, ctx))
    # the shipped dynamic footer byte (double spaces included).
    assert rendered.embed.footer == (
        "Scalar edit + reset live · use the selects below.  guild_id=7")
    assert rendered.embed.description == (
        "_Prohibited words, command deletion, channel hygiene_\n"
        "visibility tier: `administrator`  ·  subsystem key: `cleanup`")
    names = [f[0] for f in rendered.embed.fields]
    assert names == ["Scalar settings", "Domain configuration",
                     "Existing command panels"]
    # the declared-default resolution line (no explicit row in a db-free
    # environment — provenance `default`, valid).
    assert rendered.embed.fields[0][1] == (
        "`spam_window_seconds` = `15` (`default`, default=`15`, valid)")
    assert rendered.embed.fields[2][1] == (
        "`!cleanup`, `!wordmenu`, `!cleanuphistory`")


def test_presets_widget_spec_and_renderer():
    from types import SimpleNamespace

    from sb.domain.cleanup.panels import cleanup_settings_edit_presets_spec
    from sb.kernel.panels.compile import check_panel
    from sb.spec.outcomes import DeferMode
    from sb.spec.panels import Audience
    from sb.spec.refs import HandlerRef, PanelRef, resolve as resolve_ref

    spec = cleanup_settings_edit_presets_spec()
    check_panel(spec)
    by_id = {a.action_id: a for a in spec.actions}
    assert set(by_id) == {"cl_preset_0", "cl_preset_1", "cl_preset_2", "cl_override_btn"}
    override = by_id["cl_override_btn"]
    assert override.defer_mode is DeferMode.MODAL
    assert override.modal is not None
    assert override.modal.modal_id == "cleanup.settings_number_form"
    assert override.modal.title == "Edit cleanup setting"
    assert [f.field_id for f in override.modal.fields] == ["new_value"]
    assert override.handler == HandlerRef("cleanup.settings_number_submit")
    # the shipped back route.
    assert [(r.label, r.route) for r in spec.navigation.extra_routes] == [
        ("↩ Back to Settings", PanelRef("cleanup.settings"))]

    # the renderer relabels the declared slots onto the picked spec's
    # roster (current value primary) and stamps the dispatcher prompt.
    ctx = PanelContext_for_widget()
    rendered = run(resolve_ref(spec.renderer_override)(spec, ctx))
    assert rendered.embed.description == (
        "Pick a value for `spam_window_seconds` "
        "(current=`15`, default=`15`):")
    labels = {c.custom_id: (c.label, c.style)
              for c in rendered.components
              if ".cl_preset_" in c.custom_id or c.custom_id.endswith("cl_override_btn")}
    # 10/15/30 relabeled; the current value (default 15) is primary.
    presets = sorted((label, style) for (label, style) in labels.values()
                     if label in {"10", "15", "30"})
    assert presets == [("10", "secondary"), ("15", "primary"),
                       ("30", "secondary")]


def PanelContext_for_widget():
    from types import SimpleNamespace

    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=1, actor=SimpleNamespace(user_id=42), channel_id=2,
        origin=PanelOrigin.INTERACTION, audience=Audience.INVOKER,
        params={"setting": "spam_window_seconds"})


# --- the settings widgets (the audited settings.set_scalar lane) ------------------------


class _WidgetReq:
    def __init__(self, args=None, guild_id=1):
        from types import SimpleNamespace

        self.args = dict(args or {})
        self.guild_id = guild_id
        self.channel_id = 2
        self.actor = SimpleNamespace(user_id=42)
        self.request_id = "req-1"
        self.confirmed = False
        self.origin = SimpleNamespace(message=None)


def test_preset_pick_writes_through_the_audited_lane(monkeypatch):
    from types import SimpleNamespace

    from sb.domain.cleanup import settings_widgets as widgets
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS

    calls = []

    async def fake_run(ref, ctx):
        calls.append((getattr(ref, "name", str(ref)), dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS, user_message=None,
                               before={}, after={})

    monkeypatch.setattr(engine, "run", fake_run)
    req = _WidgetReq(args={"setting": "spam_window_seconds",
                           "session_action": "cl_preset_2"})
    reply = run(widgets.settings_preset_pick(req))
    assert calls and calls[0][0] == "settings.set_scalar"
    params = calls[0][1]
    assert params["subsystem"] == "cleanup"
    assert params["name"] == "spam_window_seconds"
    assert params["value"] == "30"                 # preset index 2
    assert reply.user_message == (
        "✅ Updated `spam_window_seconds` = `30` (was `15`).")


def test_reset_writes_the_declared_default(monkeypatch):
    from types import SimpleNamespace

    from sb.domain.cleanup import settings_widgets as widgets
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS

    calls = []

    async def fake_run(ref, ctx):
        calls.append(dict(ctx.params))
        return SimpleNamespace(outcome=SUCCESS, user_message=None,
                               before={}, after={})

    monkeypatch.setattr(engine, "run", fake_run)
    req = _WidgetReq(args={"values": ("spam_window_seconds",)})
    reply = run(widgets.settings_reset_route(req))
    assert calls[0]["value"] == "15"
    assert reply.user_message == (
        "✅ Reset `spam_window_seconds` to default = `15`.")


def test_number_submit_coerces_and_bounds_check(monkeypatch):
    from types import SimpleNamespace

    from sb.domain.cleanup import settings_widgets as widgets
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS

    async def fake_run(ref, ctx):
        return SimpleNamespace(outcome=SUCCESS, user_message=None,
                               before={}, after={})

    monkeypatch.setattr(engine, "run", fake_run)
    # out of the shipped 1..300 bounds → the coercion refusal, no write.
    req = _WidgetReq(args={"setting": "spam_window_seconds",
                           "new_value": "9999"})
    reply = run(widgets.settings_number_submit(req))
    assert reply.user_message.startswith(
        "❌ Couldn't update `spam_window_seconds`: cannot coerce")
    # in-bounds writes.
    req = _WidgetReq(args={"setting": "spam_window_seconds",
                           "new_value": "60"})
    reply = run(widgets.settings_number_submit(req))
    assert reply.user_message == (
        "✅ Updated `spam_window_seconds` = `60` (was `15`).")


def test_unknown_setting_pick_is_guarded():
    from sb.domain.cleanup import settings_widgets as widgets

    reply = run(widgets.settings_edit_route(
        _WidgetReq(args={"values": ("nope",)})))
    assert reply.user_message == "❌ Unknown setting `nope`."


# --- the anti-evasion toggle -------------------------------------------------------------


def test_anti_evasion_toggle_runs_the_audited_op(monkeypatch):
    from types import SimpleNamespace

    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, resolve as resolve_ref

    calls = []

    async def fake_run(ref, ctx):
        calls.append((getattr(ref, "name", str(ref)), dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS, user_message=None,
                               before={"wordfilter_strict": {"strict": False}},
                               after={"wordfilter_strict": {"strict": True}})

    monkeypatch.setattr(engine, "run", fake_run)
    # db-free: the current-flag read degrades to the shipped default off,
    # so the toggle writes strict=True.
    req = _WidgetReq()
    reply = run(resolve_ref(HandlerRef("cleanup.anti_evasion_toggle"))(req))
    assert calls == [("cleanup.wordfilter_strict_op", {"strict": True})]
    # no session view to refresh in this harness → the honest text degrade.
    assert reply is not None
    assert reply.user_message == "🛡️ Anti-evasion matching → 🟢 **On**."


def test_anti_evasion_toggle_requires_a_guild():
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve as resolve_ref

    reply = run(resolve_ref(HandlerRef("cleanup.anti_evasion_toggle"))(
        _WidgetReq(guild_id=0)))
    assert reply.outcome == BLOCKED


def test_wordfilter_strict_op_is_registered_with_the_audit_verb():
    import sb.manifest.cleanup  # noqa: F401 — register_ops() at import
    from sb.kernel.workflow.registry import REGISTRY
    from sb.spec.refs import WorkflowRef

    spec = REGISTRY.resolve(WorkflowRef("cleanup.wordfilter_strict_op"))
    assert spec.audit_verb == "wordfilter_strict"
    assert spec.domain == "cleanup"
