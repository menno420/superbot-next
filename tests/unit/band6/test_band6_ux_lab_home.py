"""Band 6 — the UX LAB home panel (the shipped UxLabHomeView as a
session-lifecycle panel): the golden-pinned spec bytes, the compile fences,
the manifest surface, the footer renderer_override, and the shipped nav row
(nav:help + nav:hub:admin with the hub's display label).

Oracle: menno420/superbot disbot/cogs/ux_lab_cog.py +
disbot/views/ux_lab/home.py (build_home_embed + UxLabHomeView);
parity/goldens/ux_lab/sweep_uxlab.json + goldens/uxlab/sweep_slash_uxlab.json
pin the wire bytes.
"""

from __future__ import annotations

import asyncio

run = asyncio.run


# --- the spec: golden-pinned bytes ---------------------------------------------------


def test_home_spec_shape_matches_the_golden():
    from sb.domain.ux_lab.panels import ux_lab_home_spec
    from sb.spec.panels import ActionStyle, Audience, FooterMode

    spec = ux_lab_home_spec()
    assert spec.panel_id == "ux_lab.home"
    assert spec.subsystem == "ux_lab"
    assert spec.title == "🧪 UX Lab — interface gallery"
    # the shipped slash reply was PUBLIC (the golden's type-4 data carries
    # no ephemeral flag).
    assert spec.audience is Audience.PUBLIC
    assert spec.frame.style_token == "blurple"
    assert spec.frame.footer_mode is FooterMode.NONE
    # the shipped session view: run-minted ids, no anchor row — but WITH
    # the standard nav row (unlike general/utility).
    assert spec.session_lifecycle is True
    assert spec.navigation.show_help is True
    assert spec.navigation.show_home is True
    assert spec.navigation.home_hub == "admin"

    by_id = {a.action_id: a for a in spec.actions}
    # the shipped buttons carried a SEPARATE emoji field (the golden pins
    # an "emoji" key on every wing button) with the bare wing name label.
    assert by_id["buttons"].label == "Buttons"
    assert by_id["buttons"].emoji == "🔘"
    assert by_id["selects"].label == "Selects"
    assert by_id["selects"].emoji == "📋"
    assert by_id["modals"].label == "Modals"
    assert by_id["modals"].emoji == "⌨️"
    assert by_id["embeds"].label == "Embeds"
    assert by_id["embeds"].emoji == "\U0001faa7"
    assert by_id["components_v2"].label == "Components V2"
    assert by_id["components_v2"].emoji == "\U0001f9f1"
    assert by_id["pil_cards"].label == "PIL cards"
    assert by_id["pil_cards"].emoji == "🎨"
    assert by_id["mock_studio"].label == "Mock studio"
    assert by_id["mock_studio"].emoji == "🎭"
    assert by_id["probe_bench"].label == "Probe bench"
    assert by_id["probe_bench"].emoji == "🔬"
    assert by_id["compare"].label == "Compare"
    assert by_id["compare"].emoji == "⚖️"
    # wire styles: the first seven wings blurple (1); Probe bench and
    # Compare grey (2) — the golden pins the mix.
    for aid in ("buttons", "selects", "modals", "embeds",
                "components_v2", "pil_cards", "mock_studio"):
        assert by_id[aid].style is ActionStyle.PRIMARY, aid
    for aid in ("probe_bench", "compare"):
        assert by_id[aid].style is ActionStyle.SECONDARY, aid

    assert spec.layout.pages[0].rows == (
        ("buttons", "selects", "modals", "embeds"),
        ("components_v2", "pil_cards", "mock_studio", "probe_bench"),
        ("compare",),
    )


def test_blurple_style_token_is_the_shipped_color():
    from sb.kernel.panels.render import STYLE_TOKEN_COLORS

    assert STYLE_TOKEN_COLORS["blurple"] == 5793266  # discord.Color.blurple()


def test_home_spec_passes_the_compile_fences():
    from sb.domain.ux_lab.panels import ux_lab_home_spec
    from sb.kernel.panels.compile import check_panel

    check_panel(ux_lab_home_spec())  # raises PanelCompileError on drift


# --- the render: footer literal + the shipped nav row --------------------------------


def _ctx():
    from types import SimpleNamespace

    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=1, actor=SimpleNamespace(user_id=42),
        channel_id=2, origin=PanelOrigin.INTERACTION,
        audience=Audience.PUBLIC, locale=LocaleContext(), params={})


def test_render_carries_the_plan_doc_footer_and_the_admin_nav_row():
    from sb.domain.ux_lab.panels import _render_home, ux_lab_home_spec

    rendered = run(_render_home(ux_lab_home_spec(), _ctx()))
    assert rendered.embed.footer == (
        "Design: docs/planning/ux-lab-interface-gallery-plan-2026-06-12.md")
    assert "**Nothing here is real**" in rendered.embed.description
    assert rendered.embed.fields[0][0] == "Exhibits"
    assert "Probe bench **10**" in rendered.embed.fields[0][1]
    assert rendered.embed.fields[1][0] == "How to browse"
    # the shipped standard nav: nav:help + nav:hub:admin labeled with the
    # HUB'S display name (subsystem_registry "Administration", verbatim —
    # the golden pins "↩ Administration", never "↩ Home").
    nav = {c.custom_id: c for c in rendered.components if c.row == 4}
    assert nav["nav:help"].label == "📚 Help"
    assert nav["nav:hub:admin"].label == "↩ Administration"
    # PUBLIC audience — no invoker lock (the shipped author-lock rejoins
    # with the wings slice; the module docstring carries the note).
    assert rendered.invoker_lock is None


def test_unmapped_hub_keeps_the_home_placeholder():
    from sb.kernel.panels.render import HUB_NAV_LABELS

    assert HUB_NAV_LABELS.get("admin") == "Administration"
    assert "economy" not in HUB_NAV_LABELS  # lands when a golden pins it


# --- the refs + manifest --------------------------------------------------------------


def test_panel_and_handler_refs_registered():
    from sb.domain.ux_lab import handlers, panels
    from sb.spec.refs import HandlerRef, PanelRef, is_registered

    panels.ensure_panel_refs()
    handlers.ensure_handler_refs()
    assert is_registered(PanelRef("ux_lab.home"))
    for name in ("ux_lab.home_view", "ux_lab.render_home",
                 "ux_lab.buttons_wing", "ux_lab.selects_wing",
                 "ux_lab.modals_wing", "ux_lab.embeds_wing",
                 "ux_lab.components_v2_wing", "ux_lab.pil_cards_wing",
                 "ux_lab.mock_studio_wing", "ux_lab.probe_bench_wing",
                 "ux_lab.compare_wing"):
        assert is_registered(HandlerRef(name)), name


def test_manifest_declares_the_home_entry_points():
    from sb.manifest.ux_lab import MANIFEST
    from sb.spec.commands import CommandKind
    from sb.spec.outcomes import DeferMode
    from sb.spec.refs import HandlerRef

    assert MANIFEST.key == "ux_lab"
    (cmd, slash) = MANIFEST.commands
    assert cmd.name == "uxlab"
    assert cmd.kind is CommandKind.PREFIX
    assert cmd.aliases == ("interfacelab",)
    assert cmd.route == HandlerRef("ux_lab.home_view")
    # the shipped admin_or_owner() gate — administrator tier.
    assert cmd.audience_tier == "administrator"
    # the shipped slash front door: same one handler, DIRECT type-4 answer
    # (no defer — goldens/uxlab/sweep_slash_uxlab pins the bare type-4).
    assert slash.name == "uxlab"
    assert slash.kind is CommandKind.SLASH
    assert slash.route == HandlerRef("ux_lab.home_view")
    assert slash.defer_mode is DeferMode.NONE
    assert slash.audience_tier == "administrator"
    (spec,) = MANIFEST.panels
    assert spec.panel_id == "ux_lab.home"
    # R2 stays vacuous for ux_lab: the shipped lab is zero-write.
    assert MANIFEST.stores == () and MANIFEST.events == ()
    assert MANIFEST.settings == ()


def test_responder_records_the_original_response_fetch():
    """The shipped `view.message = await interaction.original_response()`
    (ux_lab_cog.uxlab_slash) — the capture twin records the GET verbatim
    AFTER the type-4 response; message surfaces never fetch."""
    from types import SimpleNamespace

    from sb.adapters.parity.transport import ParityResponder, ParityTransport
    from sb.kernel.interaction.request import Surface

    transport = ParityTransport(ids=SimpleNamespace(allocate=lambda: 1),
                                clock=SimpleNamespace())
    responder = ParityResponder(transport, surface=Surface.SLASH,
                                channel_id=2, interaction_id=3)
    # before any response exists there is nothing to fetch.
    run(responder.fetch_original_response())
    assert [c.method for c in transport.calls] == []
    responder.present_panel({"content": None})
    run(responder.fetch_original_response())
    assert [c.method for c in transport.calls] == [
        "interaction_response", "get_original_response"]
    assert transport.calls[1].args == {}

    prefix = ParityResponder(transport, surface=Surface.PREFIX, channel_id=2)
    run(prefix.fetch_original_response())    # message surface: no-op
    assert [c.method for c in transport.calls] == [
        "interaction_response", "get_original_response"]


def test_wing_clicks_land_on_the_polite_pending_terminal():
    from types import SimpleNamespace

    from sb.domain.ux_lab import handlers  # noqa: F401 — registers refs
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    reply = run(resolve(HandlerRef("ux_lab.buttons_wing"))(
        SimpleNamespace(args={}, guild_id=1)))
    assert reply.outcome == BLOCKED
    assert "Buttons wing" in reply.user_message
