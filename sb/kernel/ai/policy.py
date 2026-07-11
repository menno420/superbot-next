"""NL should-reply policy resolver (K10) — the single chokepoint answering
"should the bot reply?" for one inbound message.

Ported from shipped ``disbot/services/ai_natural_language_policy.py``
@7f7628e1 with the DB coupling cut: the shipped resolver read four tables
(``ai_guild_policy`` + channel/category/role policies) directly; here the
per-guild bundle arrives through the installable
:func:`install_policy_bundle_reader` port (the settings/AI band installs
the real settings-backed reader). The precedence rule itself is ported
verbatim — pure, trace-capable, side-effect-free:

    guild AI hard gate (enabled)
        → channel explicit mode → category explicit mode
        → guild natural-language baseline
        → role policy (explicit deny wins; most permissive level override)
        → level gate (+ fresh-user mention allowance)
        → (cooldown — enforced by the caller via :func:`is_on_cooldown`)

``mode='inherit'`` / missing row = "no opinion at this scope"; param
values at an inherit scope still apply (value-inheritance chain).

The cooldown + fresh-allowance BOOKKEEPING (shipped
``ai_permission_service``) also lives here: in-process, reset-seamed. The
K8 interaction cooldown keeps its fixed 5/60s AI axis as the outer rail;
THIS module owns the real per-guild policy (the S9 note's "AI band owns
real policy").
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from sb.kernel.ai.contracts import PolicyDenialReason

__all__ = [
    "MessageContext",
    "PolicyBundle",
    "PolicyDecision",
    "consume_fresh_allowance",
    "forget_guild_throttles",
    "fresh_allowance_remaining",
    "install_policy_bundle_reader",
    "is_on_cooldown",
    "mark_reply_sent",
    "reset_policy_for_tests",
    "resolve_policy",
]


# ---------------------------------------------------------------------------
# Inputs / outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MessageContext:
    """Minimal context the resolver needs about an inbound message."""

    guild_id: int
    channel_id: int
    category_id: int | None
    user_id: int
    user_level: int
    user_role_ids: tuple[int, ...]
    is_mention: bool
    is_fresh_user: bool


@dataclass(frozen=True)
class PolicyBundle:
    """One guild's policy tables, as the installed reader supplies them.

    ``policy`` mirrors the shipped ``ai_guild_policy`` row (keys consumed:
    ``enabled``, ``natural_language_enabled``, ``minimum_level_default``,
    ``cooldown_seconds``, ``guild_instruction_profile_id``,
    ``fresh_user_mention_allowance``, ``generation``). ``channel`` /
    ``category`` map ids → rows with optional ``mode`` /
    ``min_level`` / ``cooldown_seconds`` / ``instruction_profile_id``.
    ``role`` maps role ids → rows with ``decision`` (allow|deny|inherit),
    optional ``min_level_override``, ``bypass_cooldown``.
    """

    policy: Mapping[str, Any] | None
    channel: Mapping[int, Mapping[str, Any]] = field(default_factory=dict)
    category: Mapping[int, Mapping[str, Any]] = field(default_factory=dict)
    role: Mapping[int, Mapping[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyDecision:
    """Result of policy resolution. ``allowed`` is the sole signal callers
    need; ``reason_code`` is always populated (NONE sentinel on success).
    ``precedence_trace`` fills only under ``dry_run=True``.
    ``used_fresh_allowance``: the allow relied on the fresh-user mention
    allowance — the caller consumes one unit only when it actually sends a
    reply."""

    allowed: bool
    reason_code: PolicyDenialReason
    effective_min_level: int
    effective_cooldown: int
    effective_mode: str = ""
    effective_source: str = ""
    instruction_profile_ids: tuple[int, ...] = ()
    policy_snapshot_hash: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
    precedence_trace: tuple[str, ...] = ()
    used_fresh_allowance: bool = False


@dataclass(frozen=True)
class _EffectivePolicy:
    source: Literal["channel", "category", "guild"]
    mode: Literal["always_reply", "mention_only", "disabled"]
    min_level: int
    cooldown_seconds: int
    instruction_profile_ids: tuple[int, ...]


_DISABLED_REASON_BY_SOURCE: dict[str, PolicyDenialReason] = {
    "channel": PolicyDenialReason.CHANNEL_DISABLED,
    "category": PolicyDenialReason.CATEGORY_DISABLED,
    "guild": PolicyDenialReason.AI_NL_DISABLED_FOR_GUILD,
}


# ---------------------------------------------------------------------------
# Installable bundle reader (replaces the shipped 4-table read + cache; the
# real reader owns its own caching/invalidation against the settings seam)
# ---------------------------------------------------------------------------

PolicyBundleReader = Callable[[int], Awaitable[PolicyBundle]]

_bundle_reader: PolicyBundleReader | None = None


def install_policy_bundle_reader(reader: PolicyBundleReader) -> None:
    global _bundle_reader
    _bundle_reader = reader


async def _load_bundle(guild_id: int) -> PolicyBundle:
    if _bundle_reader is None:
        # No reader installed → behave like an unconfigured guild
        # (deny-by-default; an unconfigured deployment never silently
        # starts replying).
        return PolicyBundle(policy=None)
    return await _bundle_reader(guild_id)


# ---------------------------------------------------------------------------
# Cooldown + fresh-allowance bookkeeping (shipped ai_permission_service)
# ---------------------------------------------------------------------------

_LAST_REPLY_AT: dict[tuple[int, int], float] = defaultdict(float)
_FRESH_ALLOWANCE_USED: dict[tuple[int, int], int] = defaultdict(int)


def is_on_cooldown(guild_id: int, user_id: int, cooldown_seconds: int) -> bool:
    if cooldown_seconds <= 0:
        return False
    last = _LAST_REPLY_AT[(guild_id, user_id)]
    return (time.time() - last) < cooldown_seconds


def mark_reply_sent(guild_id: int, user_id: int) -> None:
    _LAST_REPLY_AT[(guild_id, user_id)] = time.time()


def fresh_allowance_remaining(guild_id: int, user_id: int, allowance: int) -> int:
    used = _FRESH_ALLOWANCE_USED[(guild_id, user_id)]
    return max(0, int(allowance) - used)


def consume_fresh_allowance(guild_id: int, user_id: int) -> None:
    _FRESH_ALLOWANCE_USED[(guild_id, user_id)] += 1


def forget_guild_throttles(guild_id: int) -> int:
    """Drop process-local cooldown + allowance entries for ``guild_id``
    (guild-lifecycle teardown; unbounded growth guard)."""
    removed = 0
    for tracker in (_LAST_REPLY_AT, _FRESH_ALLOWANCE_USED):
        drop = [key for key in tracker if key[0] == guild_id]
        for key in drop:
            del tracker[key]
        removed += len(drop)
    return removed


def reset_policy_for_tests() -> None:
    global _bundle_reader
    _bundle_reader = None
    _LAST_REPLY_AT.clear()
    _FRESH_ALLOWANCE_USED.clear()


# ---------------------------------------------------------------------------
# Resolution (precedence ported verbatim)
# ---------------------------------------------------------------------------


async def resolve_policy(ctx: MessageContext, *, dry_run: bool = False) -> PolicyDecision:
    """Run the precedence rule for ``ctx``. Pure read (no side effects on
    cooldown / audit state), so a dry-run is safe from an admin preview."""
    trace: list[str] | None = [] if dry_run else None
    bundle = await _load_bundle(ctx.guild_id)
    policy = dict(bundle.policy or {})

    if not bundle.policy:
        if trace is not None:
            trace.append(
                # the shipped trace byte verbatim (ai_natural_language_policy
                # @7f7628e1:211) — goldens/ai/sweep_ai_policy pins it.
                "guild_ai_gate: no ai_guild_policy row → deny GUILD_NOT_CONFIGURED",
            )
        return PolicyDecision(
            allowed=False,
            reason_code=PolicyDenialReason.GUILD_NOT_CONFIGURED,
            effective_min_level=2,
            effective_cooldown=30,
            policy_snapshot_hash=_hash({"missing": True}),
            precedence_trace=tuple(trace or ()),
        )

    if not policy.get("enabled"):
        if trace is not None:
            trace.append("guild_ai_gate: AI enabled=false → deny AI_GLOBALLY_DISABLED")
        return _deny(
            policy,
            reason=PolicyDenialReason.AI_GLOBALLY_DISABLED,
            min_level=int(policy.get("minimum_level_default", 2)),
            cooldown=int(policy.get("cooldown_seconds", 30)),
            trace=trace,
        )

    if trace is not None:
        trace.append("guild_ai_gate: AI enabled=true")

    # ---- Phase A: accumulate params (guild → category → channel) ----
    min_level = int(policy.get("minimum_level_default", 2))
    cooldown = int(policy.get("cooldown_seconds", 30))
    profile_ids: list[int] = []
    if policy.get("guild_instruction_profile_id"):
        profile_ids.append(int(policy["guild_instruction_profile_id"]))

    cat_row = bundle.category.get(ctx.category_id) if ctx.category_id else None
    cat_mode: str | None = None
    if cat_row:
        row_mode = cat_row.get("mode")
        if row_mode and row_mode != "inherit":
            cat_mode = row_mode
        if cat_row.get("min_level") is not None:
            min_level = int(cat_row["min_level"])
        if cat_row.get("cooldown_seconds") is not None:
            cooldown = int(cat_row["cooldown_seconds"])
        if cat_row.get("instruction_profile_id"):
            profile_ids.append(int(cat_row["instruction_profile_id"]))
        if trace is not None:
            trace.append(
                f"category_policy: mode={row_mode or 'inherit'} "
                f"min_level={min_level} cooldown={cooldown}s",
            )
    elif trace is not None and ctx.category_id is not None:
        trace.append(f"category_policy: no row for {ctx.category_id} (inherit)")

    chan_row = bundle.channel.get(ctx.channel_id)
    chan_mode: str | None = None
    if chan_row:
        row_mode = chan_row.get("mode")
        if row_mode and row_mode != "inherit":
            chan_mode = row_mode
        if chan_row.get("min_level") is not None:
            min_level = int(chan_row["min_level"])
        if chan_row.get("cooldown_seconds") is not None:
            cooldown = int(chan_row["cooldown_seconds"])
        if chan_row.get("instruction_profile_id"):
            profile_ids.append(int(chan_row["instruction_profile_id"]))
        if trace is not None:
            trace.append(
                f"channel_policy: mode={row_mode or 'inherit'} "
                f"min_level={min_level} cooldown={cooldown}s",
            )
    elif trace is not None:
        trace.append(f"channel_policy: no row for {ctx.channel_id} (inherit)")

    # ---- Phase B: select effective policy (most-specific-wins for mode) ----
    nl_enabled = bool(policy.get("natural_language_enabled"))
    baseline_mode: Literal["always_reply", "disabled"] = (
        "always_reply" if nl_enabled else "disabled"
    )
    if trace is not None:
        trace.append(
            f"guild_baseline: natural_language_enabled={nl_enabled} → "
            f"baseline mode={baseline_mode}",
        )

    effective: _EffectivePolicy
    if chan_mode is not None:
        effective = _EffectivePolicy(
            source="channel",
            mode=chan_mode,  # type: ignore[arg-type]
            min_level=min_level,
            cooldown_seconds=cooldown,
            instruction_profile_ids=tuple(profile_ids),
        )
    elif cat_mode is not None:
        effective = _EffectivePolicy(
            source="category",
            mode=cat_mode,  # type: ignore[arg-type]
            min_level=min_level,
            cooldown_seconds=cooldown,
            instruction_profile_ids=tuple(profile_ids),
        )
    else:
        effective = _EffectivePolicy(
            source="guild",
            mode=baseline_mode,
            min_level=min_level,
            cooldown_seconds=cooldown,
            instruction_profile_ids=tuple(profile_ids),
        )

    if trace is not None:
        trace.append(
            f"effective_policy: source={effective.source} mode={effective.mode} "
            f"min_level={effective.min_level} cooldown={effective.cooldown_seconds}s",
        )

    # ---- Mode gate ----
    if effective.mode == "disabled":
        reason = _DISABLED_REASON_BY_SOURCE[effective.source]
        if trace is not None:
            trace.append(f"mode_gate: mode=disabled → deny {reason.name}")
        return _deny(
            policy,
            reason=reason,
            min_level=effective.min_level,
            cooldown=effective.cooldown_seconds,
            profile_ids=list(effective.instruction_profile_ids),
            effective_mode=effective.mode,
            effective_source=effective.source,
            trace=trace,
        )
    if effective.mode == "mention_only" and not ctx.is_mention:
        if trace is not None:
            trace.append(
                "mode_gate: mode=mention_only and is_mention=false → "
                "deny NO_MENTION_REQUIRED",
            )
        return _deny(
            policy,
            reason=PolicyDenialReason.NO_MENTION_REQUIRED,
            min_level=effective.min_level,
            cooldown=effective.cooldown_seconds,
            profile_ids=list(effective.instruction_profile_ids),
            effective_mode=effective.mode,
            effective_source=effective.source,
            trace=trace,
        )
    if trace is not None:
        trace.append("mode_gate: allowed")

    # ---- Role gate ----
    role_decision = _resolve_role(bundle.role, ctx.user_role_ids)
    if role_decision["denied"]:
        if trace is not None:
            trace.append("role_gate: explicit deny → deny ROLE_DENIED")
        return _deny(
            policy,
            reason=PolicyDenialReason.ROLE_DENIED,
            min_level=effective.min_level,
            cooldown=effective.cooldown_seconds,
            profile_ids=list(effective.instruction_profile_ids),
            effective_mode=effective.mode,
            effective_source=effective.source,
            trace=trace,
        )

    gated_min_level = effective.min_level
    if role_decision["override_min_level"] is not None:
        candidate = int(role_decision["override_min_level"])
        gated_min_level = min(gated_min_level, candidate)
        if trace is not None:
            trace.append(
                f"role_gate: most-permissive override → min_level={gated_min_level}",
            )
    elif trace is not None:
        trace.append("role_gate: allowed")

    bypass_cooldown = role_decision["bypass_cooldown"]
    effective_cooldown = 0 if bypass_cooldown else effective.cooldown_seconds
    if trace is not None and bypass_cooldown:
        trace.append("role_gate: bypass_cooldown=true → effective_cooldown=0s")

    # ---- Level gate (XP / fresh-user allowance) ----
    used_fresh_allowance = False
    if ctx.user_level < gated_min_level:
        allowance = int(policy.get("fresh_user_mention_allowance", 0) or 0)
        remaining = fresh_allowance_remaining(ctx.guild_id, ctx.user_id, allowance)
        if ctx.is_fresh_user and ctx.is_mention and remaining > 0:
            used_fresh_allowance = True
            if trace is not None:
                trace.append(
                    f"level_gate: level={ctx.user_level} < min={gated_min_level} "
                    f"BUT fresh-user mention allowance ({remaining} left) → allowed",
                )
        else:
            if trace is not None:
                trace.append(
                    f"level_gate: level={ctx.user_level} < min={gated_min_level} → "
                    "deny BELOW_MIN_LEVEL",
                )
            return _deny(
                policy,
                reason=PolicyDenialReason.BELOW_MIN_LEVEL,
                min_level=gated_min_level,
                cooldown=effective_cooldown,
                profile_ids=list(effective.instruction_profile_ids),
                effective_mode=effective.mode,
                effective_source=effective.source,
                trace=trace,
            )
    elif trace is not None:
        trace.append(
            f"level_gate: level={ctx.user_level} ≥ min={gated_min_level} → allowed",
        )

    snapshot = _hash(
        {
            "g": policy.get("generation", 0),
            "min": gated_min_level,
            "cd": effective_cooldown,
            "profiles": list(effective.instruction_profile_ids),
            "allowed": True,
        },
    )
    if trace is not None:
        trace.append(
            f"final_decision: allowed min_level={gated_min_level} "
            f"cooldown={effective_cooldown}s",
        )
    return PolicyDecision(
        allowed=True,
        reason_code=PolicyDenialReason.NONE,
        effective_min_level=gated_min_level,
        effective_cooldown=effective_cooldown,
        effective_mode=effective.mode,
        effective_source=effective.source,
        instruction_profile_ids=effective.instruction_profile_ids,
        policy_snapshot_hash=snapshot,
        precedence_trace=tuple(trace or ()),
        used_fresh_allowance=used_fresh_allowance,
    )


def _deny(
    policy: Mapping[str, Any],
    *,
    reason: PolicyDenialReason,
    min_level: int,
    cooldown: int,
    profile_ids: list[int] | None = None,
    effective_mode: str = "",
    effective_source: str = "",
    trace: list[str] | None = None,
) -> PolicyDecision:
    return PolicyDecision(
        allowed=False,
        reason_code=reason,
        effective_min_level=int(min_level),
        effective_cooldown=int(cooldown),
        effective_mode=effective_mode,
        effective_source=effective_source,
        instruction_profile_ids=tuple(profile_ids or ()),
        policy_snapshot_hash=_hash(
            {"g": policy.get("generation", 0), "deny": reason.value},
        ),
        precedence_trace=tuple(trace or ()),
    )


def _resolve_role(
    role_table: Mapping[int, Mapping[str, Any]],
    user_role_ids: tuple[int, ...],
) -> dict[str, Any]:
    """Aggregate the user's roles: explicit deny short-circuits; among
    allows, the smallest ``min_level_override`` (most permissive) wins and
    ``bypass_cooldown`` flags OR together; inherit rows have no effect."""
    denied = False
    override: int | None = None
    bypass = False
    for role_id in user_role_ids:
        row = role_table.get(role_id)
        if not row:
            continue
        if row.get("decision") == "deny":
            denied = True
            break
        if row.get("decision") == "allow":
            if row.get("min_level_override") is not None:
                candidate = int(row["min_level_override"])
                override = candidate if override is None else min(override, candidate)
            if row.get("bypass_cooldown"):
                bypass = True
    return {
        "denied": denied,
        "override_min_level": override,
        "bypass_cooldown": bypass,
    }


def _hash(obj: Any) -> str:
    """Stable short hash for the audit snapshot column."""
    blob = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]
