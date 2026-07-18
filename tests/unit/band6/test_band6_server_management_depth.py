"""Depth coverage for sb/domain/server_management — the lanes the slice-A/B
suites left uncovered: the MEMBER_ID erasure/tombstone lane
(ops.py ``routing.tombstone_policy_actor`` + routing.py
``tombstone_policy_actor``), the ``routing.record_set_policy`` refusal +
coercion arms, the access-projection DENY/unknown fail-closed edges
(``_axis_command_access`` role_not_held / bootstrap-bypass detail,
``_axis_governance`` no-member unknown, ``_axis_help_visibility`` no-category
unknown), the routing read ordering (``list_for_guild``), and the
``help_preview._is_help_hidden`` fail-closed arm.

Additive + DB-free: the tombstone/store legs monkeypatch the module-bound
``routing.execute``/``routing.fetchall`` over an in-memory table (the
band5 ``test_tombstone_erasure_body`` direct-call pattern); the projection
axes monkeypatch the ported owners (the band6 ``_patch_owners`` pattern).
No golden, no migration — the slice-A/B goldens pin the hub bytes, untouched.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run


# ============================================================================
# P1 — the erasure/tombstone lane (MEMBER_ID compliance path; zero coverage)
# ============================================================================


def _ctx(params: dict, *, uid: int = 7, gid: int = 1):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params)


def test_tombstone_workflow_scrubs_actor_keeps_rows_and_audits_count(
        monkeypatch):
    """The ops.py erasure body drives the real store fn over an in-memory
    table: it NULLs the subject's actor_id, leaves the policy rows (and
    their enabled flag) intact, and reports the affected count in
    ``after['rows']`` for the S11 audit."""
    from sb.domain.server_management import ops, routing

    # in-memory command_routing_policy: (scope) -> row.
    table = {
        ("guild", "games"): {"enabled": True, "actor_id": 42},
        ("channel", "economy"): {"enabled": False, "actor_id": 42},
        ("guild", "moderation"): {"enabled": True, "actor_id": 99},
    }

    async def fake_execute(query, params, *, conn=None):
        assert query.startswith(
            "UPDATE command_routing_policy SET actor_id=NULL")
        (user_id,) = params
        scrubbed = 0
        for row in table.values():
            if row["actor_id"] == user_id:
                row["actor_id"] = None
                scrubbed += 1
        return f"UPDATE {scrubbed}"

    monkeypatch.setattr(routing, "execute", fake_execute)

    out = run(ops._tombstone_policy_actor(None, _ctx({"subject_user_id": 42})))

    # the affected count rides the audit leg's `after`.
    assert out.after == {"rows": 2}
    assert out.before == {}
    # subject 42's pointer is scrubbed in place — rows KEPT (guild config,
    # not the subject's trail), enabled flags untouched.
    assert table[("guild", "games")] == {"enabled": True, "actor_id": None}
    assert table[("channel", "economy")] == {"enabled": False,
                                             "actor_id": None}
    # a different actor's row is left entirely alone.
    assert table[("guild", "moderation")] == {"enabled": True,
                                              "actor_id": 99}


def test_tombstone_store_parses_row_count_from_command_tag(monkeypatch):
    """The store fn's ``rsplit``-based parse returns the int on a well-formed
    ``UPDATE N`` command tag (oracle command-tag posture)."""
    from sb.domain.server_management import routing

    async def fake_execute(query, params, *, conn=None):
        return "UPDATE 3"

    monkeypatch.setattr(routing, "execute", fake_execute)
    assert run(routing.tombstone_policy_actor(None, user_id=42)) == 3


@pytest.mark.parametrize("tag", [None, "UPDATE", "", "UPDATE x"])
def test_tombstone_store_returns_zero_on_malformed_tag(monkeypatch, tag):
    """The ``except (ValueError, TypeError): return 0`` fail-closed arm — a
    malformed/None command tag yields 0, never a crash (None -> 'None',
    'UPDATE' -> no trailing int, 'UPDATE x' -> non-numeric)."""
    from sb.domain.server_management import routing

    async def fake_execute(query, params, *, conn=None):
        return tag

    monkeypatch.setattr(routing, "execute", fake_execute)
    assert run(routing.tombstone_policy_actor(None, user_id=42)) == 0


# ============================================================================
# P2 — routing.record_set_policy refusal + coercion arms
# ============================================================================


def _policy_ctx(params: dict, *, uid: int = 7, gid: int = 1):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params)


def test_record_set_policy_empty_cog_name_refuses(monkeypatch):
    """An empty cog_name is the oracle's non-empty-cog guard: it raises the
    copy-only refusal BEFORE any store read/write."""
    from sb.domain.server_management import ops, routing
    from sb.kernel.interaction.errors import ValidatorError

    async def _boom(*a, **kw):  # the store must never be reached
        raise AssertionError("store touched despite refusal")

    monkeypatch.setattr(routing, "get_policy", _boom)
    monkeypatch.setattr(routing, "upsert_policy", _boom)

    with pytest.raises(ValidatorError) as ei:
        run(ops._record_set_policy(None, _policy_ctx(
            {"scope_type": "channel", "scope_id": 5, "cog_name": "  ",
             "enabled": False})))
    assert ei.value.user_copy == "A cog name is required."


def test_record_set_policy_coerces_string_false_to_bool(monkeypatch):
    """The str-coercion arm: enabled='false' -> False (anything else the
    default-true posture); the coerced bool reaches the upsert verbatim."""
    from sb.domain.server_management import ops, routing

    captured = {}

    async def fake_get(guild_id, scope_type, scope_id, cog_name, conn=None):
        return None

    async def fake_upsert(conn, *, guild_id, scope_type, scope_id, cog_name,
                          enabled, actor_id):
        captured["enabled"] = enabled

    monkeypatch.setattr(routing, "get_policy", fake_get)
    monkeypatch.setattr(routing, "upsert_policy", fake_upsert)

    run(ops._record_set_policy(None, _policy_ctx(
        {"scope_type": "channel", "scope_id": 5, "cog_name": "games",
         "enabled": "false"})))
    assert captured["enabled"] is False

    # the str-coercion default arm: any other string is TRUE (the drafting
    # bug never silently disables a cog).
    run(ops._record_set_policy(None, _policy_ctx(
        {"scope_type": "channel", "scope_id": 5, "cog_name": "games",
         "enabled": "yes"})))
    assert captured["enabled"] is True


# ============================================================================
# P3 — access-projection DENY / unknown fail-closed edges
# ============================================================================


def _feature(subsystem="economy", command="balance", tier="user"):
    from sb.domain.server_management.access_projection import FeatureEntry

    return FeatureEntry(subsystem=subsystem, command_name=command,
                        visibility_tier=tier)


def _actx(**kw):
    from sb.domain.server_management.access_projection import AccessContext

    defaults = dict(guild_id=1, channel_id=2, member_tier="user")
    defaults.update(kw)
    return AccessContext(**defaults)


def _fake_decision(**kw):
    from sb.kernel.authority.decision import ChannelAccessDecision
    from sb.spec.outcomes import DenialReason

    defaults = dict(
        allowed=True, mode=None, reason=DenialReason.ALLOWED, detail="",
        owner_override=False, bootstrap_bypass=False,
        would_deny_without_override=False, denial_message=None)
    defaults.update(kw)
    return ChannelAccessDecision(**defaults)


def _patch_command_access(monkeypatch, decision):
    """Point the axis-1+2 owners at a fixed channel-access verdict."""
    from sb.domain.platform import command_access as ca
    from sb.kernel.authority import channel_access as chan

    async def fake_snapshot(guild_id):
        return None

    async def fake_resolve(*a, **kw):
        return decision

    monkeypatch.setattr(ca, "read_policy_snapshot", fake_snapshot)
    monkeypatch.setattr(chan, "resolve_channel_access", fake_resolve)


def test_axis_command_access_role_not_held_denies_with_reason_code(
        monkeypatch):
    """The R-16 per-channel role-set denial: the axis carries the resolver's
    ``role_not_held`` detail token through as the deny reason_code (which the
    reason table maps to the user-safe role-limited copy)."""
    from sb.domain.server_management.access_projection import (
        AccessAxis,
        _axis_command_access,
        safe_locked_reason,
    )

    _patch_command_access(monkeypatch, _fake_decision(
        allowed=False, detail="role_not_held"))
    outcome = run(_axis_command_access(_feature(), _actx()))
    assert outcome.axis is AccessAxis.COMMAND_ACCESS
    assert outcome.state == "deny"
    assert outcome.reason_code == "role_not_held"
    # the token resolves to the ported user-safe copy, not a leak.
    assert safe_locked_reason("role_not_held").safe_text == (
        "Commands in this channel are limited to specific roles.")


def test_axis_command_access_bootstrap_bypass_records_allow_detail(
        monkeypatch):
    """A bootstrap-bypass allow is recorded as ``allow`` with the
    ``bootstrap bypass`` diagnostic detail (the shipped bypass path)."""
    from sb.domain.server_management.access_projection import (
        AccessAxis,
        _axis_command_access,
    )

    _patch_command_access(monkeypatch, _fake_decision(
        allowed=True, bootstrap_bypass=True))
    outcome = run(_axis_command_access(_feature(), _actx()))
    assert outcome.axis is AccessAxis.COMMAND_ACCESS
    assert outcome.state == "allow"
    assert outcome.detail == "bootstrap bypass"


def test_axis_governance_no_member_is_unknown_not_a_guess():
    """No declared member facts (member_tier=None AND user_id=None): the
    governance axis reports ``unknown`` rather than guess — a guess could
    falsely allow."""
    from sb.domain.server_management.access_projection import (
        AccessAxis,
        _axis_governance,
    )

    outcome = run(_axis_governance(
        _feature(), _actx(member_tier=None, user_id=None)))
    assert outcome.axis is AccessAxis.GOVERNANCE
    assert outcome.state == "unknown"
    assert outcome.detail == "no member"


def test_composed_effective_is_unknown_when_governance_cannot_resolve(
        monkeypatch):
    """A no-member context whose gating axes otherwise allow composes to
    ``unknown`` — the read model never claims an ``allow`` it could not
    verify (never a false allow)."""
    from sb.domain.server_management import routing
    from sb.domain.server_management.access_projection import (
        resolve_feature_access,
    )

    # command-access allows (mode=None default-allow) …
    _patch_command_access(monkeypatch, _fake_decision(allowed=True))

    # … routing allows (no rows -> default-true chain) …
    async def no_row(guild_id, scope_type, scope_id, cog_name, conn=None):
        return None

    monkeypatch.setattr(routing, "get_policy", no_row)

    # … but governance is unknown (no member facts).
    decision = run(resolve_feature_access(
        _feature(), _actx(member_tier=None, user_id=None)))
    assert decision.effective == "unknown"
    assert decision.deciding_axis is None      # unknown is not a deny
    assert decision.reason is None


def test_axis_help_visibility_no_category_mapping_is_unknown(monkeypatch):
    """A feature whose subsystem resolves to no category record reports
    ``unknown`` (the fail-closed defensive arm) — never a crash."""
    from sb.domain.help import categories as cats
    from sb.domain.server_management.access_projection import (
        AccessAxis,
        _axis_help_visibility,
    )

    monkeypatch.setattr(cats, "category_by_key", lambda key: None)
    outcome = _axis_help_visibility(
        _feature(subsystem="mystery_subsystem", command="thing"), _actx())
    assert outcome.axis is AccessAxis.HELP
    assert outcome.state == "unknown"
    assert outcome.detail == "no category mapping"


# ============================================================================
# P4 — routing read ordering + help_preview / resolver fail-closed
# ============================================================================


def test_list_for_guild_orders_scope_cog_scopeid_nulls_first(monkeypatch):
    """The panel/diagnostics list read pins the oracle ordering:
    (scope_type, cog_name, scope_id NULLS FIRST) — guild rows (scope_id
    NULL) sort ahead of their category/channel siblings."""
    from sb.domain.server_management import routing

    seen = {}
    ordered_rows = [
        {"scope_type": "channel", "scope_id": None, "cog_name": "games"},
        {"scope_type": "channel", "scope_id": 42, "cog_name": "games"},
    ]

    async def fake_fetchall(query, params, *, conn=None):
        seen["query"] = query
        seen["params"] = params
        return ordered_rows

    monkeypatch.setattr(routing, "fetchall", fake_fetchall)
    rows = run(routing.list_for_guild(99))
    assert rows is ordered_rows
    assert seen["params"] == (99,)
    # the ORDER BY clause IS the ordering contract (the DB applies it).
    assert "ORDER BY scope_type, cog_name, scope_id NULLS FIRST" in \
        seen["query"]


def test_is_help_hidden_invalid_tier_fails_closed_true():
    """``help_preview._is_help_hidden`` fail-closed arm: on a staff-gated
    subsystem an unparseable tier raises inside ``tier_at_or_above`` and the
    ``except (ValueError, KeyError): return True`` hides it (fail closed)."""
    from sb.domain.server_management.help_preview import _is_help_hidden

    # moderation is a staff-only category -> the gate is live.
    assert _is_help_hidden("moderation", "not_a_real_tier") is True
    # a valid staff tier passes the gate (contrast: not the blanket-True).
    assert _is_help_hidden("moderation", "administrator") is False
    # a non-staff subsystem short-circuits False before the tier check,
    # so even a bogus tier never trips the fail-closed arm.
    assert _is_help_hidden("economy", "not_a_real_tier") is False


def test_is_cog_enabled_category_only_skips_channel_lookup(monkeypatch):
    """channel_id=None short-circuits past the channel scope: the resolver
    consults category then guild only, and the category row wins."""
    from sb.domain.server_management import routing

    calls = []

    async def fake_get(guild_id, scope_type, scope_id, cog_name, conn=None):
        calls.append((scope_type, scope_id))
        if scope_type == "category" and scope_id == 7:
            return {"enabled": False}
        return None

    monkeypatch.setattr(routing, "get_policy", fake_get)
    enabled = run(routing.is_cog_enabled(
        guild_id=1, cog_name="games", channel_id=None, category_id=7))
    # the category row disables the cog …
    assert enabled is False
    # … and NO channel-scope lookup was issued (the None short-circuit).
    assert ("channel", None) not in calls
    assert calls == [("category", 7)]     # early-exit before the guild leg
