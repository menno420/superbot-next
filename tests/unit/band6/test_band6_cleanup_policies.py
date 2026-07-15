"""The 🧹 Cleanup Policies panel family (the 2026-07-13 cleanup-policy
slice — the LAST cleanup pending retired): the oracle spec bytes
(views/cleanup/policy_panel.py @9776401 — the diagnostics view, the
scope→target→level→preview→confirm presets builder, the select-driven
custom builder, the remove flow), the compile fences, the manifest
surface, the hub repoint, the level vocabulary round-trip, the
dry-run preview semantics over the REAL resolver, and the flow
handlers' guard/refusal bytes.

Headless posture: no DB and no roster port installed — reads degrade
to the empty diagnostics state (never a crash, never a false ⚠️
stale flag), the oracle-degrade bytes render, and the preview page
renders the fallback-default current state.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

run = asyncio.run


def _ctx(params=None, guild_id=1):
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=guild_id, actor=SimpleNamespace(user_id=42),
        channel_id=2, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, params=dict(params or {}))


# --- the specs: oracle bytes + compile fences -------------------------------------------


def test_policies_spec_shape_matches_the_oracle():
    from sb.domain.cleanup.policy_panels import cleanup_policies_spec
    from sb.kernel.panels.compile import check_panel
    from sb.spec.panels import ActionStyle, Audience, FooterMode
    from sb.spec.refs import HandlerRef, PanelRef

    spec = cleanup_policies_spec()
    check_panel(spec)
    assert spec.panel_id == "cleanup.policies"
    assert spec.subsystem == "cleanup"
    assert spec.title == "🧹 Cleanup Policies — Diagnostics"
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "red"        # the shipped ADMIN_COLOR
    assert spec.frame.footer_mode is FooterMode.NONE
    assert spec.session_lifecycle is True

    by_id = {a.action_id: a for a in spec.actions}
    # the shipped PERSISTENT custom_ids verbatim (cleanup_policy:*).
    expected = {
        "cl_pol_build": ("🔧 Set a policy", ActionStyle.SUCCESS,
                         "cleanup_policy:build"),
        "cl_pol_remove": ("🗑️ Remove a policy", ActionStyle.DANGER,
                          "cleanup_policy:remove"),
        "cl_pol_refresh": ("🔄 Refresh", ActionStyle.SECONDARY,
                           "cleanup_policy:refresh"),
    }
    assert set(by_id) == set(expected)
    for aid, (label, style, custom_id) in expected.items():
        assert by_id[aid].label == label, aid
        assert by_id[aid].style is style, aid
        assert by_id[aid].custom_id_override == custom_id, aid
        assert by_id[aid].audience_tier == "administrator", aid

    # routes: 🔧 opens the scope page; 🗑️ routes through the no-rows
    # guard handler; 🔄 re-renders in place.
    from sb.spec.panels import ResultRender

    assert by_id["cl_pol_build"].handler == PanelRef("cleanup.policies_scope")
    assert by_id["cl_pol_remove"].handler == HandlerRef(
        "cleanup.policies_remove_route")
    assert by_id["cl_pol_refresh"].handler == PanelRef("cleanup.policies")
    assert by_id["cl_pol_refresh"].result_render is ResultRender.REFRESH_PANEL

    # the oracle attached "↩ Back to Cleanup" (label verbatim).
    routes = {r.label: r.route for r in spec.navigation.extra_routes}
    assert routes == {"↩ Back to Cleanup": PanelRef("cleanup.hub")}


def test_flow_page_specs_compile_and_route():
    from sb.domain.cleanup import policy_panels as pp
    from sb.kernel.panels.compile import check_panel
    from sb.spec.panels import SelectorKind
    from sb.spec.refs import HandlerRef, PanelRef

    for _pid, factory in pp._PANEL_SPECS:
        check_panel(factory())

    # the scope page carries the oracle's three options verbatim.
    scope = pp.cleanup_policies_scope_spec()
    sel = scope.selectors[0]
    assert sel.kind is SelectorKind.ENUM
    assert [o["value"] for o in sel.options_source] == [
        "guild", "category", "channel"]
    assert [o["emoji"] for o in sel.options_source] == ["🌐", "📁", "📡"]
    assert sel.on_select == HandlerRef("cleanup.policies_scope_pick")

    # the channel pick is the Discord-NATIVE channel select (D-0070);
    # the category pick rides the roster string select (D-0070(a)).
    chan = pp.cleanup_policies_channel_pick_spec()
    assert chan.selectors[0].kind is SelectorKind.CHANNEL
    cat = pp.cleanup_policies_category_pick_spec()
    assert cat.selectors[0].kind is SelectorKind.ENTITY

    # every sub-page carries the ↩ Back to Policies route (never-strand).
    for factory in (pp.cleanup_policies_scope_spec,
                    pp.cleanup_policies_channel_pick_spec,
                    pp.cleanup_policies_category_pick_spec,
                    pp.cleanup_policies_level_spec,
                    pp.cleanup_policies_custom_spec,
                    pp.cleanup_policies_preview_spec,
                    pp.cleanup_policies_remove_spec):
        nav = factory().navigation
        assert [r.route for r in nav.extra_routes] == [
            PanelRef("cleanup.policies")], factory.__name__


def test_hub_policies_button_repoints_to_the_ported_panel():
    """Byte-neutral repoint (the Dex-button precedent): label/style/
    custom_id untouched vs goldens/cleanup/sweep_cleanup; only the
    handler moves off the retired pending."""
    from sb.domain.cleanup.panels import cleanup_hub_spec
    from sb.spec.panels import ActionStyle
    from sb.spec.refs import PanelRef

    by_id = {a.action_id: a for a in cleanup_hub_spec().actions}
    action = by_id["policies"]
    assert action.label == "🧹 Cleanup Policies"
    assert action.style is ActionStyle.PRIMARY
    assert action.custom_id_override == "cleanup:policies"
    assert action.handler == PanelRef("cleanup.policies")


def test_manifest_carries_the_policy_panels_and_refs_register():
    import sb.manifest.cleanup as manifest
    from sb.spec.refs import HandlerRef, PanelRef, is_registered

    panel_ids = {p.panel_id for p in manifest.MANIFEST.panels}
    for pid in ("cleanup.policies", "cleanup.policies_scope",
                "cleanup.policies_channel_pick",
                "cleanup.policies_category_pick", "cleanup.policies_level",
                "cleanup.policies_custom", "cleanup.policies_preview",
                "cleanup.policies_remove"):
        assert pid in panel_ids, pid
        assert is_registered(PanelRef(pid)), pid
    for name in ("cleanup.policies_scope_pick", "cleanup.policies_level_pick",
                 "cleanup.policies_custom_preview", "cleanup.policies_apply",
                 "cleanup.policies_cancel", "cleanup.policies_remove_route",
                 "cleanup.policies_remove_pick"):
        assert is_registered(HandlerRef(name)), name


# --- the level vocabulary -----------------------------------------------------------------


def test_level_options_and_round_trip():
    """The level select mirrors LEVELS (+ ⚙️ Custom…, description bytes
    verbatim) and level_for_columns is the exact inverse."""
    from sb.domain.cleanup import policy_service as svc
    from sb.domain.cleanup.policy_widgets import (
        CUSTOM_VALUE,
        policies_level_options,
    )
    from sb.domain.setup.cleanup import LEVELS

    options = run(policies_level_options(_ctx()))
    assert [o["value"] for o in options] == [*LEVELS, CUSTOM_VALUE]
    assert options[-1]["label"] == "Custom…"
    assert options[-1]["emoji"] == "⚙️"
    # the oracle description byte for Light: after=10s · invalid=yes ·
    # failed=no.
    light = next(o for o in options if o["value"] == "Light")
    assert light["description"] == "after=10s · invalid=yes · failed=no"

    for name, cols in LEVELS.items():
        assert svc.level_for_columns(
            delete_invalid_commands=cols["delete_invalid_commands"],
            delete_failed_commands=cols["delete_failed_commands"],
            delete_after_seconds=cols["delete_after_seconds"]) == name
    # a non-preset tuple names back to None → rendered "Custom".
    assert svc.level_for_columns(delete_invalid_commands=True,
                                 delete_failed_commands=True,
                                 delete_after_seconds=42) is None


def test_custom_builder_options_reflect_the_staged_args():
    from sb.domain.cleanup.policy_widgets import (
        DURATION_OPTIONS,
        policies_after_options,
        policies_failed_options,
        policies_invalid_options,
    )

    after = run(policies_after_options(_ctx({"pol_das": "60"})))
    assert [o["value"] for o in after] == [str(s) for s, _l in
                                           DURATION_OPTIONS]
    assert [o["label"] for o in after][:2] == ["Instant (0s)", "2 seconds"]
    assert next(o for o in after if o["value"] == "60")["default"] is True
    assert sum(1 for o in after if o["default"]) == 1

    inv = run(policies_invalid_options(_ctx({"pol_div": "no"})))
    assert [(o["label"], o["default"]) for o in inv] == [
        ("Yes", False), ("No", True)]
    fail = run(policies_failed_options(_ctx()))          # default: no
    assert [(o["label"], o["default"]) for o in fail] == [
        ("Yes", False), ("No", True)]


# --- the renderers (headless: empty diagnostics, oracle bytes) -------------------------------


def test_diagnostics_renders_the_empty_state_with_the_swap_footer():
    from sb.domain.cleanup.policy_panels import cleanup_policies_spec
    from sb.spec.refs import resolve as resolve_ref

    spec = cleanup_policies_spec()
    rendered = run(resolve_ref(spec.renderer_override)(spec, _ctx()))
    assert rendered.embed.description == (
        "Resolution walks **channel → category → guild → default**; the "
        "most specific override wins. Threads inherit from their parent "
        "channel.")
    fields = rendered.embed.fields
    assert fields[0][0] == "Configured policies"
    assert fields[0][1] == ("_None — every scope uses the fallback default "
                            "(delete after 5s)._")
    assert fields[1][0] == "ℹ️ Tip"
    assert "Command Access → 🗑️ Delete blocked commands" in fields[1][1]
    # empty → the oracle's empty-state footer byte.
    assert rendered.embed.footer == "Use “Set a policy” to add one."


def test_level_page_renders_the_per_scope_prompts():
    from sb.domain.cleanup.policy_panels import cleanup_policies_level_spec
    from sb.spec.refs import resolve as resolve_ref

    spec = cleanup_policies_level_spec()
    render = resolve_ref(spec.renderer_override)

    guild = run(render(spec, _ctx({"pol_scope": "guild",
                                   "pol_label": "Guild default"})))
    assert guild.embed.description == "Pick the guild-default cleanup level:"

    cat = run(render(spec, _ctx({"pol_scope": "category",
                                 "pol_label": "Category Mods"})))
    assert cat.embed.description == (
        "Pick the cleanup level for category **Mods**:")

    chan = run(render(spec, _ctx({"pol_scope": "channel",
                                  "pol_label": "#general"})))
    assert chan.embed.description == "Pick the cleanup level for #general:"
    sel = next(c for c in chan.components
               if c.custom_id.endswith(".cl_pol_level"))
    assert sel.placeholder == "Level for #general…"     # the oracle byte


def test_custom_page_renders_the_summary_bytes():
    from sb.domain.cleanup.policy_panels import cleanup_policies_custom_spec
    from sb.spec.refs import resolve as resolve_ref

    spec = cleanup_policies_custom_spec()
    rendered = run(resolve_ref(spec.renderer_override)(spec, _ctx(
        {"pol_das": "60", "pol_div": "yes", "pol_dfc": "no"})))
    assert rendered.embed.description == (
        "**Custom cleanup policy** — pick values, then **Preview & "
        "apply**:\n"
        "• Delete after: **1 minute**\n"
        "• Delete invalid commands: **Yes**\n"
        "• Delete failed commands: **No**")


def _no_stored_rows(monkeypatch):
    """DB-free resolver: no stored cleanup rows → the compat fallback
    default (delete invalid after 5s) — the real resolver still runs."""
    from sb.domain.governance import store

    async def _none(_gid, _scope_type, _scope_id, conn=None):
        return None

    monkeypatch.setattr(store, "get_cleanup_policy", _none)


def test_preview_renders_the_dry_run_over_the_real_resolver(monkeypatch):
    """No stored rows: the resolver answers the compat fallback default
    (delete invalid after 5s) — the preview pins the oracle bytes:
    current source fallback_default, After applying names the scope
    override, will_change=True → orange."""
    from sb.domain.cleanup.policy_panels import cleanup_policies_preview_spec
    from sb.spec.refs import resolve as resolve_ref

    _no_stored_rows(monkeypatch)
    spec = cleanup_policies_preview_spec()
    rendered = run(resolve_ref(spec.renderer_override)(spec, _ctx(
        {"pol_scope": "guild", "pol_target": "1", "pol_level": "Light",
         "pol_div": "yes", "pol_dfc": "no", "pol_das": "10"})))
    embed = rendered.embed
    assert embed.description == "Set **Guild default** to `Light`?"
    fields = {f[0]: f[1] for f in embed.fields}
    assert fields["Currently resolves to"] == (
        "delete=yes, after=5s\n_source: fallback_default_")
    assert fields["After applying"] == (
        "invalid cmds=yes, failed cmds=no, after=10s\n"
        "_source: guild override_")
    assert embed.footer == "Nothing has been written yet."
    assert embed.style_token == "orange"                # will_change


def test_preview_no_change_renders_greyple_and_the_no_change_field(
        monkeypatch):
    """Setting the guild default to the fallback's own effect: the
    effect matches but the write PINS an explicit guild override —
    will_change stays True with the oracle same-effect warning. A
    same-source no-op needs a stored row (DB), so the DB-free case
    exercised here is the pins-source warning byte."""
    from sb.domain.cleanup.policy_panels import cleanup_policies_preview_spec
    from sb.spec.refs import resolve as resolve_ref

    _no_stored_rows(monkeypatch)
    spec = cleanup_policies_preview_spec()
    rendered = run(resolve_ref(spec.renderer_override)(spec, _ctx(
        {"pol_scope": "guild", "pol_target": "1", "pol_level": "Standard",
         "pol_div": "yes", "pol_dfc": "yes", "pol_das": "5"})))
    fields = {f[0]: f[1] for f in rendered.embed.fields}
    assert fields["⚠️ Note"] == (
        "Same effect as today, but this pins an explicit override on the "
        "guild (currently inherited from fallback_default).")
    assert rendered.embed.style_token == "orange"


def test_preview_failure_renders_the_oracle_degrade_byte():
    from sb.domain.cleanup.policy_panels import cleanup_policies_preview_spec
    from sb.spec.refs import resolve as resolve_ref

    spec = cleanup_policies_preview_spec()
    # a bad scope_type fails validation inside the preview → the
    # oracle degrade byte, never a crash.
    rendered = run(resolve_ref(spec.renderer_override)(spec, _ctx(
        {"pol_scope": "thread", "pol_target": "1"})))
    assert rendered.embed.description == (
        "Could not build the preview — see logs.")


# --- the flow handlers (guard bytes; no DB writes) --------------------------------------------


def _req(args=None, guild_id=1):
    return SimpleNamespace(
        actor=SimpleNamespace(user_id=42), guild_id=guild_id, channel_id=2,
        request_id="t", confirmed=False, args=dict(args or {}), origin=None)


def test_flow_handlers_guard_missing_guild():
    from sb.domain.cleanup import policy_widgets as w
    from sb.spec.outcomes import BLOCKED

    for fn in (w.policies_scope_pick, w.policies_channel_pick,
               w.policies_category_pick, w.policies_level_pick,
               w.policies_custom_preview, w.policies_apply,
               w.policies_remove_route, w.policies_remove_pick):
        reply = run(fn(_req(guild_id=None)))
        assert reply is not None and reply.outcome == BLOCKED, fn.__name__
        assert reply.user_message == ("❌ Cleanup policies can only be "
                                 "configured inside a server."), fn.__name__


def test_apply_guards_bare_args_and_cancel_answers_the_oracle_byte():
    from sb.domain.cleanup import policy_widgets as w
    from sb.spec.outcomes import BLOCKED, SUCCESS

    # a stale/foreign page open leaves the args bare — the guard
    # answers, never a write.
    reply = run(w.policies_apply(_req({})))
    assert reply.outcome == BLOCKED

    reply = run(w.policies_cancel(_req({})))
    assert reply.outcome == SUCCESS
    assert reply.user_message == "Cancelled — nothing was written."


def test_remove_pick_refuses_an_unparseable_selection():
    from sb.domain.cleanup import policy_widgets as w
    from sb.spec.outcomes import BLOCKED

    reply = run(w.policies_remove_pick(
        _req({"values": ("guild:notanumber",)})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "Could not parse that selection — try again."


def test_headless_diagnostics_degrade_never_flags_stale():
    """No roster port installed → labels degrade to mentions and NOTHING
    is flagged stale (the module-doc ledger: a headless 'everything is
    stale' report would be a false alarm)."""
    from sb.domain.cleanup import policy_service as svc

    names = run(svc.scope_labels(1))
    assert names.attested is False
    label, stale = svc._target_label(names, 1, "channel", 123)
    assert (label, stale) == ("<#123>", False)
    label, stale = svc._target_label(names, 1, "guild", 1)
    assert (label, stale) == ("Guild default", False)
