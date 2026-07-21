"""The armed settings-hub audit view (settings-admin slice 2): the 🕒
Recent-changes hub button routes to the declared ``settings.audit``
PanelRef open-child sub-panel — oracle disbot/views/settings/
audit_view.py (the last-10 settings-mutation audit rows, DM guard +
missing-table + empty-table degrades) ported over the K7 central audit
spine: ``audit_log`` rows with ``subsystem='settings'``, read through
the K3 pool seam (the btd6 D-0046 re-home precedent). The frozen
``settings_hub.audit`` custom_id never moves (only the server-side route
did); the command-access pending terminal stays untouched (slice 3)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
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


def _ctx(params=None, guild_id=GID):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=guild_id, actor=SimpleNamespace(user_id=42),
        channel_id=CHAN, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(),
        params=dict(params or {}))


def _fields():
    from sb.spec.refs import ProviderRef, resolve

    return resolve(ProviderRef("settings.audit_fields"))


def _install_rows(monkeypatch, rows):
    """Stub the audit-spine read (sb.kernel.db.pool.fetchall); records
    the (query, params) calls."""
    from sb.kernel.db import pool

    calls: list[tuple[str, tuple]] = []

    async def fake_fetchall(query, params=(), *, conn=None):
        calls.append((query, params))
        if isinstance(rows, Exception):
            raise rows
        return list(rows)

    monkeypatch.setattr(pool, "fetchall", fake_fetchall)
    return calls


def _row(*, verb="setting_set", target="settings.set_scalar",
         prev=None, new=None, actor_id=42, actor_type="user",
         at=datetime(2026, 7, 13, 12, 0, 0, tzinfo=timezone.utc)):
    return {"mutation_type": verb, "target": target, "prev_value": prev,
            "new_value": new, "actor_id": actor_id,
            "actor_type": actor_type, "occurred_at": at}


# --- the spec + hub route ---------------------------------------------------------


def test_audit_spec_shape_is_the_shipped_view():
    from sb.domain.settings.panels import settings_audit_spec
    from sb.kernel.panels.compile import check_panel
    from sb.spec.panels import Audience, FooterMode
    from sb.spec.refs import HandlerRef, PanelRef, ProviderRef

    spec = settings_audit_spec()
    check_panel(spec)
    assert spec.panel_id == "settings.audit"
    assert spec.title == "🕒 Recent settings changes"
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "blurple"    # discord.Color.blurple()
    assert spec.frame.footer_mode is FooterMode.NONE
    assert spec.session_lifecycle is True
    assert spec.navigation.parent == PanelRef("settings.hub")
    assert spec.renderer_override == HandlerRef("settings.render_audit")
    assert spec.body[1].provider == ProviderRef("settings.audit_fields")
    (back,) = spec.actions
    assert back.handler == PanelRef("settings.hub")
    assert back.label == "Back to Hub"
    assert back.emoji == "↩"
    # run-minted (no new compat pin) — the shipped settings_audit.back
    # id is not in the freeze.
    assert back.custom_id_override == ""


def test_hub_audit_button_routes_to_the_panel_on_the_frozen_wire_id():
    from sb.domain.settings.panels import settings_hub_spec
    from sb.spec.refs import PanelRef

    by_id = {a.action_id: a for a in settings_hub_spec().actions}
    assert by_id["audit"].handler == PanelRef("settings.audit")
    assert by_id["audit"].custom_id_override == "settings_hub.audit"
    assert by_id["audit"].label == "Recent changes"
    assert by_id["audit"].emoji == "🕒"


# --- the fields provider: the shipped body over the spine read --------------------


def test_audit_dm_guard_is_the_shipped_copy(monkeypatch):
    calls = _install_rows(monkeypatch, ())
    fields = run(_fields()(_ctx(guild_id=0)))
    assert fields == (
        ("Result",
         "*Run this from within a guild — DM has no audit history.*"),)
    assert calls == []                     # the guard returns before the read


def test_audit_empty_state_is_the_shipped_copy(monkeypatch):
    calls = _install_rows(monkeypatch, ())
    fields = run(_fields()(_ctx()))
    assert fields == (("Result", "*No audit rows for this guild yet.*"),)
    # the read is guild-scoped to the settings subsystem, last-10.
    (query, params) = calls[0]
    assert "FROM audit_log" in query
    assert "subsystem = 'settings'" in query
    assert "ORDER BY occurred_at DESC LIMIT 10" in query
    assert params == (GID,)


def test_audit_read_soft_fails_like_the_shipped_missing_table(monkeypatch):
    _install_rows(monkeypatch, RuntimeError("relation does not exist"))
    fields = run(_fields()(_ctx()))
    assert fields == ((
        "Audit table",
        "*Could not read `audit_log` — "
        "`RuntimeError: relation does not exist`.  "
        "Migration 0003 may not have been applied yet.*"),)


def test_audit_lines_render_the_scalar_rollup_as_the_shipped_shape(
        monkeypatch):
    _install_rows(monkeypatch, (
        _row(prev='{"write_scalar": {"key": "welcome.delay", '
                  '"value": null}}',
             new='{"write_scalar": {"key": "welcome.delay", '
                 '"value": "5"}}'),
        _row(verb="setting_cleared", target="settings.clear_scalar",
             prev='{"erase_scalar": {"key": "welcome.delay", '
                  '"value": "5"}}',
             new='{"erase_scalar": {"key": "welcome.delay", '
                 '"value": null}}',
             actor_id=7, actor_type="system",
             at=datetime(2026, 7, 13, 11, 0, 0, tzinfo=timezone.utc)),
    ))
    fields = run(_fields()(_ctx()))
    assert fields == ((
        "Last 2 change(s)",
        "`2026-07-13 12:00:00Z` `welcome.delay` = `'5'` (was `None`) "
        "by `user` `42`\n"
        "`2026-07-13 11:00:00Z` `welcome.delay` = `None` (was `'5'`) "
        "by `system` `7`"),)


def test_audit_binding_rows_fall_back_to_the_op_target_label(monkeypatch):
    _install_rows(monkeypatch, (
        _row(verb="binding_set", target="settings.bind",
             prev='{"write_binding": {"resource_id": null}}',
             new='{"write_binding": {"resource_id": 555}}'),
    ))
    fields = run(_fields()(_ctx()))
    assert fields == ((
        "Last 1 change(s)",
        "`2026-07-13 12:00:00Z` `settings.bind` = `555` (was `None`) "
        "by `user` `42`"),)


def test_audit_unparseable_rollup_degrades_to_the_raw_text(monkeypatch):
    _install_rows(monkeypatch, (
        _row(prev=None, new="not json", at=None),))
    fields = run(_fields()(_ctx()))
    assert fields == ((
        "Last 1 change(s)",
        "`—` `settings.set_scalar` = `'not json'` (was `None`) "
        "by `user` `42`"),)


# --- the renderer override: the shipped guild-keyed footer ------------------------


def test_audit_footer_renders_only_on_the_rows_path(monkeypatch):
    from sb.domain.settings.panels import _render_audit, settings_audit_spec

    _install_rows(monkeypatch, (
        _row(new='{"write_scalar": {"key": "welcome.delay", '
                 '"value": "5"}}'),))
    rendered = run(_render_audit(settings_audit_spec(), _ctx()))
    assert rendered.embed.footer == (
        f"audit_log · subsystem=settings · guild_id={GID}")

    _install_rows(monkeypatch, ())
    rendered = run(_render_audit(settings_audit_spec(), _ctx()))
    assert rendered.embed.footer == ""     # the shipped early return


def test_audit_and_group_pending_terminals_are_retired():
    from sb.domain.settings import handlers
    from sb.spec.refs import HandlerRef, is_registered

    handlers.ensure_handler_refs()
    assert not is_registered(HandlerRef("settings.audit_pending"))
    # slice 3 retired the command-access terminal too; settings epic S0
    # retired the last one — the per-group edit page (settings.group_edit)
    # displaced settings.group_pending (option A).
    assert not is_registered(HandlerRef("settings.command_access_pending"))
    assert not is_registered(HandlerRef("settings.group_pending"))
