"""The arrangement-invariance test (S3 deliverable; design-spec §2.10.2/§2.10.3).

Changing ONLY [A]-tagged fields (arrangement — sim-owned) must leave every
SEMANTIC projection of the snapshot byte-identical: namespace corpus, stores,
events, refs, and every [S]-tagged field. A sim bug can corrupt arrangement
but structurally cannot touch semantics/custom_ids/capabilities.
"""

import dataclasses

from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, handler
from sb.spec.roles import field_role
from tests.unit.compiler.conftest import (
    CommandSpec,
    ComponentSpec,
    NavigationSpec,
    PanelActionSpec,
    PanelSpec,
    StoreSpec,
)
from tools.manifest_compile import canonical_json, compile_manifests


def _manifest(help_order: int, layout: tuple):
    @handler("economy.give")
    def _give():  # pragma: no cover
        pass

    action = PanelActionSpec("econ.act", handler=HandlerRef("economy.give"))
    return SubsystemManifest(
        key="economy",
        commands=(CommandSpec("give", surface="slash", help_order=help_order),),
        panels=(PanelSpec("econ_hub", navigation=NavigationSpec(), actions=(action,),
                          components=(ComponentSpec(action_id="econ.act"),),
                          layout=layout),),
        stores=(StoreSpec("economy_wallets"),),
    )


def test_a_field_changes_leave_semantics_invariant():
    from sb.spec.refs import clear_ref_table

    base = compile_manifests(manifests=[_manifest(help_order=1, layout=("row1",))])
    assert base.ok, base.violations
    clear_ref_table()
    rearranged = compile_manifests(manifests=[_manifest(help_order=7, layout=("row2", "row3"))])
    assert rearranged.ok, rearranged.violations

    # Every semantic projection is byte-identical under the arrangement change.
    for section in ("namespace", "stores", "events", "refs"):
        assert canonical_json(base.snapshot["projections"][section]) == \
            canonical_json(rearranged.snapshot["projections"][section]), section

    # The serialized subsystems differ ONLY in [A]-tagged fields.
    def strip_a_fields(node, type_name):
        if isinstance(node, dict):
            return {k: strip_a_fields(v, type_name) for k, v in node.items()
                    if _role_of(k) != "A"}
        if isinstance(node, list):
            return [strip_a_fields(v, type_name) for v in node]
        return node

    def _role_of(field_name):
        for tn in ("SubsystemManifest", "CommandSpec", "PanelSpec", "PanelActionSpec",
                   "ComponentSpec", "NavigationSpec", "StoreSpec"):
            role = field_role(tn, field_name)
            if role is not None:
                return role.value
        return None

    assert canonical_json(strip_a_fields(base.snapshot["subsystems"], None)) == \
        canonical_json(strip_a_fields(rearranged.snapshot["subsystems"], None))

    # And the arrangement change IS a content change (the hash moves) —
    # arrangement is committed data, just sim-owned.
    assert base.stable_hash != rearranged.stable_hash


def test_probe_fields_are_actually_tagged():
    assert field_role("CommandSpec", "help_order").value == "A"
    assert field_role("PanelSpec", "layout").value == "A"
    assert field_role("CommandSpec", "name").value == "S"


def test_replace_only_a_field_keeps_namespace_projection():
    m = _manifest(help_order=1, layout=())  # registers economy.give once
    base = compile_manifests(manifests=[m])
    changed_cmd = dataclasses.replace(m.commands[0], help_order=99)
    m2 = dataclasses.replace(m, commands=(changed_cmd,))
    other = compile_manifests(manifests=[m2])  # same ref table, [A]-only delta
    assert canonical_json(base.snapshot["projections"]["namespace"]) == \
        canonical_json(other.snapshot["projections"]["namespace"])
