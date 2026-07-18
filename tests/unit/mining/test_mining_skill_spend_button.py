"""Mining 🌳 Skill Tree per-branch spend buttons (backlog B2) — the shipped
⛏️/⚔️/🍀/🛠️ branch buttons made a live handler that spends ONE point into the
clicked branch through the audited skill op.

ORACLE (menno420/superbot): disbot/views/mining/skills_panel.py
(``MiningSkillsView._spend`` -> ``skill_service.allocate`` with the default
``n=1``) + disbot/services/skill_service.py (``allocate`` — the branch/amount/
cap/budget validation and the response strings, VERBATIM).

The branch buttons run the SAME audited op the LIVE `!skill <branch>` command
lane carries (``mining.skill`` -> ``record_skill``), already byte-pinned by
goldens/mining/mining_skill_write.json + mining_skill_bad_branch.json via that
command lane. No golden drives a skills-panel click: the parity harness would
capture the oracle's in-place panel re-render, which sb deliberately diverges
from — so this terminal is covered by these unit tests + the op-leg integration
suite (tests/integration/test_mining_skill_leg.py), NOT a fabricated golden.

Accepted sb divergence from the oracle, mirroring the landed
``skill_respec_route`` sibling (also a skills-panel button): the reply is a
RESULT_CARD `<@u> {message}` text card, not the oracle's in-place ❌/✅ note
re-render, and the invoker mention prefixes BOTH the success and the
business-refusal face (the skill family's ``ctx.send(f"{mention} …")`` posture,
unlike the vault lane which returns refusals bare).

DB-free: the route handler runs over a faked ``_op_after`` seam (the engine.run
txn is the pg-walled seam the command-lane goldens already cover) — the
tests/unit/mining/test_mining_vault_move.py lineage.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.spec.refs import HandlerRef, resolve

run = asyncio.run


def _req(args: dict, *, uid: int = 123):
    return SimpleNamespace(
        actor=SimpleNamespace(user_id=uid, actor_type="user"),
        args=dict(args), guild_id=1, request_id="r-1", confirmed=False,
        origin=None)


def _patch_op_after(monkeypatch, *, result):
    """Capture the (op_key, params) the handler runs and return a canned
    ``(blocked_reply, after)``. Re-runs ``ensure_handler_refs`` first so the
    route is in the ref table even under the pytest-randomly ref-table shuffle
    (the test_band6_mining_grid_panels / test_mining_vault_move precedent)."""
    import sb.domain.mining.service as service

    service.ensure_handler_refs()

    calls: list[tuple[str, dict]] = []

    async def fake_op_after(req, op_key, params=None):
        calls.append((op_key, dict(params or {})))
        return result

    monkeypatch.setattr(service, "_op_after", fake_op_after)
    return calls


@pytest.mark.parametrize("action,branch", [
    ("sk_mining", "mining"),
    ("sk_combat", "combat"),
    ("sk_fortune", "fortune"),
    ("sk_crafting", "crafting"),
])
def test_branch_button_spends_one_point_into_its_branch(
        monkeypatch, action, branch):
    # each ⛏️/⚔️/🍀/🛠️ button rides its ``sk_<branch>`` session_action -> the
    # branch token, and spends exactly ONE point (argv=(branch,), no numeric
    # token -> the op defaults amount to 1, the oracle allocate n=1).
    message = (f"Spent **1** point into **{branch}** (now 1/10). "
               "**1** point left.")
    calls = _patch_op_after(monkeypatch, result=(None, {"message": message}))
    handler = resolve(HandlerRef("mining.skill_spend_route"))
    reply = run(handler(_req({"session_action": action})))
    assert calls == [("mining.skill", {"argv": (branch,), "values": ()})]
    assert reply.outcome is SUCCESS
    assert reply.user_message == f"<@123> {message}"


def test_success_prefixes_the_invoker_mention(monkeypatch):
    message = "Spent **1** point into **mining** (now 3/10). **5** points left."
    _patch_op_after(monkeypatch, result=(None, {"message": message}))
    handler = resolve(HandlerRef("mining.skill_spend_route"))
    reply = run(handler(_req({"session_action": "sk_mining"}, uid=777)))
    assert reply.outcome is SUCCESS
    assert reply.user_message == f"<@777> {message}"


def test_refusal_prefixes_the_mention_verbatim_no_points(monkeypatch):
    # the skill family prefixes the mention on BOTH faces (skill_respec_route /
    # skill_route posture) — unlike the vault lane, the refusal is NOT bare.
    # The refusal copy is the oracle allocate's VERBATIM available-points face.
    from sb.domain.mining.service import Reply

    refusal = Reply(BLOCKED,
                    "You only have **0** skill points to spend — "
                    "level up (play more) to earn more.")
    _patch_op_after(monkeypatch, result=(refusal, {}))
    handler = resolve(HandlerRef("mining.skill_spend_route"))
    reply = run(handler(_req({"session_action": "sk_combat"})))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "<@123> You only have **0** skill points to spend — "
        "level up (play more) to earn more.")


def test_refusal_prefixes_the_mention_verbatim_per_branch_cap(monkeypatch):
    # the oracle allocate's VERBATIM per-branch-cap refusal, surfaced with the
    # mention prefix (the whole txn rolls back — a refused click writes nothing).
    from sb.domain.mining.service import Reply

    refusal = Reply(BLOCKED,
                    "**mining** caps at **10** points "
                    "(you have 10 — room for 0).")
    _patch_op_after(monkeypatch, result=(refusal, {}))
    handler = resolve(HandlerRef("mining.skill_spend_route"))
    reply = run(handler(_req({"session_action": "sk_mining"})))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "<@123> **mining** caps at **10** points (you have 10 — room for 0).")


def test_unexpected_session_action_falls_through_to_the_op(monkeypatch):
    # a non ``sk_`` id is passed through as the (invalid) branch token so the op
    # owns the verbatim bad-branch refusal — the route never guesses a branch.
    calls = _patch_op_after(monkeypatch, result=(None, {"message": "ok"}))
    handler = resolve(HandlerRef("mining.skill_spend_route"))
    run(handler(_req({"session_action": "weird"})))
    assert calls == [("mining.skill", {"argv": ("weird",), "values": ()})]


def test_missing_session_action_passes_a_blank_branch(monkeypatch):
    # defensive: no session_action -> a blank branch token, which the op refuses
    # as the ``(blank)`` bad-branch face; the route stays a thin pass-through.
    calls = _patch_op_after(monkeypatch, result=(None, {"message": "ok"}))
    handler = resolve(HandlerRef("mining.skill_spend_route"))
    run(handler(_req({})))
    assert calls == [("mining.skill", {"argv": ("",), "values": ()})]
