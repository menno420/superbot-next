"""The K6 grammar leaves: sb.spec.outcomes (spec 02 §2/§7.1, RC-6) and
sb.spec.authority (spec 04 §3.2/§3.6, RC-3 + R-16)."""

import pytest

from sb.spec.authority import (
    ADMIN_FLOOR_TIER,
    TIERS,
    BadAuthorityError,
    FormatError,
    Lane,
    classify_authority_ref,
    is_tier_sufficient,
    role_binding_name,
    validate_authority_ref,
)
from sb.spec.outcomes import (
    BLOCKED,
    DECLINED,
    DISCORD_FAILED,
    OUTCOMES,
    PARTIAL,
    SUCCESS,
    DeferMode,
    DenialReason,
    ErrorClass,
    ReplyVisibility,
)


# --- outcomes leaf ---------------------------------------------------------

def test_outcome_constants_are_shipped_values_verbatim():
    # contracts.py:48-52 verbatim — golden harness reads new-as-old.
    assert (SUCCESS, PARTIAL, BLOCKED, DECLINED, DISCORD_FAILED) == (
        "success", "partial", "blocked", "declined", "discord_failed")
    assert OUTCOMES == (SUCCESS, PARTIAL, BLOCKED, DECLINED, DISCORD_FAILED)
    assert len(OUTCOMES) == 5  # NO sixth constant, ever (spec 02 §8 fork 1)


def test_denial_reason_is_exactly_the_frozen_twelve():
    assert {m.value for m in DenialReason} == {
        "allowed", "draining", "authority", "disabled", "visibility",
        "channel", "user_error", "cooldown", "ai_throttle", "not_found",
        "confirm_declined", "dispatch_error",
    }


def test_error_class_reply_visibility_defer_mode_members():
    assert {m.value for m in ErrorClass} == {
        "none", "user_error", "denied", "transient", "bug"}
    assert {m.value for m in ReplyVisibility} == {"ephemeral", "public", "silent"}
    assert {m.value for m in DeferMode} == {"auto", "modal", "none"}


def test_outcomes_leaf_owns_no_lane_enum():
    # RC-3: 04's Lane (sb.spec.authority) wins; 02's AuthorityLane is dropped.
    import sb.spec.outcomes as outcomes
    assert not hasattr(outcomes, "AuthorityLane")
    assert not hasattr(outcomes, "Lane")


# --- authority leaf: classifier (spec 04 §3.2, pinned) ---------------------

def test_tier_order_is_shipped_verbatim():
    assert TIERS == ("user", "trusted", "staff", "moderator", "administrator", "owner")
    assert ADMIN_FLOOR_TIER == "administrator"


@pytest.mark.parametrize("ref,lane", [
    ("", Lane.CAPABILITY),                       # empty => ADMIN floor
    ("economy.wallet.transfer", Lane.CAPABILITY),
    ("a.b", Lane.CAPABILITY),                    # dotted => CAPABILITY, arity later
    ("a.b.c.d", Lane.CAPABILITY),
    ("user", Lane.TIER),
    ("administrator", Lane.TIER),
    ("owner", Lane.TIER),
    ("role:verified_member", Lane.ROLE_SET),     # R-16: prefix beats dot rule
    ("role:mod.team", Lane.ROLE_SET),            # prefix classified FIRST
])
def test_classify_is_total_and_pinned(ref, lane):
    assert classify_authority_ref(ref) is lane


def test_classify_rejects_unclassifiable_and_is_case_sensitive():
    with pytest.raises(BadAuthorityError):
        classify_authority_ref("Administrator")  # no silent case-folding
    with pytest.raises(BadAuthorityError):
        classify_authority_ref("bogus_token")


# --- authority leaf: validator (compiler P4 seam) ---------------------------

def test_validate_empty_and_tier_and_3part_pass_without_corpus():
    validate_authority_ref("")
    validate_authority_ref("moderator")
    validate_authority_ref("economy.wallet.transfer")
    validate_authority_ref("role:verified_member")


@pytest.mark.parametrize("bad", ["a.b", "a.b.c.d", "a..c", ".b.c"])
def test_validate_capability_not_3_part(bad):
    with pytest.raises(FormatError, match="capability_not_3_part"):
        validate_authority_ref(bad)


def test_validate_capability_against_reservation_corpus():
    reserved = frozenset({"economy.wallet.transfer"})
    validate_authority_ref("economy.wallet.transfer", reserved)
    with pytest.raises(BadAuthorityError, match="not namespace-reserved"):
        validate_authority_ref("economy.wallet.freeze", reserved)
    with pytest.raises(FormatError, match="kernel-reserved prefix"):
        validate_authority_ref("system.ops.reboot", reserved)


def test_validate_role_binding_forms():
    assert role_binding_name("role:verified_member") == "verified_member"
    with pytest.raises(FormatError, match="role_binding_malformed"):
        validate_authority_ref("role:")
    with pytest.raises(FormatError, match="role_binding_malformed"):
        validate_authority_ref("role:mod.team")
    validate_authority_ref("role:mods", reserved_role_bindings=frozenset({"mods"}))
    with pytest.raises(BadAuthorityError, match="not a declared"):
        validate_authority_ref("role:ghosts", reserved_role_bindings=frozenset({"mods"}))


def test_is_tier_sufficient_order_compare():
    assert is_tier_sufficient("administrator", "moderator")
    assert is_tier_sufficient("moderator", "moderator")
    assert not is_tier_sufficient("staff", "moderator")
    assert is_tier_sufficient("owner", "administrator")
    # unknown tokens rank as the lowest tier (shipped verbatim)
    assert is_tier_sufficient("mystery", "user")
    assert not is_tier_sufficient("mystery", "staff")
