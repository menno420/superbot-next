"""The owner-ordered render rule (presentation rework, D-0055): an empty
section renders a MEANINGFUL line — why it is empty and what arrives next —
never a bare em-dash. Roster-free (no sb.manifest import)."""

from __future__ import annotations

import asyncio

from sb.kernel import settings as settings_mod


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def test_spine_hub_with_no_declared_settings_explains_itself():
    from sb.domain.operator_spine import _ensure_settings_provider
    from sb.spec.refs import resolve as resolve_ref

    settings_mod.clear_for_tests()
    try:
        ref = _ensure_settings_provider("admin")
        rows = run(resolve_ref(ref)(type("Ctx", (), {"guild_id": 42})()))
        assert len(rows) == 1
        name, value = rows[0]
        assert name == "No declared settings"
        assert "declares no settings yet" in value
        assert "operator-spine successor" in value
        assert "—" not in value                       # never a bare dash
    finally:
        settings_mod.clear_for_tests()


def test_spine_hub_with_declared_settings_lists_them():
    from sb.domain.operator_spine import _ensure_settings_provider
    from sb.spec.refs import resolve as resolve_ref

    settings_mod.clear_for_tests()
    try:
        settings_mod.register_setting(settings_mod.SettingDeclaration(
            subsystem="welcome", name="enabled",
            activation=settings_mod.Activation.ON_BY_DEFAULT))
        ref = _ensure_settings_provider("welcome")
        rows = run(resolve_ref(ref)(type("Ctx", (), {"guild_id": 42})()))
        assert ("enabled", "`True`") in rows
    finally:
        settings_mod.clear_for_tests()
