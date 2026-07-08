"""The K7 settings-resolution read engine (design-spec §4.1-§4.4, F-3.4):
tri-state chain + the activation terminus."""

import asyncio

import pytest

import sb.kernel.settings as settings
from sb.kernel.settings import (
    UNSET,
    Activation,
    SettingDeclaration,
    install_binding_probe,
    install_secret_presence,
    install_settings_reader,
    register_setting,
    resolve,
)


@pytest.fixture(autouse=True)
def _clean():
    settings.clear_for_tests()
    yield
    settings.clear_for_tests()


def _store(rows: dict):
    async def reader(guild_id, key):
        return rows.get((guild_id, key), UNSET)
    install_settings_reader(reader)


def test_undeclared_key_is_a_hard_error():
    with pytest.raises(LookupError, match="not declared"):
        asyncio.run(resolve(1, "logging", "enabled"))


def test_tri_state_chain_explicit_always_wins():
    register_setting(SettingDeclaration("logging", "enabled",
                                        activation=Activation.ON_BY_DEFAULT))
    _store({(1, "logging.enabled"): False, (None, "logging.enabled"): True})
    # per-guild explicit beats global + activation
    assert asyncio.run(resolve(1, "logging", "enabled")) is False
    # global explicit beats activation
    assert asyncio.run(resolve(2, "logging", "enabled")) is True


def test_activation_terminus_on_by_default_and_opt_in():
    register_setting(SettingDeclaration("help", "enabled",
                                        activation=Activation.ON_BY_DEFAULT))
    register_setting(SettingDeclaration("image_mod", "enabled",
                                        activation=Activation.OFF_UNTIL_OPT_IN))
    assert asyncio.run(resolve(1, "help", "enabled")) is True
    assert asyncio.run(resolve(1, "image_mod", "enabled")) is False


def test_on_when_keyed_resolves_once_at_boot():
    register_setting(SettingDeclaration("ai", "enabled",
                                        activation=Activation.ON_WHEN_KEYED,
                                        keyed_secret="ANTHROPIC_API_KEY"))

    class Cfg:
        def is_configured(self, name):
            return name == "ANTHROPIC_API_KEY"

    install_secret_presence(Cfg())
    assert asyncio.run(resolve(1, "ai", "enabled")) is True

    class Bare:
        def is_configured(self, name):
            return False

    install_secret_presence(Bare())
    assert asyncio.run(resolve(1, "ai", "enabled")) is False


def test_on_when_bound_is_dynamic_per_read():
    register_setting(SettingDeclaration("logging", "message_log",
                                        activation=Activation.ON_WHEN_BOUND,
                                        bound_binding="log_channel"))
    bound = {"state": False}

    async def probe(guild_id, binding):
        assert binding == "log_channel"
        return bound["state"]

    install_binding_probe(probe)
    assert asyncio.run(resolve(1, "logging", "message_log")) is False
    bound["state"] = True   # flips with the binding, both directions
    assert asyncio.run(resolve(1, "logging", "message_log")) is True


def test_non_bool_terminates_at_static_default():
    register_setting(SettingDeclaration("economy", "daily_amount", default=100))
    assert asyncio.run(resolve(1, "economy", "daily_amount")) == 100
    _store({(None, "economy.daily_amount"): 250})
    assert asyncio.run(resolve(1, "economy", "daily_amount")) == 250


def test_one_owning_declaration_per_key():
    register_setting(SettingDeclaration("x", "y"))
    with pytest.raises(ValueError, match="already declared"):
        register_setting(SettingDeclaration("x", "y"))
    with pytest.raises(ValueError, match="keyed_secret"):
        register_setting(SettingDeclaration("x", "k",
                                            activation=Activation.ON_WHEN_KEYED))
    with pytest.raises(ValueError, match="bound_binding"):
        register_setting(SettingDeclaration("x", "b",
                                            activation=Activation.ON_WHEN_BOUND))
