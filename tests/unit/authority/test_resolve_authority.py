"""resolve_authority — the fixed order (spec 04 §3.3) incl. the R-16 role-set
lane, owner-override-once, and the unconditional lane_would_deny rule."""

import asyncio
import dataclasses

import pytest

from sb.kernel.authority import owner as owner_mod
from sb.kernel.authority.decision import AuthorityDecision, AuthorityRequest
from sb.kernel.authority.resolve import (
    install_capability_override_reader,
    install_role_binding_reader,
    reset_readers_for_tests,
    resolve_authority,
)
from sb.spec.authority import Lane
from sb.spec.outcomes import DenialReason


@pytest.fixture(autouse=True)
def _clean_state():
    owner_mod.reset_for_tests()
    reset_readers_for_tests()
    yield
    owner_mod.reset_for_tests()
    reset_readers_for_tests()


class _Cfg:
    BOT_OWNER_USER_ID = 111
    EXTRA_OWNER_USER_IDS = ("222",)


def _install_owner():
    owner_mod.install_owner_config(_Cfg())


def _run(req):
    return asyncio.run(resolve_authority(req))


def test_scripted_bypass_never_dereferences_ids():
    for actor_type in ("system", "backfill"):
        d = _run(AuthorityRequest("economy.wallet.transfer", actor_type=actor_type))
        assert d.allowed and not d.owner_override and not d.lane_would_deny
        assert d.member_tier is None and d.required_tier == ""
        assert d.reason is DenialReason.ALLOWED and d.denial_message is None


def test_membership_gate_owner_not_exempt():
    _install_owner()
    d = _run(AuthorityRequest("", user_id=111, guild_id=5, is_member=False))
    assert not d.allowed and not d.owner_override and not d.lane_would_deny
    assert d.reason is DenialReason.AUTHORITY
    assert d.denial_message == "You must be a member of this server to use this."


def test_capability_admin_floor_and_decision_shape():
    d = _run(AuthorityRequest("", user_id=1, guild_id=5, is_member=True,
                              member_tier="administrator"))
    assert d.allowed and d.lane is Lane.CAPABILITY
    assert d.required_tier == "administrator" and not d.lane_would_deny
    assert [f.name for f in dataclasses.fields(AuthorityDecision)] == [
        "allowed", "authority_ref", "lane", "required_tier", "member_tier",
        "owner_override", "lane_would_deny", "reason", "detail", "denial_message",
    ]  # the frozen 10-field shape (RC-2)


def test_capability_below_floor_denies_with_generic_copy():
    d = _run(AuthorityRequest("", user_id=1, guild_id=5, is_member=True,
                              member_tier="moderator"))
    assert not d.allowed and d.lane_would_deny
    assert d.denial_message == "You need administrator permission to use this."


def test_tier_lane_uses_is_tier_sufficient():
    ok = _run(AuthorityRequest("moderator", user_id=1, guild_id=5,
                               is_member=True, member_tier="administrator"))
    assert ok.allowed and ok.lane is Lane.TIER and ok.required_tier == "moderator"
    deny = _run(AuthorityRequest("moderator", user_id=1, guild_id=5,
                                 is_member=True, member_tier="staff"))
    assert not deny.allowed
    assert deny.denial_message == "You need the **moderator** role (or higher) to use this."


def test_revoke_overlay_flips_allow_to_deny_but_never_grants():
    async def reader(guild_id, capability):
        return {"economy.wallet.transfer": False,
                "economy.wallet.grant": True}.get(capability)
    install_capability_override_reader(reader)
    revoked = _run(AuthorityRequest("economy.wallet.transfer", user_id=1, guild_id=5,
                                    is_member=True, member_tier="administrator"))
    assert not revoked.allowed and revoked.lane_would_deny
    assert revoked.denial_message == (
        "This action has been turned off for your role in this server.")
    # explicit True never grants a below-floor actor
    below = _run(AuthorityRequest("economy.wallet.grant", user_id=1, guild_id=5,
                                  is_member=True, member_tier="staff"))
    assert not below.allowed


def test_owner_override_once_beats_lane_and_revoke():
    _install_owner()
    async def reader(guild_id, capability):
        return False  # guild tries to revoke everything
    install_capability_override_reader(reader)
    d = _run(AuthorityRequest("economy.wallet.transfer", user_id=111, guild_id=5,
                              is_member=True, member_tier="user"))
    assert d.allowed and d.owner_override and d.lane_would_deny  # transparency input
    d2 = _run(AuthorityRequest("owner", user_id=222, guild_id=5,
                               is_member=True, member_tier="user"))
    assert d2.allowed and d2.owner_override  # EXTRA_OWNER_USER_IDS clears the seam


def test_owner_override_is_false_before_install():
    d = _run(AuthorityRequest("", user_id=111, guild_id=5, is_member=True,
                              member_tier="user"))
    assert not d.allowed and not d.owner_override  # fail-closed


def test_setup_delegate_floor_and_revoke_subject():
    d = _run(AuthorityRequest("economy.wallet.transfer", actor_type="setup_delegate",
                              user_id=9, guild_id=5, is_member=True, member_tier="user"))
    assert d.allowed and not d.owner_override and d.lane_would_deny

    async def reader(guild_id, capability):
        return False
    install_capability_override_reader(reader)
    revoked = _run(AuthorityRequest("economy.wallet.transfer",
                                    actor_type="setup_delegate", user_id=9,
                                    guild_id=5, is_member=True, member_tier="user"))
    assert not revoked.allowed


def test_role_set_lane_allow_set_and_fail_closed():
    async def bindings(guild_id, name):
        return frozenset({10, 11}) if name == "verified_member" else None
    install_role_binding_reader(bindings)
    ok = _run(AuthorityRequest("role:verified_member", user_id=1, guild_id=5,
                               is_member=True, member_tier="user",
                               role_ids=frozenset({11, 99})))
    assert ok.allowed and ok.lane is Lane.ROLE_SET and ok.required_tier == ""
    miss = _run(AuthorityRequest("role:verified_member", user_id=1, guild_id=5,
                                 is_member=True, member_tier="administrator",
                                 role_ids=frozenset({99})))
    assert not miss.allowed and "role_not_held" in miss.detail
    assert miss.denial_message == (
        "You need one of this server's configured roles to use this.")
    # unconfigured binding => deny-until-role (quarantine posture, A-14)
    unconfigured = _run(AuthorityRequest("role:ghosts", user_id=1, guild_id=5,
                                         is_member=True, role_ids=frozenset({1})))
    assert not unconfigured.allowed


def test_role_set_owner_override_still_wins():
    _install_owner()
    d = _run(AuthorityRequest("role:verified_member", user_id=111, guild_id=5,
                              is_member=True, role_ids=frozenset()))
    assert d.allowed and d.owner_override and d.lane_would_deny
