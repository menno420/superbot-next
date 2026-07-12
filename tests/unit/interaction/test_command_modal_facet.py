"""The CommandSpec MODAL facet (G-10 on the command facet — the D-0073
named successor: a slash command declares "this command opens modal X",
the shipped ``send_modal``-as-initial-response app-command ingress class,
ORACLE cogs/btd6/_unified.py strat_submit_slash).

The engine is deliberately UNCHANGED: resolve()'s ACK boundary duck-reads
``defer_mode``/``modal`` off the target spec (the PanelActionSpec.modal
lane), so these tests pin that a REAL CommandSpec rides the same
open-terminal / stash / submit-re-entry contract — plus the two dispatch
indexes' new (modal_id, Surface.MODAL) row, the seam ``request_from_modal``
tries BEFORE the panel static-table fallthrough.

NO manifest declares the facet yet: the sole shipped consumer
(`/btd6 strat submit`) is GOLDEN-BLOCKED — goldens/btd6/
sweep_slash_btd6_strat_submit pins the unregistered-slash SILENCE (zero
calls, the #151 drop rule; the #218 trap-17 class of 30). See D-0076.
"""

from __future__ import annotations

import asyncio

from types import SimpleNamespace

import pytest

from sb.kernel.interaction.request import Surface
from sb.kernel.interaction.resolve import pop_modal_args, resolve
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.outcomes import SUCCESS, DeferMode, ReplyVisibility
from sb.spec.panels import ModalFieldSpec, ModalSpec
from sb.spec.refs import HandlerRef
from tests.unit.interaction.conftest import FakeResponder, make_request

run = asyncio.run

_CALLS: list[dict] = []


async def _submit_probe(req):
    _CALLS.append(dict(req.args))
    return None


def _ensure_handler() -> HandlerRef:
    """Idempotent registration: sibling suites (tests/unit/compiler) wipe
    the global ref table around each of their tests, so a module-import
    registration can be gone by the time this module RUNS — re-register the
    STABLE probe (same callable, module-global recorder) per test."""
    from sb.spec import refs

    ref = HandlerRef("cmdmodal.submit_probe")
    try:
        refs.handler("cmdmodal.submit_probe")(_submit_probe)
    except Exception:  # noqa: BLE001 — RefRedefined: already ours
        pass
    return ref


@pytest.fixture(autouse=True)
def _fresh_calls():
    _CALLS.clear()
    yield
    _CALLS.clear()


FORM = ModalSpec(
    modal_id="cmdmodal.form",
    title="Probe form",
    fields=(ModalFieldSpec(field_id="title", label="Title"),),
)


def _command(**overrides) -> CommandSpec:
    kwargs = dict(
        name="probe-submit",
        kind=CommandKind.SLASH,
        route=_ensure_handler(),
        modal=FORM,
        defer_mode=DeferMode.MODAL,
        audience_tier="user",
        reply_visibility=ReplyVisibility.EPHEMERAL,
    )
    kwargs.update(overrides)
    return CommandSpec(**kwargs)


def test_modal_field_is_declared_S_and_defaults_none():
    from sb.spec.roles import field_role

    assert CommandSpec(name="x", kind=CommandKind.PREFIX).modal is None
    assert field_role("CommandSpec", "modal").value == "S"


def test_slash_open_issues_the_form_and_never_dispatches():
    cmd = _command()
    responder = FakeResponder(Surface.SLASH)
    result = run(resolve(make_request(
        cmd, surface=Surface.SLASH, responder=responder,
        args={"session": "opening-arg"})))
    # the modal IS the response (G-10 terminal): no defer-ack, no dispatch.
    assert responder.modals == [FORM]
    assert responder.acks == []
    assert result.outcome == SUCCESS
    assert _CALLS == []
    # the opening args rode the kernel stash (keyed form/user/origin-message;
    # a slash origin has no message => None on both sides).
    assert pop_modal_args("cmdmodal.form", 1, None) == {"session": "opening-arg"}


def test_modal_submit_reentry_dispatches_the_route_with_the_fields():
    cmd = _command()
    responder = FakeResponder(Surface.MODAL)
    result = run(resolve(make_request(
        cmd, surface=Surface.MODAL, responder=responder,
        args={"title": "T"})))
    # the submit re-entry acks like AUTO with the DECLARED visibility and
    # dispatches the command's own route with the field values.
    assert responder.acks == [True]          # ReplyVisibility.EPHEMERAL
    assert result.outcome == SUCCESS
    assert _CALLS == [{"title": "T"}]


def test_build_live_index_registers_the_modal_root_surface_modal():
    from sb.app.build_runtime import build_live_index

    cmd = _command()
    plain = CommandSpec(name="plain", kind=CommandKind.SLASH,
                        route=_ensure_handler())
    manifest = SimpleNamespace(key="probe", commands=(cmd, plain), panels=())
    index = build_live_index([manifest])

    target = index.get(("cmdmodal.form", Surface.MODAL))
    assert target is not None and target.spec is cmd
    assert target.key == "cmdmodal.form"     # subsystem derives from the root
    # a modal-less command mints NO Surface.MODAL row.
    assert not any(surface is Surface.MODAL and entry.spec is plain
                   for (_key, surface), entry in index.items())


def test_parity_boot_index_mirrors_the_live_modal_row():
    from sb.adapters.parity.boot import Harness

    cmd = _command()
    h = object.__new__(Harness)
    h._index = {}
    h._build_index([SimpleNamespace(key="probe", commands=(cmd,), panels=())])
    target = h._index.get(("cmdmodal.form", Surface.MODAL))
    assert target is not None and target.spec is cmd


def test_dispatch_modal_routes_the_wire_submit_via_the_modal_index():
    """The adapter-level round-trip: the type-5 submit resolves through
    (modal_id, Surface.MODAL) — request_from_modal's FIRST lookup — never
    needing a panel static-table binding, and restores the stashed opening
    args (submitted fields win ties)."""
    from sb.app.build_runtime import build_live_index
    from sb.kernel.interaction.adapters import install_target_index
    from sb.kernel.interaction.adapters.modal import dispatch_modal

    cmd = _command()
    index = build_live_index(
        [SimpleNamespace(key="probe", commands=(cmd,), panels=())])
    install_target_index(lambda key, surface: index.get((key, surface)))

    # the OPEN (slash) — stashes the opening args under (form, user, None).
    open_responder = FakeResponder(Surface.SLASH)
    run(resolve(make_request(cmd, surface=Surface.SLASH,
                             responder=open_responder,
                             args={"session": "opening-arg"})))
    assert open_responder.modals == [FORM]

    # the SUBMIT (wire type 5) — the live component feed's dispatch seam.
    member = SimpleNamespace(
        id=1, name="probe",
        guild_permissions=SimpleNamespace(administrator=False,
                                          moderate_members=False,
                                          manage_guild=False),
        roles=[])
    interaction = SimpleNamespace(
        id=901,
        user=member,
        guild=SimpleNamespace(id=42, owner_id=7),
        channel_id=7,
        message=None,
        data={"custom_id": "cmdmodal.form",
              "components": [{"components": [
                  {"custom_id": "title", "value": "T"}]}]},
    )
    responder = FakeResponder(Surface.MODAL)
    result = run(dispatch_modal(interaction, responder=responder))
    assert result is not None and result.outcome == SUCCESS
    assert _CALLS == [{"session": "opening-arg", "title": "T",
                       "interaction_id": 901}]
