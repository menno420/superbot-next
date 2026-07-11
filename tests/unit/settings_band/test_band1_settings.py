"""Band-1 settings subsystem tests: facet fences, the manifest bridge,
ops registration + leg writes, coercion, the legacy vocabulary, panels,
and the K10 reader installs' fail-closed fallbacks."""

from __future__ import annotations

import asyncio

import pytest

from sb.kernel import settings as ksettings
from sb.spec.settings import (
    Activation,
    BindingKind,
    BindingSpec,
    PresetKind,
    ProvisioningHint,
    ProvisioningPriority,
    ResourceKind,
    ResourceRequirement,
    SettingSpec,
    check_setting_spec,
    validate_settings_facets,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    ksettings.clear_for_tests()
    yield
    ksettings.clear_for_tests()


# --- facet grammar fences (design-spec §2.5/§4.4) --------------------------------

def test_bool_spec_requires_activation():
    spec = SettingSpec(name="enabled", value_type=bool, default=False)
    problems = check_setting_spec("karma", spec)
    assert any("must declare `activation`" in p for p in problems)


def test_non_bool_spec_refuses_activation():
    spec = SettingSpec(name="cooldown", value_type=int, default=60,
                       activation=Activation.ON_BY_DEFAULT)
    assert any("must leave `activation` None" in p
               for p in check_setting_spec("karma", spec))


def test_external_side_effects_forces_opt_in():
    spec = SettingSpec(name="scan", value_type=bool, default=False,
                       activation=Activation.ON_BY_DEFAULT,
                       external_side_effects=True)
    assert any("off_until_opt_in" in p for p in check_setting_spec("imgmod", spec))
    clean = SettingSpec(name="scan", value_type=bool, default=False,
                        activation=Activation.OFF_UNTIL_OPT_IN,
                        external_side_effects=True)
    assert check_setting_spec("imgmod", clean) == []


def test_str_presets_require_text_preset_kind():
    spec = SettingSpec(name="dm_template", value_type=str, default="",
                       presets=("hi", "bye"))
    assert any("preset_kind=text" in p for p in check_setting_spec("mod", spec))
    ok = SettingSpec(name="dm_template", value_type=str, default="",
                     presets=("hi",), preset_kind=PresetKind.TEXT)
    assert check_setting_spec("mod", ok) == []


def test_value_type_canonicalizes_and_rejects_junk():
    assert SettingSpec(name="x", value_type=int, default=1).value_type == "int"
    assert SettingSpec(name="y", value_type="list[int]", default=[]).is_list
    with pytest.raises(ValueError):
        SettingSpec(name="z", value_type=dict, default={})


def test_binding_resource_link_cross_validation():
    class _M:
        key = "logging"
        settings = (
            BindingSpec(name="mod_channel", kind=BindingKind.CHANNEL,
                        required=True, hint="", capability_required="",
                        resource_link="ghost"),
        )
    problems = validate_settings_facets(_M())
    assert any("names no declared ResourceRequirement" in p for p in problems)

    class _M2:
        key = "logging"
        settings = (
            ResourceRequirement(
                kind=ResourceKind.CHANNEL, intent="log_destination",
                provisioning=ProvisioningHint(ProvisioningPriority.RECOMMENDED),
                binding_name="mod_channel"),
            BindingSpec(name="mod_channel", kind=BindingKind.CHANNEL,
                        required=True, hint="", capability_required="",
                        resource_link="mod_channel"),
        )
    assert validate_settings_facets(_M2()) == []


# --- the manifest bridge + tri-state resolve -------------------------------------

def _manifest(settings=()):
    class _M:
        key = "karma"
    _M.settings = settings
    return _M()


def test_register_manifest_settings_and_persisted_key():
    minted = ksettings.register_manifest_settings(_manifest((
        SettingSpec(name="enabled", value_type=bool, default=False,
                    settings_key="karma_enabled",
                    activation=Activation.ON_BY_DEFAULT),
        SettingSpec(name="cooldown", value_type=int, default=60,
                    settings_key="karma_cooldown"),
    )))
    assert [d.key for d in minted] == ["karma.enabled", "karma.cooldown"]
    assert ksettings.persisted_key("karma", "enabled") == "karma_enabled"
    # activation terminus: unset bool resolves ON_BY_DEFAULT -> True
    assert asyncio.run(ksettings.resolve(1, "karma", "enabled")) is True
    assert asyncio.run(ksettings.resolve(1, "karma", "cooldown")) == 60


def test_bridge_runs_fences():
    with pytest.raises(ValueError, match="settings facet fences"):
        ksettings.register_manifest_settings(_manifest((
            SettingSpec(name="enabled", value_type=bool, default=False),
        )))


# --- coercion (ported settings_resolution semantics) ------------------------------

def test_coerce_value_bool_int_bounds_and_fallback():
    from sb.domain.settings.service import coerce_value

    b = SettingSpec(name="on", value_type=bool, default=False,
                    activation=Activation.OFF_UNTIL_OPT_IN)
    assert coerce_value(b, "true") == (True, True, ())
    n = SettingSpec(name="n", value_type=int, default=5, bounds=(1, 10))
    assert coerce_value(n, "7") == (7, True, ())
    value, valid, diags = coerce_value(n, "99")
    assert (value, valid) == (5, False) and diags
    lst = SettingSpec(name="ids", value_type="list[int]", default=[])
    assert coerce_value(lst, "[1, 2]") == ([1, 2], True, ())


# --- ops + stores -----------------------------------------------------------------

def test_ops_register_and_are_natural_key():
    from sb.domain.settings.ops import register_ops
    from sb.kernel.workflow.registry import REGISTRY

    register_ops()
    register_ops()   # idempotent
    spec = REGISTRY.resolve_op_kind("settings.set_scalar")
    assert spec.lane.value == "scalar" and spec.idempotency.value == "natural_key"
    assert REGISTRY.resolve_op_kind("settings.bind").lane.value == "binding"


def test_stores_are_registered_and_lifecycle_clean():
    from sb.kernel.db.settings import BINDINGS_STORE, SETTINGS_STORE
    from tools.check_data_lifecycle import check as lifecycle_check
    from tools.check_rollback_disposition import check as rollback_check

    assert SETTINGS_STORE.table == "settings"
    assert lifecycle_check([SETTINGS_STORE, BINDINGS_STORE]) == []
    assert rollback_check([SETTINGS_STORE, BINDINGS_STORE],
                          covered=frozenset(), retired_tables=frozenset()) == []


# --- vocabulary --------------------------------------------------------------------

def test_legacy_vocabulary_is_complete_and_verbatim():
    from sb.domain.settings.keys import ALL_LEGACY_KEYS, LEGACY_SETTINGS_KEYS, owning_module

    assert len(LEGACY_SETTINGS_KEYS) == 17
    assert len(ALL_LEGACY_KEYS) == 124
    assert LEGACY_SETTINGS_KEYS["karma"]["KARMA_COOLDOWN"] == "karma_cooldown"
    assert owning_module("logging_enabled") == "logging"
    assert owning_module("net_new_key") is None


# --- panels + manifest -------------------------------------------------------------

def test_settings_hub_panel_registers():
    from sb.domain.settings.panels import install_settings_panels

    spec = install_settings_panels()
    assert spec.panel_id == "settings.hub"
    assert install_settings_panels().panel_id == "settings.hub"  # idempotent


def test_manifest_compiles_in_isolation():
    import sb.manifest.settings as m
    from tools.manifest_compile import compile_manifests

    m.ENSURE_REFS()
    result = compile_manifests(manifests=[m.MANIFEST])
    assert result.ok, [str(v) for v in result.violations]


# --- K10 seam installs --------------------------------------------------------------

def test_ai_readers_fail_closed_without_declarations():
    from sb.domain.settings.ai_readers import _memory_settings, _policy_bundle

    # undeclared / never-written ai.* keys → the shipped
    # GUILD_NOT_CONFIGURED posture: NO policy row (band-7 parity — the
    # resolver denies with the shipped reason code, not
    # AI_GLOBALLY_DISABLED; goldens/ai/sweep_ai_policy pins the trace).
    bundle = asyncio.run(_policy_bundle(1))
    assert bundle.policy is None
    assert bundle.channel == {} and bundle.role == {}
    assert asyncio.run(_memory_settings(1)) == (0, False)


def test_legacy_task_ids_claimable():
    from sb.domain.settings.ai_tasks import register_ai_tasks
    from sb.kernel.ai import tasks

    register_ai_tasks()
    register_ai_tasks()   # idempotent
    assert tasks.get_task("settings.explain").owner_subsystem == "settings"
    assert tasks.get_task("settings.propose").owner_subsystem == "settings"
