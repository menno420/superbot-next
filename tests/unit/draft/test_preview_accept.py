"""S10: T2-5 confirmation rule, challenge verification, and the
AND-over-distinct-refs accept gate (frozen L0 spec 06 §3.3/§3.4)."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone

import pytest

from sb.kernel.authority.decision import AuthorityDecision, AuthorityRequest
from sb.kernel.draft.accept import derive_accept_authority, resolve_draft_accept
from sb.kernel.draft.preview import (
    DraftConfirmationSpec,
    preview_hash_of,
    requires_confirmation,
    verify_confirmation,
)
from sb.spec.authority import Lane
from sb.spec.draft import (
    ConfirmChallenge,
    ConfirmationResponse,
    Draft,
    DraftOperation,
    DraftStatus,
    OwnerScope,
    Producer,
)
from sb.spec.outcomes import DenialReason

run = asyncio.run
NOW = datetime(2026, 7, 8, tzinfo=timezone.utc)


def op(seq=1, op_kind="set_setting", authority_ref="settings.manage", **kw):
    defaults = dict(subsystem="logging", payload={"k": "v"}, label="set x")
    defaults.update(kw)
    return DraftOperation(op_seq=seq, op_kind=op_kind,
                          authority_ref=authority_ref, **defaults)


def draft(ops, producer=Producer.HUMAN_SETUP):
    return Draft(draft_id="d1", producer=producer,
                 owner_scope=OwnerScope(guild_id=42, actor_id=7),
                 status=DraftStatus.OPEN, operations=tuple(ops),
                 created_at=NOW, updated_at=NOW, correlation_id="d1")


def test_requires_confirmation_t2_5():
    d1 = draft([op()])
    assert not requires_confirmation(d1, "reversible", 1)   # single reversible direct-lane
    assert requires_confirmation(draft([op()], Producer.AI_ORCHESTRATION),
                                  "reversible", 1)          # AI-produced
    assert requires_confirmation(d1, "irreversible", 1)     # destructive
    assert requires_confirmation(d1, "reversible", 2)       # bulk/compound


def test_verify_confirmation_fail_closed():
    button = DraftConfirmationSpec(reversibility="reversible",
                                   challenge=ConfirmChallenge.BUTTON)
    assert verify_confirmation(button, ConfirmationResponse(ConfirmChallenge.BUTTON))
    assert not verify_confirmation(button, None)
    assert not verify_confirmation(
        button, ConfirmationResponse(ConfirmChallenge.TYPED_PHRASE, "x"))

    phrase = DraftConfirmationSpec(reversibility="irreversible",
                                   challenge=ConfirmChallenge.TYPED_PHRASE,
                                   expected_phrase="apply d1")
    assert verify_confirmation(phrase, ConfirmationResponse(
        ConfirmChallenge.TYPED_PHRASE, "apply d1"))
    assert not verify_confirmation(phrase, ConfirmationResponse(
        ConfirmChallenge.TYPED_PHRASE, "apply d2"))

    hashed = DraftConfirmationSpec(
        reversibility="irreversible", challenge=ConfirmChallenge.TYPED_HASH,
        expected_hash=hashlib.sha256(b"wipe").hexdigest())
    assert verify_confirmation(hashed, ConfirmationResponse(
        ConfirmChallenge.TYPED_HASH, "wipe"))
    assert not verify_confirmation(hashed, ConfirmationResponse(
        ConfirmChallenge.TYPED_HASH, "nope"))


def test_preview_hash_pins_the_op_set():
    d = draft([op()])
    h1 = preview_hash_of(d)
    assert h1 == preview_hash_of(d)                       # stable
    d2 = draft([op(), op(seq=2, op_kind="bind_channel",
                         authority_ref="logging.manage")])
    assert preview_hash_of(d2) != h1                      # op set changed


def test_derive_accept_authority_display_floor():
    homogeneous = (op(), op(seq=2))
    assert derive_accept_authority(homogeneous) == "settings.manage"
    mixed = (op(), op(seq=2, authority_ref="moderator"))
    assert derive_accept_authority(mixed) == "administrator"   # max tier floor
    assert derive_accept_authority(()) == ""


def _decision(allowed, ref):
    return AuthorityDecision(
        allowed=allowed, authority_ref=ref, lane=Lane.CAPABILITY,
        required_tier="administrator", member_tier="administrator",
        owner_override=False, lane_would_deny=not allowed,
        reason=DenialReason.ALLOWED if allowed else DenialReason.AUTHORITY,
        detail="", denial_message=None if allowed else "denied: " + ref)


def test_resolve_draft_accept_and_over_distinct_refs_veto():
    """A revoke overlay on ANY single ref vetoes the whole draft."""
    seen = []

    async def resolver(req):
        seen.append(req.authority_ref)
        return _decision(req.authority_ref != "governance.setup.apply",
                         req.authority_ref)

    d = draft([op(), op(seq=2, authority_ref="governance.setup.apply"),
               op(seq=3, authority_ref="settings.manage")])
    req = AuthorityRequest(authority_ref="", actor_type="user", user_id=7,
                           guild_id=42, is_member=True,
                           member_tier="administrator", role_ids=frozenset())
    decision = run(resolve_draft_accept(d, req, resolver=resolver))
    assert not decision.allowed
    assert decision.denial_message == "denied: governance.setup.apply"
    assert seen == ["governance.setup.apply"]   # first denial wins — short-circuit

    async def allow_all(req):
        return _decision(True, req.authority_ref)
    decision = run(resolve_draft_accept(d, req, resolver=allow_all))
    assert decision.allowed
