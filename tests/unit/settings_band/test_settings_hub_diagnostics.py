"""The armed settings-hub diagnostics (settings-admin slice 1): the three
read-only hub buttons (📋 Needs setup / ⚠️ Invalid settings / 🔗 Missing
bindings) route to declared PanelRef open-child sub-panels — oracle
disbot/views/settings/{needs_setup,invalid_settings,missing_bindings}.py
copy verbatim over the manifest declaration walk, the K7 typed resolution
(service.resolve_setting) and the subsystem_bindings store read. The
frozen ``settings_hub.*`` custom_ids never move (only server-side routes
did — the armed-explorer PR precedent), and the audit / command-access
pending terminals stay untouched (slices 2/3)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run

GID, CHAN = 1, 200


@pytest.fixture(autouse=True)
def _armed_refs():
    """Re-arm the settings refs (suite-order registry resets)."""
    from sb.domain.settings import handlers, panels

    panels.ensure_panel_refs()
    handlers.ensure_handler_refs()
    yield


# --- fakes ---------------------------------------------------------------------


def _ctx(params=None, guild_id=GID):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=guild_id, actor=SimpleNamespace(user_id=42),
        channel_id=CHAN, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(),
        params=dict(params or {}))


def _binding(name, kind=None, required=False):
    from sb.spec.settings import BindingKind, BindingSpec

    return BindingSpec(name=name, kind=kind or BindingKind.CHANNEL,
                       required=required)


def _resource(intent, priority=None):
    from sb.spec.settings import (
        ProvisioningHint,
        ProvisioningPriority,
        ResourceKind,
        ResourceRequirement,
    )

    return ResourceRequirement(
        kind=ResourceKind.CHANNEL, intent=intent,
        provisioning=ProvisioningHint(
            priority=priority or ProvisioningPriority.OPTIONAL))


def _setting(name, default=0):
    from sb.spec.settings import SettingSpec

    return SettingSpec(name=name, value_type=int, default=default)


def _install_facets(monkeypatch, facets):
    """Stub the ONE manifest inventory walk: ((key, manifest), ...)."""
    from sb.domain.settings import panels

    monkeypatch.setattr(panels, "_iter_settings_facets", lambda: facets)


def _facet(key, *specs):
    return (key, SimpleNamespace(key=key, settings=tuple(specs)))


def _install_resolution(monkeypatch, results: dict):
    """Stub the K7 typed read: {(subsystem, name): SettingResolution |
    Exception}; records the calls."""
    from sb.domain.settings import service

    calls: list[tuple] = []

    async def fake_resolve(guild_id, subsystem, name, spec=None):
        calls.append((guild_id, subsystem, name, spec))
        result = results[(subsystem, name)]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(service, "resolve_setting", fake_resolve)
    return calls


def _resolution(subsystem, name, *, valid=True, raw=None, default=0,
                diagnostics=()):
    from sb.domain.settings.service import SettingResolution

    return SettingResolution(
        subsystem=subsystem, name=name, value=default,
        provenance="explicit" if raw is not None else "default",
        default=default, valid=valid, raw=raw,
        diagnostics=tuple(diagnostics))


def _install_binding_rows(monkeypatch, rows):
    """Stub the subsystem_bindings store read (fetchall_bindings)."""
    from sb.kernel.db import settings as db_settings

    async def fake_fetchall(guild_id, conn=None):
        assert guild_id == GID
        return list(rows)

    monkeypatch.setattr(db_settings, "fetchall_bindings", fake_fetchall)


def _fields(name):
    from sb.spec.refs import ProviderRef, resolve

    return resolve(ProviderRef(name))


# --- the hub routes: armed PanelRefs, frozen wire ids, honest leftovers ----------


def test_hub_routes_the_armed_diagnostics_and_keeps_the_frozen_ids():
    from sb.domain.settings.panels import settings_hub_spec
    from sb.kernel.panels.compile import check_panel
    from sb.spec.refs import HandlerRef, PanelRef

    spec = settings_hub_spec()
    check_panel(spec)
    by_id = {a.action_id: a for a in spec.actions}
    # the four armed diagnostics — PanelRef open-child terminals
    # (slice 1: the read-only trio; slice 2: the audit view).
    assert by_id["needs_setup"].handler == PanelRef("settings.needs_setup")
    assert by_id["invalid"].handler == PanelRef("settings.invalid")
    assert by_id["missing_bindings"].handler == PanelRef(
        "settings.missing_bindings")
    assert by_id["audit"].handler == PanelRef("settings.audit")
    # slice 3 keeps its honest pending terminal.
    assert by_id["command_access"].handler == HandlerRef(
        "settings.command_access_pending")
    # the compat-frozen wire ids never move.
    for action_id in ("needs_setup", "invalid", "missing_bindings",
                      "audit", "command_access"):
        assert (by_id[action_id].custom_id_override
                == f"settings_hub.{action_id}")


def test_the_retired_pending_refs_stay_gone_and_the_kept_ones_stay():
    from sb.domain.settings import handlers
    from sb.spec.refs import HandlerRef, is_registered

    handlers.ensure_handler_refs()
    for name in ("settings.needs_setup_pending",
                 "settings.invalid_pending",
                 "settings.missing_bindings_pending",
                 "settings.audit_pending"):        # slice 2 retired it
        assert not is_registered(HandlerRef(name)), name
    for name in ("settings.command_access_pending",
                 "settings.group_pending"):
        assert is_registered(HandlerRef(name)), name


def test_diagnostic_specs_compile_and_carry_the_back_door():
    from sb.domain.settings.panels import (
        settings_audit_spec,
        settings_invalid_spec,
        settings_missing_bindings_spec,
        settings_needs_setup_spec,
    )
    from sb.kernel.panels.compile import check_panel
    from sb.spec.refs import PanelRef

    for spec in (settings_needs_setup_spec(), settings_invalid_spec(),
                 settings_missing_bindings_spec(), settings_audit_spec()):
        check_panel(spec)
        assert spec.session_lifecycle is True
        assert spec.navigation.parent == PanelRef("settings.hub")
        (back,) = spec.actions
        assert back.handler == PanelRef("settings.hub")
        assert back.label == "Back to Hub"
        assert back.emoji == "↩"
        # run-minted (no new compat pin) — the shipped settings_*.back
        # ids are not in the freeze.
        assert back.custom_id_override == ""


# --- 📋 Needs setup: declaration-only planning view ------------------------------


def test_needs_setup_lists_required_bindings_and_resources(monkeypatch):
    from sb.spec.settings import ProvisioningPriority

    _install_facets(monkeypatch, (
        _facet("economy",
               _resource("log_channel", ProvisioningPriority.REQUIRED),
               _resource("shop_window")),          # optional — filtered out
        _facet("welcome",
               _binding("channel", required=True),
               _binding("entry_role")),            # optional — filtered out
    ))
    fields = run(_fields("settings.needs_setup_fields")(_ctx()))
    assert fields == (
        ("Required bindings (1)", "`welcome` — required: `channel`"),
        ("Required resources (1)", "`economy` — required: `log_channel`"))


def test_needs_setup_empty_state_is_the_shipped_copy(monkeypatch):
    _install_facets(monkeypatch, (
        _facet("welcome", _binding("channel"), _setting("delay")),))
    fields = run(_fields("settings.needs_setup_fields")(_ctx()))
    assert fields == (
        ("Result",
         "*No subsystem declares any required bindings or resources.*"),)


def test_needs_setup_footer_carries_the_coverage_counts(monkeypatch):
    from sb.domain.governance.registry import SUBSYSTEM_META
    from sb.domain.settings.panels import (
        _render_needs_setup,
        settings_needs_setup_spec,
    )
    from sb.spec.settings import ProvisioningPriority

    _install_facets(monkeypatch, (
        _facet("economy",
               _resource("log_channel", ProvisioningPriority.REQUIRED)),
        _facet("welcome", _binding("channel", required=True)),
    ))
    rendered = run(_render_needs_setup(settings_needs_setup_spec(), _ctx()))
    assert rendered.embed.footer == (
        "1 subsystem(s) with required bindings · "
        "1 with required resources · "
        f"{len(SUBSYSTEM_META)} subsystems total.")


def test_needs_setup_empty_state_sets_no_footer(monkeypatch):
    from sb.domain.settings.panels import (
        _render_needs_setup,
        settings_needs_setup_spec,
    )

    _install_facets(monkeypatch, ())
    rendered = run(_render_needs_setup(settings_needs_setup_spec(), _ctx()))
    assert rendered.embed.footer == ""     # the shipped early return


# --- ⚠️ Invalid settings: the K7 typed-resolution walk ----------------------------


def test_invalid_lists_the_failed_rows_verbatim(monkeypatch):
    _install_facets(monkeypatch, (
        _facet("welcome", _setting("delete_after"), _setting("delay"),
               _binding("channel")),                # bindings never scanned
    ))
    calls = _install_resolution(monkeypatch, {
        ("welcome", "delete_after"): _resolution(
            "welcome", "delete_after", valid=False, raw="abc", default=0,
            diagnostics=("coercion_failed: not an int",)),
        ("welcome", "delay"): _resolution("welcome", "delay"),
    })
    fields = run(_fields("settings.invalid_fields")(_ctx()))
    assert fields == ((
        "Invalid settings (1 of 2 scanned)",
        "`welcome.delete_after` = `'abc'` → fallback to `0` "
        "(coercion_failed: not an int)"),)
    # the walk resolved through the typed seam, spec attached.
    assert [(c[0], c[1], c[2]) for c in calls] == [
        (GID, "welcome", "delete_after"), (GID, "welcome", "delay")]
    assert all(c[3] is not None for c in calls)


def test_invalid_soft_fails_a_raising_row(monkeypatch):
    _install_facets(monkeypatch, (_facet("welcome", _setting("delay")),))
    _install_resolution(monkeypatch, {
        ("welcome", "delay"): RuntimeError("store down")})
    fields = run(_fields("settings.invalid_fields")(_ctx()))
    assert fields == ((
        "Invalid settings (1 of 1 scanned)",
        "`welcome.delay` — resolver raised RuntimeError"),)


def test_invalid_clean_scan_is_the_shipped_success_copy(monkeypatch):
    _install_facets(monkeypatch, (
        _facet("welcome", _setting("delete_after"), _setting("delay")),))
    _install_resolution(monkeypatch, {
        ("welcome", "delete_after"): _resolution("welcome", "delete_after"),
        ("welcome", "delay"): _resolution("welcome", "delay"),
    })
    fields = run(_fields("settings.invalid_fields")(_ctx()))
    assert fields == (
        ("Result", "*✅ No invalid settings.  (2 setting(s) scanned.)*"),)


def test_invalid_dm_guard_is_the_shipped_copy():
    fields = run(_fields("settings.invalid_fields")(_ctx(guild_id=0)))
    assert fields == (
        ("Result",
         "*Run this from within a guild — DM has no scalar values "
         "to resolve.*"),)


def test_invalid_footer_renders_only_with_findings(monkeypatch):
    from sb.domain.settings.panels import (
        _INVALID_FOOTER,
        _render_invalid,
        settings_invalid_spec,
    )

    _install_facets(monkeypatch, (_facet("welcome", _setting("delay")),))
    _install_resolution(monkeypatch, {
        ("welcome", "delay"): _resolution(
            "welcome", "delay", valid=False, raw="x", default=0)})
    rendered = run(_render_invalid(settings_invalid_spec(), _ctx()))
    assert rendered.embed.footer == _INVALID_FOOTER

    _install_resolution(monkeypatch, {
        ("welcome", "delay"): _resolution("welcome", "delay")})
    rendered = run(_render_invalid(settings_invalid_spec(), _ctx()))
    assert rendered.embed.footer == ""     # the shipped no-findings shape


# --- 🔗 Missing bindings: declared slots vs the binding store ---------------------


def test_missing_bindings_lists_every_non_bound_slot(monkeypatch):
    from sb.spec.settings import BindingKind

    _install_facets(monkeypatch, (
        _facet("economy", _binding("log_channel", required=True)),
        _facet("welcome",
               _binding("channel"),
               _binding("entry_role", BindingKind.ROLE)),
    ))
    _install_binding_rows(monkeypatch, (
        {"subsystem": "welcome", "binding_name": "channel",
         "kind": "channel", "target_id": 555, "status": "bound"},
        {"subsystem": "economy", "binding_name": "log_channel",
         "kind": "channel", "target_id": 777, "status": "missing"},
        # welcome.entry_role has NO row — the shipped `unresolved`.
    ))
    fields = run(_fields("settings.missing_bindings_fields")(_ctx()))
    assert fields == ((
        "Unbound or invalid bindings (2 of 3 scanned)",
        "`economy.log_channel` (**required**) — status=`missing` "
        "kind=`channel`\n"
        "`welcome.entry_role` (optional) — status=`unresolved` "
        "kind=`role`"),)


def test_missing_bindings_all_bound_is_the_shipped_success_copy(monkeypatch):
    _install_facets(monkeypatch, (_facet("welcome", _binding("channel")),))
    _install_binding_rows(monkeypatch, (
        {"subsystem": "welcome", "binding_name": "channel",
         "kind": "channel", "target_id": 555, "status": "bound"},))
    fields = run(_fields("settings.missing_bindings_fields")(_ctx()))
    assert fields == (
        ("Result", "*✅ Every binding is bound.  (1 binding(s) scanned.)*"),)


def test_missing_bindings_bound_status_without_target_is_not_bound(
        monkeypatch):
    """The shipped is_bound demands target AND status (bindings.py:99)."""
    _install_facets(monkeypatch, (_facet("welcome", _binding("channel")),))
    _install_binding_rows(monkeypatch, (
        {"subsystem": "welcome", "binding_name": "channel",
         "kind": "channel", "target_id": None, "status": "bound"},))
    fields = run(_fields("settings.missing_bindings_fields")(_ctx()))
    assert "`welcome.channel` (optional) — status=`bound`" in fields[0][1]


def test_missing_bindings_dm_guard_is_the_shipped_copy():
    fields = run(_fields("settings.missing_bindings_fields")(
        _ctx(guild_id=0)))
    assert fields == (
        ("Result",
         "*Run this from within a guild — DM has no per-guild binding "
         "state.*"),)


def test_missing_bindings_store_read_soft_fails(monkeypatch):
    from sb.kernel.db import settings as db_settings

    _install_facets(monkeypatch, (_facet("welcome", _binding("channel")),))

    async def boom(guild_id, conn=None):
        raise TimeoutError("pool gone")

    monkeypatch.setattr(db_settings, "fetchall_bindings", boom)
    fields = run(_fields("settings.missing_bindings_fields")(_ctx()))
    assert fields == (
        ("Result", "*Binding store read raised TimeoutError — try again.*"),)


# --- the real manifest walk stays sane -------------------------------------------


def test_the_manifest_walk_yields_sorted_unique_keys():
    from sb.domain.settings.panels import _iter_settings_facets

    facets = _iter_settings_facets()
    keys = [key for key, _ in facets]
    assert keys == sorted(keys)
    assert "settings" in keys and "welcome" in keys
    # every facet object answers the duck-read the gatherers use.
    assert all(hasattr(m, "settings") for _, m in facets)
