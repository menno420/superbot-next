"""Band 7 — the guided CT-team flow (curation report 2026-07-13 row 2:
``btd6.ctteam.set_team`` REWORK; the ``btd6.ctteam_set_pending``
terminal retires).

ORACLE: disbot/services/btd6_ct_team_service.py (parse/set/clear
semantics) + views/btd6/ct_group_flow.py (modal + preview + Confirm/
Cancel copy) + cogs/btd6/_builders.handle_ctteam @9c16365. The decided
shape (Q-0064): URL/id → parse → preview → confirm — never an immediate
write; ``clear`` stays immediate. Live NK bracket standings ride D-0046
— the preview/status slots render the shipped no-active-event byte.

Golden safety: the bare `!btd6 ctteam` open keeps its pinned bytes
(sweep_btd6_ctteam — unset copy, label/emoji/style/row unchanged);
asserted on the specs below. DB-free: the workflow-engine seam is
recorded like the sibling band-7 suites."""

from __future__ import annotations

import asyncio
import dataclasses
from types import SimpleNamespace

import pytest

run = asyncio.run


def _handler(name: str):
    from sb.spec.refs import HandlerRef, resolve as resolve_ref

    return resolve_ref(HandlerRef(name))


@dataclasses.dataclass
class Req:
    args: dict
    guild_id: int | None = 42
    channel_id: int | None = 7
    request_id: str = "req-1"
    confirmed: bool = False
    actor: object = dataclasses.field(default_factory=lambda: SimpleNamespace(
        user_id=7, member_tier="staff", is_guild_operator=True))


@pytest.fixture()
def ensure_refs():
    import sb.manifest.btd6 as m

    m.ENSURE_REFS()


@pytest.fixture()
def engine_recorder(monkeypatch):
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS

    calls: list = []

    async def fake_run(ref, ctx):
        calls.append((getattr(ref, "name", str(ref)), dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS, user_message=None,
                               after={"ct_team": {"value": ""}}, before={})

    monkeypatch.setattr(engine, "run", fake_run)
    return calls


@pytest.fixture()
def panel_recorder(monkeypatch):
    from sb.kernel.panels import engine as panel_engine

    opened: list = []

    async def fake_open(ref, req):
        opened.append((getattr(ref, "name", str(ref)), dict(req.args)))
        return "msg-1"

    monkeypatch.setattr(panel_engine, "open_panel", fake_open)
    return opened


# --- parse_group_id (oracle btd6_ct_team_service.parse_group_id, verbatim) --------


def test_parse_group_id_accepts_bare_ids_and_group_urls():
    from sb.domain.btd6.ct_team import parse_group_id

    assert parse_group_id("ABCDEF1234") == "abcdef1234"
    assert parse_group_id("  abcdef1234  ") == "abcdef1234"
    assert parse_group_id(
        "https://data.ninjakiwi.com/btd6/ct/ct_1/leaderboard/group/"
        "ABCDEF1234abcdef?x=1#frag") == "abcdef1234abcdef"
    assert parse_group_id("…/leaderboard/group/deadbeef99/") == "deadbeef99"


def test_parse_group_id_rejects_the_mis_paste():
    from sb.domain.btd6.ct_team import parse_group_id

    assert parse_group_id("") is None
    assert parse_group_id("   ") is None
    assert parse_group_id("nope!") is None
    assert parse_group_id("1234567") is None           # < 8 hex chars
    assert parse_group_id("x" * 65) is None
    assert parse_group_id("/group/") is None


# --- the panel specs (modal ingress + confirm page shape) --------------------------


def test_set_team_button_is_the_shipped_modal_ingress():
    from sb.domain.btd6.panels import CTTEAM_SET_MODAL, ctteam_spec
    from sb.spec.panels import DeferMode
    from sb.spec.refs import HandlerRef

    spec = ctteam_spec()
    set_team = {a.action_id: a for a in spec.actions}["set_team"]
    # golden safety (sweep_btd6_ctteam): label/emoji/style/row unchanged.
    assert set_team.label == "Set CT team…"
    assert set_team.emoji == "🛡️"
    assert spec.layout.pages[0].rows == (("set_team",),)
    assert set_team.defer_mode is DeferMode.MODAL
    assert set_team.modal is CTTEAM_SET_MODAL
    # oracle-verbatim form (views/btd6/ct_group_flow.CTGroupFlowModal).
    assert CTTEAM_SET_MODAL.modal_id == "btd6.ctteam_set_form"
    assert CTTEAM_SET_MODAL.title == "Set CT team"
    (field,) = CTTEAM_SET_MODAL.fields
    assert field.field_id == "raw"
    assert field.label == "CT bracket URL or id"
    assert field.placeholder == (
        "https://…/leaderboard/group/<id> or the bare id")
    assert field.required is True
    assert field.max_length == 200
    assert CTTEAM_SET_MODAL.on_submit == HandlerRef("btd6.ctteam_set_submit")


def test_confirm_page_is_the_shipped_confirm_view_shape():
    from sb.domain.btd6.panels import ctteam_confirm_spec
    from sb.spec.panels import ActionStyle
    from sb.spec.refs import HandlerRef

    spec = ctteam_confirm_spec()
    actions = {a.action_id: a for a in spec.actions}
    assert actions["confirm"].label == "Confirm"
    assert actions["confirm"].style is ActionStyle.SUCCESS
    assert actions["confirm"].audience_tier == "staff"
    assert actions["confirm"].handler == HandlerRef(
        "btd6.ctteam_confirm_submit")
    assert actions["cancel"].label == "Cancel"
    assert actions["cancel"].style is ActionStyle.SECONDARY
    assert spec.session_lifecycle is True                # author-locked view
    assert spec.timeout_s == 180                         # BaseView 180s
    assert spec.layout.pages[0].rows == (("confirm", "cancel"),)


def test_the_pending_terminal_is_retired(ensure_refs):
    import sb.domain.btd6.oracle_surface as surface
    from sb.spec.refs import HandlerRef, is_registered

    assert not is_registered(HandlerRef("btd6.ctteam_set_pending"))
    src = open(surface.__file__, encoding="utf-8").read()
    assert 'pending_handler("btd6.ctteam_set_pending"' not in src
    for ref in ("btd6.ctteam_set_submit", "btd6.ctteam_confirm_submit",
                "btd6.ctteam_cancel"):
        assert is_registered(HandlerRef(ref))


# --- the cards (preview + team view bytes) -----------------------------------------


def test_ctteam_card_unset_keeps_the_golden_bytes():
    from sb.domain.btd6.oracle_cards import ctteam_card

    card = ctteam_card()
    assert card.description == (
        "No CT team is set for this server.\n"
        "An admin can set one with `!btd6 ctteam <bracket id or group "
        "URL>` — copy your team's `…/leaderboard/group/<id>` link from "
        "the CT team leaderboard.")
    assert card.footer == "ctx=btd6_ct:team"
    assert card.fields == ()


def test_ctteam_card_configured_shows_pointer_and_d0046_status():
    from sb.domain.btd6.oracle_cards import ctteam_card

    card = ctteam_card("abcdef1234")
    assert card.description == "Configured bracket id: `abcdef1234`"
    assert card.fields == (
        ("Status", "No Contested Territory event is active right now.",
         False),)
    assert card.footer == "ctx=btd6_ct:team"


def test_confirm_card_change_line_and_footer():
    from sb.domain.btd6.oracle_cards import ctteam_confirm_card

    fresh = ctteam_confirm_card("", "abcdef1234")
    assert fresh.title == "🛡️ BTD6 — Confirm CT team"
    assert fresh.fields[0] == ("Bracket id", "`abcdef1234`", False)
    assert fresh.fields[1] == (
        "Preview", "No Contested Territory event is active right now.",
        False)
    assert fresh.footer == (
        "Confirm to save, Cancel to discard. • ctx=btd6_ct:confirm")

    change = ctteam_confirm_card("deadbeef99", "abcdef1234")
    assert change.fields[0] == (
        "Change", "`deadbeef99` → `abcdef1234`", False)
    # same-id re-paste renders the bare id line (oracle else-branch).
    same = ctteam_confirm_card("abcdef1234", "abcdef1234")
    assert same.fields[0] == ("Bracket id", "`abcdef1234`", False)


# --- the modal submit (CTGroupFlowModal.on_submit) ----------------------------------


def test_modal_submit_refuses_the_mis_paste(ensure_refs, panel_recorder):
    from sb.spec.outcomes import BLOCKED

    submit = _handler("btd6.ctteam_set_submit")
    reply = run(submit(Req(args={"raw": "not a bracket"})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "That doesn't look like a CT bracket id or group URL. Paste "
        "your team's `…/leaderboard/group/<id>` link or the bare id.")
    assert panel_recorder == []              # a refusal never opens the page


def test_modal_submit_opens_the_confirm_page(ensure_refs, panel_recorder):
    submit = _handler("btd6.ctteam_set_submit")
    reply = run(submit(Req(args={
        "raw": "https://x/btd6/ct/ct_1/leaderboard/group/ABCDEF1234"})))
    assert reply is None
    (panel_id, args), = panel_recorder
    assert panel_id == "btd6.ctteam_confirm"
    assert args["ct_group_id"] == "abcdef1234"


# --- the confirm/cancel step (CTGroupConfirmView) -----------------------------------


def test_confirm_commits_through_the_audited_op(ensure_refs,
                                                engine_recorder):
    confirm = _handler("btd6.ctteam_confirm_submit")
    reply = run(confirm(Req(args={"ct_group_id": "abcdef1234"})))
    assert reply.user_message == "✅ CT team set to `abcdef1234`."
    (op_name, params), = engine_recorder
    assert op_name == "btd6.set_ct_team"
    assert params == {"group_id": "abcdef1234"}


def test_confirm_defensive_branch_never_writes(ensure_refs,
                                               engine_recorder):
    from sb.spec.outcomes import BLOCKED

    confirm = _handler("btd6.ctteam_confirm_submit")
    # a stale/foreign page open leaves the args bare (cleanup posture) —
    # the shipped defensive byte answers, never a write.
    reply = run(confirm(Req(args={})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "That bracket id no longer parses — nothing saved.")
    assert engine_recorder == []


def test_cancel_speaks_the_shipped_byte(ensure_refs, engine_recorder):
    cancel = _handler("btd6.ctteam_cancel")
    reply = run(cancel(Req(args={"ct_group_id": "abcdef1234"})))
    assert reply.user_message == "Cancelled — CT team unchanged."
    assert engine_recorder == []


# --- the typed leg (`!btd6 ctteam …` — handle_ctteam, copy verbatim) ----------------


def _cmd_req(arg: str, *, operator: bool = True,
             guild_id: int | None = 42) -> Req:
    return Req(args={"argv": tuple(arg.split()) if arg else ()},
               guild_id=guild_id,
               actor=SimpleNamespace(user_id=7, member_tier="staff",
                                     is_guild_operator=operator))


def _card_embed(panel_recorder):
    (panel_id, args), = panel_recorder
    assert panel_id == "btd6.card"
    return args["_card"]


def test_cmd_ctteam_dm_guard(ensure_refs, panel_recorder):
    cmd = _handler("btd6.cmd_ctteam")
    assert run(cmd(_cmd_req("", guild_id=None))) is None
    embed = _card_embed(panel_recorder)
    assert embed.title == "🛡️ BTD6 — Your CT Team"
    assert embed.description == "Use this in a server, not a DM."
    assert embed.footer == ""                # notices carry no ctx footer


def test_cmd_ctteam_permission_notice(ensure_refs, panel_recorder):
    cmd = _handler("btd6.cmd_ctteam")
    assert run(cmd(_cmd_req("abcdef1234", operator=False))) is None
    embed = _card_embed(panel_recorder)
    assert embed.description == (
        "You need the Manage Server permission to change the CT team.")


def test_cmd_ctteam_clear_is_immediate_and_audited(ensure_refs,
                                                   panel_recorder,
                                                   engine_recorder):
    cmd = _handler("btd6.cmd_ctteam")
    assert run(cmd(_cmd_req("CLEAR"))) is None       # case-insensitive
    (op_name, params), = engine_recorder
    assert op_name == "btd6.set_ct_team"
    assert params == {"group_id": ""}
    embed = _card_embed(panel_recorder)
    assert embed.description == "Cleared this server's CT team."


def test_cmd_ctteam_mis_paste_notice(ensure_refs, panel_recorder,
                                     engine_recorder):
    cmd = _handler("btd6.cmd_ctteam")
    assert run(cmd(_cmd_req("nope!"))) is None
    embed = _card_embed(panel_recorder)
    assert embed.description == (
        "That doesn't look like a CT bracket id or group URL. Paste "
        "your team's `…/leaderboard/group/<id>` link or the bare id.")
    assert engine_recorder == []             # parse refusal never writes


def test_cmd_ctteam_arg_opens_the_confirm_page_never_writes(
        ensure_refs, panel_recorder, engine_recorder):
    cmd = _handler("btd6.cmd_ctteam")
    assert run(cmd(_cmd_req("ABCDEF1234"))) is None
    (panel_id, args), = panel_recorder
    assert panel_id == "btd6.ctteam_confirm"
    assert args["ct_group_id"] == "abcdef1234"
    assert engine_recorder == []             # the commit is Confirm's


def test_cmd_ctteam_bare_still_opens_the_team_view(ensure_refs,
                                                   panel_recorder):
    cmd = _handler("btd6.cmd_ctteam")
    assert run(cmd(_cmd_req(""))) is None
    (panel_id, args), = panel_recorder
    assert panel_id == "btd6.ctteam"
    assert args["can_manage"] is True


# --- the K7 op row -------------------------------------------------------------------


def test_set_ct_team_op_shape(ensure_refs):
    from sb.domain.btd6.ops import CT_GROUP_KEY, CT_TEAM

    assert CT_GROUP_KEY == "btd6_ct_group_id"    # settings key, verbatim
    assert CT_TEAM.op_key == "btd6.set_ct_team"
    assert CT_TEAM.authority_ref == "staff"      # Manage-Server gate
    assert CT_TEAM.audit_verb == "btd6_ct_team_set"
    (leg,) = CT_TEAM.legs
    assert leg.handler.name == "btd6.record_ct_team"
