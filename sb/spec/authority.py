"""The authority grammar leaf (K6, frozen L0 spec 04 §3.2/§3.6 — RC-3).

Dependency-free (stdlib only) so the compiler (01 P4) and the namespace import
it with no cycle. Owns: the ``Lane`` enum, the tier order (``TIERS``, ported
``utils/visibility_rules.py:21``), ``ADMIN_FLOOR_TIER``, the total
non-overlapping ``classify_authority_ref``, the compile-time
``validate_authority_ref`` (P4's seam), and the pure tier-string order compare
``is_tier_sufficient`` (ported ``visibility_rules.py:61``).

A-12 / rider R-16 (canonical plan §11b — the K6/S7 fold): ``Lane.ROLE_SET``
lands alongside CAPABILITY/TIER with the namespaced ref form
``role:<binding_name>`` — classified BY PREFIX, *before* the dot rule, so the
classifier stays total. Refs name a declared role BINDING (BindingKind.ROLE),
never literal role IDs (specs are guild-agnostic). R-2's role-bound /
dual-permission-floor legs are expressible through the TIER + ROLE_SET lanes
(the classifier is amended exactly once, here); R-2's resource-owner clause
carries no frozen grammar yet and is a labeled deferral to the ticket /
moderation port bands (see ledger D-0009 — NOT decided here).

The ONE manifest [S] field this grammar governs is ``authority_ref: str`` on
the six authority-bearing spec types (CommandSpec / PanelActionSpec /
SelectorSpec / SettingSpec / BindingSpec / ResourceRequirement — Q-0237d);
those types absorb the field when they are cut (S9+).
"""

from __future__ import annotations

import enum

__all__ = [
    "ADMIN_FLOOR_TIER",
    "ROLE_REF_PREFIX",
    "TIERS",
    "TIER_DISCORD_PERMISSION",
    "BadAuthorityError",
    "FormatError",
    "Lane",
    "classify_authority_ref",
    "is_tier_sufficient",
    "role_binding_name",
    "validate_authority_ref",
]


class Lane(enum.Enum):
    """The authority lane an ``authority_ref`` classifies to (RC-3 — this
    enum, NOT spec 02's retired ``AuthorityLane``; ``CAPABILITY`` ≡ 02's
    ``CONFIG_GOVERNANCE`` ⇒ EPHEMERAL default, ``TIER`` ≡ ``DOMAIN`` ⇒ PUBLIC).
    ``ROLE_SET`` is the A-12/R-16 role-scoped lane (guild-configured role
    binding; lane default follows CAPABILITY's EPHEMERAL posture)."""

    CAPABILITY = "capability"
    TIER = "tier"
    ROLE_SET = "role_set"


# The shipped 6-tier ladder, verbatim order (visibility_rules.py:21).
TIERS: tuple[str, ...] = (
    "user",
    "trusted",       # reserved for a future trust/progression system
    "staff",
    "moderator",
    "administrator",
    "owner",
)

_TIER_INDEX: dict[str, int] = {tier: i for i, tier in enumerate(TIERS)}

# tier -> Discord guild_permissions attribute (None = no permission bit).
# Ported verbatim (visibility_rules.py TIER_DISCORD_PERMISSION); read by the
# K8 surface adapter's member-tier computation (RC-12) — the KERNEL never
# reads it (the tier arrives pre-computed on AuthorityRequest.member_tier).
TIER_DISCORD_PERMISSION: dict[str, str | None] = {
    "user": None,
    "trusted": None,
    "staff": "manage_guild",
    "moderator": "moderate_members",
    "administrator": "administrator",
    "owner": None,  # resolved by member.id == guild.owner_id
}

# The administrator floor preserved from the shipped mutation pipelines
# (capability.py:48-51 _DEFAULT_REQUIRED_TIER). v1 keeps a single floor for
# every CAPABILITY-lane ref; a future capability->tier matrix replaces the
# constant with a lookup without touching the classifier (spec 04 §3.2/§9).
ADMIN_FLOOR_TIER = "administrator"

# R-16: the role-scoped ref prefix, classified BEFORE the dot rule.
ROLE_REF_PREFIX = "role:"


class BadAuthorityError(ValueError):
    """An ``authority_ref`` that classifies to no lane (compiler P4 →
    ``bad_authority`` / COMPILE_ERROR)."""


class FormatError(BadAuthorityError):
    """A ref that classified to a lane but fails that lane's format rule
    (e.g. ``capability_not_3_part`` — spec 04 §3.2)."""


def classify_authority_ref(ref: str) -> Lane:
    """The total, non-overlapping, PURE SYNTACTIC classifier (spec 04 §3.2,
    pinned; amended once by R-16 — the ``role:`` prefix rule runs before the
    dot rule so the three-way split stays total).

    - ``""`` (empty)            => CAPABILITY (ADMIN floor — capability.py:27
                                   "empty resolves to the floor, NOT no-auth")
    - ``role:<binding_name>``   => ROLE_SET (R-16; prefix beats the dot rule)
    - ANY dotted string         => CAPABILITY (arity checked at validate, not
                                   here — classify never raises on arity)
    - exact tier token          => TIER (case-sensitive; TIERS are lowercase)
    - anything else             => BadAuthorityError (unclassifiable)
    """
    if ref == "":
        return Lane.CAPABILITY
    if ref.startswith(ROLE_REF_PREFIX):
        return Lane.ROLE_SET
    if "." in ref:
        return Lane.CAPABILITY
    if ref in TIERS:
        return Lane.TIER
    raise BadAuthorityError(
        f"authority_ref {ref!r} is neither empty, role:-prefixed, dotted, "
        f"nor a tier token in {TIERS}"
    )


def role_binding_name(ref: str) -> str:
    """The declared binding name inside a ROLE_SET ref (``role:<name>``)."""
    return ref[len(ROLE_REF_PREFIX):]


def validate_authority_ref(
    ref: str,
    reserved_capabilities: frozenset[str] | None = None,
    *,
    reserved_role_bindings: frozenset[str] | None = None,
) -> None:
    """The compile-time validator — the compiler P4 seam
    (``authority.validate(ref) -> None | raise``, spec 04 §3.6).

    Check order mirrors the pinned classifier: (1) classify — a raise here is
    ``bad_authority``; (2) CAPABILITY and non-empty ⇒ exactly 3 dotted parts
    (else ``FormatError("capability_not_3_part")``), then, when a reservation
    corpus is supplied, membership + the reserved-prefix rule
    (``_internal.*``/``system.*``/``governance.*`` heads are kernel-reserved,
    subsystem_registry.py:7 ported); (3) ROLE_SET ⇒ non-empty binding name,
    dot-free (a binding name, not a path), plus corpus membership when
    supplied; (4) TIER needs nothing further (classify guaranteed it).

    ``reserved_capabilities=None`` / ``reserved_role_bindings=None`` = "no
    corpus available" (compile passes P4 with format checks only — the K1
    capability/binding reservation sets are threaded once manifests exist).
    """
    lane = classify_authority_ref(ref)  # raises BadAuthorityError

    if lane is Lane.CAPABILITY and ref != "":
        parts = ref.split(".")
        if len(parts) != 3 or not all(parts):
            raise FormatError(f"capability_not_3_part: {ref!r}")
        if reserved_capabilities is not None:
            head = parts[0]
            if head in ("_internal", "system", "governance"):
                raise FormatError(
                    f"capability head {head!r} is a kernel-reserved prefix: {ref!r}"
                )
            if ref not in reserved_capabilities:
                raise BadAuthorityError(
                    f"capability {ref!r} is not namespace-reserved (K1 P3)"
                )
    elif lane is Lane.ROLE_SET:
        name = role_binding_name(ref)
        if not name or "." in name or ":" in name:
            raise FormatError(f"role_binding_malformed: {ref!r}")
        if reserved_role_bindings is not None and name not in reserved_role_bindings:
            raise BadAuthorityError(
                f"role binding {name!r} is not a declared BindingKind.ROLE binding"
            )


def is_tier_sufficient(member_tier: str, required_tier: str) -> bool:
    """True iff ``member_tier`` is at least as high as ``required_tier`` —
    the pure order compare over TIER STRINGS (ported visibility_rules.py:61;
    unknown tokens rank as the lowest tier, verbatim)."""
    return _TIER_INDEX.get(member_tier, 0) >= _TIER_INDEX.get(required_tier, 0)
