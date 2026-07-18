"""Mining stash/unstash refusals render VERBATIM (slice C6 — the D-0060
two-arg ``ValidatorError`` fix).

Before this slice the vault stash/unstash lane raised the SINGLE-arg
``ValidatorError(sentence)`` — the whole domain sentence rode the ``param``
slot, so the dispatch envelope (``sb.kernel.interaction.errors.from_exception``)
wrapped every refusal in the missing-argument boilerplate
("Missing/invalid argument: `<sentence>`. `!help …` for usage.") instead of
the shipped copy. The fix converts each raise to the D-0060 TWO-arg form
``ValidatorError(param, message)`` so the 2nd arg is the VERBATIM user copy the
render layer speaks bare (matching the oracle ``mining_workflow.vault_deposit``
/ ``vault_withdraw`` / ``vault_deposit_all_resources`` strings).

The bug (and this fix) is SHARED by BOTH the modal/panel path AND the `!stash`
/ `!unstash` command path: both route to the same ``mining.stash`` /
``mining.unstash`` / ``mining.stash_all`` op, and the refusals raise inside the
shared op legs + the shared ``_item_from`` / ``_qty_from`` argv helpers — so one
op-level fix covers every lane. These tests drive the op leg and assert the
rendered envelope carries the exact sentence with NO boilerplate wrapper.

DB-free: the op legs run against a monkeypatched in-memory store (the
test_mining_vault_move.py lineage).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.kernel.interaction.errors import ValidatorError, from_exception
from sb.kernel.interaction.request import Surface, TargetRef
from sb.kernel.workflow.context import WorkflowContext

run = asyncio.run

UID, GID = 42, 1

# a stand-in dispatch target so the render layer takes the WITH-target path
# (the boilerplate wrap it would otherwise apply needs `target.key` for the
# `!help <cmd>` hint — proving the wrap is skipped in favour of the verbatim
# copy, not merely absent because target is None).
_TARGET = TargetRef(key="stash", spec=object())


def _ctx(params: dict | None = None) -> WorkflowContext:
    return WorkflowContext(
        actor=SimpleNamespace(user_id=UID, actor_type="user"),
        guild_id=GID, request_id="req-1", params=dict(params or {}))


def _rendered(err: ValidatorError) -> str:
    """The user-facing message the dispatch envelope would show."""
    return from_exception(err, surface=Surface.PREFIX,
                          target=_TARGET).user_message


def _seed_pack(monkeypatch, inventory: dict) -> None:
    from sb.domain.mining import store

    async def get_mining_inventory(uid, gid, conn=None):
        return dict(inventory)

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(store, "get_mining_inventory", get_mining_inventory)
    monkeypatch.setattr(store, "update_mining_item", _noop)
    monkeypatch.setattr(store, "update_vault_item", _noop)


def _seed_vault(monkeypatch, vault: dict) -> None:
    from sb.domain.mining import store

    async def get_vault(uid, gid, conn=None):
        return dict(vault)

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(store, "get_vault", get_vault)
    monkeypatch.setattr(store, "update_vault_item", _noop)
    monkeypatch.setattr(store, "update_mining_item", _noop)


def _seed_stash_all(monkeypatch, inventory: dict) -> None:
    from sb.domain.mining import store

    async def get_mining_inventory(uid, gid, conn=None):
        return dict(inventory)

    monkeypatch.setattr(store, "get_mining_inventory", get_mining_inventory)


# --- the render layer speaks the verbatim sentence, never the wrap ---------------


NO_WRAP = "Missing/invalid argument"


def test_stash_insufficient_qty_renders_verbatim(monkeypatch):
    from sb.domain.mining.ops import _record_stash

    _seed_pack(monkeypatch, {"iron": 2})
    with pytest.raises(ValidatorError) as err:
        run(_record_stash(None, _ctx({"item": "iron", "qty": 5})))
    assert _rendered(err.value) == "You have only **2× iron** to deposit."
    assert NO_WRAP not in _rendered(err.value)


def test_stash_missing_item_renders_verbatim(monkeypatch):
    from sb.domain.mining.ops import _record_stash

    _seed_pack(monkeypatch, {})
    with pytest.raises(ValidatorError) as err:
        run(_record_stash(None, _ctx({"item": "iron", "qty": 5})))
    assert _rendered(err.value) == "You have no **iron** to deposit."
    assert NO_WRAP not in _rendered(err.value)


def test_unstash_insufficient_qty_renders_verbatim(monkeypatch):
    from sb.domain.mining.ops import _record_unstash

    _seed_vault(monkeypatch, {"iron": 2})
    with pytest.raises(ValidatorError) as err:
        run(_record_unstash(None, _ctx({"item": "iron", "qty": 5})))
    assert _rendered(err.value) == "Your vault holds only **2× iron**."
    assert NO_WRAP not in _rendered(err.value)


def test_unstash_missing_item_renders_verbatim(monkeypatch):
    from sb.domain.mining.ops import _record_unstash

    _seed_vault(monkeypatch, {})
    with pytest.raises(ValidatorError) as err:
        run(_record_unstash(None, _ctx({"item": "iron", "qty": 5})))
    assert _rendered(err.value) == "Your vault holds no **iron**."
    assert NO_WRAP not in _rendered(err.value)


def test_stash_all_no_resources_renders_verbatim(monkeypatch):
    from sb.domain.mining.ops import _record_stash_all

    _seed_stash_all(monkeypatch, {})   # nothing sellable
    with pytest.raises(ValidatorError) as err:
        run(_record_stash_all(None, _ctx()))
    assert _rendered(err.value) == (
        "You have no raw resources to stash — go mine some!")
    assert NO_WRAP not in _rendered(err.value)


# --- the shared argv helpers (_item_from / _qty_from) also render bare -----------


def test_stash_no_item_named_renders_verbatim(monkeypatch):
    # the argv command lane with no item token -> _item_from refuses.
    from sb.domain.mining.ops import _record_stash

    _seed_pack(monkeypatch, {"iron": 5})
    with pytest.raises(ValidatorError) as err:
        run(_record_stash(None, _ctx({"argv": ()})))
    assert _rendered(err.value) == "Name an item."
    assert NO_WRAP not in _rendered(err.value)


def test_stash_bad_qty_renders_verbatim(monkeypatch):
    from sb.domain.mining.ops import _record_stash

    _seed_pack(monkeypatch, {"iron": 5})
    with pytest.raises(ValidatorError) as err:
        # a negative qty trips the guard (qty=0 falls to the default 1 via
        # ``int(qty or default)`` — the argv parse never yields a bare 0).
        run(_record_stash(None, _ctx({"item": "iron", "qty": -1})))
    assert _rendered(err.value) == "Quantity must be positive."
    assert NO_WRAP not in _rendered(err.value)
