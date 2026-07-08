"""The step-3 cooldown charge (frozen L0 spec 02 §3.2/§5 — CONSUMED shape).

In-memory, resets on restart — identical to shipped behavior; a durable
cooldown store is the explicit deferral (02 §9). `CooldownSpec` is consumed
duck-typed: a bare number (seconds between uses, per-user — the conftest/G-4
scalar form) or an object with `rate`/`per_s`/`scope ∈ {user, guild,
channel}`. The AI-throttle is a DISTINCT axis charged by the NL rungs.

Refund rule (02 §3.2, fork D): refund iff `error_class ∈ {transient, bug}`;
kept on SUCCESS/PARTIAL, user_error, and a DECLINED confirm.
"""

from __future__ import annotations

import time
from collections import deque

__all__ = ["charge", "refund", "reset_for_tests"]

_buckets: dict[tuple, deque] = {}
# the AI-throttle axis: (guild_id, user_id) -> deque of charge times
_AI_RATE, _AI_PER_S = 5, 60.0


def _spec_params(cooldown: object) -> tuple[int, float, str]:
    if isinstance(cooldown, (int, float)):
        return 1, float(cooldown), "user"
    return (int(getattr(cooldown, "rate", 1) or 1),
            float(getattr(cooldown, "per_s", 0.0) or 0.0),
            str(getattr(cooldown, "scope", "user") or "user"))


def _scope_key(scope: str, *, target_key: str, guild_id, channel_id, user_id) -> tuple:
    if scope == "guild":
        return (target_key, "guild", guild_id)
    if scope == "channel":
        return (target_key, "channel", guild_id, channel_id)
    return (target_key, "user", guild_id, user_id)


def charge(cooldown: object, *, target_key: str, guild_id, channel_id,
           user_id, ai_axis: bool = False,
           now: float | None = None) -> tuple[bool, float]:
    """Charge one token. Returns (allowed, retry_after_s)."""
    t = now if now is not None else time.monotonic()
    allowed, retry = True, 0.0
    if cooldown is not None:
        rate, per_s, scope = _spec_params(cooldown)
        if per_s > 0:
            key = _scope_key(scope, target_key=target_key, guild_id=guild_id,
                             channel_id=channel_id, user_id=user_id)
            q = _buckets.setdefault(key, deque())
            while q and t - q[0] >= per_s:
                q.popleft()
            if len(q) >= rate:
                allowed, retry = False, per_s - (t - q[0])
            else:
                q.append(t)
    if allowed and ai_axis:
        key = ("__ai__", guild_id, user_id)
        q = _buckets.setdefault(key, deque())
        while q and t - q[0] >= _AI_PER_S:
            q.popleft()
        if len(q) >= _AI_RATE:
            allowed, retry = False, _AI_PER_S - (t - q[0])
        else:
            q.append(t)
    return allowed, max(retry, 0.0)


def refund(cooldown: object, *, target_key: str, guild_id, channel_id,
           user_id) -> None:
    """Pop the most recent charge (transient/bug — not the actor's fault)."""
    if cooldown is None:
        return
    _rate, per_s, scope = _spec_params(cooldown)
    if per_s <= 0:
        return
    key = _scope_key(scope, target_key=target_key, guild_id=guild_id,
                     channel_id=channel_id, user_id=user_id)
    q = _buckets.get(key)
    if q:
        q.pop()


def reset_for_tests() -> None:
    _buckets.clear()
