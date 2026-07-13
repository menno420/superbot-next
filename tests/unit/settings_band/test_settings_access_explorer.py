"""The armed Access Policy Explorer (curation rows 82-87,
docs/review/curation-report-2026-07-13.md L1237-1242): the governance
diagnostic read seam (``governance.resolve_subsystem_state`` — the exact
name the retired pending copy promised), the six armed controls
(subsystem/scope selects, Explain, Reset, ◀ Prev / Next ▶) and the
explorer-open byte pin (parity/goldens/settings/sweep_settings_access
replays UNCHANGED — persistent custom_ids + open-state bytes identical;
only server-side handler routes moved)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run

GID, CHAN, CAT = 1, 200, 300


@pytest.fixture(autouse=True)
def _armed_refs():
    """Re-arm the settings refs (suite-order registry resets) and start
    every test from an empty explorer session table."""
    from sb.domain.settings import handlers, panels

    panels.ensure_panel_refs()
    handlers.ensure_handler_refs()
    handlers._ACCESS_SESSIONS.clear()
    yield
    handlers._ACCESS_SESSIONS.clear()


# --- fakes ---------------------------------------------------------------------


def _install_rows(monkeypatch, rows: dict):
    """Stub the ONE store read the seam uses:
    {(scope_type, scope_id): {subsystem: True|False|None}}."""
    from sb.domain.governance import store

    async def fake_fetch(guild_id, chain, conn=None):
        assert guild_id == GID
        return {key: dict(val) for key, val in rows.items()
                if key in set(chain)}

    monkeypatch.setattr(store, "fetch_visibility_for_chain", fake_fetch)


def _req(args=None, guild_id=GID, message_id=900, category_id=CAT):
    channel = SimpleNamespace(category_id=category_id)
    message = SimpleNamespace(id=message_id) if message_id else None
    return SimpleNamespace(
        args=dict(args or {}), guild_id=guild_id, channel_id=CHAN,
        actor=SimpleNamespace(user_id=42), request_id="req-1",
        confirmed=False,
        origin=SimpleNamespace(
            message=message, channel=channel,
            author=SimpleNamespace(display_name="AdminActor")))


def _handler(name):
    from sb.spec.refs import HandlerRef, resolve

    return resolve(HandlerRef(name))


def _install_refresh(monkeypatch, ok: bool = True):
    """Stub the engine's in-place re-render; records (message_key, params)."""
    import sb.kernel.panels.engine as engine

    calls: list[tuple[str, dict]] = []

    async def fake_refresh(req, *, message_key, params, expire=False):
        calls.append((message_key, dict(params)))
        return ok

    monkeypatch.setattr(engine, "refresh_session_view", fake_refresh)
    return calls


def _resolution(subsystem="games", state="enabled", source="registry_default",
                checks=(), blocks=(), known=True, tier="user"):
    from sb.domain.governance.models import PolicySource, SubsystemState
    from sb.domain.governance.service import SubsystemResolution

    return SubsystemResolution(
        subsystem=subsystem, known=known,
        state=next(s for s in SubsystemState if s.value == state),
        source=next(p for p in PolicySource if p.value == source),
        checks=tuple(checks), dependency_blocks=tuple(blocks),
        visibility_tier=tier)


def _install_seam(monkeypatch, resolution):
    """Stub the governance diagnostic read; records the call axes."""
    from sb.domain.governance import service

    calls: list[dict] = []

    async def fake_resolve(guild_id, subsystem, **axes):
        calls.append({"guild_id": guild_id, "subsystem": subsystem, **axes})
        return resolution

    monkeypatch.setattr(service, "resolve_subsystem_state", fake_resolve)
    return calls


# --- the read seam: resolution + provenance -------------------------------------


def test_channel_override_beats_guild_override(monkeypatch):
    from sb.domain.governance.models import PolicySource, SubsystemState
    from sb.domain.governance.service import resolve_subsystem_state

    _install_rows(monkeypatch, {("channel", CHAN): {"games": False},
                                ("guild", GID): {"games": True}})
    res = run(resolve_subsystem_state(GID, "games", channel_id=CHAN,
                                      category_id=CAT))
    assert res.known is True
    assert res.state is SubsystemState.DISABLED
    assert res.source is PolicySource.CHANNEL_OVERRIDE
    # the walked chain, most-specific first, with the ONE matched row.
    assert [(c.scope_type, c.scope_id, c.matched) for c in res.checks] == [
        ("channel", CHAN, True), ("category", CAT, False),
        ("guild", GID, False)]
    # the guild row is reported but shadowed.
    assert res.checks[2].has_row is True and res.checks[2].value is True


def test_guild_override_beats_registry_default(monkeypatch):
    from sb.domain.governance.models import PolicySource, SubsystemState
    from sb.domain.governance.service import resolve_subsystem_state

    _install_rows(monkeypatch, {("guild", GID): {"games": False}})
    res = run(resolve_subsystem_state(GID, "games", channel_id=CHAN,
                                      category_id=CAT))
    assert res.state is SubsystemState.DISABLED
    assert res.source is PolicySource.GUILD_OVERRIDE
    assert res.checks[0].has_row is False           # channel: no row
    assert res.checks[-1].matched is True


def test_no_rows_terminates_at_the_registry_default(monkeypatch):
    from sb.domain.governance.models import PolicySource, SubsystemState
    from sb.domain.governance.service import resolve_subsystem_state

    _install_rows(monkeypatch, {})
    res = run(resolve_subsystem_state(GID, "games", channel_id=CHAN))
    assert res.state is SubsystemState.ENABLED
    assert res.source is PolicySource.REGISTRY_DEFAULT
    assert all(not c.has_row for c in res.checks)
    assert res.visibility_tier == "user"


def test_explicit_null_row_inherits_from_the_next_scope(monkeypatch):
    from sb.domain.governance.models import PolicySource, SubsystemState
    from sb.domain.governance.service import resolve_subsystem_state

    _install_rows(monkeypatch, {("channel", CHAN): {"games": None},
                                ("guild", GID): {"games": False}})
    res = run(resolve_subsystem_state(GID, "games", channel_id=CHAN))
    assert res.state is SubsystemState.DISABLED
    assert res.source is PolicySource.GUILD_OVERRIDE
    # the NULL row is visible in the chain but never the match.
    assert res.checks[0].has_row is True
    assert res.checks[0].value is None
    assert res.checks[0].matched is False


def test_guild_scope_walks_the_guild_only_chain(monkeypatch):
    from sb.domain.governance.service import resolve_subsystem_state

    _install_rows(monkeypatch, {("channel", CHAN): {"games": False}})
    # no channel/category axes = the explorer's Guild (server-wide) scope:
    # the channel override is OUT of the chain.
    res = run(resolve_subsystem_state(GID, "games"))
    assert [c.scope_type for c in res.checks] == ["guild"]
    assert res.state.value == "enabled"


def test_dependency_block_propagates_with_provenance(monkeypatch):
    from sb.domain.governance.models import PolicySource, SubsystemState
    from sb.domain.governance.service import resolve_subsystem_state

    # inventory hard-depends on economy (SUBSYSTEM_META verbatim).
    _install_rows(monkeypatch, {("guild", GID): {"economy": False}})
    res = run(resolve_subsystem_state(GID, "inventory", channel_id=CHAN))
    assert res.state is SubsystemState.BLOCKED_DEPENDENCY
    assert res.source is PolicySource.DEPENDENCY_BLOCK
    assert res.dependency_blocks == ("economy",)


def test_unknown_subsystem_is_fail_open(monkeypatch):
    from sb.domain.governance.models import PolicySource, SubsystemState
    from sb.domain.governance.service import resolve_subsystem_state

    _install_rows(monkeypatch, {})
    res = run(resolve_subsystem_state(GID, "not_a_subsystem"))
    assert res.known is False
    assert res.state is SubsystemState.ENABLED
    assert res.source is PolicySource.REGISTRY_DEFAULT
    assert res.checks == ()


# --- the armed selects: session state + in-place re-render ----------------------


def test_subsystem_select_stores_the_pick_and_refreshes(monkeypatch):
    calls = _install_refresh(monkeypatch)
    reply = run(_handler("settings.access_subsystem")(
        _req({"values": ("games",)})))
    assert reply is None                      # the edit IS the ack
    key, params = calls[0]
    assert key == "900"
    assert params["access_subsystem"] == "games"
    assert params["access_scope"] == "channel"      # the shipped default
    assert params["access_page"] == 1
    assert params["invoker_name"] == "AdminActor"
    assert params["category_id"] == CAT


def test_subsystem_select_degrades_to_the_summary_text(monkeypatch):
    _install_refresh(monkeypatch, ok=False)
    _install_seam(monkeypatch, _resolution(
        subsystem="games", state="disabled", source="guild"))
    reply = run(_handler("settings.access_subsystem")(
        _req({"values": ("games",)})))
    assert reply.outcome == "success"
    assert "`games`" in reply.user_message
    assert "🚫 Disabled" in reply.user_message
    assert "guild override" in reply.user_message


def test_scope_select_re_resolves_at_the_new_scope(monkeypatch):
    calls = _install_refresh(monkeypatch)
    run(_handler("settings.access_subsystem")(_req({"values": ("games",)})))
    reply = run(_handler("settings.access_scope")(
        _req({"values": ("guild",)})))
    assert reply is None
    assert calls[-1][1]["access_scope"] == "guild"
    assert calls[-1][1]["access_subsystem"] == "games"   # the pick survives


def test_scope_select_rejects_an_unknown_scope(monkeypatch):
    calls = _install_refresh(monkeypatch)
    reply = run(_handler("settings.access_scope")(
        _req({"values": ("planet",)})))
    assert calls == []
    assert "expired" in reply.user_message


# --- 🔬 Explain Access: the decision chain ---------------------------------------


def test_explain_without_a_pick_prompts_first():
    reply = run(_handler("settings.access_explain")(_req()))
    assert reply.outcome == "success"
    assert "Pick a subsystem" in reply.user_message


def test_explain_renders_the_resolution_chain(monkeypatch):
    from sb.domain.governance.service import ScopeCheck

    _install_refresh(monkeypatch)
    run(_handler("settings.access_subsystem")(_req({"values": ("games",)})))
    seam_calls = _install_seam(monkeypatch, _resolution(
        subsystem="games", state="disabled", source="guild",
        checks=(ScopeCheck("channel", CHAN, False, None, False),
                ScopeCheck("category", CAT, True, None, False),
                ScopeCheck("guild", GID, True, False, True))))
    reply = run(_handler("settings.access_explain")(_req()))
    msg = reply.user_message
    assert "🔬 **Access resolution — `games` (Channel (current))**" in msg
    assert f"1. channel `{CHAN}` — no override row" in msg
    assert f"2. category `{CAT}` — explicit inherit (falls through)" in msg
    assert f"3. guild `{GID}` — **override: disabled** ← matched" in msg
    assert "4. registry default — enabled (visibility tier: user)" in msg
    assert msg.rstrip().endswith("→ 🚫 Disabled")
    # the seam saw the CHANNEL scope's full axes.
    assert seam_calls[0] == {"guild_id": GID, "subsystem": "games",
                             "channel_id": CHAN, "category_id": CAT}


def test_explain_names_the_dependency_block(monkeypatch):
    from sb.domain.governance.service import ScopeCheck

    _install_refresh(monkeypatch)
    run(_handler("settings.access_subsystem")(
        _req({"values": ("inventory",)})))
    _install_seam(monkeypatch, _resolution(
        subsystem="inventory", state="blocked_dep",
        source="dependency_block", blocks=("economy",),
        checks=(ScopeCheck("guild", GID, False, None, False),)))
    reply = run(_handler("settings.access_explain")(_req()))
    assert "Dependency block: `economy` disabled" in reply.user_message
    assert "⛔ Blocked by dependency" in reply.user_message


def test_explain_is_honest_about_an_unknown_subsystem(monkeypatch):
    _install_refresh(monkeypatch)
    run(_handler("settings.access_subsystem")(_req({"values": ("ghost",)})))
    _install_seam(monkeypatch, _resolution(subsystem="ghost", known=False,
                                           tier=""))
    reply = run(_handler("settings.access_explain")(_req()))
    assert "fail-open" in reply.user_message
    assert "gates only registered rows" in reply.user_message


# --- 🔄 Reset: the ONE write (K7 SET_VISIBILITY clear) ----------------------------


def _install_write(monkeypatch, outcome="success"):
    from sb.domain.governance import service

    writes: list[dict] = []

    async def fake_set(ctx, *, scope_type, scope_id, subsystem, enabled):
        writes.append({"scope_type": scope_type, "scope_id": scope_id,
                       "subsystem": subsystem, "enabled": enabled,
                       "actor": getattr(ctx.actor, "user_id", None)})
        return SimpleNamespace(outcome=outcome, user_message="nope")

    monkeypatch.setattr(service, "set_subsystem_visibility", fake_set)
    return writes


def test_reset_without_a_pick_writes_nothing(monkeypatch):
    writes = _install_write(monkeypatch)
    reply = run(_handler("settings.access_reset")(_req()))
    assert writes == []
    assert "Pick a subsystem" in reply.user_message


def test_reset_clears_the_channel_override(monkeypatch):
    _install_refresh(monkeypatch)
    writes = _install_write(monkeypatch)
    run(_handler("settings.access_subsystem")(_req({"values": ("games",)})))
    reply = run(_handler("settings.access_reset")(_req()))
    assert writes == [{"scope_type": "channel", "scope_id": CHAN,
                       "subsystem": "games", "enabled": None, "actor": 42}]
    assert reply.outcome == "success"
    assert "Cleared the channel override for `games`" in reply.user_message


def test_reset_targets_the_selected_scope(monkeypatch):
    _install_refresh(monkeypatch)
    writes = _install_write(monkeypatch)
    run(_handler("settings.access_subsystem")(_req({"values": ("games",)})))
    run(_handler("settings.access_scope")(_req({"values": ("guild",)})))
    run(_handler("settings.access_reset")(_req()))
    assert writes[-1]["scope_type"] == "guild"
    assert writes[-1]["scope_id"] == GID


def test_reset_refuses_category_scope_without_a_category(monkeypatch):
    _install_refresh(monkeypatch)
    writes = _install_write(monkeypatch)
    run(_handler("settings.access_subsystem")(
        _req({"values": ("games",)}, category_id=None)))
    run(_handler("settings.access_scope")(
        _req({"values": ("category",)}, category_id=None)))
    reply = run(_handler("settings.access_reset")(_req(category_id=None)))
    assert writes == []
    assert "no category" in reply.user_message


def test_reset_reports_a_failed_write(monkeypatch):
    _install_refresh(monkeypatch)
    writes = _install_write(monkeypatch, outcome="denied")
    run(_handler("settings.access_subsystem")(_req({"values": ("games",)})))
    reply = run(_handler("settings.access_reset")(_req()))
    assert len(writes) == 1
    assert reply.outcome == "denied"
    assert "Couldn't reset `games`" in reply.user_message


# --- ◀ Prev / Next ▶: roster paging with clamped bounds ---------------------------


def test_next_pages_forward_and_prev_returns(monkeypatch):
    calls = _install_refresh(monkeypatch)
    reply = run(_handler("settings.access_page")(
        _req({"session_action": "access_next"})))
    assert reply is None
    assert calls[-1][1]["access_page"] == 2
    run(_handler("settings.access_page")(
        _req({"session_action": "access_prev"})))
    assert calls[-1][1]["access_page"] == 1


def test_paging_clamps_at_both_edges(monkeypatch):
    calls = _install_refresh(monkeypatch)
    run(_handler("settings.access_page")(
        _req({"session_action": "access_prev"})))
    assert calls[-1][1]["access_page"] == 1        # stale ◀ on page 1
    run(_handler("settings.access_page")(
        _req({"session_action": "access_next"})))
    run(_handler("settings.access_page")(
        _req({"session_action": "access_next"})))
    assert calls[-1][1]["access_page"] == 2        # stale ▶ on the last page


def test_page_click_without_a_message_key_degrades():
    reply = run(_handler("settings.access_page")(
        _req({"session_action": "access_next"}, message_id=None)))
    assert "expired" in reply.user_message


# --- the spec + the explorer-open byte pin ----------------------------------------


def _ctx(params=None):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=GID, actor=SimpleNamespace(user_id=42),
        channel_id=CHAN, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(),
        params=dict(params or {}))


def test_spec_routes_to_the_armed_handlers_and_compiles():
    from sb.domain.settings.panels import settings_access_spec
    from sb.kernel.panels.compile import check_panel
    from sb.spec.refs import HandlerRef

    spec = settings_access_spec()
    check_panel(spec)
    subsystem, scope = spec.selectors
    assert subsystem.on_select == HandlerRef("settings.access_subsystem")
    assert scope.on_select == HandlerRef("settings.access_scope")
    by_id = {a.action_id: a for a in spec.actions}
    assert by_id["explain"].handler == HandlerRef("settings.access_explain")
    assert by_id["reset"].handler == HandlerRef("settings.access_reset")
    assert by_id["access_prev"].handler == HandlerRef("settings.access_page")
    assert by_id["access_next"].handler == HandlerRef("settings.access_page")


def test_the_retired_pending_refs_stay_gone():
    from sb.domain.settings import handlers
    from sb.spec.refs import HandlerRef, is_registered

    handlers.ensure_handler_refs()
    for name in ("settings.access_subsystem_pending",
                 "settings.access_scope_pending",
                 "settings.access_explain_pending",
                 "settings.access_reset_pending",
                 "settings.access_page_pending"):
        assert not is_registered(HandlerRef(name)), name


def test_open_state_bytes_are_the_golden_pin():
    """The explorer-open render with ONLY the opening args (the golden's
    state) — every byte the sweep_settings_access golden pins: pinned
    placeholder, the 25-option page-1 roster VERBATIM from the spec, ◀
    Prev disabled / Next ▶ live, inline prompt fields, the author-lock
    footer, the persistent custom_ids."""
    from sb.domain.settings.panels import _render_access, settings_access_spec

    spec = settings_access_spec()
    rendered = run(_render_access(spec, _ctx({"invoker_name": "AdminActor"})))
    by_id = {c.custom_id: c for c in rendered.components}
    subsystem = by_id["settings.access.subsystem"]
    assert subsystem.placeholder == "Choose a subsystem… — page 1/2"
    assert subsystem.options == tuple(spec.selectors[0].options_source)
    assert len(subsystem.options) == 25
    scope = by_id["access:select_scope"]
    assert scope.options == tuple(spec.selectors[1].options_source)
    assert by_id["settings.access.access_prev"].disabled is True
    assert by_id["settings.access.access_next"].disabled is False
    assert "access:explain" in by_id and "access:reset" in by_id
    assert rendered.embed.fields == (
        ("Subsystem", "_Pick from the first dropdown._", True),
        ("Scope", "_Pick from the second dropdown._", True))
    assert rendered.embed.footer == (
        "Invoker: AdminActor. Only the invoker can interact with this panel.")


def test_page_two_swaps_the_roster_and_flips_the_page_turns():
    from sb.domain.settings.panels import (
        _access_page2_options,
        _render_access,
        settings_access_spec,
    )

    spec = settings_access_spec()
    rendered = run(_render_access(spec, _ctx(
        {"invoker_name": "A", "access_page": 2})))
    by_id = {c.custom_id: c for c in rendered.components}
    subsystem = by_id["settings.access.subsystem"]
    assert subsystem.placeholder == "Choose a subsystem… — page 2/2"
    assert subsystem.options == _access_page2_options()
    assert by_id["settings.access.access_prev"].disabled is False
    assert by_id["settings.access.access_next"].disabled is True


def test_page_two_roster_is_the_registry_remainder():
    from sb.domain.governance.registry import SUBSYSTEM_META
    from sb.domain.settings.panels import (
        _ACCESS_SUBSYSTEMS,
        _access_page2_options,
    )

    page1 = [v for v, _, _, _ in _ACCESS_SUBSYSTEMS]
    page2 = [o["value"] for o in _access_page2_options()]
    assert len(page2) <= 25                       # the select page cap
    assert not set(page1) & set(page2)            # disjoint pages
    # together the pages cover the WHOLE governance registry.
    assert set(page1) | set(page2) == set(SUBSYSTEM_META)
    # declaration order survives the filter (deterministic paging).
    meta_order = [k for k in SUBSYSTEM_META if k not in set(page1)]
    assert page2 == meta_order


def test_selection_marks_the_default_options():
    from sb.domain.settings.panels import _render_access, settings_access_spec

    rendered = run(_render_access(settings_access_spec(), _ctx(
        {"invoker_name": "A", "access_subsystem": "games",
         "access_scope": "guild"})))
    by_id = {c.custom_id: c for c in rendered.components}
    subsystem = {o["value"]: o.get("default")
                 for o in by_id["settings.access.subsystem"].options}
    assert subsystem["games"] is True
    assert not any(v for k, v in subsystem.items() if k != "games")
    scope = {o["value"]: o.get("default")
             for o in by_id["access:select_scope"].options}
    assert scope == {"channel": False, "category": False, "guild": True}


def test_fields_provider_renders_the_resolved_state(monkeypatch):
    from sb.spec.refs import ProviderRef, resolve

    _install_seam(monkeypatch, _resolution(
        subsystem="games", state="enabled", source="registry_default"))
    fields = run(resolve(ProviderRef("settings.access_fields"))(_ctx(
        {"access_subsystem": "games", "access_scope": "guild",
         "category_id": None})))
    assert fields[0][0] == "Subsystem"
    assert "Games (`games`)" in fields[0][1]
    assert "✅ Enabled — registry default (no override)" in fields[0][1]
    assert fields[1][0] == "Scope"
    assert "Guild (server-wide)" in fields[1][1]


def test_fields_provider_keeps_the_pinned_prompts_without_a_selection():
    from sb.spec.refs import ProviderRef, resolve

    fields = run(resolve(ProviderRef("settings.access_fields"))(_ctx()))
    assert fields == (("Subsystem", "_Pick from the first dropdown._"),
                      ("Scope", "_Pick from the second dropdown._"))
