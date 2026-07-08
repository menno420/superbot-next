"""S9b generated panels: settings-as-projection + help-as-projection —
both compile-clean and rendering real declared data."""

from __future__ import annotations

import asyncio

from sb.kernel import settings as settings_mod
from sb.kernel.interaction.locale import LocaleContext
from sb.kernel.panels.compile import check_panel
from sb.kernel.panels.context import PanelContext, PanelOrigin
from sb.kernel.panels.projections import help_panel_spec, settings_panel_spec
from sb.kernel.panels.registry import register_panel
from sb.kernel.panels.render import render_panel
from sb.spec.panels import Audience

from tests.unit.panels.conftest import make_actor

run = asyncio.run


def ctx():
    return PanelContext(bot=None, guild_id=42, actor=make_actor(), channel_id=7,
                        origin=PanelOrigin.INTERACTION, audience=Audience.INVOKER,
                        locale=LocaleContext())


def test_settings_panel_projection_compiles_and_renders_declared_values():
    settings_mod.clear_for_tests()
    settings_mod.register_setting(settings_mod.SettingDeclaration(
        subsystem="logging", name="enabled",
        activation=settings_mod.Activation.ON_BY_DEFAULT))
    settings_mod.register_setting(settings_mod.SettingDeclaration(
        subsystem="logging", name="channel", default=None))
    try:
        spec = settings_panel_spec("logging")
        check_panel(spec)
        register_panel(spec)
        rendered = run(render_panel(spec, ctx()))
        fields = dict(rendered.embed.fields)
        assert fields["logging.enabled"] == "True"    # activation terminus
        assert fields["logging.channel"] == "None"
    finally:
        settings_mod.clear_for_tests()


def test_help_panel_projection_from_command_inventory():
    spec = help_panel_spec({
        "economy": (("balance", "Show your balance"), ("give", "Give coins")),
        "karma": (("karma", "Check karma"),),
    })
    check_panel(spec)
    register_panel(spec)
    rendered = run(render_panel(spec, ctx()))
    fields = dict(rendered.embed.fields)
    assert "`balance` — Show your balance" in fields["economy"]
    assert "karma" in fields
    # help is its own home: no nav:help button on the help hub
    assert "nav:help" not in [c.custom_id for c in rendered.components]
