"""The 🔓 Access Map port (server_management projections slice A): the
P1A composed read model (sb/domain/server_management/access_projection.py)
+ the P1C subpanel (access_map.py) + the hub-button flip.

Oracle: menno420/superbot disbot/services/access_projection.py +
disbot/views/server_management/access_map.py (AccessMapView half). No
golden drives the interior (the hub-open goldens pin only the hub bytes,
which stay identical — label/style/custom_id unchanged on the flipped
button); these tests pin the ported copy + composition semantics.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run


# --- shared fixtures -------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    from sb.domain.governance import cache as gcache
    from sb.domain.server_management import access_map as am

    gcache.reset_cache_for_tests()
    am._tier_pick.clear()
    am._last_projection.clear()
    yield
    gcache.reset_cache_for_tests()
    am._tier_pick.clear()
    am._last_projection.clear()


def _patch_owners(monkeypatch, *, mode=None, allowed_channels=frozenset(),
                  overrides=None):
    """Point the two DB-reading owners at in-memory truths."""
    from sb.domain.governance import store as gov_store
    from sb.domain.platform import command_access as ca
    from sb.kernel.authority.channel_access import CommandAccessSnapshot

    async def fake_snapshot(guild_id):
        return CommandAccessSnapshot(mode=mode,
                                     allowed_channels=allowed_channels)

    async def fake_overrides(guild_id, chain):
        return overrides or {}

    monkeypatch.setattr(ca, "read_policy_snapshot", fake_snapshot)
    monkeypatch.setattr(gov_store, "fetch_visibility_for_chain",
                        fake_overrides)


def _feature(subsystem="economy", command="balance", tier="user"):
    from sb.domain.server_management.access_projection import FeatureEntry

    return FeatureEntry(subsystem=subsystem, command_name=command,
                        visibility_tier=tier)


def _actx(**kw):
    from sb.domain.server_management.access_projection import AccessContext

    defaults = dict(guild_id=1, channel_id=2, member_tier="user")
    defaults.update(kw)
    return AccessContext(**defaults)


# --- the feature inventory ---------------------------------------------------------


def test_feature_inventory_covers_the_whole_registry():
    from sb.domain.governance.registry import SUBSYSTEM_META
    from sb.domain.server_management.access_projection import (
        feature_inventory,
    )

    rows = feature_inventory()
    assert {r.subsystem for r in rows} == set(SUBSYSTEM_META)
    by_key = {r.subsystem: r for r in rows}
    # the registry's shipped visibility tiers ride along verbatim.
    assert by_key["server_management"].visibility_tier == "administrator"
    assert by_key["economy"].visibility_tier == "user"
    # a ported subsystem carries its first declared manifest command
    # (qualified name — the compiled analog of entry_points[0]).
    assert by_key["economy"].command_name


def test_unported_subsystem_rows_skip_the_command_axis():
    """A registry row with no manifest carries command_name=None and the
    command-access + help axes record ``skipped`` — never a guess."""
    from sb.domain.server_management.access_projection import (
        AccessAxis,
        _axis_command_access,
        _axis_help_visibility,
    )

    feature = _feature(command=None)
    outcome = run(_axis_command_access(feature, _actx()))
    assert outcome.axis is AccessAxis.COMMAND_ACCESS
    assert outcome.state == "skipped"
    assert outcome.detail == "no representative command"
    help_outcome = _axis_help_visibility(feature, _actx())
    assert help_outcome.state == "skipped"


# --- the user-safe reason table ------------------------------------------------------


def test_safe_locked_reason_known_codes_verbatim():
    from sb.domain.server_management.access_projection import (
        safe_locked_reason,
    )

    r = safe_locked_reason("commands_disabled")
    assert r.safe_text == "Commands are currently disabled in this server."
    assert r.source == "command_access"
    r = safe_locked_reason("channel_not_allowed")
    assert r.safe_text == "This command isn't enabled in this channel."
    assert r.unlock_hint == "try one of the server's command channels"
    r = safe_locked_reason("subsystem_hidden")
    assert r.safe_text == "You don't have access to this feature here."
    assert r.source == "governance"
    # the compiled R-16 row (the ported channel lane's role-set denial).
    r = safe_locked_reason("role_not_held")
    assert r.safe_text == (
        "Commands in this channel are limited to specific roles.")


def test_safe_locked_reason_unmapped_code_is_the_generic_denial():
    from sb.domain.server_management.access_projection import (
        safe_locked_reason,
    )

    r = safe_locked_reason("some_future_code")
    assert r.code == "access_denied"
    assert r.safe_text == "You can't use this feature here right now."
    assert safe_locked_reason(None).code == "access_denied"


# --- axis composition ----------------------------------------------------------------


def test_commands_disabled_short_circuits_with_safe_copy(monkeypatch):
    from sb.domain.server_management.access_projection import (
        AccessAxis,
        resolve_feature_access,
    )

    _patch_owners(monkeypatch, mode="disabled_except_bootstrap")
    decision = run(resolve_feature_access(_feature(), _actx()))
    assert decision.effective == "deny"
    assert decision.deciding_axis is AccessAxis.COMMAND_ACCESS
    assert decision.reason.code == "commands_disabled"
    assert decision.reason.safe_text == (
        "Commands are currently disabled in this server.")
    assert decision.remediation == (
        "Enable commands in the Command Access settings.")
    # short-circuit: only the deciding axis is in the chain.
    assert [o.axis for o in decision.source_chain] == [
        AccessAxis.COMMAND_ACCESS]


def test_selected_channels_miss_denies_channel_not_allowed(monkeypatch):
    from sb.domain.server_management.access_projection import (
        AccessAxis,
        resolve_feature_access,
    )

    _patch_owners(monkeypatch, mode="selected_channels",
                  allowed_channels=frozenset({999}))
    decision = run(resolve_feature_access(_feature(), _actx(channel_id=2)))
    assert decision.effective == "deny"
    assert decision.deciding_axis is AccessAxis.COMMAND_ACCESS
    assert decision.reason.code == "channel_not_allowed"
    assert decision.remediation == (
        "Add this channel in the Command Access settings.")


def test_governance_hides_above_tier_subsystems_for_simulated_user(
        monkeypatch):
    from sb.domain.server_management.access_projection import (
        AccessAxis,
        resolve_feature_access,
    )

    _patch_owners(monkeypatch)
    feature = _feature(subsystem="server_management",
                       command="servermanagement", tier="administrator")
    decision = run(resolve_feature_access(feature, _actx(member_tier="user")))
    assert decision.effective == "deny"
    assert decision.deciding_axis is AccessAxis.GOVERNANCE
    assert decision.reason.code == "subsystem_hidden"
    assert decision.reason.safe_text == (
        "You don't have access to this feature here.")
    # the deny detail names the tier floor + the simulation limit label.
    gv = next(o for o in decision.source_chain
              if o.axis is AccessAxis.GOVERNANCE)
    assert "required_tier=administrator" in gv.detail
    assert "simulated tier=user" in gv.detail


def test_allow_records_the_whole_chain_with_skipped_axes(monkeypatch):
    from sb.domain.server_management.access_projection import (
        AccessAxis,
        resolve_feature_access,
    )

    _patch_owners(monkeypatch)
    decision = run(resolve_feature_access(
        _feature(), _actx(member_tier="administrator")))
    assert decision.effective == "allow"
    assert decision.deciding_axis is None and decision.reason is None
    by_axis = {o.axis: o for o in decision.source_chain}
    assert by_axis[AccessAxis.COMMAND_ACCESS].state == "allow"
    # routing is honestly skipped — cog routing is not ported.
    assert by_axis[AccessAxis.ROUTING].state == "skipped"
    assert "not ported" in by_axis[AccessAxis.ROUTING].detail
    assert by_axis[AccessAxis.GOVERNANCE].state == "allow"
    assert by_axis[AccessAxis.AVAILABILITY].state == "skipped"
    # the help axis is recorded, non-gating.
    assert by_axis[AccessAxis.HELP].state in ("shown", "hidden")


def test_unknown_owner_never_claims_allow(monkeypatch):
    """A raising owner degrades its axis to unknown — the composed result
    is unknown, never a false allow (the read-model never-crash rule)."""
    from sb.domain.governance import store as gov_store
    from sb.domain.platform import command_access as ca
    from sb.domain.server_management.access_projection import (
        resolve_feature_access,
    )

    async def boom(*a, **kw):
        raise RuntimeError("db down")

    monkeypatch.setattr(ca, "read_policy_snapshot", boom)
    monkeypatch.setattr(gov_store, "fetch_visibility_for_chain", boom)
    decision = run(resolve_feature_access(_feature(), _actx()))
    assert decision.effective == "unknown"
    assert decision.deciding_axis is None


def test_help_axis_staff_gate_simulation():
    from sb.domain.server_management.access_projection import (
        _axis_help_visibility,
    )

    # moderation lives under the staff-only moderation mother hub.
    feature = _feature(subsystem="moderation", command="warn",
                       tier="moderator")
    assert _axis_help_visibility(
        feature, _actx(member_tier="user")).state == "hidden"
    assert _axis_help_visibility(
        feature, _actx(member_tier="moderator")).state == "shown"
    # non-staff categories always show.
    assert _axis_help_visibility(
        _feature(), _actx(member_tier="user")).state == "shown"


def test_project_access_map_projects_every_feature(monkeypatch):
    from sb.domain.governance.registry import SUBSYSTEM_META
    from sb.domain.server_management.access_projection import (
        project_access_map,
    )

    _patch_owners(monkeypatch)
    decisions = run(project_access_map(_actx(member_tier="administrator")))
    assert {d.feature for d in decisions} == set(SUBSYSTEM_META)
    # an administrator simulation sees no governance denials on defaults.
    assert all(d.effective != "deny" for d in decisions)


# --- the panel spec --------------------------------------------------------------------


def test_access_map_spec_shape():
    from sb.domain.server_management.access_map import access_map_spec
    from sb.spec.panels import Audience, FooterMode, SelectorKind
    from sb.spec.refs import HandlerRef, PanelRef

    spec = access_map_spec()
    assert spec.panel_id == "server_management.access_map"
    assert spec.subsystem == "server_management"
    assert spec.title == "🔓 Access Map"
    assert spec.audience is Audience.INVOKER
    # the shipped ADMIN_COLOR — discord.Color.red().
    assert spec.frame.style_token == "red"
    assert spec.frame.footer_mode is FooterMode.NONE
    tier_sel, feature_sel = spec.selectors
    assert tier_sel.selector_id == "am_tier"
    assert tier_sel.kind is SelectorKind.ENUM
    assert tier_sel.placeholder == "Simulate audience…"     # shipped byte
    assert tier_sel.audience_tier == "administrator"
    assert tier_sel.on_select == HandlerRef(
        "server_management.access_map_tier")
    assert feature_sel.selector_id == "am_feature"
    assert feature_sel.placeholder == (
        "Inspect a feature's source chain…")                # shipped byte
    assert feature_sel.on_select == HandlerRef(
        "server_management.access_map_inspect")
    assert spec.navigation.parent == PanelRef("server_management.hub")
    assert spec.layout.pages[0].rows == (("am_tier",), ("am_feature",))


def test_access_map_spec_passes_the_compile_fences():
    from sb.domain.server_management.access_map import access_map_spec
    from sb.kernel.panels.compile import check_panel

    check_panel(access_map_spec())


def _ctx(gid=1, uid=42, channel_id=2):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=gid, actor=SimpleNamespace(user_id=uid),
        channel_id=channel_id, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(), params={},
        surface="component")


def test_render_carries_footer_and_tier_keyed_description(monkeypatch):
    from sb.domain.server_management import access_map as am

    _patch_owners(monkeypatch)
    rendered = run(am._render_access_map(am.access_map_spec(), _ctx()))
    assert rendered.embed.footer == (
        "Read-only · pick a feature below for the full source chain")
    assert rendered.embed.description.startswith(
        "Effective feature access for a **Normal member** in this channel")
    # the pinned §16.4 label is always the last field.
    assert rendered.embed.fields[-1] == (
        "Simulation limits", am.SIMULATION_LIMIT_NOTE)

    # a stashed tier pick re-keys the description (the shipped re-render).
    am._tier_pick[(1, 42)] = "moderator"
    am._last_projection.clear()
    rendered = run(am._render_access_map(am.access_map_spec(), _ctx()))
    assert "**Moderator**" in rendered.embed.description


def test_fields_provider_buckets_and_chunking(monkeypatch):
    from sb.domain.server_management import access_map as am
    from sb.domain.server_management import access_projection as ap

    long_reason = ap.LockedReason(
        code="commands_disabled",
        safe_text="Commands are currently disabled in this server.",
        source="command_access")

    def _decision(key, effective, axis=None, reason=None):
        return ap.AccessDecision(
            feature=key, command_name=key, effective=effective,
            deciding_axis=axis, reason=reason, source_chain=())

    decisions = tuple(
        [_decision("okay", "allow"), _decision("mystery", "unknown")]
        + [_decision(f"denied_{i:02d}", "deny",
                     axis=ap.AccessAxis.COMMAND_ACCESS, reason=long_reason)
           for i in range(30)])

    async def fake_project(ctx):
        return decisions

    monkeypatch.setattr(ap, "project_access_map", fake_project)
    fields = run(am._access_map_fields(_ctx()))
    names = [n for n, _ in fields]
    assert names[0] == "✅ Allowed (1)"
    assert names[1] == "❌ Denied (30)"
    # 30 denial lines overflow Discord's 1024-char cap → (cont.) parts,
    # nothing sheds (the shipped _chunk_field).
    assert "❌ Denied (30) (cont.)" in names
    assert names[-1] == "Simulation limits"
    assert any(n == "❓ Unresolved (1)" for n in names)
    denied_text = "\n".join(v for n, v in fields if n.startswith("❌"))
    assert "❌ **denied_00** — Commands are currently disabled in this " \
           "server. *(axis: command_access)*" in denied_text
    assert denied_text.count("❌ **denied_") == 30


def test_tier_options_mark_the_current_pick(monkeypatch):
    from sb.domain.server_management import access_map as am

    options = run(am._tier_options(_ctx()))
    assert [o["value"] for o in options] == [
        "user", "trusted", "staff", "moderator", "administrator"]
    assert [o["label"] for o in options] == [
        "Normal member", "Trusted user", "Staff", "Moderator",
        "Administrator"]
    assert [o["default"] for o in options] == [True, False, False, False,
                                               False]
    am._tier_pick[(1, 42)] = "staff"
    options = run(am._tier_options(_ctx()))
    assert next(o for o in options if o["value"] == "staff")["default"]


def test_feature_options_carry_state_glyphs(monkeypatch):
    from sb.domain.server_management import access_map as am
    from sb.domain.server_management import access_projection as ap

    async def fake_project(ctx):
        return (
            ap.AccessDecision(feature="economy", command_name="balance",
                              effective="allow", deciding_axis=None,
                              reason=None, source_chain=()),
            ap.AccessDecision(feature="moderation", command_name="warn",
                              effective="deny",
                              deciding_axis=ap.AccessAxis.GOVERNANCE,
                              reason=None, source_chain=()),
        )

    monkeypatch.setattr(ap, "project_access_map", fake_project)
    options = run(am._feature_options(_ctx()))
    assert options == (
        {"label": "✅ economy", "value": "economy"},
        {"label": "❌ moderation", "value": "moderation"},
    )


# --- the handlers ------------------------------------------------------------------------


import dataclasses


@dataclasses.dataclass
class _Req:
    """dataclass so the handlers' ``dataclasses.replace(req, …)`` re-open
    path works (the operator-hub-edits C test fixture pattern)."""

    args: dict
    guild_id: int | None = 1
    channel_id: int | None = 2
    request_id: str = "req-1"
    confirmed: bool = False
    actor: object = dataclasses.field(
        default_factory=lambda: SimpleNamespace(user_id=42))


def _req(values, gid=1, uid=42, channel_id=2):
    return _Req(args={"values": values}, guild_id=gid, channel_id=channel_id,
                actor=SimpleNamespace(user_id=uid))


def test_tier_select_stashes_and_reopens(monkeypatch):
    from sb.domain.server_management import access_map as am
    from sb.kernel.panels import engine
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return ""

    monkeypatch.setattr(engine, "open_panel", fake_open)
    handler = resolve(HandlerRef("server_management.access_map_tier"))
    reply = run(handler(_req(["moderator"])))
    assert reply.outcome == SUCCESS and reply.user_message is None
    assert am.tier_for(1, 42) == "moderator"
    assert opened == ["server_management.access_map"]

    # an unknown/stale option lands on the polite terminal, never a crash.
    reply = run(handler(_req(["owner"])))
    assert reply.user_message == "That audience tier is not available."
    assert am.tier_for(1, 42) == "moderator"       # unchanged


def test_inspect_renders_the_source_chain(monkeypatch):
    import time

    from sb.domain.server_management import access_map as am
    from sb.domain.server_management import access_projection as ap
    from sb.spec.refs import HandlerRef, resolve

    decision = ap.AccessDecision(
        feature="moderation", command_name="warn", effective="deny",
        deciding_axis=ap.AccessAxis.GOVERNANCE,
        reason=ap.safe_locked_reason("subsystem_hidden"),
        source_chain=(
            ap.AxisOutcome(ap.AccessAxis.COMMAND_ACCESS, "allow"),
            ap.AxisOutcome(ap.AccessAxis.ROUTING, "skipped",
                           detail="cog routing not ported"),
            ap.AxisOutcome(ap.AccessAxis.GOVERNANCE, "deny",
                           reason_code="subsystem_hidden",
                           detail="required_tier=moderator"),
        ))
    am._last_projection[(1, 42)] = (time.monotonic(), "user", (decision,))
    handler = resolve(HandlerRef("server_management.access_map_inspect"))
    reply = run(handler(_req(["moderation"])))
    msg = reply.user_message
    assert msg.startswith("**Source chain — moderation**")
    assert "`command_access` → **allow**" in msg
    assert "`routing` → **skipped** — cog routing not ported" in msg
    assert "`governance` → **deny** — required_tier=moderator" in msg
    assert "User-safe reason: You don't have access to this feature " \
           "here." in msg
    assert am.SIMULATION_LIMIT_NOTE in msg


def test_inspect_unknown_feature_polite_terminal(monkeypatch):
    from sb.spec.refs import HandlerRef, resolve

    handler = resolve(HandlerRef("server_management.access_map_inspect"))
    reply = run(handler(_req(["not_a_feature"])))
    assert reply.user_message == (
        "That feature is not in the current projection.")


def test_inspect_survives_evicted_view_state(monkeypatch):
    """A restart-evicted projection re-derives the one picked feature
    fresh instead of stranding the click."""
    from sb.domain.server_management import access_map as am
    from sb.spec.refs import HandlerRef, resolve

    _patch_owners(monkeypatch)
    am._last_projection.clear()
    handler = resolve(HandlerRef("server_management.access_map_inspect"))
    reply = run(handler(_req(["economy"])))
    assert reply.user_message.startswith("**Source chain — economy**")


# --- the hub flip + refs + manifest ---------------------------------------------------------


def test_hub_access_map_button_forwards_to_the_ported_panel():
    from sb.domain.server_management.panels import server_management_hub_spec
    from sb.spec.panels import ActionStyle
    from sb.spec.refs import PanelRef

    by_id = {a.action_id: a for a in server_management_hub_spec().actions}
    action = by_id["access_map"]
    assert action.handler == PanelRef("server_management.access_map")
    # the hub-open goldens stay byte-identical: label/style/custom_id
    # unchanged on the flip.
    assert action.label == "🔓 Access Map"
    assert action.style is ActionStyle.SECONDARY
    assert action.custom_id_override == "server_management:access_map"
    assert action.audience_tier == "administrator"


def test_refs_registered_and_pending_terminal_retired():
    from sb.domain.server_management import access_map as am
    from sb.spec.refs import HandlerRef, PanelRef, ProviderRef, is_registered

    am.ensure_access_map_refs()
    assert is_registered(PanelRef("server_management.access_map"))
    for name in ("server_management.render_access_map",
                 "server_management.access_map_tier",
                 "server_management.access_map_inspect"):
        assert is_registered(HandlerRef(name)), name
    for name in ("server_management.access_map_fields",
                 "server_management.access_map_tiers",
                 "server_management.access_map_features"):
        assert is_registered(ProviderRef(name)), name
    # the pending terminal is retired with this slice.
    assert not is_registered(
        HandlerRef("server_management.access_map_pending"))


def test_manifest_declares_the_access_map_panel():
    from sb.manifest.server_management import MANIFEST

    ids = [p.panel_id for p in MANIFEST.panels]
    assert "server_management.hub" in ids
    assert "server_management.access_map" in ids
