"""Mining 🏦 Vault deposit/withdraw write faces (backlog B1) — the shipped
📥 Deposit / 📤 Withdraw modal buttons made a live G-10 modal that runs the
audited move op.

ORACLE (menno420/superbot): disbot/views/mining/vault_panel.py
(``_VaultMoveModal.on_submit`` -> ``mining_workflow.vault_deposit`` /
``vault_withdraw``) + disbot/services/mining_workflow.py
(``vault_deposit`` / ``vault_withdraw`` — the atomic pack<->vault move and the
response strings, VERBATIM).

The modal buttons run the SAME audited op the LIVE `!stash` / `!unstash`
command lane carries (``mining.stash`` / ``mining.unstash`` ->
``record_stash`` / ``record_unstash``), already byte-pinned by
goldens/mining/mining_stash_write.json + mining_unstash_write.json via that
command lane. No golden drives a vault-panel click and the parity harness
cannot drive a modal submit, and the MODAL-defer button renders identical
session ``<cid:N>`` wire bytes (sweep_vault stays byte-clean) — so this
terminal is covered by these unit tests, NOT a golden (no fabricated parity).

Accepted sb divergences from the oracle, each mirroring a landed sibling:
* the reply is a RESULT_CARD `<@u> {message}` text card, not the oracle
  modal's in-place panel re-render (the ``stash_all_route`` /
  ``vaultupgrade_route`` posture);
* the item is taken VERBATIM (lowercased in-leg), no fuzzy resolver — the same
  posture ``stash_route`` / ``unstash_route`` already ship (sb carries no
  vault-item ``resolve_item_name``).

DB-free: the op legs run against a monkeypatched in-memory store (the
tests/unit/mining/test_title_equip.py lineage); the modal handlers run over a
faked ``_op_after`` seam.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.kernel.interaction.errors import ValidatorError
from sb.kernel.workflow.context import WorkflowContext
from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.spec.refs import HandlerRef, resolve

run = asyncio.run

UID, GID = 42, 1


def _ctx(params: dict | None = None) -> WorkflowContext:
    return WorkflowContext(
        actor=SimpleNamespace(user_id=UID, actor_type="user"),
        guild_id=GID, request_id="req-1", params=dict(params or {}))


# --- the deposit / withdraw op legs: mining_workflow copy VERBATIM ---------------


def _seed_pack(monkeypatch, inventory: dict) -> list[tuple[str, str, int]]:
    """Fake the pack read + record both move legs (pack debit / vault credit)."""
    from sb.domain.mining import store

    moves: list[tuple[str, str, int]] = []

    async def get_mining_inventory(uid, gid, conn=None):
        return dict(inventory)

    async def update_mining_item(conn, *, user_id, guild_id, item, delta):
        moves.append(("pack", item, delta))

    async def update_vault_item(conn, *, user_id, guild_id, item, delta):
        moves.append(("vault", item, delta))

    monkeypatch.setattr(store, "get_mining_inventory", get_mining_inventory)
    monkeypatch.setattr(store, "update_mining_item", update_mining_item)
    monkeypatch.setattr(store, "update_vault_item", update_vault_item)
    return moves


def _seed_vault(monkeypatch, vault: dict) -> list[tuple[str, str, int]]:
    """Fake the vault read + record both move legs (vault debit / pack credit)."""
    from sb.domain.mining import store

    moves: list[tuple[str, str, int]] = []

    async def get_vault(uid, gid, conn=None):
        return dict(vault)

    async def update_vault_item(conn, *, user_id, guild_id, item, delta):
        moves.append(("vault", item, delta))

    async def update_mining_item(conn, *, user_id, guild_id, item, delta):
        moves.append(("pack", item, delta))

    monkeypatch.setattr(store, "get_vault", get_vault)
    monkeypatch.setattr(store, "update_vault_item", update_vault_item)
    monkeypatch.setattr(store, "update_mining_item", update_mining_item)
    return moves


def test_deposit_leg_moves_pack_to_vault_and_replies_verbatim(monkeypatch):
    from sb.domain.mining.ops import _record_stash

    moves = _seed_pack(monkeypatch, {"diamond": 10})
    out = run(_record_stash(None, _ctx({"item": "diamond", "qty": 5})))
    assert out.after["message"] == (
        "Deposited **5× diamond** into your vault — safe and out of your pack.")
    # both legs commit: pack debited, vault credited (the one-txn contract).
    assert ("pack", "diamond", -5) in moves
    assert ("vault", "diamond", 5) in moves


def test_deposit_leg_lowercases_the_item_like_the_oracle(monkeypatch):
    # oracle vault_deposit: item = item.strip().lower()
    from sb.domain.mining.ops import _record_stash

    moves = _seed_pack(monkeypatch, {"diamond": 10})
    out = run(_record_stash(None, _ctx({"item": "  DIAMOND ", "qty": 2})))
    assert out.after["message"] == (
        "Deposited **2× diamond** into your vault — safe and out of your pack.")
    assert ("pack", "diamond", -2) in moves


# NOTE (pre-existing, flagged as follow-up — NOT in B1 scope): the shipped
# stash/unstash ops raise the SINGLE-arg ValidatorError, so the domain refusal
# rides ``.param`` (not ``.user_copy``) and currently renders wrapped in the
# missing-argument boilerplate rather than verbatim (the D-0060 two-arg form is
# the fix). This is a latent bug in the already-landed ops SHARED with the
# `!stash` / `!unstash` command lane (unpinned by any golden); the modal reuses
# the same op, so its refusal matches the command lane exactly. These tests pin
# that the refusal branch is reached with the intended verbatim copy and writes
# nothing — the render-wrap fix is deferred so B1 stays a pure modal-wiring slice.
def test_deposit_leg_refuses_when_pack_holds_too_few(monkeypatch):
    from sb.domain.mining.ops import _record_stash

    moves = _seed_pack(monkeypatch, {"diamond": 2})
    with pytest.raises(ValidatorError) as err:
        run(_record_stash(None, _ctx({"item": "diamond", "qty": 5})))
    assert err.value.param == "You have only **2× diamond** to deposit."
    assert moves == []                              # the txn wrote nothing


def test_deposit_leg_refuses_when_pack_has_none(monkeypatch):
    from sb.domain.mining.ops import _record_stash

    moves = _seed_pack(monkeypatch, {})
    with pytest.raises(ValidatorError) as err:
        run(_record_stash(None, _ctx({"item": "diamond", "qty": 5})))
    assert err.value.param == "You have no **diamond** to deposit."
    assert moves == []


def test_withdraw_leg_moves_vault_to_pack_and_replies_verbatim(monkeypatch):
    from sb.domain.mining.ops import _record_unstash

    moves = _seed_vault(monkeypatch, {"diamond": 10})
    out = run(_record_unstash(None, _ctx({"item": "diamond", "qty": 5})))
    assert out.after["message"] == (
        "Withdrew **5× diamond** from your vault back into your pack.")
    assert ("vault", "diamond", -5) in moves
    assert ("pack", "diamond", 5) in moves


def test_withdraw_leg_refuses_when_vault_holds_too_few(monkeypatch):
    from sb.domain.mining.ops import _record_unstash

    moves = _seed_vault(monkeypatch, {"diamond": 2})
    with pytest.raises(ValidatorError) as err:
        run(_record_unstash(None, _ctx({"item": "diamond", "qty": 5})))
    assert err.value.param == "Your vault holds only **2× diamond**."
    assert moves == []


def test_withdraw_leg_refuses_when_vault_has_none(monkeypatch):
    from sb.domain.mining.ops import _record_unstash

    moves = _seed_vault(monkeypatch, {})
    with pytest.raises(ValidatorError) as err:
        run(_record_unstash(None, _ctx({"item": "diamond", "qty": 5})))
    assert err.value.param == "Your vault holds no **diamond**."
    assert moves == []


# --- the modal submit handlers: parse / route / RESULT_CARD format ---------------


def _req(args: dict, *, uid: int = 123):
    return SimpleNamespace(
        actor=SimpleNamespace(user_id=uid, actor_type="user"),
        args=dict(args), guild_id=1, request_id="r-1", confirmed=False,
        origin=None)


def _patch_op_after(monkeypatch, *, result):
    """Capture the (op_key, params) the handler runs and return a canned
    ``(blocked_reply, after)`` — the engine.run txn is the pg-walled seam the
    command-lane goldens already cover."""
    import sb.domain.mining.service as service

    # Guarantee the mining route handlers are in the ref table before we
    # resolve them: another suite (the interaction/panel tests) calls
    # ``clear_ref_table()``, and service.py's import-time ``_register()`` will
    # NOT re-run on the already-cached module — so relying on ambient
    # registration is order-fragile (pytest-randomly). Re-run the canonical
    # ``ensure_handler_refs`` (idempotent), the test_band6_mining_grid_panels
    # precedent for a mining unit test that resolves a handler by name.
    service.ensure_handler_refs()

    calls: list[tuple[str, dict]] = []

    async def fake_op_after(req, op_key, params=None):
        calls.append((op_key, dict(params or {})))
        return result

    monkeypatch.setattr(service, "_op_after", fake_op_after)
    return calls


def test_deposit_handler_routes_to_stash_and_prefixes_mention(monkeypatch):
    calls = _patch_op_after(monkeypatch, result=(None, {
        "message": "Deposited **5× diamond** into your vault — "
                   "safe and out of your pack."}))
    handler = resolve(HandlerRef("mining.vault_deposit_route"))
    reply = run(handler(_req({"item": "diamond", "qty": "5"})))
    assert calls == [("mining.stash", {"item": "diamond", "qty": 5})]
    assert reply.outcome is SUCCESS
    assert reply.user_message == (
        "<@123> Deposited **5× diamond** into your vault — "
        "safe and out of your pack.")


def test_withdraw_handler_routes_to_unstash_and_prefixes_mention(monkeypatch):
    calls = _patch_op_after(monkeypatch, result=(None, {
        "message": "Withdrew **5× diamond** from your vault back "
                   "into your pack."}))
    handler = resolve(HandlerRef("mining.vault_withdraw_route"))
    reply = run(handler(_req({"item": "diamond", "qty": "5"})))
    assert calls == [("mining.unstash", {"item": "diamond", "qty": 5})]
    assert reply.outcome is SUCCESS
    assert reply.user_message == (
        "<@123> Withdrew **5× diamond** from your vault back into your pack.")


def test_deposit_handler_blank_qty_defaults_to_one(monkeypatch):
    # the Amount field is optional (default "1"); a missing value -> 1.
    calls = _patch_op_after(monkeypatch, result=(None, {"message": "ok"}))
    handler = resolve(HandlerRef("mining.vault_deposit_route"))
    run(handler(_req({"item": "iron"})))
    assert calls == [("mining.stash", {"item": "iron", "qty": 1})]


def test_deposit_handler_non_numeric_qty_defaults_to_one(monkeypatch):
    # sb posture: a non-digit Amount falls to 1 (the `!stash` argv parse
    # ignores non-digit tokens) — never the oracle modal's "isn't a number".
    calls = _patch_op_after(monkeypatch, result=(None, {"message": "ok"}))
    handler = resolve(HandlerRef("mining.vault_deposit_route"))
    run(handler(_req({"item": "iron", "qty": "lots"})))
    assert calls == [("mining.stash", {"item": "iron", "qty": 1})]


def test_deposit_handler_passes_refusal_through_without_mention(monkeypatch):
    # the landed sibling posture (stash_all_route / vaultupgrade_route): a
    # business refusal returns bare, only the success face prefixes the mention.
    from sb.domain.mining.service import Reply

    refusal = Reply(BLOCKED, "You have only **2× diamond** to deposit.")
    _patch_op_after(monkeypatch, result=(refusal, {}))
    handler = resolve(HandlerRef("mining.vault_deposit_route"))
    reply = run(handler(_req({"item": "diamond", "qty": "5"})))
    assert reply is refusal


@pytest.mark.parametrize("raw,expected", [
    ("5", 5), ("", 1), ("abc", 1), ("  3 ", 3), (None, 1), ("10", 10)])
def test_modal_qty_parse(raw, expected):
    from sb.domain.mining.service import _modal_qty

    assert _modal_qty(raw) == expected
