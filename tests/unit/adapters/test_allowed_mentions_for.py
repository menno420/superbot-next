"""`allowed_mentions_for` — the S11 default-deny mass-ping fence (spec 10
§2.A/§8.1).

`sb/adapters/discord/egress.py:allowed_mentions_for` is the ONLY module that
constructs `discord.AllowedMentions`, computed purely from
`(trust, allow_mentions)`. The existing e2e coverage
(`tests/e2e/test_egress_trust_policy_e2e.py`) exercises only the `none()` path
and a single `user:` token; the **mention-OPENING** branches (`everyone`/`here`
and `role:`) — the only ones that can authorize a ping — plus the trust fence
that must override an explicit allowlist are covered HERE, as a pure unit test
directly on the transform.

discord is import-guarded in CI containers; where it is absent the function
raises `RuntimeError` and these tests skip. Every assertion below was verified
against a live run of the real function.
"""

from __future__ import annotations

import pytest

from sb.adapters.discord.egress import allowed_mentions_for
from sb.kernel.interaction.egress import OutboundContent, TrustLevel

discord = pytest.importorskip("discord")


def _am(trust: TrustLevel, allow_mentions: tuple[str, ...]):
    return allowed_mentions_for(
        OutboundContent(body="x", trust=trust, allow_mentions=allow_mentions))


def _is_none_equivalent(am) -> bool:
    """discord.AllowedMentions.none() = everyone/roles/users/replied all False."""
    return (am.everyone, am.roles, am.users, am.replied_user) == (
        False, False, False, False)


# --- the mention-OPENING branches (the only paths that authorize a ping) -----

@pytest.mark.parametrize("token", ["everyone", "here"])
def test_everyone_and_here_open_everyone_only(token: str) -> None:
    """`everyone` OR `here` sets everyone=True; roles/users stay denied.
    `here` is a distinct token that lands on the SAME everyone flag (there is
    no separate here field in discord.AllowedMentions)."""
    am = _am(TrustLevel.TRUSTED, (token,))
    assert am.everyone is True
    assert am.roles is False
    assert am.users is False
    assert am.replied_user is False


def test_role_tokens_map_to_object_ids() -> None:
    """`role:<id>` tokens become real discord.Object(id) entries; everyone
    stays denied and the `roles or False` fallback is not taken."""
    am = _am(TrustLevel.TRUSTED, ("role:123", "role:456"))
    assert am.everyone is False
    assert am.users is False
    assert [type(o) for o in am.roles] == [discord.Object, discord.Object]
    assert [o.id for o in am.roles] == [123, 456]


def test_mixed_everyone_role_user_all_honored() -> None:
    """everyone + role + user in one allowlist are honored simultaneously —
    each token class routed to its own field."""
    am = _am(TrustLevel.SYSTEM, ("everyone", "role:5", "user:9"))
    assert am.everyone is True
    assert [o.id for o in am.roles] == [5]
    assert [o.id for o in am.users] == [9]
    assert am.replied_user is False


# --- the default-deny fences ------------------------------------------------

def test_trusted_empty_allowlist_is_none_equivalent() -> None:
    """A TRUSTED sender with an EMPTY allowlist collapses to none() — the
    `not content.allow_mentions` short-circuit, distinct from the trust fence."""
    assert _is_none_equivalent(_am(TrustLevel.TRUSTED, ()))


@pytest.mark.parametrize("trust", [TrustLevel.TRUSTED, TrustLevel.SYSTEM])
def test_trusted_here_and_role_are_honored_not_denied(trust: TrustLevel) -> None:
    """Guard the fence isn't over-broad: a TRUSTED/SYSTEM sender's explicit
    allowlist really does open — regression here would silently mute all
    legitimate pings."""
    assert _am(trust, ("here",)).everyone is True
    assert [o.id for o in _am(trust, ("role:7",)).roles] == [7]


def test_untrusted_everyone_allowlist_still_denied() -> None:
    """THE fence: an UNTRUSTED sender that carries an explicit ("everyone",)
    allowlist STILL collapses to none(). Trust wins over the allowlist — this
    guards against a refactor to `UNTRUSTED and not allow_mentions`, which
    would leak @everyone to untrusted content."""
    assert _is_none_equivalent(_am(TrustLevel.UNTRUSTED, ("everyone",)))


def test_untrusted_role_and_user_allowlist_still_denied() -> None:
    """The fence holds for role/user tokens too: UNTRUSTED denies regardless of
    what the allowlist asks for."""
    assert _is_none_equivalent(
        _am(TrustLevel.UNTRUSTED, ("role:1", "user:2", "here")))
