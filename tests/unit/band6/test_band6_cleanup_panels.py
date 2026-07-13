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

    # the curation rework: 📝 Logging Status routes to the PORTED
    # logging.hub (its server-logging successor slice landed); ⚙️/🧹
    # stay honest pending terminals (their slices are unported).
    from sb.spec.refs import HandlerRef, PanelRef

    assert by_id["logging"].handler == PanelRef("logging.hub")
    assert by_id["settings"].handler == HandlerRef("cleanup.settings_pending")
    assert by_id["policies"].handler == HandlerRef("cleanup.policies_pending")


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
    (`!cleanuphistory`'s handler). 🛡️ stays the honest pending terminal
    (the word-mutation slice's toggle)."""
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

    # 🛡️ — still the declared + honest pending terminal.
    assert by_id["anti_evasion"].handler == HandlerRef(
        "cleanup.anti_evasion_pending")
    assert is_registered(HandlerRef("cleanup.anti_evasion_pending"))


def test_retired_pending_terminals_are_gone():
    """The five retired refs must not linger — a stale pending handler
    hides a regression of the same name (the burn-down posture)."""
    from sb.domain.cleanup import handlers
    from sb.spec.refs import HandlerRef, is_registered

    handlers.ensure_handler_refs()
    for name in ("cleanup.word_add_pending", "cleanup.word_remove_pending",
                 "cleanup.word_refresh_pending",
                 "cleanup.scan_history_pending", "cleanup.logging_pending"):
        assert not is_registered(HandlerRef(name)), name


def test_words_renderer_override_stamps_the_footer_only():
    from sb.domain.cleanup.panels import cleanup_words_spec
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience
    from sb.spec.refs import resolve as resolve_ref

    spec = cleanup_words_spec()
    from types import SimpleNamespace

    ctx = PanelContext(
        bot=None, guild_id=1, actor=SimpleNamespace(user_id=42), channel_id=2,
        origin=PanelOrigin.INTERACTION, audience=Audience.INVOKER)
    rendered = run(resolve_ref(spec.renderer_override)(spec, ctx))
    assert rendered.embed.footer == (
        "Use buttons below to manage prohibited words.")
    # no description (the golden's embed carries no description key).
    assert rendered.embed.description == ""
    # the golden-pinned literals (the capture-order `_word_cache` leak —
    # the in-code under-port note).
    assert rendered.embed.fields == (
        ("Current Words", "`test`"),
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
    assert panel_ids == ["cleanup.hub", "cleanup.words"]


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
