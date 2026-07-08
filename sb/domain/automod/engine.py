"""The automod decision core (shipped services/automod_service.py rules as
PURE functions over supplied message facts — deterministic by design, the
go/no-go §3 injectable-clock lesson). The gateway feed (on_message) is the
message band's; this engine takes (history, message) and answers."""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["AutomodPolicy", "MessageFact", "evaluate", "load_policy"]

# shipped defaults, verbatim (services/automod_config.py)
DEFAULTS = {
    "enabled": False, "spam_enabled": False, "invites_enabled": False,
    "caps_enabled": False, "mentions_enabled": False,
    "cross_channel_spam_enabled": False, "duplicate_enabled": False,
    "spam_count": 5, "spam_window_seconds": 7, "caps_percent": 70,
    "mentions_count": 4, "cross_channel_spam_count": 4, "duplicate_count": 3,
}

_INVITE_TOKENS = ("discord.gg/", "discord.com/invite/", "discordapp.com/invite/")


@dataclass(frozen=True)
class AutomodPolicy:
    enabled: bool = False
    spam_enabled: bool = False
    invites_enabled: bool = False
    caps_enabled: bool = False
    mentions_enabled: bool = False
    cross_channel_spam_enabled: bool = False
    duplicate_enabled: bool = False
    spam_count: int = 5
    spam_window_seconds: int = 7
    caps_percent: int = 70
    mentions_count: int = 4
    cross_channel_spam_count: int = 4
    duplicate_count: int = 3
    exempt_roles: frozenset[int] = frozenset()
    exempt_channels: frozenset[int] = frozenset()


@dataclass(frozen=True)
class MessageFact:
    """One message's automod-relevant facts (adapter-normalized)."""

    user_id: int
    channel_id: int
    content: str
    at: float                            # epoch seconds (logical clock)
    mention_count: int = 0
    role_ids: frozenset[int] = field(default_factory=frozenset)


def _as_bool(v: object, d: bool) -> bool:
    if isinstance(v, bool):
        return v
    t = str(v).strip().lower()
    return True if t in ("1", "true", "yes", "on") else (
        False if t in ("0", "false", "no", "off") else d)


def _as_int(v: object, d: int) -> int:
    try:
        return int(str(v))
    except (TypeError, ValueError):
        return d


def _ids(v: object) -> frozenset[int]:
    out = set()
    for token in str(v or "").replace(";", ",").split(","):
        token = token.strip().lstrip("<#@&").rstrip(">")
        if token.isdigit():
            out.add(int(token))
    return frozenset(out)


async def load_policy(guild_id: int) -> AutomodPolicy:
    from sb.kernel.settings import resolve

    async def _get(name):
        return await resolve(guild_id, "automod", name)

    return AutomodPolicy(
        enabled=_as_bool(await _get("enabled"), False),
        spam_enabled=_as_bool(await _get("spam_enabled"), False),
        invites_enabled=_as_bool(await _get("invites_enabled"), False),
        caps_enabled=_as_bool(await _get("caps_enabled"), False),
        mentions_enabled=_as_bool(await _get("mentions_enabled"), False),
        cross_channel_spam_enabled=_as_bool(
            await _get("cross_channel_spam_enabled"), False),
        duplicate_enabled=_as_bool(await _get("duplicate_enabled"), False),
        spam_count=_as_int(await _get("spam_count"), 5),
        spam_window_seconds=_as_int(await _get("spam_window_seconds"), 7),
        caps_percent=_as_int(await _get("caps_percent"), 70),
        mentions_count=_as_int(await _get("mentions_count"), 4),
        cross_channel_spam_count=_as_int(
            await _get("cross_channel_spam_count"), 4),
        duplicate_count=_as_int(await _get("duplicate_count"), 3),
        exempt_roles=_ids(await _get("exempt_roles")),
        exempt_channels=_ids(await _get("exempt_channels")),
    )


def evaluate(message: MessageFact, history: tuple[MessageFact, ...],
             policy: AutomodPolicy) -> tuple[str, ...]:
    """Violation tags for one message given the user's recent history
    (shipped rule set: spam / invites / caps / mentions / cross-channel /
    duplicate). Empty tuple = clean. Pure; the caller owns enforcement."""
    if not policy.enabled:
        return ()
    if message.channel_id in policy.exempt_channels:
        return ()
    if message.role_ids & policy.exempt_roles:
        return ()
    tags: list[str] = []
    window = [m for m in history
              if m.user_id == message.user_id
              and message.at - m.at <= policy.spam_window_seconds]
    if policy.spam_enabled and len(window) + 1 >= policy.spam_count:
        tags.append("spam")
    if policy.cross_channel_spam_enabled:
        channels = {m.channel_id for m in window} | {message.channel_id}
        if len(channels) >= policy.cross_channel_spam_count:
            tags.append("cross_channel_spam")
    if policy.invites_enabled and any(
            token in message.content.lower() for token in _INVITE_TOKENS):
        tags.append("invites")
    if policy.caps_enabled:
        alpha = [c for c in message.content if c.isalpha()]
        if len(alpha) >= 10:
            caps = sum(1 for c in alpha if c.isupper())
            if caps * 100 >= policy.caps_percent * len(alpha):
                tags.append("caps")
    if policy.mentions_enabled and message.mention_count >= policy.mentions_count:
        tags.append("mentions")
    if policy.duplicate_enabled:
        dupes = sum(1 for m in window if m.content == message.content)
        if dupes + 1 >= policy.duplicate_count:
            tags.append("duplicate")
    return tuple(tags)
