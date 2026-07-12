"""The SETTINGS panels (the shipped Settings Manager hub + the Access
Policy Explorer as declarative panels): the golden-pinned spec bytes,
the compile fences, the manifest surface (BOTH front doors + the
`!settings access` subcommand), the renderer overrides (footer literal /
invoker footer + inline fields + first-page Prev disable), the verbatim
persistent custom_ids, and the pending terminals.

Oracle: menno420/superbot disbot/cogs/settings_cog.py +
disbot/views/settings/hub.py (SettingsHubView/build_embed) +
disbot/views/access/explorer.py; parity/goldens/settings/
(settings_hub_open, sweep_settings, sweep_settings_access,
sweep_slash_settings) pins every wire byte.
"""

from __future__ import annotations

import asyncio

run = asyncio.run


# --- the hub spec: golden-pinned bytes -------------------------------------------------


def test_hub_spec_shape_matches_the_goldens():
    from sb.domain.settings.panels import settings_hub_spec
    from sb.spec.panels import ActionStyle, Audience, FooterMode

    spec = settings_hub_spec()
    assert spec.panel_id == "settings.hub"
    assert spec.subsystem == "settings"
    assert spec.title == "⚙️ Settings Manager"
    # the shipped slash twin answered EPHEMERAL (flags 64 in the golden).
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "blurple"    # discord.Color.blurple()
    assert spec.frame.footer_mode is FooterMode.NONE
    # no nav row (the goldens pin exactly three component rows); the
    # never-strand fence takes the session-view exemption — every id is
    # override-pinned so nothing is run-minted (no panel_anchors row).
    assert spec.session_lifecycle is True
    assert spec.navigation.show_help is False
    assert spec.navigation.show_home is False

    (select,) = spec.selectors
    assert select.selector_id == "subsystem_select"
    assert select.custom_id_override == "settings_hub.subsystem_select"
    assert select.placeholder == "Open a settings group…"
    # the group select NAVIGATES read-only (the shipped SettingsHubView
    # navigation, ported as a read subset) — not the pending terminal.
    from sb.spec.refs import HandlerRef as _HRef
    assert select.on_select == _HRef("settings.open_group")
    # the shipped 19-group actionable roster, order verbatim.
    values = [o["value"] for o in select.options_source]
    assert values == [
        "welcome", "counters", "security", "proof_channel", "role",
        "cleanup", "automod", "image_moderation", "moderation", "logging",
        "ai", "help", "economy", "xp", "karma", "blackjack", "btd6",
        "deathmatch", "rps_tournament"]

    by_id = {a.action_id: a for a in spec.actions}
    # the shipped buttons carried the emoji as a SEPARATE component field
    # (discord.ui.button(emoji=...)) + the PERSISTENT custom_id verbatim.
    expected = {
        "needs_setup": ("Needs setup", "📋"),
        "invalid": ("Invalid settings", "⚠️"),
        "missing_bindings": ("Missing bindings", "🔗"),
        "audit": ("Recent changes", "🕒"),
        "command_access": ("Command access", "🚪"),
    }
    assert set(by_id) == set(expected)
    for aid, (label, emoji) in expected.items():
        assert by_id[aid].label == label, aid
        assert by_id[aid].emoji == emoji, aid
        assert by_id[aid].style is ActionStyle.SECONDARY, aid
        assert by_id[aid].custom_id_override == f"settings_hub.{aid}", aid
        assert by_id[aid].audience_tier == "administrator", aid

    assert spec.layout.pages[0].rows == (
        ("subsystem_select",),
        ("needs_setup", "invalid", "missing_bindings", "audit"),
        ("command_access",),
    )


def test_access_spec_shape_matches_the_golden():
    from sb.domain.settings.panels import settings_access_spec
    from sb.spec.panels import ActionStyle, Audience, FooterMode

    spec = settings_access_spec()
    assert spec.panel_id == "settings.access"
    assert spec.title == "🔍 Access Policy Explorer"
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "blue"       # discord.Color.blue()
    assert spec.frame.footer_mode is FooterMode.NONE
    assert spec.session_lifecycle is True
    # the shipped standard nav row: 📚 Help + ↩ Administration.
    assert spec.navigation.show_help is True
    assert spec.navigation.home_hub == "admin"

    subsystem, scope = spec.selectors
    # the paged subsystem select is run-minted (<cid:1> in the golden) —
    # no override; the shipped page-1/2 placeholder byte survives.
    assert subsystem.selector_id == "subsystem"
    assert subsystem.custom_id_override == ""
    assert subsystem.placeholder == "Choose a subsystem… — page 1/2"
    assert len(subsystem.options_source) == 25    # the shipped page cap
    assert subsystem.options_source[0]["value"] == "help"
    assert subsystem.options_source[-1]["value"] == "security"
    # the scope select keeps its shipped persistent id + channel default.
    assert scope.custom_id_override == "access:select_scope"
    assert scope.placeholder == "Choose a scope…"
    assert [o["value"] for o in scope.options_source] == [
        "channel", "category", "guild"]
    assert scope.options_source[0].get("default") is True
    assert all("emoji" not in o for o in scope.options_source)

    by_id = {a.action_id: a for a in spec.actions}
    # emoji IN the labels (no separate emoji field in the golden).
    assert by_id["explain"].label == "🔬 Explain Access"
    assert by_id["explain"].style is ActionStyle.PRIMARY
    assert by_id["explain"].custom_id_override == "access:explain"
    assert by_id["reset"].label == "🔄 Reset"
    assert by_id["reset"].style is ActionStyle.SECONDARY
    assert by_id["reset"].custom_id_override == "access:reset"
    # the session page-turn pair is run-minted (<cid:2>/<cid:3>).
    assert by_id["access_prev"].label == "◀ Prev"
    assert by_id["access_prev"].custom_id_override == ""
    assert by_id["access_next"].label == "Next ▶"
    assert by_id["access_next"].custom_id_override == ""

    assert spec.layout.pages[0].rows == (
        ("subsystem",),
        ("select_scope",),
        ("explain", "reset"),
        ("access_prev", "access_next"),
    )


def test_both_specs_pass_the_compile_fences():
    from sb.domain.settings.panels import settings_access_spec, settings_hub_spec
    from sb.kernel.panels.compile import check_panel

    check_panel(settings_hub_spec())
    check_panel(settings_access_spec())


def test_style_tokens_are_the_shipped_colors():
    from sb.kernel.panels.render import STYLE_TOKEN_COLORS

    assert STYLE_TOKEN_COLORS["blurple"] == 5793266  # the hub embed
    assert STYLE_TOKEN_COLORS["blue"] == 3447003     # the explorer embed


# --- the renders: overrides -------------------------------------------------------------


def _ctx(params: dict | None = None):
    from types import SimpleNamespace

    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=1, actor=SimpleNamespace(user_id=42),
        channel_id=2, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(),
        params=dict(params or {}))


def test_hub_render_carries_the_footer_and_the_pinned_fields():
    from sb.domain.settings import panels
    from sb.domain.settings.panels import _render_hub, settings_hub_spec

    panels.ensure_panel_refs()      # re-arm after suite-order registry resets
    rendered = run(_render_hub(settings_hub_spec(), _ctx()))
    assert rendered.embed.footer == (
        "Tip: `!platform customization` and `!platform settings-registry` "
        "expose the underlying catalogues.")
    assert rendered.embed.description.startswith(
        "Browse platform settings, bindings, resource requirements, and "
        "recent audit history.  The dropdown")
    assert rendered.embed.fields[0][0] == "Inventory"
    assert rendered.embed.fields[0][1] == (
        "`groups`: 19  ·  `subsystems`: 43  ·  `schemas`: 19\n"
        "`settings`: 0  ·  `bindings`: 17  ·  `resources`: 15")
    assert rendered.embed.fields[1] == ("Customization findings",
                                        "*catalogue not built yet*")
    # no engine-injected nav components (the goldens' exactly-three rows).
    assert all(not c.custom_id.startswith("nav:") for c in rendered.components)
    # every wire id is the shipped persistent id, never a minted one.
    assert [c.custom_id for c in rendered.components] == [
        "settings_hub.subsystem_select", "settings_hub.needs_setup",
        "settings_hub.invalid", "settings_hub.missing_bindings",
        "settings_hub.audit", "settings_hub.command_access"]


def test_access_render_footer_inline_fields_and_disabled_prev():
    from sb.domain.settings import panels
    from sb.domain.settings.panels import _render_access, settings_access_spec

    panels.ensure_panel_refs()      # re-arm after suite-order registry resets
    spec = settings_access_spec()
    rendered = run(_render_access(spec, _ctx({"invoker_name": "AdminActor"})))
    # the shipped invoker-named author-lock footer (the golden byte).
    assert rendered.embed.footer == (
        "Invoker: AdminActor. Only the invoker can interact with this panel.")
    # the shipped inline selection-prompt fields.
    assert rendered.embed.fields == (
        ("Subsystem", "_Pick from the first dropdown._", True),
        ("Scope", "_Pick from the second dropdown._", True))
    by_id = {c.custom_id: c for c in rendered.components}
    # first-page ◀ Prev renders disabled; Next ▶ stays live.
    assert by_id["settings.access.access_prev"].disabled is True
    assert by_id["settings.access.access_next"].disabled is False
    # the nav row is present (help + the admin hub home).
    assert "nav:help" in by_id
    assert "nav:hub:admin" in by_id
    # the persistent overrides survive verbatim.
    assert "access:select_scope" in by_id
    assert "access:explain" in by_id and "access:reset" in by_id


# --- the refs + manifest ----------------------------------------------------------------


def test_panel_and_handler_refs_registered():
    from sb.domain.settings import handlers, panels
    from sb.spec.refs import HandlerRef, PanelRef, ProviderRef, is_registered

    panels.ensure_panel_refs()
    handlers.ensure_handler_refs()
    assert is_registered(PanelRef("settings.hub"))
    assert is_registered(PanelRef("settings.access"))
    assert is_registered(ProviderRef("settings.hub_fields"))
    assert is_registered(ProviderRef("settings.access_fields"))
    for name in ("settings.render_hub", "settings.render_access",
                 "settings.access_view", "settings.open_group",
                 "settings.group_pending",
                 "settings.needs_setup_pending", "settings.invalid_pending",
                 "settings.missing_bindings_pending", "settings.audit_pending",
                 "settings.command_access_pending",
                 "settings.access_subsystem_pending",
                 "settings.access_scope_pending",
                 "settings.access_explain_pending",
                 "settings.access_reset_pending",
                 "settings.access_page_pending"):
        assert is_registered(HandlerRef(name)), name


def test_manifest_declares_the_front_doors():
    from sb.manifest.settings import MANIFEST
    from sb.spec.commands import CommandKind
    from sb.spec.outcomes import DeferMode
    from sb.spec.refs import HandlerRef, PanelRef

    assert MANIFEST.key == "settings"
    hub_cmd, access_cmd = MANIFEST.commands
    assert hub_cmd.name == "settings"
    assert hub_cmd.kind is CommandKind.BOTH
    assert hub_cmd.route == PanelRef("settings.hub")
    # the shipped slash surface: direct type-4 answer, no defer (the
    # golden pins the bare type-4 with flags 64 — the utility-flip trap
    # rule, applied by rule).
    assert hub_cmd.defer_mode is DeferMode.NONE
    assert hub_cmd.audience_tier == "administrator"
    # `!settings access` dispatches independently (the shipped cog note).
    assert access_cmd.name == "access"
    assert access_cmd.group == "settings"
    assert access_cmd.qualified_name == "settings access"
    assert access_cmd.kind is CommandKind.PREFIX
    assert access_cmd.route == HandlerRef("settings.access_view")
    hub_spec, access_spec = MANIFEST.panels
    assert hub_spec.panel_id == "settings.hub"
    assert access_spec.panel_id == "settings.access"


def test_clicks_land_on_the_polite_pending_terminal():
    from types import SimpleNamespace

    from sb.domain.settings import handlers  # noqa: F401
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    reply = run(resolve(HandlerRef("settings.command_access_pending"))(
        SimpleNamespace(args={}, guild_id=1)))
    assert reply.outcome == BLOCKED
    assert "Command Access panel" in reply.user_message


# --- the group-select read-only navigation (settings.open_group) ---------------------


class TestGroupSelectNavigation:
    """The Settings-hub group select navigates read-only to a group's
    operator-spine hub (welcome/counters/security/automod/image_moderation)
    and lands on the pending terminal for every other group — the write
    seam (per-group edit) is never touched (mirrors help.open_category)."""

    @staticmethod
    def _handler():
        from sb.domain.settings import handlers
        from sb.spec.refs import HandlerRef, resolve as resolve_ref

        handlers.ensure_handler_refs()
        return resolve_ref(HandlerRef("settings.open_group"))

    @staticmethod
    def _ensure_real_operator_hubs():
        # import the real manifests (idempotent) so the registry carries the
        # genuine hub specs — never a fake ensure_hub (which would re-register
        # a panel id with a differing spec and corrupt the global registry).
        import importlib

        for name in ("welcome", "counters", "security", "automod",
                     "image_moderation"):
            importlib.import_module(f"sb.manifest.{name}")

    def test_group_with_an_operator_hub_navigates_to_it(self, monkeypatch):
        import sb.kernel.panels.engine as engine

        self._ensure_real_operator_hubs()
        opened: list[str] = []

        async def fake_open(ref, req):
            opened.append(ref.name)

        monkeypatch.setattr(engine, "open_panel", fake_open)
        handler = self._handler()

        class Req:
            args = {"values": ("welcome",)}

        # navigation returns None (open_panel took over) and opened the
        # subsystem's READ-ONLY hub — no mutation, no Reply.
        assert run(handler(Req())) is None
        assert opened == ["welcome.hub"]

    def test_every_operator_hub_group_navigates(self, monkeypatch):
        import sb.kernel.panels.engine as engine
        from sb.domain.operator_spine import operator_hub_subsystems

        self._ensure_real_operator_hubs()
        assert {"welcome", "counters", "security", "automod",
                "image_moderation"} <= operator_hub_subsystems()

        opened: list[str] = []

        async def fake_open(ref, req):
            opened.append(ref.name)

        monkeypatch.setattr(engine, "open_panel", fake_open)
        handler = self._handler()

        for sub in ("welcome", "counters", "security", "automod",
                    "image_moderation"):
            class Req:
                args = {"values": (sub,)}

            assert run(handler(Req())) is None
        assert opened == ["welcome.hub", "counters.hub", "security.hub",
                          "automod.hub", "image_moderation.hub"]

    def test_group_without_an_operator_hub_stays_pending(self, monkeypatch):
        import sb.kernel.panels.engine as engine
        from sb.spec.outcomes import BLOCKED

        opened: list[str] = []

        async def fake_open(ref, req):     # must NOT be called
            opened.append(ref.name)

        monkeypatch.setattr(engine, "open_panel", fake_open)
        handler = self._handler()

        # `moderation` has a custom action hub (ban/kick modals), NOT an
        # operator-spine read-only hub — the select must not open it.
        class Req:
            args = {"values": ("moderation",)}

        reply = run(handler(Req()))
        assert reply.outcome == BLOCKED
        assert "per-group settings page" in reply.user_message
        assert opened == []      # read-only: no navigation, no write seam

    def test_empty_selection_stays_pending(self, monkeypatch):
        import sb.kernel.panels.engine as engine
        from sb.spec.outcomes import BLOCKED

        async def fake_open(ref, req):
            raise AssertionError("open_panel must not fire on empty values")

        monkeypatch.setattr(engine, "open_panel", fake_open)
        handler = self._handler()

        class Req:
            args = {}

        reply = run(handler(Req()))
        assert reply.outcome == BLOCKED
