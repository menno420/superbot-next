"""resolve_channel_access — the folded-in channel lane (spec 04 §3.4,
RC-4/RC-13, L-12 fix) + the R-16 per-channel role-set constraint."""

import asyncio
import dataclasses

from sb.kernel.authority.channel_access import (
    AccessMode,
    CommandAccessSnapshot,
    resolve_channel_access,
)
from sb.kernel.authority.decision import ChannelAccessDecision
from sb.spec.outcomes import DenialReason


def _run(policy, channel_id=1, **kw):
    kw.setdefault("owner_override", False)
    kw.setdefault("is_bootstrap", False)
    kw.setdefault("is_operator", False)
    kw.setdefault("is_owner", False)
    return asyncio.run(resolve_channel_access(policy, channel_id, **kw))


def test_access_mode_values_are_shipped_verbatim():
    assert AccessMode.ALL_CHANNELS.value == "all_channels"
    assert AccessMode.SELECTED_CHANNELS.value == "selected_channels"
    assert AccessMode.DISABLED_EXCEPT_BOOTSTRAP.value == "disabled_except_bootstrap"
    # name-stable to the DB CHECK constraint: no migration needed
    assert AccessMode("all_channels") is AccessMode.ALL_CHANNELS


def test_decision_is_the_canonical_8_field_shape():
    assert [f.name for f in dataclasses.fields(ChannelAccessDecision)] == [
        "allowed", "mode", "reason", "detail", "owner_override",
        "bootstrap_bypass", "would_deny_without_override", "denial_message",
    ]  # RC-13: 04's 8-field form (adds detail) is canonical


def test_unconfigured_and_all_channels_allow():
    assert _run(None).allowed
    assert _run(CommandAccessSnapshot()).allowed
    assert _run(CommandAccessSnapshot(mode="all_channels")).allowed


def test_disabled_except_bootstrap_denies_with_detail():
    d = _run(CommandAccessSnapshot(mode="disabled_except_bootstrap"))
    assert not d.allowed and d.reason is DenialReason.CHANNEL
    assert d.detail == "commands_disabled" and d.denial_message


def test_selected_channels_hit_and_miss():
    policy = CommandAccessSnapshot(mode="selected_channels",
                                   allowed_channels=frozenset({1, 2}))
    assert _run(policy, channel_id=2).allowed
    miss = _run(policy, channel_id=3)
    assert not miss.allowed and miss.detail == "channel_not_allowed"


def test_owner_override_bypasses_any_restriction_l12_fix():
    policy = CommandAccessSnapshot(mode="disabled_except_bootstrap")
    d = _run(policy, owner_override=True)
    assert d.allowed and d.owner_override and not d.bootstrap_bypass
    assert d.would_deny_without_override  # transparency input


def test_bootstrap_bypass_operator_and_owner_legs():
    policy = CommandAccessSnapshot(mode="disabled_except_bootstrap")
    op = _run(policy, is_bootstrap=True, is_operator=True)
    assert op.allowed and op.bootstrap_bypass
    ow = _run(policy, is_bootstrap=True, is_owner=True)
    assert ow.allowed and ow.bootstrap_bypass
    nobody = _run(policy, is_bootstrap=True)
    assert not nobody.allowed
    non_bootstrap = _run(policy, is_operator=True)
    assert not non_bootstrap.allowed  # bypass is bootstrap-commands-only


def test_role_set_constraint_r16_under_all_channels():
    policy = CommandAccessSnapshot(
        mode="all_channels",
        channel_role_sets={7: frozenset({100})},
    )
    held = _run(policy, channel_id=7, actor_role_ids=frozenset({100, 5}))
    assert held.allowed
    miss = _run(policy, channel_id=7, actor_role_ids=frozenset({5}))
    assert not miss.allowed and miss.detail == "role_not_held"
    assert miss.reason is DenialReason.CHANNEL  # NOT a 4th AccessMode
    other_channel = _run(policy, channel_id=8, actor_role_ids=frozenset())
    assert other_channel.allowed  # unconstrained channel


def test_role_set_constraint_overridden_by_owner_and_bootstrap():
    policy = CommandAccessSnapshot(channel_role_sets={7: frozenset({100})})
    assert _run(policy, channel_id=7, owner_override=True).allowed
    assert _run(policy, channel_id=7, is_bootstrap=True, is_operator=True).allowed
