"""The S9b registration fences (design-spec §2.3/§2.4/§2.6 + §3.4 + G-10)."""

from __future__ import annotations

import pytest

from sb.kernel.panels.compile import PanelCompileError, check_panel
from sb.spec.confirmation import ConfirmationSpec
from sb.spec.outcomes import DeferMode
from sb.spec.panels import (
    ActionStyle,
    Audience,
    LayoutSpec,
    ModalFieldSpec,
    ModalSpec,
    NavigationSpec,
    PageSpec,
    SelectorKind,
    SelectorSpec,
)
from sb.spec.refs import HandlerRef, WorkflowRef
from sb.kernel.workflow.registry import REGISTRY

from tests.unit.panels.conftest import make_action, make_panel


def err(code, spec):
    with pytest.raises(PanelCompileError) as exc:
        check_panel(spec)
    assert exc.value.code == code, exc.value


def test_clean_panel_compiles():
    check_panel(make_panel(actions=(make_action(),)))


def test_layout_must_place_every_declared_component():
    spec = make_panel(actions=(make_action("a", "A"), make_action("b", "B")),
                      layout=LayoutSpec(pages=(PageSpec(rows=(("a",),)),)))
    err("layout_coverage", spec)


def test_layout_may_not_place_undeclared_or_duplicate():
    spec = make_panel(actions=(make_action("a", "A"),),
                      layout=LayoutSpec(pages=(PageSpec(rows=(("a", "ghost"),)),)))
    err("layout_coverage", spec)
    spec = make_panel(actions=(make_action("a", "A"),),
                      layout=LayoutSpec(pages=(PageSpec(rows=(("a",), ("a",))),)))
    err("layout_coverage", spec)


def test_discord_caps_enforced():
    actions = tuple(make_action(f"a{i}", f"A{i}") for i in range(6))
    spec = make_panel(actions=actions,
                      layout=LayoutSpec(pages=(PageSpec(rows=(tuple(
                          a.action_id for a in actions),)),)))
    err("layout_caps", spec)
    # 6 rows of 1
    spec = make_panel(actions=actions,
                      layout=LayoutSpec(pages=(PageSpec(rows=tuple(
                          (a.action_id,) for a in actions)),)))
    err("layout_caps", spec)


def test_persistent_requires_timeout_none():
    err("persistent_timeout",
        make_panel(audience=Audience.PERSISTENT, timeout_s=180))
    check_panel(make_panel(audience=Audience.PERSISTENT, timeout_s=None))


def test_destructive_requires_danger_and_never_row0():
    err("destructive_style", make_panel(actions=(make_action(destructive=True),)))
    # danger but in row 0
    err("destructive_placement", make_panel(
        actions=(make_action(destructive=True, style=ActionStyle.DANGER),)))
    # danger, row 1 — clean
    a = make_action("del", "Delete", destructive=True, style=ActionStyle.DANGER)
    b = make_action("view", "View")
    check_panel(make_panel(
        actions=(a, b),
        layout=LayoutSpec(pages=(PageSpec(rows=(("view",), ("del",))),))))


def test_g10_modal_rules():
    err("modal_rules", make_panel(actions=(make_action(defer_mode=DeferMode.MODAL),)))
    too_many = ModalSpec(modal_id="m", title="T", fields=tuple(
        ModalFieldSpec(field_id=f"f{i}", label="L") for i in range(6)))
    err("modal_rules", make_panel(actions=(
        make_action(defer_mode=DeferMode.MODAL, modal=too_many),)))
    dup = ModalSpec(modal_id="m", title="T", fields=(
        ModalFieldSpec(field_id="x", label="L"), ModalFieldSpec(field_id="x", label="L2")))
    err("modal_rules", make_panel(actions=(
        make_action(defer_mode=DeferMode.MODAL, modal=dup),)))
    ok = ModalSpec(modal_id="m", title="T",
                   fields=(ModalFieldSpec(field_id="x", label="L"),))
    check_panel(make_panel(actions=(
        make_action(defer_mode=DeferMode.MODAL, modal=ok),)))


def test_never_strand_unless_session_lifecycle():
    nav = NavigationSpec(parent=None, show_help=False, show_home=False)
    err("never_strand", make_panel(navigation=nav))
    check_panel(make_panel(navigation=nav, session_lifecycle=True))


def test_custom_id_override_may_not_carry_scheme_token():
    err("scheme_token_override", make_panel(actions=(
        make_action(custom_id_override="g1:blackjack:s:hit"),)))
    sel = SelectorSpec(selector_id="pick", kind=SelectorKind.ROLE,
                       custom_id_override="g1:x:y:z")
    err("scheme_token_override", make_panel(selectors=(sel,)))
    # a legacy non-scheme override is fine
    check_panel(make_panel(actions=(make_action(custom_id_override="legacy_btn"),)))
    # …and so is a shipped legacy id that merely LOOKS like a scheme token
    # (a subsystem name ending in a digit — the shipped BTD6 hub's
    # persistent ids, goldens/btd6/sweep_btd6menu). Only a REGISTERED
    # scheme token is fenced; register_scheme_parser refuses the reverse
    # collision (see test_router_scheme_token_disjointness below).
    check_panel(make_panel(actions=(make_action(custom_id_override="btd6:ask"),)))


def test_router_scheme_token_disjointness():
    """§3.4 two-sided: a NEW scheme token may not claim a prefix a
    registered static custom_id already uses (static-first precedence
    would silently shadow every dynamic id under it — the compile fence's
    twin, guarding the direction the fence relaxation opened for the
    shipped ``btd6:*`` ids)."""
    from sb.kernel.panels import registry, router

    spec = make_panel(actions=(
        make_action(custom_id_override="zz9:probe"),))
    registry.register_panel(spec)
    try:
        with pytest.raises(ValueError, match="must stay disjoint"):
            router.register_scheme_parser("zz9", lambda cid: None)
        assert not router.is_scheme_token("zz9")
        assert router.is_scheme_token("g1")
    finally:
        registry.clear_panels_for_tests()


def test_escape_hatch_requires_justification():
    err("escape_hatch_justification",
        make_panel(renderer_override=HandlerRef("econ.board")))
    check_panel(make_panel(renderer_override=HandlerRef("econ.board"),
                           justification="game board — grammar-inexpressible"))


def test_irreversible_workflow_requires_confirm(monkeypatch):
    class FakeOp:
        reversibility = "irreversible"
    REGISTRY._by_op_key["econ.wipe"] = FakeOp()  # noqa: SLF001 — test seam
    try:
        err("confirm_required", make_panel(actions=(
            make_action(handler=WorkflowRef("econ.wipe")),)))
        check_panel(make_panel(actions=(make_action(
            handler=WorkflowRef("econ.wipe"),
            confirm=ConfirmationSpec(reversibility="irreversible")),)))
        # unregistered ref: P2's failure surface, not this fence's
        check_panel(make_panel(actions=(
            make_action(handler=WorkflowRef("econ.unknown")),)))
    finally:
        REGISTRY.clear_for_tests()
