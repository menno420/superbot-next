"""Band 4 (XP) — DEPTH slice: the access-projection permission gates, the
rank_view refusal + arg-walk surface, the givexp/resetxp handler copy, the
level-curve boundary sweep, the remaining migrate formats, and the
channel/avatar/fan-out/INV-G seams.

Additive characterization only — NO product behavior changes; DB-free
(``FakeXpStore`` + monkeypatch, and ``sb.kernel.db.pool`` monkeypatched for
the INV-G legs). The store.py SQL (add_xp/set_imported_xp/top ordering/erase)
stays a DB-backed follow-up (deviation ledgered) — not attempted here.
"""

from __future__ import annotations

import asyncio
import dataclasses as _dc
import datetime as dt
from types import SimpleNamespace

import pytest

run = asyncio.run


@pytest.fixture(autouse=True)
def _clean_state():
    from sb.domain.economy.service import reset_economy_ports_for_tests
    from sb.domain.xp.service import reset_xp_ports_for_tests
    from sb.kernel import settings as ksettings

    ksettings.clear_for_tests()
    reset_economy_ports_for_tests()
    reset_xp_ports_for_tests()
    yield
    ksettings.clear_for_tests()
    reset_economy_ports_for_tests()
    reset_xp_ports_for_tests()


def _clock(epoch: int):
    return lambda: dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc)


def _ctx(params: dict, *, uid: int = 42, gid: int = 1, epoch: int = 1_000_000):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params, clock=_clock(epoch))


class FakeXpStore:
    """The band4_xp harness twin — DB-free store seam over an in-memory
    ``(user, guild) -> row`` dict (see tests/unit/band4/test_band4_xp.py)."""

    def __init__(self, rows: dict | None = None):
        self.rows = dict(rows or {})

    def install(self, monkeypatch):
        from sb.domain.xp.levels import level_progress

        async def get_xp(user_id, guild_id, conn=None):
            row = self.rows.get((user_id, guild_id))
            if row is None:
                return {"user_id": user_id, "guild_id": guild_id, "xp": 0,
                        "level": 0, "messages": 0, "last_xp": 0}
            return dict(row, user_id=user_id, guild_id=guild_id)

        async def add_xp(conn, *, user_id, guild_id, amount, now):
            row = self.rows.setdefault((user_id, guild_id),
                                       {"xp": 0, "level": 0, "messages": 0,
                                        "last_xp": 0})
            row["xp"] += amount
            row["messages"] += 1
            row["last_xp"] = now
            new_level, _, _ = level_progress(row["xp"])
            leveled = new_level > row["level"]
            if leveled:
                row["level"] = new_level
            return row["xp"], row["level"], leveled

        async def set_imported_xp(conn, *, user_id, guild_id, xp, level, now):
            row = self.rows.get((user_id, guild_id))
            if row is None or xp > row["xp"]:
                old = row["xp"] if row else -1
                self.rows[(user_id, guild_id)] = {
                    "xp": max(xp, row["xp"] if row else 0), "level": level,
                    "messages": row["messages"] if row else 0,
                    "last_xp": row["last_xp"] if row else now}
                return xp, level, xp > old
            return row["xp"], row["level"], False

        async def delete_xp(conn, *, user_id, guild_id):
            return 1 if self.rows.pop((user_id, guild_id), None) else 0

        from sb.domain.xp import store as store_mod

        for name, fn in list(locals().items()):
            if callable(fn) and hasattr(store_mod, name):
                monkeypatch.setattr(store_mod, name, fn)
        return self


@_dc.dataclass
class _FakeReq:
    """ResolveRequest twin — carries only the fields the read/command
    handlers touch (they ``dataclasses.replace`` it, so it must be a
    dataclass)."""

    actor: object
    guild_id: int
    channel_id: int
    args: dict
    request_id: str = "r-xpdepth"
    confirmed: bool = True


def _req(args: dict, *, uid: int = 42, gid: int = 1, channel: int = 555):
    return _FakeReq(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        channel_id=channel, args=args)


def _patch_engine(monkeypatch, *, outcome, user_message="", after=None):
    """Intercept the K7 engine with a recorder returning a forced result —
    the givexp/resetxp wrappers import the module and call ``engine.run``."""
    from sb.kernel.workflow import engine

    seen = []

    async def fake_run(ref, ctx):
        seen.append((ref.name, dict(ctx.params)))
        return SimpleNamespace(outcome=outcome, user_message=user_message,
                               after=after or {})

    monkeypatch.setattr(engine, "run", fake_run)
    return seen


# --- P1: access-projection / permission gates (pure spec reads) ----------------------

def test_hub_tier_gates():
    """`rank` is a user-tier action; config/givexp/resetxp sit on the ADMIN
    floor (``audience_tier == ""``) — the shipped `_XpHubView` gating."""
    from sb.domain.xp.panels import xp_hub_spec

    actions = {a.action_id: a for a in xp_hub_spec().actions}
    assert actions["rank"].audience_tier == "user"
    for aid in ("config", "givexp", "resetxp"):
        assert actions[aid].audience_tier == "", aid


def test_resetxp_confirm_fence():
    """The hub `resetxp` action carries the irreversible typed-phrase confirm
    fence (the resolver's own confirm gate; ops.py re-homed the op-level
    confirm onto this PanelActionSpec)."""
    from sb.domain.xp.panels import xp_hub_spec
    from sb.spec.confirmation import Challenge

    reset = {a.action_id: a for a in xp_hub_spec().actions}["resetxp"]
    assert reset.destructive is True
    assert reset.confirm is not None
    assert reset.confirm.reversibility == "irreversible"
    assert reset.confirm.challenge is Challenge.TYPED_PHRASE


def test_config_panel_tier_gates():
    """All four xp.config buttons are ADMIN-floor (``audience_tier == ""``)."""
    from sb.domain.xp.panels import xp_config_spec

    actions = xp_config_spec().actions
    assert len(actions) == 4
    for a in actions:
        assert a.audience_tier == "", a.action_id


def test_hub_overview_projection(monkeypatch):
    """The hub_overview provider projects the "Your rank"/"Messages" fields
    ONLY for a real actor; user_id=0 gets the actor-independent fields alone
    (panels.py hub_overview)."""
    from sb.domain.xp import panels, service
    from sb.spec.refs import resolve

    FakeXpStore({(7, 1): {"xp": 100, "level": 1, "messages": 12,
                          "last_xp": 0}}).install(monkeypatch)

    async def _no_channel(guild_id):
        return None

    monkeypatch.setattr(service, "bound_announce_channel", _no_channel)
    fn = resolve(panels._ensure_hub_provider())

    anon = run(fn(SimpleNamespace(guild_id=1,
                                  actor=SimpleNamespace(user_id=0))))
    labels_anon = [label for label, _ in anon]
    assert "Your rank" not in labels_anon and "Messages" not in labels_anon
    assert "Chat awards" in labels_anon        # actor-independent fields stay

    real = dict(run(fn(SimpleNamespace(
        guild_id=1, actor=SimpleNamespace(user_id=7)))))
    assert "Your rank" in real and "Messages" in real
    assert real["Messages"] == "12"
    assert "Level **1**" in real["Your rank"] and "100 XP" in real["Your rank"]


# --- P1: refusal paths on the read handler (rank_view) -------------------------------

def test_rank_view_blocked_on_name():
    """A non-mention, non-category, non-digit token escalates to the shipped
    MemberConverter name leg — a gateway read this world lacks — so the walk
    returns the bot1.py generic fallback (handlers.py ~:74)."""
    from sb.domain.xp import handlers
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    handlers.ensure_handler_refs()
    fn = resolve(HandlerRef("xp.rank_view"))
    reply = run(fn(_req({"argv": ("somename",)})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == handlers._GENERIC_ERROR


def test_rank_view_stat_and_member_arg_walk(monkeypatch):
    """xp/coins/both set the stat; ``<@id>`` sets the member. With no
    category, the walk opens the rank IMAGE card panel — patched here so the
    rank_stat/rank_target projection is observable without the panel engine."""
    from sb.domain.xp import handlers
    from sb.kernel.panels import engine
    from sb.spec.refs import HandlerRef, resolve

    captured = []

    async def fake_open_panel(ref, req):
        captured.append((ref, req))
        return "key"

    monkeypatch.setattr(engine, "open_panel", fake_open_panel)
    handlers.ensure_handler_refs()
    fn = resolve(HandlerRef("xp.rank_view"))

    for tok in ("xp", "coins", "both"):
        captured.clear()
        assert run(fn(_req({"argv": (tok,)}))) is None
        _, req = captured[-1]
        assert req.args["rank_stat"] == tok
        assert req.args["rank_target"] == 42       # the actor (default uid)

    # <@id> sets the member; stat defaults to "both"
    captured.clear()
    assert run(fn(_req({"argv": ("<@8>",)}))) is None
    _, req = captured[-1]
    assert req.args["rank_target"] == 8 and req.args["rank_stat"] == "both"


def test_rank_view_category_routing(monkeypatch):
    """A registered category token routes to ``provider.member_rank`` — the
    empty-hint branch (member_rank -> None) vs the ``Rank #N`` branch
    (handlers.py ~:79-85)."""
    from sb.domain.community import rank_providers
    from sb.domain.xp import handlers
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    async def member_rank(gid, member):
        return (None, None) if member == 7 else (5, "Level 2 (300 XP)")

    fake = SimpleNamespace(name="faketest", display_title="🎯 Test Board",
                           empty_hint="No test rank yet.",
                           member_rank=member_rank)
    monkeypatch.setattr(
        rank_providers, "get_provider",
        lambda key: fake if str(key).lower() == "faketest" else None)
    handlers.ensure_handler_refs()
    fn = resolve(HandlerRef("xp.rank_view"))

    r_empty = run(fn(_req({"argv": ("faketest", "<@7>")})))
    assert r_empty.outcome == SUCCESS
    assert "🎯 Test Board — <@7>" in r_empty.user_message
    assert "No test rank yet." in r_empty.user_message

    r_rank = run(fn(_req({"argv": ("faketest", "<@8>")})))
    assert r_rank.outcome == SUCCESS
    assert "Rank **#5** · Level 2 (300 XP)" in r_rank.user_message


def test_givexp_handler_copy(monkeypatch):
    """`!givexp` wrapper — <2 argv => BLOCKED usage copy; a non-SUCCESS op
    passes its user_message through; SUCCESS renders the gave-copy from the
    award dict (handlers.py ~:99-118)."""
    from sb.domain.xp import handlers
    from sb.spec.outcomes import BLOCKED, SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    handlers.ensure_handler_refs()
    fn = resolve(HandlerRef("xp.givexp"))

    r = run(fn(_req({"argv": ("<@7>",)})))
    assert (r.outcome, r.user_message) == (
        BLOCKED, "Usage: `!givexp @user <amount>`")
    assert run(fn(_req({"argv": ()}))).outcome == BLOCKED

    _patch_engine(monkeypatch, outcome=BLOCKED, user_message="❌ nope")
    r_pt = run(fn(_req({"argv": ("<@7>", "10")})))
    assert (r_pt.outcome, r_pt.user_message) == (BLOCKED, "❌ nope")

    _patch_engine(monkeypatch, outcome=SUCCESS,
                  after={"award": {"delta": 10, "new_xp": 110,
                                   "new_level": 3}})
    r_ok = run(fn(_req({"argv": ("<@7>", "10")})))
    assert r_ok.outcome == SUCCESS
    assert r_ok.user_message == (
        "✅ Gave **10** XP to <@7>. They now have **110** XP "
        "(Level **3**).")


def test_resetxp_handler_copy(monkeypatch):
    """`!resetxp` wrapper — empty argv => BLOCKED usage copy; non-SUCCESS
    passthrough; SUCCESS renders the reset ack (handlers.py ~:120-134)."""
    from sb.domain.xp import handlers
    from sb.spec.outcomes import BLOCKED, SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    handlers.ensure_handler_refs()
    fn = resolve(HandlerRef("xp.resetxp"))

    r = run(fn(_req({"argv": ()})))
    assert (r.outcome, r.user_message) == (BLOCKED, "Usage: `!resetxp @user`")

    _patch_engine(monkeypatch, outcome=BLOCKED, user_message="❌ cannot")
    r_pt = run(fn(_req({"argv": ("<@7>",)})))
    assert (r_pt.outcome, r_pt.user_message) == (BLOCKED, "❌ cannot")

    _patch_engine(monkeypatch, outcome=SUCCESS)
    r_ok = run(fn(_req({"argv": ("<@7>",)})))
    assert (r_ok.outcome, r_ok.user_message) == (
        SUCCESS, "✅ Reset XP for <@7>.")


# --- P2: XP math edges (pure, levels.py) --------------------------------------------

def test_level_curve_boundary_sweep():
    """``level_progress(total_xp_for_level(L)) == (L, 0, xp_for_level(L))``
    at each boundary, and one-below lands at the top of the previous level —
    swept across L=0..20."""
    from sb.domain.xp.levels import (
        level_progress,
        total_xp_for_level,
        xp_for_level,
    )

    for lv in range(0, 21):
        total = total_xp_for_level(lv)
        assert level_progress(total) == (lv, 0, xp_for_level(lv)), lv
        if lv >= 1:
            assert level_progress(total - 1) == (
                lv - 1, xp_for_level(lv - 1) - 1, xp_for_level(lv - 1)), lv


def test_level_progress_zero_and_negative():
    """level_progress(0) == (0, 0, 100); a negative total exits on the FIRST
    iteration (no infinite loop) — remaining stays negative at level 0."""
    from sb.domain.xp.levels import level_progress

    assert level_progress(0) == (0, 0, 100)
    assert level_progress(-5) == (0, -5, 100)


def test_import_negative_level_guard(monkeypatch):
    """Q-0120 (confirmed in code): the ops.py negative-level guard is DEAD via
    the public records path — ``reduce_max_levels``' ``-1`` sentinel
    (``level > best.get(user_id, -1)``) filters any level < 0 before the loop,
    so a lone ``(7, -1)`` reduces to ``{}`` (no write, no raise). Forcing a
    negative PAST the reducer proves the guard still fires (ops.py ~:184)."""
    from sb.domain.xp import migrate, ops
    from sb.kernel.interaction.errors import ValidatorError

    FakeXpStore().install(monkeypatch)
    # natural path: the -1 sentinel drops the record => nothing imported
    out = run(ops._record_import(
        None, _ctx({"records": ((7, -1),), "source": "import:arcane"})))
    assert out.after["users"] == 0 and out.after["raised"] == 0

    # force a negative past the reducer => the guard refuses
    monkeypatch.setattr(migrate, "reduce_max_levels", lambda recs: {7: -1})
    with pytest.raises(ValidatorError) as exc:
        run(ops._record_import(
            None, _ctx({"records": ((7, 5),), "source": "import:arcane"})))
    assert exc.value.user_copy == "❌ Level must be >= 0, got -1."


# --- P2: migrate formats (migrate.py) ------------------------------------------------

def test_migrate_remaining_formats():
    """mee6 (advanced-to + name_re), superbot, generic (``\\blevel N``),
    bold-marker tolerance, and first-mention-wins with multiple ids — only
    ``arcane`` was previously covered."""
    from sb.domain.xp.migrate import get_format, parse_level_message

    # mee6 — "advanced to level **N**" + the name_re fallback + bold marker
    mee6 = get_format("mee6")
    p = parse_level_message("GG @User, you just advanced to level **3**!",
                            mention_ids=(), fmt=mee6)
    assert p is not None and p.level == 3 and p.name == "User"
    # a mention wins over the name leg
    pm = parse_level_message("GG @User, you just advanced to level 3!",
                             mention_ids=(555,), fmt=mee6)
    assert pm.user_id == 555 and pm.name is None

    # superbot — "reached **Level N**"; name_re is None => name stays None
    sbot = get_format("superbot")
    ps = parse_level_message("@User reached **Level 3**!", fmt=sbot)
    assert ps.level == 3 and ps.name is None and ps.user_id is None

    # generic — any "\blevel N", bold-marker tolerant (0 and 2 asterisks)
    gen = get_format("generic")
    assert parse_level_message("congrats, you hit level 7 today",
                               fmt=gen).level == 7
    assert parse_level_message("now at level **12**", fmt=gen).level == 12

    # first-mention-wins with MULTIPLE mention ids (arcane)
    arc = get_format("arcane")
    pmm = parse_level_message("@A and @B reached level 4",
                              mention_ids=(11, 22), fmt=arc)
    assert pmm.user_id == 11 and pmm.level == 4


# --- P2: refusal/seam paths (service.py) ---------------------------------------------

def test_resolve_text_channel_seam():
    """``<#id>``/bare-snowflake -> int; short/non-digit + no resolver -> None;
    a resolver raise reads as not-found -> None; an installed resolver's hit
    -> its id (service.py ~:149-163)."""
    from sb.domain.xp import service

    assert run(service.resolve_text_channel(
        1, "<#123456789012345>")) == 123456789012345
    assert run(service.resolve_text_channel(
        1, "123456789012345")) == 123456789012345
    assert run(service.resolve_text_channel(1, "123")) is None      # too short
    assert run(service.resolve_text_channel(1, "general")) is None  # no resolver

    async def boom(gid, name):
        raise RuntimeError("directory down")

    service.install_channel_resolver(boom)
    assert run(service.resolve_text_channel(1, "general")) is None

    async def ok(gid, name):
        return 42 if name == "general" else None

    service.install_channel_resolver(ok)
    assert run(service.resolve_text_channel(1, "general")) == 42


def test_fetch_avatar_png_seam():
    """No fetcher -> None; a fetcher raise -> None (the any-failure->None
    posture); an installed fetcher's bytes pass through (service.py ~:175-186)."""
    from sb.domain.xp import service

    assert run(service.fetch_avatar_png(7, 1)) is None

    async def boom(uid, gid):
        raise RuntimeError("cdn 500")

    service.install_avatar_fetcher(boom)
    assert run(service.fetch_avatar_png(7, 1)) is None

    async def ok(uid, gid):
        return b"PNGDATA"

    service.install_avatar_fetcher(ok)
    assert run(service.fetch_avatar_png(7, 1)) == b"PNGDATA"


def test_levelup_fanout_unbound_and_granter_swallow(monkeypatch):
    """An unbound announce channel emits nothing; a role-granter that raises
    is swallowed and never kills the fan-out (service.py ~:313-327)."""
    from sb.domain.xp import service
    from sb.kernel.interaction import egress

    sent = []

    class FakeEmitter:
        async def send(self, channel_id, content, *, guild_id=None):
            sent.append((channel_id, guild_id))

    monkeypatch.setattr(egress, "active_channel_emitter", lambda: FakeEmitter())

    async def unbound(guild_id):
        return None

    monkeypatch.setattr(service, "bound_announce_channel", unbound)

    async def boom(guild_id, user_id, new_level):
        raise RuntimeError("role api down")

    service.install_level_role_granter(boom)

    run(service._route_level_up(guild_id=1, user_id=7, new_level=3,
                                source="chat"))
    assert sent == []          # unbound => the emitter was never reached


# --- P3: INV-G level-consistency (DB-free via a monkeypatched pool) -------------------

def test_inv_g_check_flags_inconsistent(monkeypatch):
    """``check_level_consistency`` flags a ``level != level_progress(xp)``
    row (one Violation carrying row_id + detail) and returns empty when every
    row is consistent (invariants.py)."""
    from sb.domain.xp.invariants import xp_level_consistency_spec
    from sb.kernel.db import pool
    from sb.spec.refs import resolve

    spec = xp_level_consistency_spec()          # registers the check provider
    check = resolve(spec.check_ref)

    # xp=100 derives level 1; a stored level 5 is drift, level 1 is consistent
    async def drift(sql, params, conn=None):
        return [{"user_id": 7, "xp": 100, "level": 5},
                {"user_id": 8, "xp": 100, "level": 1}]

    monkeypatch.setattr(pool, "fetchall", drift)
    violations = run(check(spec, guild_id=1))
    assert len(violations) == 1
    assert violations[0].row_id == "7:1"
    assert "level 5 != derived 1" in violations[0].detail

    async def all_ok(sql, params, conn=None):
        return [{"user_id": 8, "xp": 100, "level": 1}]

    monkeypatch.setattr(pool, "fetchall", all_ok)
    assert run(check(spec, guild_id=1)) == ()


def test_inv_g_repair_leg(monkeypatch):
    """The repair leg re-derives ``level := level_progress(xp).level`` for a
    present row and UPDATEs; a vanished row repairs False with no write
    (ops.py ~:201-231)."""
    from sb.domain.xp import ops
    from sb.kernel.db import pool

    executed = []

    async def fake_execute(sql, params, conn=None):
        executed.append((sql, params))

    monkeypatch.setattr(pool, "execute", fake_execute)

    async def present(sql, params, conn=None):
        return {"xp": 100, "level": 9}          # xp=100 -> derived level 1

    monkeypatch.setattr(pool, "fetchone", present)
    out = run(ops._record_repair_level(
        None, _ctx({"violation": {"row_id": "7:1"}})))
    assert out.after == {"repaired": True, "level": 1}
    assert out.before == {"level": 9}
    assert executed and executed[-1][1] == (7, 1, 1)

    executed.clear()

    async def gone(sql, params, conn=None):
        return None

    monkeypatch.setattr(pool, "fetchone", gone)
    out2 = run(ops._record_repair_level(
        None, _ctx({"violation": {"row_id": "7:1"}})))
    assert out2.after == {"repaired": False, "reason": "row_gone"}
    assert executed == []
