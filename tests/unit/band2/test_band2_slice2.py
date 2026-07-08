"""Band 2 slice 2 (the remaining operator-spine eight) — engine unit legs."""

from __future__ import annotations

import asyncio

import pytest


def test_automod_engine_rules():
    from sb.domain.automod.engine import AutomodPolicy, MessageFact, evaluate

    policy = AutomodPolicy(enabled=True, spam_enabled=True, caps_enabled=True,
                           mentions_enabled=True, duplicate_enabled=True,
                           invites_enabled=True)
    base = dict(user_id=1, channel_id=10, at=100.0)
    history = tuple(
        MessageFact(content=f"m{i}", **{**base, "at": 95.0 + i})
        for i in range(4))
    # 5th message inside the 7s window => spam
    tags = evaluate(MessageFact(content="m5", **base), history, policy)
    assert "spam" in tags
    # caps rule
    tags = evaluate(MessageFact(content="THIS IS ALL VERY LOUD YES", **base),
                    (), policy)
    assert "caps" in tags
    # invite rule
    tags = evaluate(MessageFact(content="join discord.gg/abc", **base), (), policy)
    assert "invites" in tags
    # mentions rule
    tags = evaluate(MessageFact(content="hi", mention_count=4, **base), (), policy)
    assert "mentions" in tags
    # disabled master switch => always clean
    off = AutomodPolicy(enabled=False, spam_enabled=True)
    assert evaluate(MessageFact(content="x", **base), history, off) == ()
    # exemptions win
    exempt = AutomodPolicy(enabled=True, caps_enabled=True,
                           exempt_channels=frozenset({10}))
    assert evaluate(MessageFact(content="LOUD LOUD LOUD LOUD", **base),
                    (), exempt) == ()


def test_security_raid_window_and_age_gate():
    from sb.domain.security import RaidWindow, age_gate_action

    window = RaidWindow(join_count=3, window_seconds=60)
    assert window.note_join(0.0) is False
    assert window.note_join(10.0) is False
    assert window.note_join(20.0) is True          # threshold crossed
    fresh = RaidWindow(join_count=3, window_seconds=60)
    fresh.note_join(0.0)
    fresh.note_join(100.0)                          # first join aged out
    assert fresh.note_join(110.0) is False

    assert age_gate_action(30, enabled=True, min_days=7, action="kick") is None
    assert age_gate_action(2, enabled=True, min_days=7, action="kick") == "kick"
    assert age_gate_action(2, enabled=True, min_days=7, action="nuke") == "alert"
    assert age_gate_action(2, enabled=False, min_days=7, action="kick") is None


def test_welcome_template_render():
    from sb.domain.welcome import DEFAULT_JOIN_MESSAGE, render_message

    out = render_message(DEFAULT_JOIN_MESSAGE, user="<@1>", server="Guild",
                         count=42)
    assert out == "👋 Welcome <@1> to **Guild**! You're member #42."
    # unknown braces pass through, never KeyError
    assert render_message("hi {unknown}", user="u", server="s", count=1) == \
        "hi {unknown}"


def test_counters_render():
    from sb.domain.counters import render_counters

    out = render_counters({}, total=10, humans=8, bots=2)
    assert out == {"total": "👥 Members: 10", "humans": "🧑 Humans: 8",
                   "bots": "🤖 Bots: 2"}
    custom = render_counters({"total": "N={count}"}, total=5, humans=4, bots=1)
    assert custom["total"] == "N=5"


def test_slice2_manifests_compile_and_declare():
    import sb.manifest.admin as m_admin
    import sb.manifest.automod as m_automod
    import sb.manifest.channel as m_channel
    import sb.manifest.cleanup as m_cleanup
    import sb.manifest.counters as m_counters
    import sb.manifest.image_moderation as m_img
    import sb.manifest.security as m_security
    import sb.manifest.server_management as m_sm
    import sb.manifest.welcome as m_welcome

    keys = {m.MANIFEST.key for m in (m_admin, m_automod, m_channel, m_cleanup,
                                     m_counters, m_img, m_security, m_sm,
                                     m_welcome)}
    assert keys == {"admin", "automod", "channel", "cleanup", "counters",
                    "image_moderation", "security", "server_management",
                    "welcome"}
    # the shipped channel surface is DECLARED (names verbatim)
    names = {c.name for c in m_channel.MANIFEST.commands}
    assert {"channelmenu", "clone", "lock", "slowmode", "bulkcreate"} <= names
    # A-14 anchors on welcome
    binding_names = {getattr(s, "name", "") for s in m_welcome.MANIFEST.settings}
    assert "entry_role" in binding_names
    assert "min_account_age_days" in binding_names


def test_word_ops_registered_and_word_add_leg(monkeypatch):
    from types import SimpleNamespace

    from sb.domain.cleanup import ops, store
    from sb.kernel.workflow.context import WorkflowContext
    from sb.kernel.workflow.registry import REGISTRY
    from sb.spec.refs import WorkflowRef

    ops.register_ops()
    assert REGISTRY.resolve(WorkflowRef("cleanup.word_add_op")).lane.value == "domain"

    async def fake_add(conn, *, guild_id, word):
        assert word == "spamword"
        return True

    monkeypatch.setattr(store, "add_word", fake_add)
    ctx = WorkflowContext(actor=SimpleNamespace(user_id=1), guild_id=2,
                          request_id="r", confirmed=False,
                          params={"argv": ("SpamWord",)})
    outcome = asyncio.run(ops._word_add(None, ctx))
    assert outcome.after == {"word": "spamword", "added": True}


def test_pending_handler_is_honest_blocked():
    from sb.domain.operator_spine import pending_handler
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import resolve

    ref = pending_handler("bandtwo.test_pending", "not armed yet")
    reply = asyncio.run(resolve(ref)(None))
    assert reply.outcome == BLOCKED
    assert "not armed" in reply.user_message
