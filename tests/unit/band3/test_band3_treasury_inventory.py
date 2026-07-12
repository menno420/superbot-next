"""Band 3 slice 2 (treasury + inventory) — seam-level unit legs."""

from __future__ import annotations

import asyncio
import datetime as dt
from types import SimpleNamespace

import pytest


def _clock(epoch: int):
    return lambda: dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc)


def _ctx(params: dict, *, uid: int = 42, gid: int = 1, epoch: int = 1_000_000):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=False, params=params, clock=_clock(epoch))


class FakeMoney:
    """User coins + pool balance + the ledger, monkeypatched over both
    sole-writer store modules."""

    def __init__(self, coins: int = 0, pool: int = 0):
        self.coins = {42: coins}
        self.pool = pool
        self.pool_updated = 0
        self.audit: list[tuple] = []

    def install(self, monkeypatch):
        from sb.domain.economy import store as econ
        from sb.domain.treasury import store as treas

        async def try_debit_coins(conn, *, user_id, guild_id, amount):
            if self.coins.get(user_id, 0) < amount:
                return None
            self.coins[user_id] -= amount
            return self.coins[user_id]

        async def credit_coins(conn, *, user_id, guild_id, amount):
            self.coins[user_id] = max(0, self.coins.get(user_id, 0) + amount)
            return self.coins[user_id]

        async def get_coins(user_id, guild_id, conn=None):
            return self.coins.get(user_id, 0)

        async def insert_economy_audit(conn, *, guild_id, user_id, actor_id,
                                       delta, new_balance, reason):
            self.audit.append((user_id, actor_id, delta, reason))
            return f"m{len(self.audit)}"

        async def credit_treasury(conn, *, guild_id, amount, updated_at):
            self.pool = max(0, self.pool + amount)
            self.pool_updated = updated_at
            return self.pool

        async def try_debit_treasury(conn, *, guild_id, amount, updated_at):
            if self.pool < amount:
                return None
            self.pool -= amount
            self.pool_updated = updated_at
            return self.pool

        async def get_treasury(guild_id, conn=None):
            return self.pool

        monkeypatch.setattr(econ, "try_debit_coins", try_debit_coins)
        monkeypatch.setattr(econ, "credit_coins", credit_coins)
        monkeypatch.setattr(econ, "get_coins", get_coins)
        monkeypatch.setattr(econ, "insert_economy_audit", insert_economy_audit)
        monkeypatch.setattr(treas, "credit_treasury", credit_treasury)
        monkeypatch.setattr(treas, "try_debit_treasury", try_debit_treasury)
        monkeypatch.setattr(treas, "get_treasury", get_treasury)
        return self


# --- contribute ---------------------------------------------------------------------

def test_contribute_debits_user_credits_pool_one_ledger_row(monkeypatch):
    from sb.domain.treasury import ops

    fake = FakeMoney(coins=500, pool=100).install(monkeypatch)
    ctx = _ctx({"argv": ("250",)})
    out = asyncio.run(ops._record_contribute(None, ctx))
    assert out.after == {"treasury": 350, "user": 250, "amount": 250}
    assert fake.audit == [(42, 42, -250, "treasury:contribute")]
    assert fake.pool_updated == 1_000_000
    assert ctx.params["_reason"] == "treasury:contribute"


def test_contribute_insufficient_rolls_back(monkeypatch):
    from sb.domain.economy.service import InsufficientFundsError
    from sb.domain.treasury import ops

    fake = FakeMoney(coins=10, pool=0).install(monkeypatch)
    with pytest.raises(InsufficientFundsError):
        asyncio.run(ops._record_contribute(None, _ctx({"amount": 999})))
    assert fake.pool == 0 and not fake.audit


def test_contribute_rejects_nonpositive(monkeypatch):
    from sb.domain.treasury import ops
    from sb.kernel.interaction.errors import ValidatorError

    FakeMoney(coins=100).install(monkeypatch)
    with pytest.raises(ValidatorError):
        asyncio.run(ops._record_contribute(None, _ctx({"amount": 0})))
    with pytest.raises(ValidatorError):
        asyncio.run(ops._record_contribute(None, _ctx({"argv": ()})))


# --- disburse -----------------------------------------------------------------------

def test_disburse_underfunded_never_overdraws(monkeypatch):
    from sb.domain.treasury import ops
    from sb.kernel.interaction.errors import ValidatorError

    fake = FakeMoney(coins=0, pool=50).install(monkeypatch)
    with pytest.raises(ValidatorError):
        asyncio.run(ops._record_disburse(
            None, _ctx({"target_id": 900000000000000103, "amount": 500})))
    assert fake.pool == 50 and not fake.audit


def test_disburse_credits_target_with_manager_attribution(monkeypatch):
    from sb.domain.treasury import ops

    fake = FakeMoney(coins=0, pool=1000).install(monkeypatch)
    ctx = _ctx({"argv": ("<@900000000000000103>", "400")})
    out = asyncio.run(ops._record_disburse(None, ctx))
    assert out.after == {"treasury": 600, "user": 400, "amount": 400}
    # target's ledger row carries the MANAGER as actor (shipped verbatim)
    assert fake.audit == [(900000000000000103, 42, 400, "treasury:disburse")]


def test_disburse_argv_parse_is_positional(monkeypatch):
    """`!treasury grant <member> <amount>` — argv[0] is the member slot,
    argv[1] the amount (the shipped MemberConverter/int positional
    binding: treasury_cog.py `grant(ctx, member, amount)`)."""
    from sb.domain.treasury import ops

    snowflake = 900000000000000103

    # bare ID + amount (the golden-unpinned defect lane)
    fake = FakeMoney(coins=0, pool=1000).install(monkeypatch)
    out = asyncio.run(ops._record_disburse(
        None, _ctx({"argv": (str(snowflake), "400")})))
    assert out.after == {"treasury": 600, "user": 400, "amount": 400}
    assert fake.audit == [(snowflake, 42, 400, "treasury:disburse")]

    # nickname-mention form <@!id>
    fake2 = FakeMoney(coins=0, pool=1000).install(monkeypatch)
    out2 = asyncio.run(ops._record_disburse(
        None, _ctx({"argv": (f"<@!{snowflake}>", "250")})))
    assert out2.after["amount"] == 250
    assert fake2.audit == [(snowflake, 42, 250, "treasury:disburse")]


def test_disburse_bare_id_never_becomes_the_amount(monkeypatch):
    """REGRESSION: the first-digit-token scan bound the snowflake ITSELF
    as the amount on `!treasury grant <bare_id> <amt>` — the pool-balance
    check then refused ~9e17 coins (loud, but the wrong parse)."""
    from sb.domain.treasury import ops

    snowflake = 900000000000000103
    fake = FakeMoney(coins=0, pool=1000).install(monkeypatch)
    out = asyncio.run(ops._record_disburse(
        None, _ctx({"argv": (str(snowflake), "5")})))
    assert out.after["amount"] == 5            # not 900000000000000103
    assert fake.pool == 995
    assert fake.audit == [(snowflake, 42, 5, "treasury:disburse")]


def test_disburse_argv_failure_copy(monkeypatch):
    from sb.domain.treasury import ops
    from sb.kernel.interaction.errors import ValidatorError

    fake = FakeMoney(coins=0, pool=1000).install(monkeypatch)

    # unknown-member name leg: the shipped MemberConverter raised
    # MemberNotFound and bot1.py's global BadArgument arm sent this copy
    # (treasury_cog has no local error handler).
    with pytest.raises(ValidatorError) as exc:
        asyncio.run(ops._record_disburse(
            None, _ctx({"argv": ("somename", "5")})))
    assert exc.value.user_copy == '⚠️ Bad argument: Member "somename" not found.'

    # member-only (one arg): no amount slot at argv[1] — the amount copy,
    # and the lone snowflake must NOT be double-read as the amount
    with pytest.raises(ValidatorError) as exc2:
        asyncio.run(ops._record_disburse(
            None, _ctx({"argv": ("<@900000000000000103>",)})))
    assert exc2.value.user_copy == "➕ Give a number of coins."
    assert fake.pool == 1000 and not fake.audit


# --- op registration ------------------------------------------------------------------

def test_treasury_ops_registered_with_shipped_authority():
    from sb.domain.treasury.ops import register_ops
    from sb.kernel.workflow.registry import REGISTRY
    from sb.kernel.workflow.spec import IdempotencyPosture
    from sb.spec.refs import WorkflowRef

    register_ops()
    contribute = REGISTRY.resolve(WorkflowRef("treasury.contribute"))
    disburse = REGISTRY.resolve(WorkflowRef("treasury.disburse"))
    assert contribute.authority_ref == "user"
    assert disburse.authority_ref == "staff"      # manage_guild tier, verbatim
    for spec in (contribute, disburse):
        assert spec.idempotency is IdempotencyPosture.NATURAL_KEY
        assert spec.emits and spec.emits[0].event == "economy.balance_changed"


# --- rollback disposition / invariant --------------------------------------------------

def test_treasury_store_reverse_importable_and_covered():
    import sb.manifest.treasury  # noqa: F401 — registers store + importer
    from sb.domain.treasury.store import GUILD_TREASURY_STORE
    from sb.spec.versioning import RollbackClass, derive_rollback_class
    from tools.importer.reverse import reverse_importer_coverage

    assert derive_rollback_class(GUILD_TREASURY_STORE) is RollbackClass.REVERSE_IMPORTABLE
    assert "guild_treasury" in reverse_importer_coverage()


def test_pool_reconciliation_flags_drift(monkeypatch):
    from sb.domain.treasury import invariants as inv
    from sb.kernel.db import pool as pool_mod
    from sb.spec.refs import resolve

    spec = inv.declare_treasury_invariants()
    assert spec.severity.value == "quarantine_only"

    async def fake_fetchone(sql, params=(), conn=None):
        return {"balance": 900, "ledger_sum": 700}

    monkeypatch.setattr(pool_mod, "fetchone", fake_fetchone)
    check = resolve(spec.check_ref)
    violations = asyncio.run(check(spec, guild_id=1))
    assert len(violations) == 1 and "drift +200" in violations[0].detail

    async def fake_clean(sql, params=(), conn=None):
        return {"balance": 700, "ledger_sum": 700}

    monkeypatch.setattr(pool_mod, "fetchone", fake_clean)
    assert asyncio.run(check(spec, guild_id=1)) == ()


# --- inventory ---------------------------------------------------------------------------

def test_combined_inventory_merges_sources_lowercased(monkeypatch):
    from sb.domain.economy import store as econ
    from sb.domain.inventory import service

    service.reset_inventory_ports_for_tests()

    async def fake_inv(user_id, guild_id, conn=None):
        return {"car": 1, "toolkit": 1}

    async def mining_source(user_id, guild_id):
        return {"Stone": 5, "car": 1}      # shipped fold: lowercase + sum

    monkeypatch.setattr(econ, "get_inventory", fake_inv)
    service.install_extra_inventory_source(mining_source)
    grouped = asyncio.run(service.build_combined_inventory(42, 1))
    service.reset_inventory_ports_for_tests()

    assert [i for i, _, _ in grouped["Mining Materials"]] == ["stone"]
    econ_items = {i: q for i, q, _ in grouped["Economy Items"]}
    assert econ_items == {"car": 2}
    assert {i for i, _, _ in grouped["Tools"]} == {"toolkit"}


def test_inventory_pure_helpers_are_shipped_orders():
    from sb.domain.inventory.service import group_by_rarity, sort_items

    items = [("car", 1, {"rarity": "Rare"}),
             ("stone", 9, {"rarity": "Common"}),
             ("diamond", 2, {"rarity": "Epic"}),
             ("weird", 1, {})]
    by_rarity = sort_items(items, "rarity")
    assert [i for i, _, _ in by_rarity] == ["diamond", "car", "stone", "weird"]
    by_qty = sort_items(items, "quantity")
    assert [i for i, _, _ in by_qty][:2] == ["stone", "diamond"]
    tiers = group_by_rarity(items)
    assert [t for t, _ in tiers] == ["Epic", "Rare", "Common", "Unknown"]


def test_inventory_row_carries_the_declared_browse_algebra():
    # the row the detail provider emits must carry EXACTLY the sort/filter
    # keys the ListSpec declares — name (key), quantity (int), rarity (the
    # RARITY_ORDER RANK so ascending is rarest-first), type (filter), plus the
    # pre-rendered display line the item_render_ref emits.
    from sb.domain.economy.catalogue import RARITY_ORDER
    from sb.domain.inventory.service import inventory_row

    row = inventory_row("diamond_axe", 4, {"rarity": "Epic", "type": "Tool",
                                           "emoji": "🪓"})
    assert row["name"] == "diamond_axe"
    assert row["quantity"] == 4
    assert row["rarity"] == RARITY_ORDER["Epic"]      # rank, not the string
    assert row["type"] == "Tool"
    assert row["_line"].endswith("`Epic`")            # rarity tag appended
    assert "Diamond Axe" in row["_line"] and "× 4" in row["_line"]
    # an unknown rarity ranks last (99), never a crash.
    assert inventory_row("mystery", 1, {})["rarity"] == 99


def test_detail_provider_emits_browse_rows_sorted_by_key(monkeypatch):
    # the converted detail provider yields ROWS (not pre-rendered strings),
    # pre-sorted by item key so the engine's stable sort breaks ties alpha.
    import sb.domain.economy.store as econ
    from sb.domain.inventory import panels, service

    service.reset_inventory_ports_for_tests()

    async def fake_inv(user_id, guild_id, conn=None):
        return {"axe": 1, "iron pickaxe": 3, "toolkit": 5}

    monkeypatch.setattr(econ, "get_inventory", fake_inv)
    provider = panels._ensure_detail_provider("Tools")
    from sb.spec.refs import resolve as resolve_ref

    rows = asyncio.run(resolve_ref(provider)(SimpleNamespace(guild_id=1, actor=SimpleNamespace(user_id=42))))
    service.reset_inventory_ports_for_tests()
    assert all(isinstance(r, dict) and "_line" in r for r in rows)
    # pre-sorted alpha by key (the tie-break the engine's stable sort inherits)
    assert [r["name"] for r in rows] == ["axe", "iron pickaxe", "toolkit"]


def test_manifests_validate():
    import sb.manifest.inventory as m_inv
    import sb.manifest.treasury as m_tre

    inv_cmd = m_inv.MANIFEST.commands[0]
    assert inv_cmd.name == "inventory" and inv_cmd.aliases == ("inv",)

    by_name = {c.name: c for c in m_tre.MANIFEST.commands}
    assert set(by_name) == {"treasury", "contribute", "grant"}
    assert by_name["treasury"].aliases == ("bank", "pool")
    assert by_name["contribute"].aliases == ("donate", "deposit")
    assert by_name["grant"].aliases == ("disburse", "payout")
    assert by_name["contribute"].qualified_name == "treasury contribute"
    assert by_name["grant"].audience_tier == "staff"
    assert {s.table for s in m_tre.MANIFEST.stores} == {"guild_treasury"}


# --- treasury.hub panel: golden-pinned bytes (parity/goldens/treasury/
# sweep_treasury.json) -------------------------------------------------------------


def test_treasury_hub_spec_shape_matches_the_golden():
    from sb.domain.treasury.panels import treasury_hub_spec
    from sb.kernel.panels.compile import check_panel
    from sb.spec.panels import ActionStyle, Audience, FooterMode

    spec = treasury_hub_spec()
    check_panel(spec)                              # the compile fences hold
    assert spec.panel_id == "treasury.hub"
    assert spec.title == "🏛️ Server Treasury"
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "gold"         # the shipped ECONOMY_COLOR
    assert spec.frame.footer_mode is FooterMode.NONE
    # run-minted ids, no nav row, no panel_anchors row (the shipped
    # ctx-bound TreasuryView carried only its own two buttons).
    assert spec.session_lifecycle is True
    assert spec.navigation.show_help is False
    assert spec.navigation.show_home is False

    by_id = {a.action_id: a for a in spec.actions}
    assert set(by_id) == {"contribute", "refresh"}
    assert (by_id["contribute"].label, by_id["contribute"].emoji,
            by_id["contribute"].style) == ("Contribute", "➕",
                                           ActionStyle.SUCCESS)
    assert (by_id["refresh"].label, by_id["refresh"].emoji) == (
        "Refresh", "🔄")
    assert by_id["contribute"].custom_id_override == ""
    assert by_id["refresh"].custom_id_override == ""
    assert spec.layout.pages[0].rows == (("contribute", "refresh"),)


def test_treasury_hub_renders_the_golden_bytes(monkeypatch):
    """The renderer_override's two adjustments (see justification): the
    footer literal and both fields rendered inline — an empty pool/wallet
    matches sweep_treasury.json's captured (0, 0) state byte-for-byte."""
    from sb.domain.treasury.panels import treasury_hub_spec
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience
    from sb.spec.refs import resolve as resolve_ref

    FakeMoney(coins=0, pool=0).install(monkeypatch)

    spec = treasury_hub_spec()
    ctx = PanelContext(
        bot=None, guild_id=1, actor=SimpleNamespace(user_id=42), channel_id=2,
        origin=PanelOrigin.INTERACTION, audience=Audience.INVOKER)
    rendered = asyncio.run(resolve_ref(spec.renderer_override)(spec, ctx))

    assert rendered.embed.footer == "➕ Contribute · 🔄 Refresh"
    fields = rendered.embed.fields
    assert fields[0][:2] == ("Treasury", "🏛️ **0** 🪙 in the pool")
    assert fields[0][2] is True                     # inline (the shipped shape)
    assert fields[1][:2] == ("Your wallet", "🪙 **0** 🪙")
    assert fields[1][2] is True                     # inline (the shipped shape)
    assert len(fields) == 2                         # no "Disburse" field

    labels = [c.label for c in rendered.components]
    assert labels == ["Contribute", "Refresh"]
    assert all(c.row == 0 for c in rendered.components)   # ONE row, no nav
