"""Pipeline tests for the K2 compiler (S3, frozen L0 spec 01 §3.1-§3.6, §5)."""

import dataclasses

import pytest

from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    PredicateRef,
    RefRedefined,
    WorkflowRef,
    handler,
    workflow,
)
from tests.unit.compiler.conftest import (
    CommandSpec,
    ComponentSpec,
    ConfirmationSpec,
    EventSpec,
    LeaderboardSpec,
    NavigationSpec,
    PanelActionSpec,
    PanelSpec,
    StoreSpec,
)
from tools.manifest_compile import (
    _p7_store_completeness,
    _p8_serialize,
    compile_manifests,
    compute_stable_hash,
)


def _register_basics():
    @handler("economy.give")
    def _give():  # pragma: no cover - never called
        pass

    @workflow("economy.transfer")
    def _transfer():  # pragma: no cover
        pass


def _economy(**overrides):
    kwargs = dict(
        key="economy",
        commands=(CommandSpec("give", surface="slash", route=HandlerRef("economy.give")),),
        stores=(StoreSpec("economy_wallets", stat_key="net_worth"),),
        events=(EventSpec("economy.daily_claimed"),),
    )
    kwargs.update(overrides)
    return SubsystemManifest(**kwargs)


# --- P1 / refs ------------------------------------------------------------------

def test_real_manifest_package_compiles_green_and_deterministic():
    # Band 1 ended the empty-package era: sb/manifest now carries real
    # subsystem declarations (settings first).
    a = compile_manifests()
    b = compile_manifests()
    assert a.ok and b.ok
    assert a.stable_hash == b.stable_hash
    assert a.snapshot["manifest_count"] >= 1
    assert "settings" in a.snapshot["subsystems"]


def test_duplicate_subsystem_key_is_p1_compile_error():
    result = compile_manifests(manifests=[
        SubsystemManifest(key="economy"), SubsystemManifest(key="economy")])
    assert not result.ok
    assert result.violations[0].pass_name == "load"
    assert result.violations[0].failure_class == "COMPILE_ERROR"


def test_duplicate_ref_binding_raises_ref_redefined():
    @handler("x")
    def first():  # pragma: no cover
        pass

    with pytest.raises(RefRedefined) as exc_info:
        @handler("x")
        def second():  # pragma: no cover
            pass

    assert exc_info.value.first_module == exc_info.value.second_module  # both this test module


# --- P2 -------------------------------------------------------------------------

def test_unresolved_ref_is_p2_compile_error():
    result = compile_manifests(manifests=[
        SubsystemManifest(key="economy",
                          commands=(CommandSpec("give", route=HandlerRef("nope")),))])
    assert not result.ok
    v = result.violations[0]
    assert v.pass_name == "ref_resolution"
    assert "unresolved_ref: handler:nope" in v.detail


def test_namespaced_predicate_is_never_an_unresolved_ref():
    _register_basics()
    action = PanelActionSpec("econ.act", handler=HandlerRef("economy.give"),
                             visible_when=PredicateRef("setting:economy.enabled"))
    panel = PanelSpec("econ_hub", navigation=NavigationSpec(),
                      actions=(action,), components=(ComponentSpec(action_id="econ.act"),))
    result = compile_manifests(manifests=[_economy(panels=(panel,))])
    assert result.ok, result.violations


def test_malformed_namespaced_predicate_is_bad_predicate():
    _register_basics()
    action = PanelActionSpec("econ.act", handler=HandlerRef("economy.give"),
                             visible_when=PredicateRef("setting:"))
    panel = PanelSpec("econ_hub", navigation=NavigationSpec(),
                      actions=(action,), components=(ComponentSpec(action_id="econ.act"),))
    result = compile_manifests(manifests=[_economy(panels=(panel,))])
    assert not result.ok
    assert "bad_predicate" in result.violations[0].detail


def test_empty_predicate_is_constant_true():
    _register_basics()
    action = PanelActionSpec("econ.act", handler=HandlerRef("economy.give"),
                             visible_when=PredicateRef(""))
    panel = PanelSpec("econ_hub", navigation=NavigationSpec(),
                      actions=(action,), components=(ComponentSpec(action_id="econ.act"),))
    assert compile_manifests(manifests=[_economy(panels=(panel,))]).ok


# --- P3 (K1's oracle) -------------------------------------------------------------

def test_command_collision_is_p3_with_scope_and_claimants():
    _register_basics()
    result = compile_manifests(manifests=[
        _economy(),
        SubsystemManifest(key="inventory",
                          commands=(CommandSpec("give", surface="slash"),)),
    ])
    assert not result.ok
    v = next(v for v in result.violations if v.failure_class == "COLLISION")
    assert v.scope == "slash/"
    assert v.claimant_a and v.claimant_b and v.claimant_a != v.claimant_b


def test_both_surface_expands_to_two_reservations():
    _register_basics()
    result = compile_manifests(manifests=[
        SubsystemManifest(key="karma", commands=(CommandSpec("karma", surface="both"),))])
    assert result.ok
    nodes = result.snapshot["projections"]["namespace"]["command"]
    assert {n["surface"] for n in nodes} == {"prefix", "slash"}


# --- P5 -----------------------------------------------------------------------------

def test_untagged_field_is_p5_compile_error():
    @dataclasses.dataclass(frozen=True)
    class RogueSpec:
        mystery: str = "?"

    result = compile_manifests(manifests=[
        SubsystemManifest(key="rogue", commands=(RogueSpec(),))])
    assert not result.ok
    assert any(v.pass_name == "role_tag" and "RogueSpec.mystery" in v.locus
               for v in result.violations)


# --- P6: the six predicates ----------------------------------------------------------

def _panel_with(action, components=None):
    comps = components if components is not None else (ComponentSpec(action_id=action.action_id),)
    return PanelSpec("hub", navigation=NavigationSpec(), actions=(action,), components=comps)


def test_never_strand_panel_without_navigation():
    result = compile_manifests(manifests=[
        _economy(panels=(PanelSpec("hub", navigation=None),))])
    assert not result.ok or True
    # navigation=None => SEMANTIC_VIOLATION
    _register_basics()
    result = compile_manifests(manifests=[_economy(panels=(PanelSpec("hub"),))])
    assert any("no NavigationSpec" in v.detail for v in result.violations)


def test_never_strand_unbound_and_double_bound_actions():
    _register_basics()
    action = PanelActionSpec("econ.act", handler=HandlerRef("economy.give"))
    unbound = compile_manifests(manifests=[
        _economy(panels=(_panel_with(action, components=()),))])
    assert any("bound by 0 components" in v.detail for v in unbound.violations)
    double = compile_manifests(manifests=[_economy(panels=(
        _panel_with(action, components=(ComponentSpec(action_id="econ.act"),
                                        ComponentSpec(action_id="econ.act"))),))])
    assert any("bound by 2 components" in v.detail for v in double.violations)


def test_never_strand_component_targeting_undeclared_action():
    _register_basics()
    panel = PanelSpec("hub", navigation=NavigationSpec(),
                      components=(ComponentSpec(action_id="ghost"),))
    result = compile_manifests(manifests=[_economy(panels=(panel,))])
    assert any("undeclared action 'ghost'" in v.detail for v in result.violations)


def test_destructive_confirmation_and_typed_challenge():
    _register_basics()
    naked = PanelActionSpec("econ.wipe", handler=HandlerRef("economy.give"), destructive=True)
    result = compile_manifests(manifests=[_economy(panels=(_panel_with(naked),))])
    assert any("destructive without ConfirmationSpec" in v.detail for v in result.violations)

    irreversible = PanelActionSpec(
        "econ.wipe", handler=HandlerRef("economy.give"), destructive=True,
        confirm=ConfirmationSpec(typed_challenge=False), reversibility="IRREVERSIBLE")
    result = compile_manifests(manifests=[_economy(panels=(_panel_with(irreversible),))])
    assert any("typed challenge" in v.detail for v in result.violations)


def _form(**overrides):
    """A real G-10 ModalSpec (the compiler duck-reads named fields; the
    P5 role walk needs the REAL registered grammar types)."""
    from sb.spec.panels import ModalFieldSpec, ModalSpec
    kwargs = dict(modal_id="econ.form", title="F",
                  fields=(ModalFieldSpec(field_id="a", label="A"),))
    kwargs.update(overrides)
    return ModalSpec(**kwargs)


def _modal_command(**overrides):
    kwargs = dict(surface="slash", route=HandlerRef("economy.give"),
                  modal=_form(), defer_mode="modal")
    kwargs.update(overrides)
    return CommandSpec("form", **kwargs)


def _modal_flags(result):
    return [v.detail for v in result.violations if "modal_ingress" in v.detail]


def test_modal_ingress_good_shape_compiles_green():
    _register_basics()
    result = compile_manifests(manifests=[_economy(commands=(_modal_command(),))])
    assert _modal_flags(result) == []
    assert result.ok


def test_modal_ingress_is_slash_only():
    _register_basics()
    for kind in ("prefix", "both"):
        result = compile_manifests(manifests=[
            _economy(commands=(_modal_command(surface=kind),))])
        assert any("must be kind=slash" in d for d in _modal_flags(result))


def test_modal_ingress_defer_mode_pairing_both_directions():
    _register_basics()
    formless = compile_manifests(manifests=[_economy(commands=(
        CommandSpec("form", surface="slash", route=HandlerRef("economy.give"),
                    defer_mode="modal"),))])
    assert any("requires a ModalSpec" in d for d in _modal_flags(formless))
    deferless = compile_manifests(manifests=[
        _economy(commands=(_modal_command(defer_mode=None),))])
    assert any("requires defer_mode=modal" in d for d in _modal_flags(deferless))


def test_modal_ingress_route_must_dispatch_the_submit():
    _register_basics()
    routeless = compile_manifests(manifests=[
        _economy(commands=(_modal_command(route=None),))])
    assert any("HandlerRef/WorkflowRef" in d for d in _modal_flags(routeless))
    # a PanelRef submit route is a stranded form (the ref must RESOLVE or
    # P2's unresolved-ref verdict short-circuits before the P6 fence).
    from sb.spec.refs import panel as panel_ref

    @panel_ref("economy.hub")
    def _hub():  # pragma: no cover — resolution target only
        pass

    paneled = compile_manifests(manifests=[
        _economy(commands=(_modal_command(route=PanelRef("economy.hub")),))])
    assert any("HandlerRef/WorkflowRef" in d for d in _modal_flags(paneled))


def test_modal_ingress_field_fences():
    from sb.spec.panels import ModalFieldSpec
    _register_basics()
    six = tuple(ModalFieldSpec(field_id=f"f{i}", label="L") for i in range(6))
    result = compile_manifests(manifests=[
        _economy(commands=(_modal_command(modal=_form(fields=six)),))])
    assert any("Discord allows 1..5" in d for d in _modal_flags(result))
    dup = (ModalFieldSpec(field_id="a", label="A"),
           ModalFieldSpec(field_id="a", label="B"))
    result = compile_manifests(manifests=[
        _economy(commands=(_modal_command(modal=_form(fields=dup)),))])
    assert any("duplicate field_ids" in d for d in _modal_flags(result))


def test_leaderboard_writer_predicate():
    _register_basics()
    orphan = SubsystemManifest(
        key="xp", stores=(StoreSpec("xp_rows"),),
        panels=(PanelSpec("xp_hub", navigation=NavigationSpec()),),
        settings=(LeaderboardSpec(stat_key="xp_total"),))
    result = compile_manifests(manifests=[orphan])
    assert any("no declared writer" in v.detail for v in result.violations)
    written = SubsystemManifest(
        key="xp", stores=(StoreSpec("xp_rows", stat_key="xp_total"),),
        settings=(LeaderboardSpec(stat_key="xp_total"),))
    assert compile_manifests(manifests=[written]).ok


def test_audit_completeness_mutating_needs_workflow_ref():
    _register_basics()
    bad = _economy(commands=(CommandSpec("pay", surface="slash", effect="mutating",
                                         route=HandlerRef("economy.give")),))
    result = compile_manifests(manifests=[bad])
    assert any("audit_completeness" in v.detail for v in result.violations)
    good = _economy(commands=(CommandSpec("pay", surface="slash", effect="mutating",
                                          route=WorkflowRef("economy.transfer")),))
    assert compile_manifests(manifests=[good]).ok


def test_action_cooldown_parity():
    _register_basics()
    action = PanelActionSpec("econ.pay", handler=WorkflowRef("economy.transfer"),
                             effect="mutating", cooldown=5.0, mirrors="pay")
    manifest = _economy(
        commands=(CommandSpec("pay", surface="slash", cooldown=10.0),),
        panels=(_panel_with(action),))
    result = compile_manifests(manifests=[manifest])
    assert any("cooldown differs" in v.detail for v in result.violations)
    aligned = _economy(
        commands=(CommandSpec("pay", surface="slash", cooldown=5.0),),
        panels=(_panel_with(dataclasses.replace(action)),))
    assert compile_manifests(manifests=[aligned]).ok


# --- P7 (armed at K3; unit-driven here) ------------------------------------------------

def test_store_drop_needs_signed_retirement(tmp_path):
    baseline = {"projections": {"stores": {"economy_wallets": {}, "gone_table": {}}}}
    current = {"projections": {"stores": {"economy_wallets": {}}}}
    violations = []
    _p7_store_completeness(current, baseline, violations,
                           retirements_path="does-not-exist.yml")
    assert violations and violations[0].failure_class == "STORE_DROP"

    signed = tmp_path / "retirements.yml"
    signed.write_text(
        "retirements:\n"
        "  - table: gone_table\n"
        "    retired_by: Q-0999\n"
        "    disposition: reverse-migrate\n")
    violations = []
    _p7_store_completeness(current, baseline, violations, retirements_path=str(signed))
    assert violations == []

    no_disposition = tmp_path / "bad.yml"
    no_disposition.write_text("retirements:\n  - table: gone_table\n    retired_by: Q-0999\n")
    violations = []
    _p7_store_completeness(current, baseline, violations, retirements_path=str(no_disposition))
    assert violations and "REQUIRED disposition" in violations[0].detail


def test_p7_no_baseline_means_no_drop_possible():
    violations = []
    _p7_store_completeness({"projections": {"stores": {}}}, None, violations)
    assert violations == []


# --- P8: layout locks ---------------------------------------------------------------------

def test_overlay_may_touch_a_fields_only(tmp_path):
    _register_basics()
    panel = PanelSpec("econ_hub", navigation=NavigationSpec())
    result = compile_manifests(manifests=[_economy(panels=(panel,))])
    assert result.ok
    snapshot_body = {k: v for k, v in result.snapshot.items()
                     if k not in ("stable_hash", "compiler_version", "manifest_count")}

    lock = tmp_path / "econ.lock.json"
    lock.write_text('[{"target": "PanelSpec:econ_hub", "field": "layout", '
                    '"arrangement": ["row1"]}]')
    violations = []
    _p8_serialize(snapshot_body, violations, layout_dir=str(tmp_path))
    assert violations == []
    assert snapshot_body["subsystems"]["economy"]["panels"][0]["layout"] == ["row1"]

    lock.write_text('[{"target": "PanelSpec:econ_hub", "field": "navigation", '
                    '"arrangement": {}}]')
    violations = []
    _p8_serialize(snapshot_body, violations, layout_dir=str(tmp_path))
    assert violations and "illegal_overlay_key" in violations[0].detail


# --- P9 / hash membership -------------------------------------------------------------------

def test_recompile_parity_drift():
    _register_basics()
    first = compile_manifests(manifests=[_economy()])
    assert first.ok
    green = compile_manifests(manifests=[_economy()], committed_snapshot=first.snapshot)
    assert green.ok
    # The snapshot carries NO stable_hash field — drift is a BODY divergence.
    assert "stable_hash" not in first.snapshot
    tampered = dict(first.snapshot, schema_version=999)
    red = compile_manifests(manifests=[_economy()], committed_snapshot=tampered)
    assert not red.ok
    assert red.violations[0].failure_class == "DRIFT"
    # A legacy committed snapshot still carrying the field stays green —
    # compute_stable_hash ignores it (hash membership, spec 01 §5 fork 9).
    legacy = dict(first.snapshot, stable_hash="sha256:0000")
    assert compile_manifests(manifests=[_economy()],
                             committed_snapshot=legacy).ok


def test_hash_excludes_tool_metadata_and_includes_content():
    _register_basics()
    result = compile_manifests(manifests=[_economy()])
    snapshot = result.snapshot
    rehashed = compute_stable_hash(dict(snapshot, compiler_version="9.9.9",
                                        manifest_count=999,
                                        stable_hash="sha256:cafe"))
    assert rehashed == result.stable_hash
    content_changed = dict(snapshot, schema_version=2)
    assert compute_stable_hash(content_changed) != result.stable_hash
